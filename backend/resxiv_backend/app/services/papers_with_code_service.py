"""
PapersWithCode Service Module

This module provides access to Papers with Code API for machine learning
research data including datasets, models, benchmarks, and code repositories.

Key Features:
- Find relevant datasets by paper, task, model, author
- Find relevant models by paper, task, dataset
- Find models and datasets used in a paper
- Find papers using a dataset
- Find models used in a domain
- Get conference deadlines for AI/ML venues
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from urllib.parse import quote
import time

from .research_agent_core import (
    BaseResearchService, SearchQuery, SearchResponse, Paper, Dataset, Model, 
    Conference, DataSource, RateLimitConfig, ResearchServiceError
)

logger = logging.getLogger(__name__)


class PapersWithCodeService(BaseResearchService):
    """
    Service for accessing Papers with Code API
    
    Papers with Code tracks machine learning papers, datasets, models,
    and benchmarks with state-of-the-art results.
    """
    
    def __init__(self):
        """Initialize Papers with Code service"""
        super().__init__(
            base_url="https://paperswithcode.com/api/v1",
            rate_limit_config=RateLimitConfig(
                requests_per_second=2.0,  # Conservative rate limiting
                requests_per_minute=120,
                requests_per_hour=1000
            )
        )
    
    async def search_papers(
        self,
        query: SearchQuery,
        task: Optional[str] = None,
        dataset: Optional[str] = None
    ) -> SearchResponse:
        """
        Search for papers in Papers with Code
        
        Args:
            query: Search query parameters
            task: Filter by specific ML task
            dataset: Filter by specific dataset
            
        Returns:
            SearchResponse with Paper objects
        """
        start_time = time.time()
        
        try:
            # Build search parameters
            params = {
                'q': query.query,
                'page': (query.offset // query.limit) + 1,
                'items_per_page': min(query.limit, 50)  # PWC API limit
            }
            
            if task:
                params['task'] = task
            if dataset:
                params['dataset'] = dataset
            
            # Make request
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/papers/",
                params=params
            )
            
            # Parse results
            papers = self._parse_papers_response(response_data)
            
            return SearchResponse(
                success=True,
                query=query.query,
                data_source=DataSource.PAPERS_WITH_CODE,
                total_results=response_data.get('count', 0),
                returned_results=len(papers),
                offset=query.offset,
                results=papers,
                execution_time=time.time() - start_time,
                metadata={
                    'task_filter': task,
                    'dataset_filter': dataset,
                    'next_page': response_data.get('next')
                }
            )
            
        except Exception as e:
            logger.error(f"PapersWithCode paper search failed: {str(e)}")
            return SearchResponse(
                success=False,
                query=query.query,
                data_source=DataSource.PAPERS_WITH_CODE,
                total_results=0,
                returned_results=0,
                offset=query.offset,
                results=[],
                execution_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
    
    async def search_datasets(
        self,
        query: Optional[str] = None,
        task: Optional[str] = None,
        modality: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for datasets
        
        Args:
            query: Search query for datasets
            task: Filter by ML task
            modality: Filter by data modality (text, image, audio, etc.)
            limit: Number of results
            offset: Offset for pagination
            
        Returns:
            Dictionary with dataset search results
        """
        start_time = time.time()
        
        try:
            params = {
                'page': (offset // limit) + 1,
                'items_per_page': min(limit, 50)
            }
            
            if query:
                params['q'] = query
            if task:
                params['task'] = task
            if modality:
                params['modality'] = modality
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/datasets/",
                params=params
            )
            
            datasets = self._parse_datasets_response(response_data)
            
            return {
                'success': True,
                'query': query,
                'total_results': response_data.get('count', 0),
                'returned_results': len(datasets),
                'datasets': datasets,
                'execution_time': time.time() - start_time,
                'metadata': {
                    'task_filter': task,
                    'modality_filter': modality
                }
            }
            
        except Exception as e:
            logger.error(f"Dataset search failed: {str(e)}")
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def search_models(
        self,
        query: Optional[str] = None,
        task: Optional[str] = None,
        dataset: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for models and their performance
        
        Args:
            query: Search query for models
            task: Filter by ML task
            dataset: Filter by dataset used
            limit: Number of results
            offset: Offset for pagination
            
        Returns:
            Dictionary with model search results
        """
        start_time = time.time()
        
        try:
            params = {
                'page': (offset // limit) + 1,
                'items_per_page': min(limit, 50)
            }
            
            if query:
                params['q'] = query
            if task:
                params['task'] = task
            if dataset:
                params['dataset'] = dataset
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/methods/",
                params=params
            )
            
            models = self._parse_models_response(response_data)
            
            return {
                'success': True,
                'query': query,
                'total_results': response_data.get('count', 0),
                'returned_results': len(models),
                'models': models,
                'execution_time': time.time() - start_time,
                'metadata': {
                    'task_filter': task,
                    'dataset_filter': dataset
                }
            }
            
        except Exception as e:
            logger.error(f"Model search failed: {str(e)}")
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific paper
        
        Args:
            paper_id: Papers with Code paper ID
            
        Returns:
            Detailed paper information including datasets and models used
        """
        try:
            # Get paper data
            paper_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/papers/{paper_id}/"
            )
            
            # Get paper's datasets
            datasets_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/papers/{paper_id}/datasets/"
            )
            
            # Get paper's models/methods
            methods_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/papers/{paper_id}/methods/"
            )
            
            # Get paper's results/benchmarks
            results_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/papers/{paper_id}/results/"
            )
            
            return {
                'success': True,
                'paper': self._parse_paper_detail(paper_response),
                'datasets': self._parse_datasets_response(datasets_response),
                'methods': self._parse_models_response(methods_response),
                'results': results_response.get('results', []),
                'repository': paper_response.get('github_repository')
            }
            
        except Exception as e:
            logger.error(f"Failed to get paper details for {paper_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_dataset_details(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific dataset
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Detailed dataset information including papers that use it
        """
        try:
            # Get dataset data
            dataset_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/datasets/{dataset_id}/"
            )
            
            # Get papers using this dataset
            papers_response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/datasets/{dataset_id}/papers/"
            )
            
            return {
                'success': True,
                'dataset': self._parse_dataset_detail(dataset_response),
                'papers_using_dataset': self._parse_papers_response(papers_response),
                'usage_count': papers_response.get('count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get dataset details for {dataset_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_task_leaderboard(
        self,
        task: str,
        dataset: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get leaderboard for a specific task
        
        Args:
            task: ML task name
            dataset: Optional dataset filter
            limit: Number of results
            
        Returns:
            Leaderboard with top-performing models
        """
        try:
            params = {
                'task': task,
                'items_per_page': min(limit, 50),
                'ordering': '-score'  # Order by score descending
            }
            
            if dataset:
                params['dataset'] = dataset
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/results/",
                params=params
            )
            
            return {
                'success': True,
                'task': task,
                'dataset': dataset,
                'leaderboard': response_data.get('results', []),
                'total_entries': response_data.get('count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get leaderboard for task {task}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_trending_papers(
        self,
        task: Optional[str] = None,
        days: int = 7,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get trending papers based on recent activity
        
        Args:
            task: Filter by specific task
            days: Time window for trending (not directly supported by API)
            limit: Number of results
            
        Returns:
            List of trending papers
        """
        try:
            params = {
                'items_per_page': min(limit, 50),
                'ordering': '-stars'  # Order by GitHub stars as proxy for trending
            }
            
            if task:
                params['task'] = task
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/papers/",
                params=params
            )
            
            papers = self._parse_papers_response(response_data)
            
            return {
                'success': True,
                'task': task,
                'papers': papers,
                'total_found': response_data.get('count', 0),
                'note': 'Trending based on GitHub stars due to API limitations'
            }
            
        except Exception as e:
            logger.error(f"Trending papers search failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def search_by_author(
        self,
        author_name: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search papers by author name
        
        Args:
            author_name: Author name to search for
            limit: Number of results
            offset: Offset for pagination
            
        Returns:
            Papers by the specified author
        """
        try:
            params = {
                'q': f'author:"{author_name}"',
                'page': (offset // limit) + 1,
                'items_per_page': min(limit, 50)
            }
            
            response_data = await self._make_request(
                method="GET",
                url=f"{self.base_url}/papers/",
                params=params
            )
            
            papers = self._parse_papers_response(response_data)
            
            return {
                'success': True,
                'author': author_name,
                'papers': papers,
                'total_found': response_data.get('count', 0)
            }
            
        except Exception as e:
            logger.error(f"Author search failed for {author_name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_papers_response(self, response_data: Dict[str, Any]) -> List[Paper]:
        """Parse Papers with Code papers response into Paper objects"""
        papers = []
        
        for paper_data in response_data.get('results', []):
            try:
                # Parse publication date
                pub_date = None
                if paper_data.get('published'):
                    pub_date = self._parse_date(paper_data['published'])
                
                # Extract repository URL
                repo_url = None
                if paper_data.get('github_repository'):
                    repo_url = f"https://github.com/{paper_data['github_repository']}"
                
                paper = Paper(
                    id=paper_data.get('id', ''),
                    title=self._clean_text(paper_data.get('title', '')),
                    source=DataSource.PAPERS_WITH_CODE,
                    url=paper_data.get('url_abs') or paper_data.get('url_pdf'),
                    description=self._clean_text(paper_data.get('abstract')),
                    abstract=self._clean_text(paper_data.get('abstract')),
                    arxiv_id=paper_data.get('arxiv_id'),
                    publication_date=pub_date,
                    venue=paper_data.get('venue'),
                    pdf_url=paper_data.get('url_pdf'),
                    metadata={
                        'pwc_id': paper_data.get('id'),
                        'github_repository': paper_data.get('github_repository'),
                        'github_stars': paper_data.get('github_stars'),
                        'tasks': paper_data.get('tasks', []),
                        'datasets': paper_data.get('datasets', []),
                        'methods': paper_data.get('methods', []),
                        'repo_url': repo_url
                    }
                )
                
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Failed to parse paper: {str(e)}")
                continue
        
        return papers
    
    def _parse_datasets_response(self, response_data: Dict[str, Any]) -> List[Dataset]:
        """Parse datasets response into Dataset objects"""
        datasets = []
        
        for dataset_data in response_data.get('results', []):
            try:
                dataset = Dataset(
                    id=dataset_data.get('id', ''),
                    title=self._clean_text(dataset_data.get('name', '')),
                    source=DataSource.PAPERS_WITH_CODE,
                    url=dataset_data.get('url'),
                    description=self._clean_text(dataset_data.get('description')),
                    task=dataset_data.get('task'),
                    modality=dataset_data.get('modality'),
                    size=dataset_data.get('size'),
                    download_url=dataset_data.get('download_url'),
                    metadata={
                        'pwc_id': dataset_data.get('id'),
                        'full_name': dataset_data.get('full_name'),
                        'homepage': dataset_data.get('homepage'),
                        'languages': dataset_data.get('languages', []),
                        'licenses': dataset_data.get('licenses', []),
                        'paper_count': dataset_data.get('paper_count', 0)
                    }
                )
                
                datasets.append(dataset)
                
            except Exception as e:
                logger.warning(f"Failed to parse dataset: {str(e)}")
                continue
        
        return datasets
    
    def _parse_models_response(self, response_data: Dict[str, Any]) -> List[Model]:
        """Parse models/methods response into Model objects"""
        models = []
        
        for model_data in response_data.get('results', []):
            try:
                model = Model(
                    id=model_data.get('id', ''),
                    title=self._clean_text(model_data.get('name', '')),
                    source=DataSource.PAPERS_WITH_CODE,
                    url=model_data.get('url'),
                    description=self._clean_text(model_data.get('description')),
                    paper_id=model_data.get('paper_id'),
                    paper_title=model_data.get('paper_title'),
                    metadata={
                        'pwc_id': model_data.get('id'),
                        'full_name': model_data.get('full_name'),
                        'categories': model_data.get('categories', []),
                        'collections': model_data.get('collections', []),
                        'paper_count': model_data.get('paper_count', 0)
                    }
                )
                
                models.append(model)
                
            except Exception as e:
                logger.warning(f"Failed to parse model: {str(e)}")
                continue
        
        return models
    
    def _parse_paper_detail(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse detailed paper information"""
        return {
            'id': paper_data.get('id'),
            'title': paper_data.get('title'),
            'abstract': paper_data.get('abstract'),
            'arxiv_id': paper_data.get('arxiv_id'),
            'url_abs': paper_data.get('url_abs'),
            'url_pdf': paper_data.get('url_pdf'),
            'published': paper_data.get('published'),
            'venue': paper_data.get('venue'),
            'github_repository': paper_data.get('github_repository'),
            'github_stars': paper_data.get('github_stars'),
            'authors': paper_data.get('authors', []),
            'tasks': paper_data.get('tasks', []),
            'datasets': paper_data.get('datasets', []),
            'methods': paper_data.get('methods', [])
        }
    
    def _parse_dataset_detail(self, dataset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse detailed dataset information"""
        return {
            'id': dataset_data.get('id'),
            'name': dataset_data.get('name'),
            'full_name': dataset_data.get('full_name'),
            'description': dataset_data.get('description'),
            'url': dataset_data.get('url'),
            'homepage': dataset_data.get('homepage'),
            'download_url': dataset_data.get('download_url'),
            'modality': dataset_data.get('modality'),
            'task': dataset_data.get('task'),
            'languages': dataset_data.get('languages', []),
            'licenses': dataset_data.get('licenses', []),
            'size': dataset_data.get('size'),
            'paper_count': dataset_data.get('paper_count', 0)
        } 