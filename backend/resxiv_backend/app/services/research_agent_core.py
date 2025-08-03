"""
Research Agent Core Module

This module provides base classes, interfaces, and common functionality
for all research agent services. It follows SOLID principles and provides
a consistent interface for different research data sources.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchSortBy(str, Enum):
    """Enumeration for search sorting options"""
    RELEVANCE = "relevance"
    DATE = "date"
    CITATIONS = "citations"
    ALPHABETICAL = "alphabetical"


class SearchSortOrder(str, Enum):
    """Enumeration for search sort order"""
    ASCENDING = "asc"
    DESCENDING = "desc"


class DataSource(str, Enum):
    """Enumeration for different data sources"""
    OPENALEX = "openalex"
    PAPERS_WITH_CODE = "papers_with_code"
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"  # Added to support Semantic Scholar references
    CROSSREF = "crossref"
    AI_DEADLINES = "ai_deadlines"
    GRANTS_GOV = "grants_gov"
    DAAD = "daad"
    CORDIS = "cordis"


@dataclass
class RateLimitConfig:
    """Configuration for API rate limiting"""
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    backoff_factor: float = 2.0
    max_backoff: float = 300.0


class SearchFilter(BaseModel):
    """Generic search filter model"""
    field: str
    operator: str = "eq"  # eq, ne, gt, lt, gte, lte, in, contains
    value: Union[str, int, float, List[str]]


class SearchQuery(BaseModel):
    """Standardized search query model across all services"""
    query: str
    filters: Optional[List[SearchFilter]] = None
    sort_by: SearchSortBy = SearchSortBy.RELEVANCE
    sort_order: SearchSortOrder = SearchSortOrder.DESCENDING
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    date_range: Optional[Tuple[datetime, datetime]] = None


class ResearchResult(BaseModel):
    """Base model for research results"""
    id: str
    title: str
    source: DataSource
    url: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    relevance_score: Optional[float] = None


class Author(BaseModel):
    """Author information model"""
    id: Optional[str] = None
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None
    orcid: Optional[str] = None
    h_index: Optional[int] = None
    citation_count: Optional[int] = None
    url: Optional[str] = None


class Paper(ResearchResult):
    """Paper-specific result model"""
    authors: List[Author] = Field(default_factory=list)
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    publication_date: Optional[datetime] = None
    venue: Optional[str] = None
    venue_type: Optional[str] = None  # conference, journal, preprint
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    topics: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    pdf_url: Optional[str] = None


class Dataset(ResearchResult):
    """Dataset-specific result model"""
    paper_id: Optional[str] = None
    paper_title: Optional[str] = None
    task: Optional[str] = None
    modality: Optional[str] = None
    size: Optional[str] = None
    download_url: Optional[str] = None


class Model(ResearchResult):
    """ML Model-specific result model"""
    paper_id: Optional[str] = None
    paper_title: Optional[str] = None
    task: Optional[str] = None
    dataset: Optional[str] = None
    architecture: Optional[str] = None
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    model_url: Optional[str] = None


class Conference(ResearchResult):
    """Conference-specific result model"""
    acronym: Optional[str] = None
    full_name: Optional[str] = None
    deadline: Optional[datetime] = None
    notification_date: Optional[datetime] = None
    conference_date: Optional[datetime] = None
    location: Optional[str] = None
    track: Optional[str] = None
    url: Optional[str] = None


class Grant(ResearchResult):
    """Grant/Funding opportunity result model"""
    funding_agency: str
    deadline: Optional[datetime] = None
    amount: Optional[str] = None
    eligibility: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    application_url: Optional[str] = None


class SearchResponse(BaseModel):
    """Standardized response model for search operations"""
    success: bool
    query: str
    data_source: DataSource
    total_results: int
    returned_results: int
    offset: int
    results: List[ResearchResult]
    execution_time: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RateLimiter:
    """Advanced rate limiter for API requests"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests = []
        self.current_delay = 0.0
        self._lock = asyncio.Lock()
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        async with self._lock:
            now = datetime.utcnow()
            
            # Clean old requests
            cutoff = now - timedelta(seconds=60)
            self.requests = [req_time for req_time in self.requests if req_time > cutoff]
            
            # Check if we need to wait
            if len(self.requests) >= self.config.requests_per_minute:
                wait_time = max(self.current_delay, 1.0 / self.config.requests_per_second)
                await asyncio.sleep(wait_time)
                self.current_delay = min(
                    self.current_delay * self.config.backoff_factor,
                    self.config.max_backoff
                )
            else:
                self.current_delay = max(0.0, self.current_delay * 0.9)
            
            self.requests.append(now)


class BaseResearchService(ABC):
    """
    Abstract base class for all research services.
    Implements common functionality and defines the interface.
    """
    
    def __init__(self, base_url: str, rate_limit_config: Optional[RateLimitConfig] = None):
        self.base_url = base_url
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.headers = {
            'User-Agent': 'ResXiv-Research-Agent/1.0'
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers
            )
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make a rate-limited HTTP request
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            json_data: JSON data for POST requests
            headers: Additional headers
            
        Returns:
            Response JSON data
            
        Raises:
            aiohttp.ClientError: For HTTP errors
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
                json=json_data,
                headers=request_headers
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {str(e)}")
            raise
    
    @abstractmethod
    async def search_papers(self, query: SearchQuery) -> SearchResponse:
        """Search for papers"""
        pass
    
    def _build_search_url(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Build search URL with parameters"""
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize text"""
        if not text:
            return None
        
        # Basic text cleaning
        text = text.strip()
        text = ' '.join(text.split())  # Normalize whitespace
        return text if text else None


class ResearchServiceFactory:
    """Factory for creating research service instances"""
    
    _services = {}
    
    @classmethod
    def register_service(cls, data_source: DataSource, service_class):
        """Register a service class for a data source"""
        cls._services[data_source] = service_class
    
    @classmethod
    def create_service(cls, data_source: DataSource, **kwargs) -> BaseResearchService:
        """Create a service instance for the given data source"""
        if data_source not in cls._services:
            raise ValueError(f"No service registered for {data_source}")
        
        service_class = cls._services[data_source]
        return service_class(**kwargs)
    
    @classmethod
    def get_available_sources(cls) -> List[DataSource]:
        """Get list of available data sources"""
        return list(cls._services.keys())


# Error classes
class ResearchServiceError(Exception):
    """Base exception for research service errors"""
    pass


class RateLimitError(ResearchServiceError):
    """Raised when rate limit is exceeded"""
    pass


class AuthenticationError(ResearchServiceError):
    """Raised when authentication fails"""
    pass


class DataNotFoundError(ResearchServiceError):
    """Raised when requested data is not found"""
    pass 