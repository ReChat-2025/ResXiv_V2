"""
Research Agent Configuration Settings

This module handles configuration for all research agent services including
API keys, rate limits, and service-specific settings.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class ResearchAgentSettings(BaseSettings):
    """Research Agent configuration settings"""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
        "env_prefix": "RESEARCH_"  # All research agent env vars start with RESEARCH_
    }
    
    # OpenAlex Settings
    openalex_email: Optional[str] = Field(default=None, env="RESEARCH_OPENALEX_EMAIL")
    openalex_rate_limit_per_second: float = Field(default=3.0, env="RESEARCH_OPENALEX_RATE_LIMIT_PER_SECOND")
    
    # Semantic Scholar Settings
    semantic_scholar_api_key: Optional[str] = Field(default=None, env="RESEARCH_SEMANTIC_SCHOLAR_API_KEY")
    semantic_scholar_rate_limit_per_second: float = Field(default=1.0, env="RESEARCH_SEMANTIC_SCHOLAR_RATE_LIMIT_PER_SECOND")
    
    # Papers with Code Settings
    papers_with_code_rate_limit_per_second: float = Field(default=2.0, env="RESEARCH_PAPERS_WITH_CODE_RATE_LIMIT_PER_SECOND")
    
    # AI Deadlines Settings
    ai_deadlines_rate_limit_per_second: float = Field(default=2.0, env="RESEARCH_AI_DEADLINES_RATE_LIMIT_PER_SECOND")
    
    # Grant Scraper Settings
    grants_gov_rate_limit_per_second: float = Field(default=0.5, env="RESEARCH_GRANTS_GOV_RATE_LIMIT_PER_SECOND")
    
    # General Settings
    default_cache_ttl: int = Field(default=3600, env="RESEARCH_DEFAULT_CACHE_TTL")  # 1 hour
    max_concurrent_requests: int = Field(default=10, env="RESEARCH_MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="RESEARCH_REQUEST_TIMEOUT")
    
    # Result Limits
    max_results_per_source: int = Field(default=100, env="RESEARCH_MAX_RESULTS_PER_SOURCE")
    default_results_limit: int = Field(default=20, env="RESEARCH_DEFAULT_RESULTS_LIMIT")
    
    # Cross-referencing Settings
    enable_cross_referencing: bool = Field(default=True, env="RESEARCH_ENABLE_CROSS_REFERENCING")
    similarity_threshold: float = Field(default=0.8, env="RESEARCH_SIMILARITY_THRESHOLD")
    
    # Caching Settings
    enable_caching: bool = Field(default=True, env="RESEARCH_ENABLE_CACHING")
    cache_backend: str = Field(default="memory", env="RESEARCH_CACHE_BACKEND")  # memory, redis
    
    # Logging Settings
    log_level: str = Field(default="INFO", env="RESEARCH_LOG_LEVEL")
    enable_request_logging: bool = Field(default=True, env="RESEARCH_ENABLE_REQUEST_LOGGING")
    
    # Service Availability Flags
    enable_openalex: bool = Field(default=True, env="RESEARCH_ENABLE_OPENALEX")
    enable_semantic_scholar: bool = Field(default=True, env="RESEARCH_ENABLE_SEMANTIC_SCHOLAR")
    enable_papers_with_code: bool = Field(default=True, env="RESEARCH_ENABLE_PAPERS_WITH_CODE")
    enable_ai_deadlines: bool = Field(default=True, env="RESEARCH_ENABLE_AI_DEADLINES")
    enable_grant_scraper: bool = Field(default=True, env="RESEARCH_ENABLE_GRANT_SCRAPER")
    
    @property
    def has_semantic_scholar_api_key(self) -> bool:
        """Check if Semantic Scholar API key is available"""
        return bool(self.semantic_scholar_api_key)
    
    @property
    def has_openalex_email(self) -> bool:
        """Check if OpenAlex email is configured for polite pooling"""
        return bool(self.openalex_email)
    
    def get_rate_limit_config(self, service: str) -> dict:
        """Get rate limit configuration for a specific service"""
        rate_limits = {
            "openalex": {
                "requests_per_second": self.openalex_rate_limit_per_second * (2.0 if self.has_openalex_email else 1.0),
                "requests_per_minute": int(self.openalex_rate_limit_per_second * 60 * (2.0 if self.has_openalex_email else 1.0)),
                "requests_per_hour": int(self.openalex_rate_limit_per_second * 3600 * (2.0 if self.has_openalex_email else 1.0))
            },
            "semantic_scholar": {
                "requests_per_second": self.semantic_scholar_rate_limit_per_second * (5.0 if self.has_semantic_scholar_api_key else 1.0),
                "requests_per_minute": int(self.semantic_scholar_rate_limit_per_second * 60 * (5.0 if self.has_semantic_scholar_api_key else 1.0)),
                "requests_per_hour": int(self.semantic_scholar_rate_limit_per_second * 3600 * (5.0 if self.has_semantic_scholar_api_key else 1.0))
            },
            "papers_with_code": {
                "requests_per_second": self.papers_with_code_rate_limit_per_second,
                "requests_per_minute": int(self.papers_with_code_rate_limit_per_second * 60),
                "requests_per_hour": int(self.papers_with_code_rate_limit_per_second * 3600)
            },
            "ai_deadlines": {
                "requests_per_second": self.ai_deadlines_rate_limit_per_second,
                "requests_per_minute": int(self.ai_deadlines_rate_limit_per_second * 60),
                "requests_per_hour": int(self.ai_deadlines_rate_limit_per_second * 3600)
            },
            "grant_scraper": {
                "requests_per_second": self.grants_gov_rate_limit_per_second,
                "requests_per_minute": int(self.grants_gov_rate_limit_per_second * 60),
                "requests_per_hour": int(self.grants_gov_rate_limit_per_second * 3600)
            }
        }
        
        return rate_limits.get(service, {
            "requests_per_second": 1.0,
            "requests_per_minute": 60,
            "requests_per_hour": 1000
        })
    
    def get_enabled_services(self) -> list:
        """Get list of enabled research agent services"""
        enabled = []
        
        if self.enable_openalex:
            enabled.append("openalex")
        if self.enable_semantic_scholar:
            enabled.append("semantic_scholar")
        if self.enable_papers_with_code:
            enabled.append("papers_with_code")
        if self.enable_ai_deadlines:
            enabled.append("ai_deadlines")
        if self.enable_grant_scraper:
            enabled.append("grant_scraper")
        
        return enabled


@lru_cache()
def get_research_agent_settings() -> ResearchAgentSettings:
    """Get cached research agent settings instance"""
    return ResearchAgentSettings()


# Convenience function to create pre-configured service instances
def create_research_services() -> dict:
    """
    Create pre-configured research service instances
    
    Returns:
        Dictionary of initialized research services
    """
    settings = get_research_agent_settings()
    services = {}
    
    try:
        if settings.enable_openalex:
            from ..services.openalex_service import OpenAlexService
            services['openalex'] = OpenAlexService(email=settings.openalex_email)
        
        if settings.enable_semantic_scholar:
            from ..services.semantic_scholar_service import SemanticScholarService
            services['semantic_scholar'] = SemanticScholarService(api_key=settings.semantic_scholar_api_key)
        
        if settings.enable_papers_with_code:
            from ..services.papers_with_code_service import PapersWithCodeService
            services['papers_with_code'] = PapersWithCodeService()
        
        if settings.enable_ai_deadlines:
            from ..services.ai_deadlines_service import AIDeadlinesService
            services['ai_deadlines'] = AIDeadlinesService()
        
        if settings.enable_grant_scraper:
            from ..services.grant_scraper_service import GrantScraperService
            services['grant_scraper'] = GrantScraperService()
        
        # Create aggregator service with configured sub-services
        from ..services.research_aggregator_service import ResearchAggregatorService
        services['aggregator'] = ResearchAggregatorService(
            openalex_email=settings.openalex_email,
            semantic_scholar_api_key=settings.semantic_scholar_api_key
        )
        
    except ImportError as e:
        # Handle case where services are not available
        print(f"Warning: Could not import research services: {e}")
    
    return services


# Service health check
async def check_research_services_health() -> dict:
    """
    Check the health/availability of all research services
    
    Returns:
        Dictionary with health status of each service
    """
    settings = get_research_agent_settings()
    health_status = {}
    
    # This would implement actual health checks by making test requests
    # For now, return basic configuration status
    
    health_status['openalex'] = {
        'enabled': settings.enable_openalex,
        'configured': settings.has_openalex_email,
        'status': 'available' if settings.enable_openalex else 'disabled'
    }
    
    health_status['semantic_scholar'] = {
        'enabled': settings.enable_semantic_scholar,
        'configured': settings.has_semantic_scholar_api_key,
        'status': 'available' if settings.enable_semantic_scholar else 'disabled'
    }
    
    health_status['papers_with_code'] = {
        'enabled': settings.enable_papers_with_code,
        'configured': True,  # No API key required
        'status': 'available' if settings.enable_papers_with_code else 'disabled'
    }
    
    health_status['ai_deadlines'] = {
        'enabled': settings.enable_ai_deadlines,
        'configured': True,  # No API key required
        'status': 'available' if settings.enable_ai_deadlines else 'disabled'
    }
    
    health_status['grant_scraper'] = {
        'enabled': settings.enable_grant_scraper,
        'configured': True,  # No API key required
        'status': 'available' if settings.enable_grant_scraper else 'disabled'
    }
    
    return health_status 