"""
CrossRef Service Module

This module provides access to CrossRef API for paper metadata and citations
as an alternative to Semantic Scholar. CrossRef is free and doesn't require API keys.

Key Features:
- Paper metadata via DOI lookup
- Citation information and reference lists
- Journal and conference information
- Author disambiguation
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from urllib.parse import quote
import time

from .research_agent_core import (
    BaseResearchService, SearchQuery, SearchResponse, Paper, Author,
    DataSource, RateLimitConfig, ResearchServiceError
)

logger = logging.getLogger(__name__)


class CrossRefService(BaseResearchService):
    """
    Service for accessing CrossRef API for paper metadata and citations
    
    Provides DOI-based paper information as an alternative to Semantic Scholar.
    """
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize CrossRef service
        
        Args:
            email: Email for polite pooling (recommended but not required)
        """
        super().__init__(
            base_url="https://api.crossref.org",
            rate_limit_config=RateLimitConfig(
                requests_per_second=50.0 if email else 5.0,  # Higher limits with email
                requests_per_minute=3000 if email else 300,
                requests_per_hour=10000 if email else 1000
            )
        )
        
        if email:
            self.headers['User-Agent'] = f'ResXiv-Research-Agent/1.0 (mailto:{email})'
    
    async def search_papers(
        self,
        query: SearchQuery,
        filters: Optional[Dict[str, Any]] = None
    ) -> SearchResponse:
        """
        Search for papers using CrossRef
        
        Args:
            query: Search query parameters
            filters: Additional filters (year, type, etc.)
            
        Returns:
            SearchResponse with Paper objects
        """
        start_time = time.time()
        
        try:
            # Build search parameters
            params = {
                'query': query.query,
                'rows': min(query.limit, 1000),  # CrossRef limit
                'offset': query.offset,
                'sort': 'relevance' if query.sort_by.value == 'relevance' else 'published'
            }
            
            # Add filters
            if filters:
                for key, value in filters.items():
                    params[f'filter'] = f'{key}:{value}'
            
            # Make request
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params=params
            )
            
            # Parse results
            papers = self._parse_crossref_response(response_data)
            
            return SearchResponse(
                success=True,
                query=query.query,
                data_source=DataSource.CROSSREF,
                total_results=response_data.get('message', {}).get('total-results', 0),
                returned_results=len(papers),
                offset=query.offset,
                results=papers,
                execution_time=time.time() - start_time,
                metadata={
                    'crossref_meta': response_data.get('message', {}),
                    'source': 'crossref'
                }
            )
            
        except Exception as e:
            logger.error(f"CrossRef search failed: {str(e)}")
            return SearchResponse(
                success=False,
                query=query.query,
                data_source=DataSource.CROSSREF,
                total_results=0,
                returned_results=0,
                offset=query.offset,
                results=[],
                execution_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
    
    async def get_paper_by_doi(self, doi: str) -> Dict[str, Any]:
        """
        Get detailed paper information by DOI
        
        Args:
            doi: Paper DOI
            
        Returns:
            Detailed paper information
        """
        try:
            # Clean DOI
            clean_doi = doi.replace('https://doi.org/', '').replace('http://dx.doi.org/', '')
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works/{clean_doi}"
            )
            
            work = response_data.get('message', {})
            paper_detail = self._parse_work_detail(work)
            
            return {
                'success': True,
                'paper': paper_detail,
                'doi': clean_doi,
                'crossref_data': work
            }
            
        except Exception as e:
            logger.error(f"Failed to get paper by DOI {doi}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_paper_citations(self, doi: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get papers citing the given DOI (alternative to citation context)
        
        Args:
            doi: Paper DOI
            limit: Number of citing papers to return
            
        Returns:
            List of papers citing the given paper
        """
        try:
            clean_doi = doi.replace('https://doi.org/', '').replace('http://dx.doi.org/', '')
            
            params = {
                'filter': f'references:{clean_doi}',
                'rows': min(limit, 1000),
                'sort': 'published'
            }
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params=params
            )
            
            citing_papers = self._parse_crossref_response(response_data)
            
            return {
                'success': True,
                'cited_doi': clean_doi,
                'citing_papers': citing_papers,
                'citation_count': len(citing_papers),
                'total_found': response_data.get('message', {}).get('total-results', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get citations for {doi}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_paper_references(self, doi: str) -> Dict[str, Any]:
        """
        Get reference list for a paper
        
        Args:
            doi: Paper DOI
            
        Returns:
            List of references
        """
        try:
            paper_data = await self.get_paper_by_doi(doi)
            
            if not paper_data.get('success'):
                return paper_data
            
            crossref_data = paper_data.get('crossref_data', {})
            references = crossref_data.get('reference', [])
            
            parsed_references = []
            for ref in references:
                parsed_ref = {
                    'title': ref.get('article-title'),
                    'author': ref.get('author'),
                    'journal': ref.get('journal-title'),
                    'year': ref.get('year'),
                    'doi': ref.get('DOI'),
                    'volume': ref.get('volume'),
                    'page': ref.get('first-page')
                }
                parsed_references.append(parsed_ref)
            
            return {
                'success': True,
                'source_doi': doi,
                'references': parsed_references,
                'reference_count': len(parsed_references)
            }
            
        except Exception as e:
            logger.error(f"Failed to get references for {doi}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_related_papers_by_author(
        self,
        author_name: str,
        limit: int = 15
    ) -> Dict[str, Any]:
        """
        Get related papers by the same author (alternative to semantic similarity)
        
        Args:
            author_name: Author name
            limit: Number of papers to return
            
        Returns:
            Papers by the same author
        """
        try:
            params = {
                'query.author': author_name,
                'rows': min(limit, 1000),
                'sort': 'published'
            }
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params=params
            )
            
            papers = self._parse_crossref_response(response_data)
            
            return {
                'success': True,
                'author': author_name,
                'papers': papers,
                'paper_count': len(papers),
                'total_found': response_data.get('message', {}).get('total-results', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get papers by author {author_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_journal_papers(
        self,
        journal_name: str,
        year: Optional[int] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get papers from a specific journal
        
        Args:
            journal_name: Journal name
            year: Publication year filter
            limit: Number of papers to return
            
        Returns:
            Papers from the journal
        """
        try:
            params = {
                'query.container-title': journal_name,
                'rows': min(limit, 1000),
                'sort': 'published'
            }
            
            if year:
                params['filter'] = f'from-pub-date:{year},until-pub-date:{year}'
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params=params
            )
            
            papers = self._parse_crossref_response(response_data)
            
            return {
                'success': True,
                'journal': journal_name,
                'year': year,
                'papers': papers,
                'paper_count': len(papers)
            }
            
        except Exception as e:
            logger.error(f"Failed to get journal papers: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_crossref_response(self, response_data: Dict[str, Any]) -> List[Paper]:
        """Parse CrossRef response into Paper objects"""
        papers = []
        
        message = response_data.get('message', {})
        items = message.get('items', [])
        
        for work in items:
            try:
                paper = self._parse_work_detail(work)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"Failed to parse CrossRef work: {str(e)}")
                continue
        
        return papers
    
    def _parse_work_detail(self, work: Dict[str, Any]) -> Optional[Paper]:
        """Parse individual CrossRef work into Paper object"""
        try:
            # Extract basic information
            title = work.get('title', ['Unknown Title'])[0] if work.get('title') else 'Unknown Title'
            doi = work.get('DOI')
            
            # Extract authors
            authors = []
            for author_data in work.get('author', []):
                name_parts = []
                if author_data.get('given'):
                    name_parts.append(author_data['given'])
                if author_data.get('family'):
                    name_parts.append(author_data['family'])
                
                name = ' '.join(name_parts) if name_parts else 'Unknown Author'
                
                # Extract affiliation
                affiliation = None
                if author_data.get('affiliation'):
                    affiliations = author_data['affiliation']
                    if affiliations and len(affiliations) > 0:
                        affiliation = affiliations[0].get('name')
                
                authors.append(Author(
                    name=name,
                    affiliation=affiliation
                ))
            
            # Extract publication date
            pub_date = None
            if work.get('published-print'):
                date_parts = work['published-print'].get('date-parts', [[]])[0]
                if len(date_parts) >= 3:
                    pub_date = datetime(date_parts[0], date_parts[1], date_parts[2])
                elif len(date_parts) >= 1:
                    pub_date = datetime(date_parts[0], 1, 1)
            elif work.get('published-online'):
                date_parts = work['published-online'].get('date-parts', [[]])[0]
                if len(date_parts) >= 1:
                    pub_date = datetime(date_parts[0], 1, 1)
            
            # Extract venue information
            venue = None
            venue_type = None
            container_title = work.get('container-title')
            if container_title:
                venue = container_title[0] if isinstance(container_title, list) else container_title
            
            work_type = work.get('type')
            if work_type:
                venue_type = 'journal' if 'journal' in work_type else 'conference'
            
            # Extract abstract (if available)
            abstract = work.get('abstract')
            if abstract:
                # Remove HTML tags if present
                import re
                abstract = re.sub('<[^<]+?>', '', abstract)
            
            # Extract reference count
            reference_count = len(work.get('reference', []))
            
            # Extract subjects
            subjects = work.get('subject', [])
            
            paper = Paper(
                id=doi or f"crossref-{work.get('id', 'unknown')}",
                title=self._clean_text(title),
                source=DataSource.CROSSREF,
                url=f"https://doi.org/{doi}" if doi else None,
                description=self._clean_text(abstract),
                authors=authors,
                abstract=self._clean_text(abstract),
                doi=doi,
                publication_date=pub_date,
                venue=venue,
                venue_type=venue_type,
                reference_count=reference_count,
                topics=subjects,
                metadata={
                    'source': 'crossref',
                    'work_type': work_type,
                    'publisher': work.get('publisher'),
                    'issn': work.get('ISSN'),
                    'isbn': work.get('ISBN'),
                    'volume': work.get('volume'),
                    'issue': work.get('issue'),
                    'page': work.get('page'),
                    'language': work.get('language')
                }
            )
            
            return paper
            
        except Exception as e:
            logger.warning(f"Failed to parse CrossRef work detail: {str(e)}")
            return None 