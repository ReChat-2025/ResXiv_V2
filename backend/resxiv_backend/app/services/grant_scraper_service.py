"""
Grant Scraper Service Module

This module provides access to funding opportunities from various sources
including Grants.gov, DAAD, CORDIS, NSF, and other funding agencies.

Key Features:
- Find funds and fellowships for research projects
- Filter by research area, eligibility, and amount
- Track application deadlines
- Scrape and aggregate from multiple funding sources
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin
import time
import re
from dataclasses import dataclass
import asyncio

from .research_agent_core import (
    BaseResearchService, SearchQuery, SearchResponse, Grant,
    DataSource, RateLimitConfig, ResearchServiceError
)

logger = logging.getLogger(__name__)


@dataclass
class FundingSource:
    """Configuration for a funding source"""
    name: str
    base_url: str
    api_endpoint: Optional[str] = None
    requires_scraping: bool = True
    rate_limit: RateLimitConfig = None


class GrantScraperService(BaseResearchService):
    """
    Service for scraping and aggregating grant/funding opportunities
    
    Supports multiple funding sources and provides unified access
    to research funding opportunities.
    """
    
    def __init__(self):
        """Initialize Grant Scraper service"""
        super().__init__(
            base_url="https://api.grants.gov",  # Primary source
            rate_limit_config=RateLimitConfig(
                requests_per_second=0.5,  # Conservative scraping
                requests_per_minute=30,
                requests_per_hour=500
            )
        )
        
        # Configure funding sources
        self.funding_sources = {
            'grants_gov': FundingSource(
                name="Grants.gov",
                base_url="https://www.grants.gov",
                api_endpoint="/grantsws/rest/opportunities/search/",
                requires_scraping=False
            ),
            'nsf': FundingSource(
                name="National Science Foundation",
                base_url="https://www.nsf.gov",
                requires_scraping=True
            ),
            'nih': FundingSource(
                name="National Institutes of Health",
                base_url="https://grants.nih.gov",
                requires_scraping=True
            ),
            'daad': FundingSource(
                name="German Academic Exchange Service",
                base_url="https://www.daad.de",
                requires_scraping=True
            ),
            'cordis': FundingSource(
                name="EU CORDIS",
                base_url="https://cordis.europa.eu",
                requires_scraping=True
            ),
            'arc': FundingSource(
                name="Australian Research Council",
                base_url="https://www.arc.gov.au",
                requires_scraping=True
            )
        }
        
        # Research area keywords mapping
        self.research_keywords = {
            'computer_science': ['computer science', 'artificial intelligence', 'machine learning', 'software engineering'],
            'ai_ml': ['artificial intelligence', 'machine learning', 'deep learning', 'neural networks'],
            'data_science': ['data science', 'big data', 'data analytics', 'statistics'],
            'robotics': ['robotics', 'automation', 'autonomous systems'],
            'cybersecurity': ['cybersecurity', 'information security', 'network security'],
            'bioinformatics': ['bioinformatics', 'computational biology', 'genomics'],
            'hci': ['human-computer interaction', 'user experience', 'interface design'],
            'vision': ['computer vision', 'image processing', 'pattern recognition'],
            'nlp': ['natural language processing', 'computational linguistics', 'text mining']
        }
    
    async def search_grants(
        self,
        query: SearchQuery,
        research_area: Optional[str] = None,
        eligibility: Optional[str] = None,
        min_amount: Optional[int] = None,
        max_amount: Optional[int] = None,
        sources: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        Search for grants across multiple funding sources
        
        Args:
            query: Search query parameters
            research_area: Research area filter
            eligibility: Eligibility requirements (e.g., 'graduate', 'postdoc', 'faculty')
            min_amount: Minimum funding amount
            max_amount: Maximum funding amount
            sources: List of funding sources to search
            
        Returns:
            SearchResponse with Grant objects
        """
        start_time = time.time()
        
        try:
            # Default to all sources if none specified
            if sources is None:
                sources = list(self.funding_sources.keys())
            
            # Search each source in parallel
            search_tasks = []
            for source in sources:
                if source in self.funding_sources:
                    task = self._search_funding_source(
                        source, query, research_area, eligibility, min_amount, max_amount
                    )
                    search_tasks.append(task)
            
            # Execute searches in parallel
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Combine results
            all_grants = []
            for result in results:
                if isinstance(result, list):
                    all_grants.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Funding source search failed: {str(result)}")
            
            # Remove duplicates and sort by deadline
            unique_grants = self._deduplicate_grants(all_grants)
            unique_grants.sort(key=lambda x: x.deadline or datetime.max)
            
            # Apply pagination
            start_idx = query.offset
            end_idx = start_idx + query.limit
            paginated_grants = unique_grants[start_idx:end_idx]
            
            return SearchResponse(
                success=True,
                query=query.query,
                data_source=DataSource.GRANTS_GOV,  # Primary source
                total_results=len(unique_grants),
                returned_results=len(paginated_grants),
                offset=query.offset,
                results=paginated_grants,
                execution_time=time.time() - start_time,
                metadata={
                    'sources_searched': sources,
                    'research_area': research_area,
                    'eligibility': eligibility,
                    'amount_range': {'min': min_amount, 'max': max_amount}
                }
            )
            
        except Exception as e:
            logger.error(f"Grant search failed: {str(e)}")
            return SearchResponse(
                success=False,
                query=query.query,
                data_source=DataSource.GRANTS_GOV,
                total_results=0,
                returned_results=0,
                offset=query.offset,
                results=[],
                execution_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
    
    async def get_grants_by_deadline(
        self,
        days_ahead: int = 60,
        research_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get grants with upcoming deadlines
        
        Args:
            days_ahead: Number of days to look ahead
            research_area: Filter by research area
            
        Returns:
            Grants with upcoming deadlines
        """
        try:
            # Create search query for upcoming deadlines
            end_date = datetime.now() + timedelta(days=days_ahead)
            
            query = SearchQuery(
                query=f"research funding {research_area or ''}".strip(),
                date_range=(datetime.now(), end_date),
                limit=50
            )
            
            # Search for grants
            response = await self.search_grants(
                query=query,
                research_area=research_area
            )
            
            if response.success:
                # Filter and sort by deadline
                grants_with_deadlines = [
                    grant for grant in response.results 
                    if isinstance(grant, Grant) and grant.deadline and grant.deadline <= end_date
                ]
                
                return {
                    'success': True,
                    'date_range': {
                        'start': datetime.now().isoformat(),
                        'end': end_date.isoformat()
                    },
                    'research_area': research_area,
                    'grants': grants_with_deadlines,
                    'count': len(grants_with_deadlines)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to search grants'
                }
                
        except Exception as e:
            logger.error(f"Failed to get grants by deadline: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_grants_by_agency(self, agency_name: str) -> Dict[str, Any]:
        """
        Get grants from a specific funding agency
        
        Args:
            agency_name: Name of the funding agency
            
        Returns:
            Grants from the specified agency
        """
        try:
            query = SearchQuery(
                query=f"funding agency:{agency_name}",
                limit=30
            )
            
            response = await self.search_grants(query=query)
            
            if response.success:
                # Filter grants by agency
                agency_grants = [
                    grant for grant in response.results
                    if isinstance(grant, Grant) and agency_name.lower() in grant.funding_agency.lower()
                ]
                
                return {
                    'success': True,
                    'agency': agency_name,
                    'grants': agency_grants,
                    'count': len(agency_grants)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to search grants by agency'
                }
                
        except Exception as e:
            logger.error(f"Failed to get grants by agency {agency_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _search_funding_source(
        self,
        source: str,
        query: SearchQuery,
        research_area: Optional[str],
        eligibility: Optional[str],
        min_amount: Optional[int],
        max_amount: Optional[int]
    ) -> List[Grant]:
        """Search a specific funding source"""
        try:
            funding_source = self.funding_sources[source]
            
            if source == 'grants_gov':
                return await self._search_grants_gov(
                    query, research_area, eligibility, min_amount, max_amount
                )
            elif source == 'nsf':
                return await self._search_nsf(query, research_area)
            elif source == 'daad':
                return await self._search_daad(query, research_area)
            elif source == 'cordis':
                return await self._search_cordis(query, research_area)
            else:
                # Generic scraping approach
                return await self._generic_funding_search(
                    funding_source, query, research_area
                )
                
        except Exception as e:
            logger.error(f"Failed to search {source}: {str(e)}")
            return []
    
    async def _search_grants_gov(
        self,
        query: SearchQuery,
        research_area: Optional[str],
        eligibility: Optional[str],
        min_amount: Optional[int],
        max_amount: Optional[int]
    ) -> List[Grant]:
        """Search Grants.gov using their API"""
        try:
            # Build search parameters
            params = {
                'keyword': query.query,
                'rows': min(query.limit, 25),  # API limit
                'startRecordNum': query.offset
            }
            
            # Add research area keywords
            if research_area and research_area in self.research_keywords:
                keywords = self.research_keywords[research_area]
                params['keyword'] += ' ' + ' OR '.join(keywords)
            
            # Make API request
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/grantsws/rest/opportunities/search/",
                params=params
            )
            
            # Parse grants
            grants = []
            for opportunity in response_data.get('oppHits', []):
                grant = self._parse_grants_gov_opportunity(opportunity)
                if grant:
                    # Apply filters
                    if eligibility and eligibility.lower() not in grant.eligibility.lower():
                        continue
                    if min_amount and self._extract_amount(grant.amount) < min_amount:
                        continue
                    if max_amount and self._extract_amount(grant.amount) > max_amount:
                        continue
                    
                    grants.append(grant)
            
            return grants
            
        except Exception as e:
            logger.error(f"Grants.gov search failed: {str(e)}")
            return []
    
    async def _search_nsf(self, query: SearchQuery, research_area: Optional[str]) -> List[Grant]:
        """Search NSF funding opportunities"""
        try:
            # NSF doesn't have a public API, so this would involve web scraping
            # For now, return sample data structure
            
            # This would involve scraping NSF's funding opportunities page
            # https://www.nsf.gov/funding/
            
            sample_grants = [
                Grant(
                    id="nsf-sample-1",
                    title="Computer and Information Science and Engineering Research Initiation Initiative",
                    source=DataSource.GRANTS_GOV,
                    funding_agency="National Science Foundation",
                    description="Supports early-career faculty in computer science and engineering research",
                    deadline=datetime(2024, 12, 1),
                    amount="$175,000",
                    eligibility="Early-career faculty at US institutions",
                    topics=["computer science", "engineering"],
                    application_url="https://www.nsf.gov/funding/pgm_summ.jsp?pims_id=505813",
                    metadata={
                        'program_number': 'NSF 21-503',
                        'division': 'CISE',
                        'estimated_awards': '40-50'
                    }
                )
            ]
            
            # Filter by query and research area
            filtered_grants = []
            for grant in sample_grants:
                if query.query.lower() in grant.title.lower() or query.query.lower() in grant.description.lower():
                    if not research_area or research_area in grant.topics:
                        filtered_grants.append(grant)
            
            return filtered_grants[:query.limit]
            
        except Exception as e:
            logger.error(f"NSF search failed: {str(e)}")
            return []
    
    async def _search_daad(self, query: SearchQuery, research_area: Optional[str]) -> List[Grant]:
        """Search DAAD funding opportunities"""
        try:
            # DAAD funding database would be scraped here
            # For now, return sample data
            
            sample_grants = [
                Grant(
                    id="daad-sample-1",
                    title="Research Grants - Doctoral Programmes in Germany",
                    source=DataSource.DAAD,
                    funding_agency="German Academic Exchange Service (DAAD)",
                    description="Funding for international doctoral students in Germany",
                    deadline=datetime(2024, 11, 15),
                    amount="€1,200/month + benefits",
                    eligibility="International students with master's degree",
                    topics=["research", "doctoral studies"],
                    application_url="https://www.daad.de/en/study-and-research-in-germany/scholarships/",
                    metadata={
                        'duration': '3-4 years',
                        'location': 'Germany',
                        'type': 'scholarship'
                    }
                )
            ]
            
            # Apply basic filtering
            filtered_grants = [
                grant for grant in sample_grants
                if query.query.lower() in grant.title.lower() or query.query.lower() in grant.description.lower()
            ]
            
            return filtered_grants[:query.limit]
            
        except Exception as e:
            logger.error(f"DAAD search failed: {str(e)}")
            return []
    
    async def _search_cordis(self, query: SearchQuery, research_area: Optional[str]) -> List[Grant]:
        """Search EU CORDIS funding opportunities"""
        try:
            # CORDIS API would be used here
            # For now, return sample data
            
            sample_grants = [
                Grant(
                    id="cordis-sample-1",
                    title="Horizon Europe - Marie Skłodowska-Curie Actions",
                    source=DataSource.CORDIS,
                    funding_agency="European Union",
                    description="Fellowship program for researchers at all career stages",
                    deadline=datetime(2024, 9, 12),
                    amount="€2,000,000",
                    eligibility="Researchers at all career stages",
                    topics=["research excellence", "innovation"],
                    application_url="https://cordis.europa.eu/programme/id/HORIZON_MSCA",
                    metadata={
                        'program': 'Horizon Europe',
                        'action_type': 'MSCA',
                        'duration': '48 months'
                    }
                )
            ]
            
            # Apply basic filtering
            filtered_grants = [
                grant for grant in sample_grants
                if query.query.lower() in grant.title.lower() or query.query.lower() in grant.description.lower()
            ]
            
            return filtered_grants[:query.limit]
            
        except Exception as e:
            logger.error(f"CORDIS search failed: {str(e)}")
            return []
    
    async def _generic_funding_search(
        self,
        funding_source: FundingSource,
        query: SearchQuery,
        research_area: Optional[str]
    ) -> List[Grant]:
        """Generic funding search for sources without specific APIs"""
        try:
            # This would implement web scraping for funding sources
            # without APIs. For now, return empty list.
            logger.info(f"Generic search not implemented for {funding_source.name}")
            return []
            
        except Exception as e:
            logger.error(f"Generic funding search failed for {funding_source.name}: {str(e)}")
            return []
    
    def _parse_grants_gov_opportunity(self, opportunity: Dict[str, Any]) -> Optional[Grant]:
        """Parse a Grants.gov opportunity into a Grant object"""
        try:
            # Parse deadline
            deadline = None
            if opportunity.get('closeDate'):
                deadline = self._parse_date(opportunity['closeDate'])
            
            return Grant(
                id=opportunity.get('id', ''),
                title=self._clean_text(opportunity.get('title', '')),
                source=DataSource.GRANTS_GOV,
                url=opportunity.get('uiLink'),
                funding_agency=opportunity.get('agencyName', 'Unknown'),
                description=self._clean_text(opportunity.get('description', '')),
                deadline=deadline,
                amount=opportunity.get('awardCeiling', 'Not specified'),
                eligibility=opportunity.get('eligibilityDesc', 'See full announcement'),
                topics=[],  # Would need to extract from description
                application_url=opportunity.get('uiLink'),
                metadata={
                    'opportunity_number': opportunity.get('opportunityNumber'),
                    'category': opportunity.get('categoryName'),
                    'funding_instrument': opportunity.get('fundingInstrumentName'),
                    'cfda_number': opportunity.get('cfdaNumbers')
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse Grants.gov opportunity: {str(e)}")
            return None
    
    def _deduplicate_grants(self, grants: List[Grant]) -> List[Grant]:
        """Remove duplicate grants based on title and funding agency"""
        seen = set()
        unique_grants = []
        
        for grant in grants:
            key = f"{grant.title.lower()}-{grant.funding_agency.lower()}"
            if key not in seen:
                seen.add(key)
                unique_grants.append(grant)
        
        return unique_grants
    
    def _extract_amount(self, amount_str: str) -> int:
        """Extract numeric amount from amount string"""
        if not amount_str:
            return 0
        
        # Remove currency symbols and extract numbers
        numbers = re.findall(r'[\d,]+', amount_str.replace(',', ''))
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                return 0
        return 0
    
    async def search_papers(self, query: SearchQuery) -> SearchResponse:
        """
        Not applicable for grant service, but required by base class
        Returns empty response
        """
        return SearchResponse(
            success=False,
            query=query.query,
            data_source=DataSource.GRANTS_GOV,
            total_results=0,
            returned_results=0,
            offset=0,
            results=[],
            execution_time=0.0,
            metadata={'note': 'Paper search not supported by Grant Scraper service'}
        ) 