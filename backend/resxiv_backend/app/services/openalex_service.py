"""
OpenAlex Service Module

This module provides comprehensive access to OpenAlex API for academic research data.
OpenAlex is a fully open bibliographic database with scholarly papers, authors, 
institutions, and more.

Key Features:
- Find highly cited papers by author, domain, time, conference
- Find relevant authors by domain, conference, citation count
- Deep dive into authors (publications, affiliations, domains)
- Deep dive into papers (citations, concepts, publication timeline)
- Deep dive into conferences (venue-level stats)
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import quote
import time

from .research_agent_core import (
    BaseResearchService, SearchQuery, SearchResponse, Paper, Author, Conference,
    DataSource, RateLimitConfig, ResearchServiceError
)

logger = logging.getLogger(__name__)


class OpenAlexService(BaseResearchService):
    """
    Service for accessing OpenAlex API
    
    OpenAlex provides access to ~250M+ scholarly papers, ~130M+ authors,
    and comprehensive citation data.
    """
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize OpenAlex service
        
        Args:
            email: Email for polite pooling (gets higher rate limits)
        """
        super().__init__(
            base_url="https://api.openalex.org",
            rate_limit_config=RateLimitConfig(
                requests_per_second=10.0 if email else 3.0,  # Higher limits with email
                requests_per_minute=600 if email else 180,
                requests_per_hour=10000 if email else 1000
            )
        )
        
        self.email = email
        if email:
            self.headers['User-Agent'] = f'ResXiv-Research-Agent/1.0 (mailto:{email})'
    
    async def search_papers(
        self,
        query: SearchQuery,
        filters: Optional[Dict[str, Any]] = None
    ) -> SearchResponse:
        """
        Search for papers in OpenAlex
        
        Args:
            query: Search query parameters
            filters: Additional OpenAlex-specific filters
            
        Returns:
            SearchResponse with Paper objects
        """
        start_time = time.time()
        
        try:
            # Build search parameters
            params = self._build_paper_search_params(query, filters)
            
            # Make request
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params=params
            )
            
            # Parse results
            papers = self._parse_papers_response(response_data)
            
            return SearchResponse(
                success=True,
                query=query.query,
                data_source=DataSource.OPENALEX,
                total_results=response_data.get('meta', {}).get('count', 0),
                returned_results=len(papers),
                offset=query.offset,
                results=papers,
                execution_time=time.time() - start_time,
                metadata={
                    'openalex_meta': response_data.get('meta', {}),
                    'group_by': response_data.get('group_by', [])
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAlex paper search failed: {str(e)}")
            return SearchResponse(
                success=False,
                query=query.query,
                data_source=DataSource.OPENALEX,
                total_results=0,
                returned_results=0,
                offset=query.offset,
                results=[],
                execution_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
    
    async def search_authors(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for authors in OpenAlex
        
        Args:
            query: Search query for authors
            filters: Additional filters (domain, institution, etc.)
            limit: Number of results to return
            offset: Offset for pagination
            
        Returns:
            Dictionary with author search results
        """
        start_time = time.time()
        
        try:
            # Build search parameters
            params = {
                'search': query,
                'per-page': min(limit, 200),  # OpenAlex max is 200
                'page': (offset // limit) + 1,
                'sort': 'cited_by_count:desc'
            }
            
            # Add filters
            if filters:
                params.update(self._build_author_filters(filters))
            
            # Make request
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/authors",
                params=params
            )
            
            # Parse authors
            authors = self._parse_authors_response(response_data)
            
            return {
                'success': True,
                'query': query,
                'total_results': response_data.get('meta', {}).get('count', 0),
                'returned_results': len(authors),
                'authors': authors,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"OpenAlex author search failed: {str(e)}")
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def get_author_details(self, author_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific author
        
        Args:
            author_id: OpenAlex author ID (e.g., 'A123456789')
            
        Returns:
            Detailed author information
        """
        try:
            # Get author data
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/authors/{author_id}"
            )
            
            # Get author's recent papers
            papers_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params={
                    'filter': f'author.id:{author_id}',
                    'sort': 'publication_date:desc',
                    'per-page': 20
                }
            )
            
            return {
                'success': True,
                'author': self._parse_author_detail(response_data),
                'recent_papers': self._parse_papers_response(papers_response),
                'paper_count': papers_response.get('meta', {}).get('count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get author details for {author_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific paper
        
        Args:
            paper_id: OpenAlex work ID (e.g., 'W123456789')
            
        Returns:
            Detailed paper information
        """
        try:
            # Get paper data
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works/{paper_id}"
            )
            
            # Get citing papers
            citing_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params={
                    'filter': f'cites:{paper_id}',
                    'sort': 'cited_by_count:desc',
                    'per-page': 10
                }
            )
            
            # Get referenced papers
            referenced_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params={
                    'filter': f'referenced_works:{paper_id}',
                    'sort': 'cited_by_count:desc',
                    'per-page': 10
                }
            )
            
            return {
                'success': True,
                'paper': self._parse_paper_detail(response_data),
                'citing_papers': self._parse_papers_response(citing_response),
                'referenced_papers': self._parse_papers_response(referenced_response),
                'citation_count': citing_response.get('meta', {}).get('count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get paper details for {paper_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def search_by_conference(
        self,
        venue_name: str,
        year_range: Optional[tuple] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search papers by conference/venue
        
        Args:
            venue_name: Conference or journal name
            year_range: Tuple of (start_year, end_year)
            limit: Number of results
            
        Returns:
            Conference papers and statistics
        """
        try:
            # Build venue filter
            filters = [f'host_venue.display_name.search:{quote(venue_name)}']
            
            if year_range:
                start_year, end_year = year_range
                filters.append(f'publication_year:{start_year}-{end_year}')
            
            params = {
                'filter': ','.join(filters),
                'sort': 'cited_by_count:desc',
                'per-page': limit,
                'group_by': 'publication_year'
            }
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params=params
            )
            
            papers = self._parse_papers_response(response_data)
            
            # Calculate venue statistics
            stats = self._calculate_venue_stats(response_data)
            
            return {
                'success': True,
                'venue': venue_name,
                'papers': papers,
                'statistics': stats,
                'total_papers': response_data.get('meta', {}).get('count', 0)
            }
            
        except Exception as e:
            logger.error(f"Conference search failed for {venue_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_trending_papers(
        self,
        domain: Optional[str] = None,
        days: int = 30,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get trending papers based on recent citation activity
        
        Args:
            domain: Research domain/concept to filter by
            days: Number of days to look back for trending
            limit: Number of results
            
        Returns:
            List of trending papers
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            filters = [
                f'from_publication_date:{start_date.strftime("%Y-%m-%d")}',
                f'to_publication_date:{end_date.strftime("%Y-%m-%d")}'
            ]
            
            if domain:
                filters.append(f'concepts.display_name.search:{quote(domain)}')
            
            params = {
                'filter': ','.join(filters),
                'sort': 'cited_by_count:desc',
                'per-page': limit
            }
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/works",
                params=params
            )
            
            papers = self._parse_papers_response(response_data)
            
            return {
                'success': True,
                'domain': domain,
                'time_range_days': days,
                'papers': papers,
                'total_found': response_data.get('meta', {}).get('count', 0)
            }
            
        except Exception as e:
            logger.error(f"Trending papers search failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _build_paper_search_params(
        self,
        query: SearchQuery,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build search parameters for OpenAlex API"""
        params = {
            'search': query.query,
            'per-page': min(query.limit, 200),  # OpenAlex max is 200
            'page': (query.offset // query.limit) + 1,
        }
        
        # Add sorting
        sort_mapping = {
            'relevance': 'relevance_score:desc',
            'date': 'publication_date:desc',
            'citations': 'cited_by_count:desc'
        }
        params['sort'] = sort_mapping.get(query.sort_by.value, 'relevance_score:desc')
        
        # Build filters
        filters = []
        
        # Date range filter
        if query.date_range:
            start_date, end_date = query.date_range
            filters.append(f'from_publication_date:{start_date.strftime("%Y-%m-%d")}')
            filters.append(f'to_publication_date:{end_date.strftime("%Y-%m-%d")}')
        
        # Custom filters
        if query.filters:
            for filter_obj in query.filters:
                filters.append(self._build_openalex_filter(filter_obj))
        
        # Additional filters
        if additional_filters:
            for key, value in additional_filters.items():
                if isinstance(value, list):
                    filters.append(f'{key}:{"|".join(map(str, value))}')
                else:
                    filters.append(f'{key}:{value}')
        
        if filters:
            params['filter'] = ','.join(filters)
        
        return params
    
    def _build_openalex_filter(self, filter_obj) -> str:
        """Convert SearchFilter to OpenAlex filter format"""
        field = filter_obj.field
        operator = filter_obj.operator
        value = filter_obj.value
        
        if operator == "eq":
            return f"{field}:{value}"
        elif operator == "ne":
            return f"{field}:!{value}"
        elif operator == "gt":
            return f"{field}:>{value}"
        elif operator == "gte":
            return f"{field}:>={value}"
        elif operator == "lt":
            return f"{field}:<{value}"
        elif operator == "lte":
            return f"{field}:<={value}"
        elif operator == "in" and isinstance(value, list):
            value_str = "|".join(map(str, value))
            return f"{field}:{value_str}"
        elif operator == "contains":
            return f"{field}.search:{quote(str(value))}"
        else:
            return f"{field}:{value}"
    
    def _build_author_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build author-specific filters"""
        openalex_filters = {}
        
        if 'institution' in filters:
            openalex_filters['filter'] = f'last_known_institution.display_name.search:{quote(filters["institution"])}'
        
        if 'domain' in filters:
            if 'filter' in openalex_filters:
                openalex_filters['filter'] += f',concepts.display_name.search:{quote(filters["domain"])}'
            else:
                openalex_filters['filter'] = f'concepts.display_name.search:{quote(filters["domain"])}'
        
        if 'min_citations' in filters:
            filter_str = f'cited_by_count:>={filters["min_citations"]}'
            if 'filter' in openalex_filters:
                openalex_filters['filter'] += f',{filter_str}'
            else:
                openalex_filters['filter'] = filter_str
        
        return openalex_filters
    
    def _parse_papers_response(self, response_data: Dict[str, Any]) -> List[Paper]:
        """Parse OpenAlex papers response into Paper objects"""
        papers = []
        
        for work in response_data.get('results', []):
            try:
                # Parse authors with robust null handling
                authors = []
                for authorship in work.get('authorships', []):
                    if not authorship or not isinstance(authorship, dict):
                        continue
                        
                    author_data = authorship.get('author', {}) or {}
                    if not isinstance(author_data, dict):
                        continue
                        
                    # Safe institution parsing
                    institution = {}
                    institutions = authorship.get('institutions', [])
                    if institutions and isinstance(institutions, list) and len(institutions) > 0:
                        institution = institutions[0] if isinstance(institutions[0], dict) else {}
                    
                    authors.append(Author(
                        id=author_data.get('id', '').replace('https://openalex.org/', ''),
                        name=author_data.get('display_name', 'Unknown'),
                        affiliation=institution.get('display_name') if institution else None,
                        orcid=author_data.get('orcid'),
                        url=author_data.get('id')
                    ))
                
                # Parse publication date
                pub_date = None
                if work.get('publication_date'):
                    pub_date = self._parse_date(work['publication_date'])
                
                # Parse venue info with null safety
                venue_info = {}
                host_venue = work.get('host_venue')
                primary_location = work.get('primary_location')
                
                if host_venue and isinstance(host_venue, dict):
                    venue_info = host_venue
                elif primary_location and isinstance(primary_location, dict):
                    venue_info = primary_location
                
                # Extract topics/concepts with null safety
                topics = []
                concepts = work.get('concepts', [])
                if concepts and isinstance(concepts, list):
                    for concept in concepts[:5]:
                        if concept and isinstance(concept, dict):
                            topic_name = concept.get('display_name', '')
                            if topic_name:
                                topics.append(topic_name)
                
                # Extract arXiv ID from DOI if present
                arxiv_id = None
                doi = work.get('doi')
                if doi and 'arxiv' in doi.lower():
                    # Extract arXiv ID from DOI patterns like:
                    # https://doi.org/10.48550/arxiv.2407.18927 -> 2407.18927
                    # https://doi.org/10.48550/arXiv.2401.05968 -> 2401.05968
                    import re
                    arxiv_match = re.search(r'arxiv\.(\d{4}\.\d{4,5})', doi, re.IGNORECASE)
                    if arxiv_match:
                        arxiv_id = arxiv_match.group(1)
                        logger.info(f"Extracted arXiv ID '{arxiv_id}' from DOI '{doi}'")
                
                # Get abstract with better handling
                abstract = self._clean_text(work.get('abstract')) or ""
                
                # Handle inverted index abstract if regular abstract is missing
                if not abstract and work.get('abstract_inverted_index'):
                    inverted_abstract = work.get('abstract_inverted_index')
                    if isinstance(inverted_abstract, dict):
                        # Reconstruct abstract from inverted index (word -> [positions])
                        try:
                            word_positions = []
                            for word, positions in inverted_abstract.items():
                                if isinstance(positions, list):
                                    for pos in positions:
                                        word_positions.append((pos, word))
                            # Sort by position and join words
                            word_positions.sort(key=lambda x: x[0])
                            abstract = ' '.join([word for _, word in word_positions])
                            abstract = self._clean_text(abstract)
                        except Exception as e:
                            logger.debug(f"Failed to reconstruct abstract from inverted index: {e}")
                            abstract = ""
                
                paper = Paper(
                    id=work.get('id', '').replace('https://openalex.org/', ''),
                    title=self._clean_text(work.get('display_name', '')),
                    source=DataSource.OPENALEX,
                    url=work.get('id'),
                    description=abstract,
                    authors=authors,
                    abstract=abstract,
                    doi=doi,
                    arxiv_id=arxiv_id,  # Now properly extracted!
                    publication_date=pub_date,
                    venue=venue_info.get('display_name'),
                    venue_type=venue_info.get('type'),
                    citation_count=work.get('cited_by_count', 0),
                    reference_count=len(work.get('referenced_works', [])),
                    topics=topics,
                    pdf_url=venue_info.get('pdf_url'),
                    metadata={
                        'openalex_id': work.get('id'),
                        'type': work.get('type'),
                        'open_access': work.get('open_access', {}),
                        'biblio': work.get('biblio', {}),
                        'concepts': work.get('concepts', []),
                        'extracted_arxiv_id': arxiv_id
                    }
                )
                
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Failed to parse paper: {str(e)}")
                continue
        
        return papers
    
    def _parse_authors_response(self, response_data: Dict[str, Any]) -> List[Author]:
        """Parse OpenAlex authors response into Author objects"""
        authors = []
        
        for author_data in response_data.get('results', []):
            try:
                # Get last known institution
                affiliation = None
                if author_data.get('last_known_institution'):
                    affiliation = author_data['last_known_institution'].get('display_name')
                
                author = Author(
                    id=author_data.get('id', '').replace('https://openalex.org/', ''),
                    name=author_data.get('display_name', 'Unknown'),
                    affiliation=affiliation,
                    orcid=author_data.get('orcid'),
                    h_index=author_data.get('summary_stats', {}).get('h_index'),
                    citation_count=author_data.get('cited_by_count', 0),
                    url=author_data.get('id')
                )
                
                authors.append(author)
                
            except Exception as e:
                logger.warning(f"Failed to parse author: {str(e)}")
                continue
        
        return authors
    
    def _parse_author_detail(self, author_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse detailed author information"""
        return {
            'id': author_data.get('id', '').replace('https://openalex.org/', ''),
            'name': author_data.get('display_name'),
            'orcid': author_data.get('orcid'),
            'citation_count': author_data.get('cited_by_count', 0),
            'h_index': author_data.get('summary_stats', {}).get('h_index'),
            'works_count': author_data.get('works_count', 0),
            'last_known_institution': author_data.get('last_known_institution', {}),
            'concepts': author_data.get('x_concepts', [])[:10],  # Top 10 concepts
            'affiliations': author_data.get('affiliations', []),
            'summary_stats': author_data.get('summary_stats', {})
        }
    
    def _parse_paper_detail(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse detailed paper information"""
        return {
            'id': paper_data.get('id', '').replace('https://openalex.org/', ''),
            'title': paper_data.get('display_name'),
            'abstract': paper_data.get('abstract'),
            'doi': paper_data.get('doi'),
            'publication_date': paper_data.get('publication_date'),
            'citation_count': paper_data.get('cited_by_count', 0),
            'reference_count': len(paper_data.get('referenced_works', [])),
            'authors': self._parse_papers_response({'results': [paper_data]})[0].authors,
            'venue': paper_data.get('host_venue', {}),
            'concepts': paper_data.get('concepts', []),
            'open_access': paper_data.get('open_access', {}),
            'type': paper_data.get('type'),
            'biblio': paper_data.get('biblio', {})
        }
    
    def _calculate_venue_stats(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate venue statistics from response data"""
        papers = response_data.get('results', [])
        
        if not papers:
            return {}
        
        total_citations = sum(paper.get('cited_by_count', 0) for paper in papers)
        avg_citations = total_citations / len(papers) if papers else 0
        
        # Get publication year distribution from group_by
        year_stats = {}
        for group in response_data.get('group_by', []):
            year_stats[group.get('key')] = group.get('count', 0)
        
        return {
            'total_papers': len(papers),
            'total_citations': total_citations,
            'average_citations': round(avg_citations, 2),
            'papers_by_year': year_stats,
            'h_index': self._calculate_h_index([p.get('cited_by_count', 0) for p in papers])
        }
    
    def _calculate_h_index(self, citations: List[int]) -> int:
        """Calculate h-index from citation counts"""
        citations.sort(reverse=True)
        h_index = 0
        
        for i, citation_count in enumerate(citations, 1):
            if citation_count >= i:
                h_index = i
            else:
                break
        
        return h_index 