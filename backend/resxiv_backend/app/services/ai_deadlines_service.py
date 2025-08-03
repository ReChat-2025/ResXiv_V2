"""
AI Deadlines Service Module

This module provides access to AI/ML conference deadlines from Papers with Code
and other sources. Helps researchers stay updated on submission deadlines
for major conferences and workshops.

Key Features:
- Get upcoming AI/ML conference deadlines
- Filter by conference type, location, or research area
- Track submission, notification, and conference dates
- Get historical deadline information
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import quote
import time
import json

from .research_agent_core import (
    BaseResearchService, SearchQuery, SearchResponse, Conference,
    DataSource, RateLimitConfig, ResearchServiceError
)

logger = logging.getLogger(__name__)


class AIDeadlinesService(BaseResearchService):
    """
    Service for accessing AI/ML conference deadlines
    
    Aggregates deadline information from multiple sources including
    Papers with Code, WikiCFP, and curated deadline lists.
    """
    
    def __init__(self):
        """Initialize AI Deadlines service"""
        super().__init__(
            base_url="https://paperswithcode.com/api/v1",
            rate_limit_config=RateLimitConfig(
                requests_per_second=2.0,
                requests_per_minute=120,
                requests_per_hour=1000
            )
        )
        
        # Common AI/ML conferences and their typical deadlines
        self.major_conferences = {
            'ICLR': 'International Conference on Learning Representations',
            'NeurIPS': 'Conference on Neural Information Processing Systems',
            'ICML': 'International Conference on Machine Learning',
            'AAAI': 'AAAI Conference on Artificial Intelligence',
            'IJCAI': 'International Joint Conference on Artificial Intelligence',
            'CVPR': 'IEEE Conference on Computer Vision and Pattern Recognition',
            'ICCV': 'International Conference on Computer Vision',
            'ECCV': 'European Conference on Computer Vision',
            'ACL': 'Annual Meeting of the Association for Computational Linguistics',
            'EMNLP': 'Conference on Empirical Methods in Natural Language Processing',
            'KDD': 'ACM SIGKDD Conference on Knowledge Discovery and Data Mining',
            'WWW': 'International World Wide Web Conference',
            'CHI': 'CHI Conference on Human Factors in Computing Systems',
            'SIGIR': 'International ACM SIGIR Conference on Research and Development in Information Retrieval'
        }
    
    async def get_upcoming_deadlines(
        self,
        days_ahead: int = 90,
        conference_type: Optional[str] = None,
        research_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get upcoming AI/ML conference deadlines
        
        Args:
            days_ahead: Number of days to look ahead for deadlines
            conference_type: Filter by conference type (e.g., 'workshop', 'conference')
            research_area: Filter by research area (e.g., 'computer-vision', 'nlp')
            
        Returns:
            List of upcoming conference deadlines
        """
        start_time = time.time()
        
        try:
            # Calculate date range
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days_ahead)
            
            # Try to get deadlines from Papers with Code
            pwc_deadlines = await self._get_pwc_deadlines(
                start_date, end_date, research_area
            )
            
            # Get curated deadlines (fallback/additional source)
            curated_deadlines = self._get_curated_deadlines(
                start_date, end_date, conference_type, research_area
            )
            
            # Combine and deduplicate deadlines
            all_deadlines = self._combine_deadline_sources(
                pwc_deadlines, curated_deadlines
            )
            
            # Sort by deadline date
            all_deadlines.sort(key=lambda x: x.get('deadline') or datetime.max)
            
            return {
                'success': True,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'filters': {
                    'conference_type': conference_type,
                    'research_area': research_area
                },
                'deadlines': all_deadlines,
                'count': len(all_deadlines),
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Failed to get upcoming deadlines: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def get_conference_details(self, conference_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific conference
        
        Args:
            conference_name: Conference name or acronym
            
        Returns:
            Detailed conference information including deadlines and history
        """
        try:
            # Normalize conference name
            conf_key = conference_name.upper()
            full_name = self.major_conferences.get(conf_key, conference_name)
            
            # Search for conference in Papers with Code
            params = {
                'q': conference_name,
                'items_per_page': 10
            }
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/conferences/",
                params=params
            )
            
            # Parse conference data
            conferences = []
            for conf_data in response_data.get('results', []):
                conferences.append(self._parse_conference_data(conf_data))
            
            # Get additional deadline information
            deadline_info = self._get_conference_deadline_info(conference_name)
            
            return {
                'success': True,
                'conference_name': conference_name,
                'full_name': full_name,
                'search_results': conferences,
                'deadline_info': deadline_info,
                'historical_data': self._get_historical_conference_data(conference_name)
            }
            
        except Exception as e:
            logger.error(f"Failed to get conference details for {conference_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def search_conferences(
        self,
        query: str,
        year: Optional[int] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for conferences by name, topic, or location
        
        Args:
            query: Search query for conferences
            year: Filter by specific year
            location: Filter by location
            
        Returns:
            Conference search results
        """
        try:
            params = {
                'q': query,
                'items_per_page': 25
            }
            
            if year:
                params['year'] = year
            if location:
                params['location'] = location
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/conferences/",
                params=params
            )
            
            conferences = []
            for conf_data in response_data.get('results', []):
                conferences.append(self._parse_conference_data(conf_data))
            
            return {
                'success': True,
                'query': query,
                'filters': {'year': year, 'location': location},
                'conferences': conferences,
                'total_results': response_data.get('count', 0),
                'returned_results': len(conferences)
            }
            
        except Exception as e:
            logger.error(f"Conference search failed for {query}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_deadlines_by_area(self, research_area: str) -> Dict[str, Any]:
        """
        Get deadlines filtered by research area
        
        Args:
            research_area: Research area (e.g., 'computer-vision', 'nlp', 'machine-learning')
            
        Returns:
            Deadlines relevant to the research area
        """
        try:
            # Map research areas to conference filters
            area_mapping = {
                'computer-vision': ['CVPR', 'ICCV', 'ECCV', 'WACV'],
                'nlp': ['ACL', 'EMNLP', 'NAACL', 'COLING'],
                'machine-learning': ['ICML', 'NeurIPS', 'ICLR', 'AISTATS'],
                'ai': ['AAAI', 'IJCAI', 'UAI'],
                'data-mining': ['KDD', 'WSDM', 'CIKM'],
                'robotics': ['ICRA', 'IROS', 'RSS'],
                'hci': ['CHI', 'UIST', 'IUI']
            }
            
            relevant_conferences = area_mapping.get(research_area.lower(), [])
            
            # Get upcoming deadlines for relevant conferences
            deadlines = await self.get_upcoming_deadlines(
                days_ahead=180,
                research_area=research_area
            )
            
            # Filter for relevant conferences if mapping exists
            if relevant_conferences:
                filtered_deadlines = []
                for deadline in deadlines.get('deadlines', []):
                    conf_name = deadline.get('acronym', '').upper()
                    if any(conf in conf_name for conf in relevant_conferences):
                        filtered_deadlines.append(deadline)
                
                deadlines['deadlines'] = filtered_deadlines
                deadlines['count'] = len(filtered_deadlines)
                deadlines['filtered_for_area'] = True
                deadlines['relevant_conferences'] = relevant_conferences
            
            return deadlines
            
        except Exception as e:
            logger.error(f"Failed to get deadlines for area {research_area}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _get_pwc_deadlines(
        self,
        start_date: datetime,
        end_date: datetime,
        research_area: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get deadlines from Papers with Code API"""
        try:
            params = {
                'items_per_page': 50,
                'ordering': 'deadline'
            }
            
            if research_area:
                params['area'] = research_area
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/conferences/",
                params=params
            )
            
            deadlines = []
            for conf_data in response_data.get('results', []):
                deadline_data = self._parse_conference_data(conf_data)
                
                # Filter by date range
                if deadline_data.get('deadline'):
                    deadline_date = deadline_data['deadline']
                    if start_date <= deadline_date <= end_date:
                        deadlines.append(deadline_data)
            
            return deadlines
            
        except Exception as e:
            logger.warning(f"Failed to get PWC deadlines: {str(e)}")
            return []
    
    def _get_curated_deadlines(
        self,
        start_date: datetime,
        end_date: datetime,
        conference_type: Optional[str] = None,
        research_area: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get curated conference deadlines (fallback data)"""
        # This would typically load from a curated dataset or API
        # For now, providing some example deadlines
        curated_data = [
            {
                'id': 'neurips2024',
                'title': 'Conference on Neural Information Processing Systems',
                'acronym': 'NeurIPS',
                'deadline': datetime(2024, 5, 15),
                'notification_date': datetime(2024, 9, 25),
                'conference_date': datetime(2024, 12, 10),
                'location': 'Vancouver, Canada',
                'url': 'https://neurips.cc',
                'type': 'conference',
                'research_areas': ['machine-learning', 'ai']
            },
            {
                'id': 'iclr2025',
                'title': 'International Conference on Learning Representations',
                'acronym': 'ICLR',
                'deadline': datetime(2024, 10, 1),
                'notification_date': datetime(2025, 1, 15),
                'conference_date': datetime(2025, 5, 1),
                'location': 'Singapore',
                'url': 'https://iclr.cc',
                'type': 'conference',
                'research_areas': ['machine-learning', 'deep-learning']
            }
        ]
        
        # Filter by date range and criteria
        filtered_deadlines = []
        for deadline in curated_data:
            deadline_date = deadline.get('deadline')
            if deadline_date and start_date <= deadline_date <= end_date:
                # Apply filters
                if conference_type and deadline.get('type') != conference_type:
                    continue
                if research_area and research_area not in deadline.get('research_areas', []):
                    continue
                
                filtered_deadlines.append(deadline)
        
        return filtered_deadlines
    
    def _combine_deadline_sources(
        self,
        pwc_deadlines: List[Dict[str, Any]],
        curated_deadlines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Combine and deduplicate deadlines from multiple sources"""
        all_deadlines = []
        seen_conferences = set()
        
        # Add PWC deadlines first
        for deadline in pwc_deadlines:
            key = f"{deadline.get('acronym', '')}-{deadline.get('deadline', '').year if deadline.get('deadline') else ''}"
            if key not in seen_conferences:
                deadline['source'] = 'papers_with_code'
                all_deadlines.append(deadline)
                seen_conferences.add(key)
        
        # Add curated deadlines if not already present
        for deadline in curated_deadlines:
            key = f"{deadline.get('acronym', '')}-{deadline.get('deadline', '').year if deadline.get('deadline') else ''}"
            if key not in seen_conferences:
                deadline['source'] = 'curated'
                all_deadlines.append(deadline)
                seen_conferences.add(key)
        
        return all_deadlines
    
    def _parse_conference_data(self, conf_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse conference data from API response"""
        # Parse dates
        deadline = None
        notification_date = None
        conference_date = None
        
        if conf_data.get('deadline'):
            deadline = self._parse_date(conf_data['deadline'])
        if conf_data.get('notification_date'):
            notification_date = self._parse_date(conf_data['notification_date'])
        if conf_data.get('start_date'):
            conference_date = self._parse_date(conf_data['start_date'])
        
        return {
            'id': conf_data.get('id'),
            'title': conf_data.get('name') or conf_data.get('title'),
            'acronym': conf_data.get('acronym'),
            'deadline': deadline,
            'notification_date': notification_date,
            'conference_date': conference_date,
            'location': conf_data.get('location'),
            'url': conf_data.get('url') or conf_data.get('website'),
            'type': conf_data.get('type', 'conference'),
            'description': conf_data.get('description'),
            'tracks': conf_data.get('tracks', []),
            'submission_types': conf_data.get('submission_types', [])
        }
    
    def _get_conference_deadline_info(self, conference_name: str) -> Dict[str, Any]:
        """Get additional deadline information for a conference"""
        # This would typically query additional sources or databases
        # For now, return basic deadline patterns
        
        patterns = {
            'NEURIPS': {
                'typical_deadline_month': 'May',
                'typical_notification_month': 'September',
                'typical_conference_month': 'December',
                'submission_rounds': 1,
                'review_process': 'Double-blind peer review'
            },
            'ICLR': {
                'typical_deadline_month': 'October',
                'typical_notification_month': 'January',
                'typical_conference_month': 'May',
                'submission_rounds': 1,
                'review_process': 'Open peer review'
            },
            'ICML': {
                'typical_deadline_month': 'February',
                'typical_notification_month': 'May',
                'typical_conference_month': 'July',
                'submission_rounds': 1,
                'review_process': 'Double-blind peer review'
            }
        }
        
        return patterns.get(conference_name.upper(), {
            'note': 'No specific deadline pattern available'
        })
    
    def _get_historical_conference_data(self, conference_name: str) -> Dict[str, Any]:
        """Get historical data for a conference"""
        # This would typically query a database of historical conference data
        return {
            'note': 'Historical data would be loaded from database',
            'available_years': [],
            'acceptance_rates': {},
            'submission_counts': {}
        }
    
    async def search_papers(self, query: SearchQuery) -> SearchResponse:
        """
        Not applicable for deadlines service, but required by base class
        Returns empty response
        """
        return SearchResponse(
            success=False,
            query=query.query,
            data_source=DataSource.AI_DEADLINES,
            total_results=0,
            returned_results=0,
            offset=0,
            results=[],
            execution_time=0.0,
            metadata={'note': 'Paper search not supported by AI Deadlines service'}
        ) 