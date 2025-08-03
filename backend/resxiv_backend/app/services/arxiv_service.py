"""
arXiv Service Module

This module provides comprehensive arXiv functionality including:
- Paper search with abstracts and metadata
- TLDR generation from abstracts
- Related papers via subject classifications
- Author analysis and paper recommendations

All functionality is consolidated in this single service file.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import quote
import time
import re
import xml.etree.ElementTree as ET

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from .research_agent_core import (
    BaseResearchService, SearchQuery, SearchResponse, Paper, Author,
    DataSource, RateLimitConfig, ResearchServiceError
)

logger = logging.getLogger(__name__)


class ArXivService(BaseResearchService):
    """
    Comprehensive arXiv service for academic paper search and analysis
    
    Provides complete arXiv functionality including paper search, TLDR generation,
    and semantic analysis using subject classifications.
    """
    
    def __init__(self):
        """Initialize arXiv service"""
        super().__init__(
            base_url="http://export.arxiv.org/api",
            rate_limit_config=RateLimitConfig(
                requests_per_second=3.0,  # arXiv rate limit
                requests_per_minute=180,
                requests_per_hour=1000
            )
        )
        
        # arXiv subject classifications for finding related papers
        self.subject_classifications = {
            'cs.AI': 'Artificial Intelligence',
            'cs.CL': 'Computation and Language (NLP)',
            'cs.CV': 'Computer Vision and Pattern Recognition',
            'cs.LG': 'Machine Learning',
            'cs.NE': 'Neural and Evolutionary Computing',
            'cs.RO': 'Robotics',
            'stat.ML': 'Machine Learning (Statistics)',
            'math.OC': 'Optimization and Control',
            'physics.data-an': 'Data Analysis, Statistics and Probability'
        }
    
    async def search_papers(
        self,
        query: SearchQuery,
        subject_class: Optional[str] = None,
        include_abstracts: bool = True
    ) -> SearchResponse:
        """
        Search for papers on arXiv with full abstracts and metadata
        
        Args:
            query: Search query parameters
            subject_class: arXiv subject classification filter
            include_abstracts: Include full abstracts for TLDR generation
            
        Returns:
            SearchResponse with Paper objects containing abstracts
        """
        start_time = time.time()
        
        try:
            # Build precise search query focused on title and abstract fields
            base_query = query.query.strip()
            
            # Remove common non-research terms that pollute ArXiv searches
            stop_words = {
                'latest', 'recent', 'new', 'papers', 'research', 'study', 'work', 'article',
                'find', 'me', 'show', 'get', 'search', 'for', 'in', 'on', 'of', 'the', 'and'
            }
            
            # Extract meaningful search terms
            words = base_query.lower().split()
            meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
            
            # If we have meaningful terms, use them; otherwise fall back to original
            if meaningful_words:
                # For multi-term queries, prefer title and abstract field searches
                if len(meaningful_words) == 1:
                    # Single term - search in title and abstract for better precision
                    search_string = f'(ti:"{meaningful_words[0]}" OR abs:"{meaningful_words[0]}")'
                elif len(meaningful_words) == 2:
                    # Two terms - search for both in title or both in abstract
                    term1, term2 = meaningful_words[0], meaningful_words[1]
                    search_string = f'(ti:"{term1}" AND ti:"{term2}") OR (abs:"{term1}" AND abs:"{term2}")'
                else:
                    # Multiple terms - build focused query with first 3 terms
                    core_terms = meaningful_words[:3]
                    title_query = ' AND '.join(f'ti:"{term}"' for term in core_terms)
                    abs_query = ' AND '.join(f'abs:"{term}"' for term in core_terms)
                    search_string = f'({title_query}) OR ({abs_query})'
            else:
                # Fallback to original query with field targeting
                search_string = f'(ti:"{base_query}" OR abs:"{base_query}")'
            
            # Add subject classification if provided
            if subject_class:
                search_string = f'({search_string}) AND cat:{subject_class}'
            
            logger.info(f"ArXiv search string: {search_string}")
            
            # Build parameters
            params = {
                'search_query': search_string,
                'start': query.offset,
                'max_results': min(query.limit, 100),  # arXiv limit
                'sortBy': 'relevance' if query.sort_by.value == 'relevance' else 'lastUpdatedDate',
                'sortOrder': 'descending'
            }
            
            # Make XML request (arXiv returns XML, not JSON)
            response_text = await self._make_xml_request(
                method="GET",
                url=f"{self.base_url}/query",
                params=params
            )
            
            # Parse XML response
            papers = self._parse_arxiv_response(response_text, include_abstracts)
            
            return SearchResponse(
                success=True,
                query=query.query,
                data_source=DataSource.ARXIV,
                total_results=len(papers),  # arXiv doesn't provide total count
                returned_results=len(papers),
                offset=query.offset,
                results=papers,
                execution_time=time.time() - start_time,
                metadata={
                    'subject_classification': subject_class,
                    'abstracts_included': include_abstracts,
                    'source': 'arxiv'
                }
            )
            
        except Exception as e:
            logger.error(f"arXiv search failed: {str(e)}")
            return SearchResponse(
                success=False,
                query=query.query,
                data_source=DataSource.ARXIV,
                total_results=0,
                returned_results=0,
                offset=query.offset,
                results=[],
                execution_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
    
    async def get_paper_details(self, arxiv_id: str) -> Dict[str, Any]:
        """
        Get detailed paper information by arXiv ID
        
        Args:
            arxiv_id: arXiv paper ID
            
        Returns:
            Detailed paper information with TLDR
        """
        try:
            # Get paper details
            params = {'id_list': arxiv_id}
            response_text = await self._make_xml_request(
                method="GET",
                url=f"{self.base_url}/query",
                params=params
            )
            
            # Parse response
            papers = self._parse_arxiv_response(response_text, include_abstracts=True)
            
            if papers:
                paper = papers[0]
                # Generate TLDR from abstract
                tldr = self._generate_tldr_from_abstract(paper.abstract)
                
                return {
                    'success': True,
                    'paper': paper,
                    'tldr': tldr,
                    'arxiv_id': arxiv_id,
                    'pdf_url': paper.pdf_url,
                    'subjects': paper.topics
                }
            else:
                return {'success': False, 'error': 'Paper not found'}
                
        except Exception as e:
            logger.error(f"Failed to get arXiv paper details for {arxiv_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_paper_tldr(self, arxiv_id: str) -> Dict[str, Any]:
        """
        Get paper TLDR using arXiv abstract
        
        Args:
            arxiv_id: arXiv paper ID
            
        Returns:
            Paper TLDR and highlights
        """
        try:
            paper_details = await self.get_paper_details(arxiv_id)
            
            if paper_details.get('success'):
                paper = paper_details['paper']
                return {
                    'success': True,
                    'paper_id': arxiv_id,
                    'title': paper.title,
                    'tldr': paper_details['tldr'],
                    'abstract': paper.abstract,
                    'authors': [author.name for author in paper.authors],
                    'subjects': paper.topics,
                    'publication_date': paper.publication_date.isoformat() if paper.publication_date else None,
                    'pdf_url': paper.pdf_url
                }
            else:
                return paper_details
                
        except Exception as e:
            logger.error(f"Failed to get arXiv TLDR for {arxiv_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_related_papers(
        self,
        arxiv_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get related papers using arXiv subject classifications
        
        Args:
            arxiv_id: arXiv paper ID
            limit: Number of related papers to return
            
        Returns:
            List of related papers based on subject classifications
        """
        try:
            # First get the paper to extract subjects
            paper_details = await self.get_paper_details(arxiv_id)
            
            if not paper_details.get('success'):
                return {'success': False, 'error': 'Source paper not found'}
            
            source_paper = paper_details['paper']
            subjects = source_paper.topics
            
            if not subjects:
                return {'success': False, 'error': 'No subject classifications found'}
            
            # Search for papers in the same subjects
            related_papers = []
            for subject in subjects[:3]:  # Use top 3 subjects
                search_query = SearchQuery(
                    query=f'cat:{subject}',
                    limit=limit // len(subjects[:3]) + 5
                )
                
                # Search papers in this subject
                subject_papers = await self.search_papers(
                    search_query, 
                    subject_class=subject,
                    include_abstracts=False
                )
                
                if subject_papers.success:
                    # Filter out the source paper
                    for paper in subject_papers.results:
                        if paper.arxiv_id != arxiv_id and len(related_papers) < limit:
                            related_papers.append({
                                'id': paper.arxiv_id,
                                'title': paper.title,
                                'authors': [a.name for a in paper.authors],
                                'abstract': paper.abstract,
                                'subjects': paper.topics,
                                'publication_date': paper.publication_date.isoformat() if paper.publication_date else None,
                                'similarity_reason': f'Shared subject: {subject}',
                                'pdf_url': paper.pdf_url
                            })
            
            return {
                'success': True,
                'source_paper_id': arxiv_id,
                'source_subjects': subjects,
                'related_papers': related_papers[:limit],
                'count': len(related_papers[:limit]),
                'method': 'subject_classification_similarity'
            }
            
        except Exception as e:
            logger.error(f"Failed to get related papers for {arxiv_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_paper_recommendations(
        self,
        research_interests: List[str],
        limit: int = 15
    ) -> Dict[str, Any]:
        """
        Get paper recommendations based on research interests
        
        Args:
            research_interests: List of research interest keywords
            limit: Number of papers to recommend
            
        Returns:
            Recommended papers based on interests
        """
        try:
            recommendations = []
            
            for interest in research_interests[:3]:  # Limit to 3 interests
                search_query = SearchQuery(
                    query=interest,
                    limit=limit // len(research_interests[:3]) + 2
                )
                
                result = await self.search_papers(
                    search_query,
                    include_abstracts=True
                )
                
                if result.success:
                    for paper in result.results:
                        if len(recommendations) < limit:
                            recommendations.append({
                                'paper': paper,
                                'recommendation_reason': f'Matches interest: {interest}',
                                'relevance_score': self._calculate_relevance_score(paper, interest)
                            })
            
            # Sort by relevance score
            recommendations.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return {
                'success': True,
                'research_interests': research_interests,
                'recommendations': recommendations[:limit],
                'count': len(recommendations[:limit])
            }
            
        except Exception as e:
            logger.error(f"Failed to get recommendations: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def search_by_author(self, author_name: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for papers by author name
        
        Args:
            author_name: Author name to search for
            limit: Maximum number of papers to return
            
        Returns:
            Papers by the specified author
        """
        try:
            search_query = SearchQuery(
                query=f'au:"{author_name}"',
                limit=limit
            )
            
            result = await self.search_papers(search_query, include_abstracts=True)
            
            if result.success:
                return {
                    'success': True,
                    'author': author_name,
                    'papers': result.results,
                    'count': len(result.results),
                    'total_found': result.total_results
                }
            else:
                return {'success': False, 'error': 'Search failed'}
                
        except Exception as e:
            logger.error(f"Failed to search papers by author {author_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_arxiv_response(self, response_text: str, include_abstracts: bool = True) -> List[Paper]:
        """Parse arXiv XML response into Paper objects"""
        papers = []
        
        try:
            # Parse XML
            root = ET.fromstring(response_text)
            
            # Find all entry elements
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', namespace)
            
            for entry in entries:
                try:
                    # Extract paper information
                    title = entry.find('atom:title', namespace)
                    title_text = title.text.strip() if title is not None else "Unknown Title"
                    
                    # Extract arXiv ID from ID URL
                    id_elem = entry.find('atom:id', namespace)
                    arxiv_id = None
                    if id_elem is not None:
                        arxiv_id = id_elem.text.split('/')[-1]
                    
                    # Extract abstract
                    abstract = None
                    if include_abstracts:
                        summary = entry.find('atom:summary', namespace)
                        if summary is not None:
                            abstract = summary.text.strip()
                    
                    # Extract authors
                    authors = []
                    author_elems = entry.findall('atom:author', namespace)
                    for author_elem in author_elems:
                        name_elem = author_elem.find('atom:name', namespace)
                        if name_elem is not None:
                            authors.append(Author(name=name_elem.text.strip()))
                    
                    # Extract publication date
                    published = entry.find('atom:published', namespace)
                    pub_date = None
                    if published is not None:
                        pub_date = self._parse_date(published.text)
                    
                    # Extract subjects/categories
                    subjects = []
                    category_elems = entry.findall('atom:category', namespace)
                    for cat_elem in category_elems:
                        term = cat_elem.get('term')
                        if term:
                            subjects.append(term)
                    
                    # Extract PDF URL
                    pdf_url = None
                    link_elems = entry.findall('atom:link', namespace)
                    for link in link_elems:
                        if link.get('title') == 'pdf':
                            pdf_url = link.get('href')
                            break
                    
                    # Create Paper object
                    paper = Paper(
                        id=arxiv_id or f"arxiv-{len(papers)}",
                        title=self._clean_text(title_text),
                        source=DataSource.ARXIV,
                        url=id_elem.text if id_elem is not None else None,
                        description=self._clean_text(abstract) if abstract else None,
                        authors=authors,
                        abstract=self._clean_text(abstract),
                        arxiv_id=arxiv_id,
                        publication_date=pub_date,
                        topics=subjects,
                        pdf_url=pdf_url,
                        metadata={
                            'source': 'arxiv',
                            'subjects': subjects,
                            'has_pdf': bool(pdf_url)
                        }
                    )
                    
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse arXiv entry: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to parse arXiv XML response: {str(e)}")
        
        return papers
    
    def _generate_tldr_from_abstract(self, abstract: str) -> str:
        """Generate a TLDR from abstract (simple extraction)"""
        if not abstract:
            return "No abstract available"
        
        # Simple TLDR generation - extract first 2 sentences
        sentences = re.split(r'[.!?]+', abstract)
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if len(meaningful_sentences) >= 2:
            tldr = '. '.join(meaningful_sentences[:2]) + '.'
        elif meaningful_sentences:
            tldr = meaningful_sentences[0] + '.'
        else:
            tldr = abstract[:200] + '...' if len(abstract) > 200 else abstract
        
        return tldr
    
    def _calculate_relevance_score(self, paper: Paper, interest: str) -> float:
        """Calculate relevance score for paper recommendations"""
        score = 0.0
        interest_lower = interest.lower()
        
        # Title match
        if interest_lower in paper.title.lower():
            score += 50
        
        # Abstract match
        if paper.abstract and interest_lower in paper.abstract.lower():
            score += 30
        
        # Subject match
        for subject in paper.topics:
            if interest_lower in subject.lower():
                score += 20
        
        # Recency bonus (more recent papers get higher scores)
        if paper.publication_date:
            days_old = (datetime.now() - paper.publication_date).days
            recency_score = max(0, 10 - (days_old / 365))  # Bonus for papers < 3 years old
            score += recency_score
        
        return score
    
    async def _make_xml_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Make a rate-limited HTTP request for XML responses
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Response text (XML)
        """
        await self.rate_limiter.wait_if_needed()
        await self._ensure_session()
        
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                headers=request_headers
            ) as response:
                response.raise_for_status()
                return await response.text()
                
        except Exception as e:
            logger.error(f"XML request failed for {url}: {str(e)}")
            raise 

    def validate_arxiv_id(self, arxiv_id: str) -> Dict[str, Any]:
        """
        Validate and clean ArXiv ID format
        
        Args:
            arxiv_id: Raw ArXiv ID string
            
        Returns:
            Validation result with clean ID
        """
        import re
        
        if not arxiv_id:
            return {
                "valid": False,
                "error": "ArXiv ID is required",
                "clean_id": None
            }
        
        # Remove 'arXiv:' prefix if present
        clean_id = arxiv_id.replace("arXiv:", "").strip()
        
        # ArXiv ID patterns:
        # New format: YYMM.NNNNN[vN] (e.g., 1802.10062, 1802.10062v1)
        # Old format: subject-class/YYMMnnn (e.g., cs.CV/0001001)
        
        new_format = r'^\d{4}\.\d{4,5}(?:v\d+)?$'
        old_format = r'^[a-z-]+(?:\.[A-Z]{2})?/\d{7}$'
        
        if re.match(new_format, clean_id) or re.match(old_format, clean_id):
            return {
                "valid": True,
                "error": None,
                "clean_id": clean_id
            }
        else:
            return {
                "valid": False,
                "error": f"Invalid ArXiv ID format: {arxiv_id}. Expected formats: YYMM.NNNNN or subject-class/YYMMnnn",
                "clean_id": None
            } 

    async def download_paper(self, arxiv_id: str) -> Dict[str, Any]:
        """
        Download paper PDF and metadata from ArXiv
        
        Args:
            arxiv_id: Clean ArXiv ID
            
        Returns:
            Download result with file path, metadata, etc.
        """
        try:
            import aiohttp
            import aiofiles
            import os
            from pathlib import Path
            from app.config.settings import get_settings
            
            # Get paper metadata first
            paper_details = await self.get_paper_details(arxiv_id)
            
            if not paper_details.get("success"):
                return paper_details
            
            paper = paper_details["paper"]
            
            # Get PDF URL and prepare download path
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            settings = get_settings()
            downloads_dir = settings.files.papers_dir / "arxiv"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            file_path = downloads_dir / f"{arxiv_id}.pdf"
            
            # Download PDF
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        
                        file_size = len(content)
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to download PDF: HTTP {response.status}"
                        }
            
            # Build result with metadata
            return {
                "success": True,
                "file_path": str(file_path),
                "file_size": file_size,
                "metadata": {
                    "title": paper.title,
                    "authors": [str(author) for author in paper.authors] if hasattr(paper, 'authors') else [],
                    "abstract": paper.abstract if hasattr(paper, 'abstract') else "",
                    "categories": paper.topics if hasattr(paper, 'topics') else [],
                    "doi": getattr(paper, 'doi', None),
                    "published": getattr(paper, 'published', None),
                    "updated": getattr(paper, 'updated', None)
                }
            }
        
        except Exception as e:
            import traceback
            logger.error(f"ArXiv download_paper exception: {e}")
            logger.error(f"ArXiv download_paper traceback: {traceback.format_exc()}")
            logger.error(f"Failed to download ArXiv paper {arxiv_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            } 