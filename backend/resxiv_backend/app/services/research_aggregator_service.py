"""
Research Aggregator Service Module

This module coordinates all research agent services to provide unified access
to multiple research data sources. It handles complex queries that require
data from multiple APIs and provides intelligent aggregation and ranking.

Key Features:
- Coordinate searches across multiple research data sources
- Intelligent result aggregation and deduplication
- Cross-reference papers, authors, and datasets across sources
- Provide comprehensive research insights
- Cache and optimize multi-source queries
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import time
import hashlib

from .research_agent_core import (
    BaseResearchService, SearchQuery, SearchResponse, Paper, Author, Dataset, 
    Model, Conference, Grant, DataSource, RateLimitConfig, ResearchServiceError,
    ResearchServiceFactory
)
from .openalex_service import OpenAlexService
from .papers_with_code_service import PapersWithCodeService
from .arxiv_service import ArXivService
from .crossref_service import CrossRefService
from .ai_deadlines_service import AIDeadlinesService
from .grant_scraper_service import GrantScraperService

logger = logging.getLogger(__name__)


class ResearchAggregatorService:
    """
    Orchestrates multiple research services to provide comprehensive research insights
    
    This service coordinates OpenAlex, PapersWithCode, arXiv, CrossRef, AI Deadlines,
    and Grant Scraper services to answer complex research queries.
    """
    
    def __init__(
        self,
        openalex_email: Optional[str] = None,
        crossref_email: Optional[str] = None
    ):
        """
        Initialize Research Aggregator with all sub-services
        
        Args:
            openalex_email: Email for OpenAlex API (higher rate limits)
            crossref_email: Email for CrossRef API (higher rate limits)
        """
        # Initialize all services (clean segregation - one service per data source)
        self.openalex = OpenAlexService(email=openalex_email)
        self.papers_with_code = PapersWithCodeService()
        self.arxiv = ArXivService()
        self.crossref = CrossRefService(email=crossref_email)
        self.ai_deadlines = AIDeadlinesService()
        self.grant_scraper = GrantScraperService()
        
        # Service mappings for dynamic access
        self.services = {
            DataSource.OPENALEX: self.openalex,
            DataSource.PAPERS_WITH_CODE: self.papers_with_code,
            DataSource.ARXIV: self.arxiv,
            DataSource.CROSSREF: self.crossref,
            DataSource.AI_DEADLINES: self.ai_deadlines,
            DataSource.GRANTS_GOV: self.grant_scraper
        }
        
        # Cache for expensive operations
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour cache TTL
    
    async def __aenter__(self):
        """Async context manager entry"""
        # Initialize all services
        for service in self.services.values():
            await service.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Close all services
        for service in self.services.values():
            await service.__aexit__(exc_type, exc_val, exc_tb)
    
    async def comprehensive_paper_search(
        self,
        query: str,
        limit: int = 20,
        include_semantics: bool = True,
        include_code: bool = True,
        cross_reference: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive paper search across multiple sources with cross-referencing
        
        Args:
            query: Search query
            limit: Number of results per source
            include_semantics: Include Semantic Scholar results
            include_code: Include Papers with Code results
            cross_reference: Cross-reference papers across sources
            
        Returns:
            Aggregated and cross-referenced paper results
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = f"search_{hashlib.md5(f'{query}_{limit}_{include_semantics}_{include_code}'.encode()).hexdigest()}"
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if time.time() - cached_result['timestamp'] < self._cache_ttl:
                logger.info(f"Returning cached search results for query: {query}")
                return cached_result['data']
        
        try:
            search_query = SearchQuery(query=query, limit=limit)
            
            # Create individual service tasks with timeout protection
            async def safe_service_call(service_name: str, service_call, timeout: float = 15.0):
                """Wrapper to make individual service calls safe"""
                # Map service names to DataSource enum values
                data_source_mapping = {
                    'openalex': DataSource.OPENALEX,
                    'arxiv': DataSource.ARXIV,
                    'crossref': DataSource.CROSSREF,
                    'papers_with_code': DataSource.PAPERS_WITH_CODE
                }
                
                try:
                    # Adaptive timeout based on service reliability
                    service_timeouts = {
                        'openalex': 12.0,        # Most reliable, shorter timeout
                        'arxiv': 10.0,           # Generally fast
                        'crossref': 15.0,        # Can be slower
                        'papers_with_code': 20.0 # Often slow, longer timeout
                    }
                    actual_timeout = service_timeouts.get(service_name, timeout)
                    
                    result = await asyncio.wait_for(service_call, timeout=actual_timeout)
                    logger.info(f"Service {service_name} completed successfully")
                    return service_name, result
                except asyncio.TimeoutError:
                    logger.warning(f"Service {service_name} timed out after {actual_timeout}s")
                    return service_name, SearchResponse(
                        success=False,
                        query=query,
                        data_source=data_source_mapping.get(service_name, DataSource.OPENALEX),
                        total_results=0,
                        returned_results=0,
                        offset=0,
                        results=[],
                        execution_time=actual_timeout,
                        metadata={'error': 'Service timeout', 'timeout_seconds': actual_timeout}
                    )
                except Exception as e:
                    logger.error(f"Service {service_name} failed: {str(e)}")
                    return service_name, SearchResponse(
                        success=False,
                        query=query,
                        data_source=data_source_mapping.get(service_name, DataSource.OPENALEX),
                        total_results=0,
                        returned_results=0,
                        offset=0,
                        results=[],
                        execution_time=0.0,
                        metadata={'error': str(e)}
                    )
            
            # Build list of service calls with priority ordering
            search_tasks = []
            
            # Priority 1: Always include OpenAlex (most reliable and comprehensive)
            search_tasks.append(
                safe_service_call('openalex', self.openalex.search_papers(search_query))
            )
            
            # Priority 2: ArXiv (reliable and fast)
            search_tasks.append(
                safe_service_call('arxiv', self.arxiv.search_papers(search_query))
            )
            
            # Priority 3: Conditional services based on user preferences
            if include_semantics:
                # CrossRef can be slow but provides good metadata
                search_tasks.append(
                    safe_service_call('crossref', self.crossref.search_papers(search_query))
                )
            
            if include_code:
                # PapersWithCode is valuable but often unreliable
                search_tasks.append(
                    safe_service_call('papers_with_code', self.papers_with_code.search_papers(search_query))
                )
            
            # Execute all searches with individual timeout protection
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results safely with better error handling
            all_papers = []
            source_stats = {}
            successful_sources = 0
            total_execution_time = 0
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Search task failed with exception: {result}")
                    continue
                    
                service_name, search_response = result
                
                if isinstance(search_response, SearchResponse):
                    source_stats[service_name] = {
                        'success': search_response.success,
                        'total_results': search_response.total_results,
                        'returned_results': search_response.returned_results,
                        'execution_time': search_response.execution_time,
                        'metadata': search_response.metadata
                    }
                    
                    if search_response.success and search_response.results:
                        all_papers.extend(search_response.results)
                        successful_sources += 1
                        logger.info(f"{service_name}: {len(search_response.results)} papers retrieved")
                    else:
                        error_msg = search_response.metadata.get('error', 'Unknown error')
                        logger.warning(f"{service_name}: Search failed - {error_msg}")
                    
                    total_execution_time += search_response.execution_time
                else:
                    logger.error(f"Invalid response type from {service_name}: {type(search_response)}")
            
            # Even if all sources fail, provide a meaningful response
            if not all_papers and successful_sources == 0:
                logger.warning(f"All search sources failed for query: {query}")
                final_result = {
                    "success": False,
                    "query": query,
                    "papers": [],
                    "total_found": 0,
                    "source_statistics": source_stats,
                    "cross_referenced": False,
                    "execution_time": time.time() - start_time,
                    "metadata": {
                        "error": "All search sources failed",
                        "successful_sources": 0,
                        "total_sources": len(search_tasks),
                        "fallback_reason": "service_failures"
                    }
                }
            else:
                # Deduplicate papers using multiple strategies
                if cross_reference and len(all_papers) > 1:
                    deduplicated_papers = await self._cross_reference_papers(all_papers)
                    cross_ref_info = {"deduplicated": True, "original_count": len(all_papers), "final_count": len(deduplicated_papers)}
                else:
                    deduplicated_papers = self._simple_deduplicate(all_papers)
                    cross_ref_info = {"deduplicated": False, "simple_dedup": True, "final_count": len(deduplicated_papers)}
                
                # Sort by relevance and citation count
                final_papers = self._rank_papers(deduplicated_papers, query)[:limit]
                
                final_result = {
                    "success": True,
                    "query": query,
                    "papers": final_papers,
                    "total_found": len(final_papers),
                    "source_statistics": source_stats,
                    "cross_referenced": cross_ref_info,
                    "execution_time": time.time() - start_time,
                    "metadata": {
                        "successful_sources": successful_sources,
                        "total_sources": len(search_tasks),
                        "deduplication": cross_ref_info,
                        "ranking_applied": True
                    }
                }
            
            # Cache successful results
            if final_result["success"]:
                self._cache[cache_key] = {
                    'data': final_result,
                    'timestamp': time.time()
                }
            
            logger.info(f"Search completed: {len(final_result.get('papers', []))} papers from {successful_sources} sources")
            return final_result
            
        except Exception as e:
            logger.error(f"Comprehensive search failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "query": query,
                "papers": [],
                "total_found": 0,
                "source_statistics": {},
                "cross_referenced": False,
                "execution_time": time.time() - start_time,
                "metadata": {
                    "error": str(e),
                    "error_type": "aggregator_failure"
                }
            }
    
    async def author_deep_dive(
        self,
        author_query: str,
        include_collaborations: bool = True,
        include_impact_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Deep dive analysis of an author across all sources
        
        Args:
            author_query: Author name or identifier
            include_collaborations: Include collaboration network analysis
            include_impact_analysis: Include citation impact analysis
            
        Returns:
            Comprehensive author profile and analysis
        """
        start_time = time.time()
        
        try:
            # Search for author across sources
            search_tasks = [
                ('openalex', self.openalex.search_authors(author_query)),
            ]
            
            results = await asyncio.gather(*[task[1] for task in search_tasks])
            
            # Find the best matching author
            best_author = None
            all_author_data = {}
            
            for i, (source_name, result) in enumerate(zip([task[0] for task in search_tasks], results)):
                if result.get('success') and result.get('authors'):
                    # Take the first/best match from each source
                    author_obj = result['authors'][0]
                    # Convert Author BaseModel to plain dict for easier downstream processing
                    if hasattr(author_obj, 'dict'):
                        author = author_obj.dict()
                    else:
                        author = author_obj
                    all_author_data[source_name] = {
                        'author': author,
                        'full_result': result
                    }
                    
                    if not best_author or author.get('citation_count', 0) > best_author.get('citation_count', 0):
                        best_author = author
            
            if not best_author:
                return {
                    'success': False,
                    'error': 'Author not found in any source'
                }
            
            # Get detailed author information
            author_details = {}
            if 'openalex' in all_author_data:
                openalex_author_data = all_author_data['openalex']
                # Get author details from OpenAlex
                if openalex_author_data:
                    openalex_details = await self.openalex.get_author_details(
                        openalex_author_data['author'].get('id')
                    )
                    if openalex_details.get('success'):
                        author_details['openalex'] = openalex_details
            
            # Collaboration analysis
            collaborations = {}
            if include_collaborations:
                collaborations = await self._analyze_collaborations(author_details)
            
            # Impact analysis
            impact_analysis = {}
            if include_impact_analysis:
                impact_analysis = await self._analyze_author_impact(author_details)
            
            # Extract papers from detailed data
            all_papers = []
            if 'openalex' in author_details and author_details['openalex'].get('success'):
                recent_papers = author_details['openalex'].get('recent_papers', [])
                all_papers.extend(recent_papers)
            
            return {
                'success': True,
                'author_query': author_query,
                'author_profile': self._merge_author_profiles(all_author_data),
                'papers': all_papers,  # Add the papers here!
                'detailed_data': author_details,
                'collaboration_analysis': collaborations,
                'impact_analysis': impact_analysis,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Author deep dive failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def research_opportunity_finder(
        self,
        research_area: str,
        career_stage: str = "any",
        location_preference: Optional[str] = None,
        include_deadlines: bool = True,
        include_funding: bool = True
    ) -> Dict[str, Any]:
        """
        Find research opportunities including conferences and funding
        
        Args:
            research_area: Research area of interest
            career_stage: Career stage (graduate, postdoc, faculty, etc.)
            location_preference: Geographic preference
            include_deadlines: Include conference deadlines
            include_funding: Include funding opportunities
            
        Returns:
            Comprehensive research opportunities
        """
        start_time = time.time()
        
        try:
            opportunities = {}
            
            # Get conference deadlines
            if include_deadlines:
                deadlines_task = self.ai_deadlines.get_deadlines_by_area(research_area)
                opportunities['conferences'] = await deadlines_task
            
            # Get funding opportunities
            if include_funding:
                funding_query = SearchQuery(
                    query=f"{research_area} {career_stage} research funding",
                    limit=20
                )
                funding_task = self.grant_scraper.search_grants(
                    query=funding_query,
                    research_area=research_area,
                    eligibility=career_stage if career_stage != "any" else None
                )
                funding_result = await funding_task
                opportunities['funding'] = funding_result
            
            # Get trending papers in the area for context
            trending_query = SearchQuery(query=f"recent {research_area} research", limit=10)
            trending_papers = await self.comprehensive_paper_search(
                query=trending_query.query,
                limit=10,
                cross_reference=False
            )
            opportunities['trending_research'] = trending_papers
            
            return {
                'success': True,
                'research_area': research_area,
                'career_stage': career_stage,
                'location_preference': location_preference,
                'opportunities': opportunities,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Research opportunity finder failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def paper_impact_analysis(
        self,
        paper_identifier: str,
        identifier_type: str = "auto"  # auto, doi, arxiv_id, title
    ) -> Dict[str, Any]:
        """
        (Temporarily disabled) Comprehensive impact analysis of a paper.
        The Semantic Scholar dependency is currently removed, so this endpoint is
        not available. Returns a graceful error instead of crashing the service.
        """
        logger.warning("paper_impact_analysis is currently disabled - service unavailable")
        return {
            'success': False,
            'error': 'paper_impact_analysis is currently disabled',
            'paper_identifier': paper_identifier,
            'identifier_type': identifier_type
        }
    
    async def dataset_ecosystem_analysis(
        self,
        dataset_name: str,
        include_papers: bool = True,
        include_models: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze the ecosystem around a specific dataset
        
        Args:
            dataset_name: Name of the dataset
            include_papers: Include papers using the dataset
            include_models: Include models trained on the dataset
            
        Returns:
            Comprehensive dataset ecosystem analysis
        """
        start_time = time.time()
        
        try:
            # Search for the dataset
            dataset_search = await self.papers_with_code.search_datasets(
                query=dataset_name,
                limit=10
            )
            
            if not dataset_search.get('success') or not dataset_search.get('datasets'):
                return {
                    'success': False,
                    'error': 'Dataset not found'
                }
            
            # Get the best matching dataset
            target_dataset = dataset_search['datasets'][0]
            dataset_id = target_dataset.get('id')
            
            ecosystem_data = {
                'dataset': target_dataset,
                'dataset_details': {}
            }
            
            # Get detailed dataset information
            if dataset_id:
                dataset_details = await self.papers_with_code.get_dataset_details(dataset_id)
                if dataset_details.get('success'):
                    ecosystem_data['dataset_details'] = dataset_details
            
            # Find papers using this dataset
            if include_papers:
                papers_search = await self.comprehensive_paper_search(
                    query=f"dataset {dataset_name}",
                    limit=15,
                    cross_reference=True
                )
                ecosystem_data['papers_using_dataset'] = papers_search
            
            # Find models trained on this dataset
            if include_models:
                models_search = await self.papers_with_code.search_models(
                    dataset=dataset_name,
                    limit=20
                )
                ecosystem_data['models_on_dataset'] = models_search
            
            # Get leaderboard for common tasks with this dataset
            task = target_dataset.get('task')
            if task:
                leaderboard = await self.papers_with_code.get_task_leaderboard(
                    task=task,
                    dataset=dataset_name,
                    limit=15
                )
                ecosystem_data['leaderboard'] = leaderboard
            
            return {
                'success': True,
                'dataset_name': dataset_name,
                'ecosystem': ecosystem_data,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Dataset ecosystem analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def _cross_reference_papers(self, papers: List[Paper]) -> List[Paper]:
        """Cross-reference papers across sources to enhance data and remove duplicates"""
        # Group papers by potential similarity (title, DOI, ArXiv ID)
        groups = defaultdict(list)
        
        for paper in papers:
            # Create keys for matching
            keys = set()
            
            if paper.doi:
                keys.add(f"doi:{paper.doi.lower()}")
            if paper.arxiv_id:
                keys.add(f"arxiv:{paper.arxiv_id.lower()}")
            if paper.title:
                # Simplified title matching
                clean_title = ''.join(c.lower() for c in paper.title if c.isalnum() or c.isspace())
                title_key = ' '.join(clean_title.split()[:8])  # First 8 words
                keys.add(f"title:{title_key}")
            
            # Add to all matching groups
            for key in keys:
                groups[key].append(paper)
        
        # Merge similar papers
        merged_papers = []
        processed_papers = set()
        
        for group in groups.values():
            if len(group) > 1:
                # Merge papers in this group
                best_paper = max(group, key=lambda p: (
                    len(p.authors),
                    p.citation_count or 0,
                    len(p.abstract or ''),
                    p.source == DataSource.SEMANTIC_SCHOLAR  # Prefer S2 for rich metadata
                ))
                
                # Enhance best paper with data from others
                for other_paper in group:
                    if other_paper != best_paper:
                        # Merge metadata
                        if not best_paper.doi and other_paper.doi:
                            best_paper.doi = other_paper.doi
                        if not best_paper.arxiv_id and other_paper.arxiv_id:
                            best_paper.arxiv_id = other_paper.arxiv_id
                        if not best_paper.abstract and other_paper.abstract:
                            best_paper.abstract = other_paper.abstract
                        if not best_paper.pdf_url and other_paper.pdf_url:
                            best_paper.pdf_url = other_paper.pdf_url
                        
                        # Merge citation counts (take max)
                        if other_paper.citation_count and (not best_paper.citation_count or other_paper.citation_count > best_paper.citation_count):
                            best_paper.citation_count = other_paper.citation_count
                
                # Mark all papers in group as processed
                for paper in group:
                    processed_papers.add(id(paper))
                
                merged_papers.append(best_paper)
            else:
                # Single paper, add if not already processed
                paper = group[0]
                if id(paper) not in processed_papers:
                    merged_papers.append(paper)
                    processed_papers.add(id(paper))
        
        return merged_papers
    
    def _simple_deduplicate(self, papers: List[Paper]) -> List[Paper]:
        """Simple deduplication based on title and DOI similarity"""
        seen_titles = set()
        seen_dois = set()
        deduplicated = []
        
        for paper in papers:
            # DOI-based deduplication (most reliable)
            if paper.doi:
                doi_normalized = paper.doi.lower().strip()
                if doi_normalized in seen_dois:
                    continue
                seen_dois.add(doi_normalized)
            
            # Title-based deduplication
            if paper.title:
                title_normalized = ''.join(c.lower() for c in paper.title if c.isalnum() or c.isspace())
                title_key = ' '.join(title_normalized.split()[:6])  # First 6 significant words
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
            
            deduplicated.append(paper)
        
        return deduplicated
    
    def _rank_papers(self, papers: List[Paper], query: str) -> List[Paper]:
        """Rank papers based on relevance, citations, and other factors"""
        query_terms = set(query.lower().split())
        
        def calculate_score(paper: Paper) -> float:
            score = 0.0
            
            # Relevance score based on query terms in title
            if paper.title:
                title_terms = set(paper.title.lower().split())
                relevance = len(query_terms.intersection(title_terms)) / len(query_terms)
                score += relevance * 100
            
            # Citation score (normalized)
            if paper.citation_count:
                score += min(paper.citation_count / 100, 50)  # Cap at 50 points
            
            # Recency score
            if paper.publication_date:
                years_old = (datetime.now() - paper.publication_date).days / 365.25
                recency_score = max(0, 20 - years_old)  # Max 20 points, decreases with age
                score += recency_score
            
            # Source preference (Semantic Scholar has richer metadata)
            if paper.source == DataSource.SEMANTIC_SCHOLAR:
                score += 5
            elif paper.source == DataSource.OPENALEX:
                score += 3
            
            # Abstract quality
            if paper.abstract and len(paper.abstract) > 100:
                score += 10
            
            return score
        
        # Sort by calculated score
        scored_papers = [(paper, calculate_score(paper)) for paper in papers]
        scored_papers.sort(key=lambda x: x[1], reverse=True)
        
        return [paper for paper, score in scored_papers]
    
    def _are_papers_similar(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two paper titles are similar"""
        if not title1 or not title2:
            return False
        
        # Simple similarity check based on common words
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union >= threshold
    
    async def _analyze_collaborations(self, author_details: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze author collaboration networks"""
        # This would implement collaboration network analysis
        # For now, return basic structure
        return {
            'note': 'Collaboration analysis would analyze co-author networks',
            'frequent_collaborators': [],
            'collaboration_timeline': {},
            'institutional_affiliations': []
        }
    
    async def _analyze_author_impact(self, author_details: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze author research impact"""
        # This would implement comprehensive impact analysis
        # For now, return basic structure
        return {
            'note': 'Impact analysis would include citation trends, h-index evolution, etc.',
            'citation_timeline': {},
            'impact_metrics': {},
            'field_influence': {}
        }
    
    def _merge_author_profiles(self, all_author_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge author profiles from different sources"""
        merged_profile = {}
        
        for source, data in all_author_data.items():
            author = data.get('author', {})
            for key, value in author.items():
                if value and (key not in merged_profile or not merged_profile[key]):
                    merged_profile[key] = value
        
        return merged_profile 