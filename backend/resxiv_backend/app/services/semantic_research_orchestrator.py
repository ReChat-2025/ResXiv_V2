"""
Semantic Research Orchestrator

Production-grade research orchestrator using LangGraph for intelligent
query understanding, service selection, and result aggregation.

Key Features:
- Semantic query understanding using LLM
- Smart service selection based on query intent
- Progressive search with fallback strategies
- Intelligent caching and result ranking
- Clean state management with focused responsibilities
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime, timedelta
import json
import hashlib
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .research_agent_core import SearchQuery, SearchResponse, Paper, DataSource
from .research_aggregator_service import ResearchAggregatorService

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Research query types for intelligent service selection"""
    PAPER_SEARCH = "paper_search"
    AUTHOR_ANALYSIS = "author_analysis"
    TREND_ANALYSIS = "trend_analysis"
    RECENT_WORK = "recent_work"
    HIGHLY_CITED = "highly_cited"
    DATASET_FOCUSED = "dataset_focused"


class ServicePriority(str, Enum):
    """Service priority levels for progressive search"""
    HIGH = "high"
    MEDIUM = "medium" 
    LOW = "low"


@dataclass
class QueryIntent:
    """Structured representation of user query intent"""
    query_type: QueryType
    search_terms: List[str]
    field_of_study: str
    temporal_focus: Optional[str] = None  # "recent", "historical", None
    specific_authors: List[str] = None
    specific_venues: List[str] = None
    search_strategy: str = "comprehensive"


@dataclass
class ServiceSelection:
    """Smart service selection based on query intent"""
    primary_services: List[DataSource]
    secondary_services: List[DataSource]
    service_configs: Dict[DataSource, Dict[str, Any]]


class SearchState(TypedDict):
    """State for the research search graph"""
    original_query: str
    query_intent: Optional[QueryIntent]
    service_selection: Optional[ServiceSelection]
    search_results: Dict[str, Any]
    final_results: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_metadata: Dict[str, Any]


class SemanticResearchOrchestrator:
    """
    Production-grade research orchestrator using semantic understanding
    and intelligent service orchestration via LangGraph.
    """
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=openai_api_key,
            temperature=0.1
        )
        self.cache = {}
        self.cache_ttl = timedelta(hours=1)
        self.graph = self._build_search_graph()
        
    def _build_search_graph(self) -> StateGraph:
        """Build the LangGraph for semantic research orchestration"""
        workflow = StateGraph(SearchState)
        
        # Add nodes with clear responsibilities
        workflow.add_node("understand_query", self._understand_query)
        workflow.add_node("select_services", self._select_services)
        workflow.add_node("execute_search", self._execute_search)
        workflow.add_node("rank_results", self._rank_results)
        
        # Define clean flow
        workflow.set_entry_point("understand_query")
        workflow.add_edge("understand_query", "select_services")
        workflow.add_edge("select_services", "execute_search")
        workflow.add_edge("execute_search", "rank_results")
        workflow.add_edge("rank_results", END)
        
        return workflow.compile()
    
    async def search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Execute semantic research search
        
        Args:
            query: Natural language research query
            limit: Maximum number of results
            
        Returns:
            Comprehensive search results with metadata
        """
        start_time = datetime.utcnow()
        
        # Check cache first
        cache_key = self._generate_cache_key(query, limit)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            logger.info(f"Returning cached result for query: {query[:50]}...")
            return cached_result
        
        try:
            # Initialize state
            initial_state = SearchState(
                original_query=query,
                query_intent=None,
                service_selection=None,
                search_results={},
                final_results=None,
                error=None,
                execution_metadata={
                    "start_time": start_time.isoformat(),
                    "limit": limit
                }
            )
            
            # Execute graph
            result_state = await self.graph.ainvoke(initial_state)
            
            # Extract results
            if result_state.get("error"):
                return {
                    "success": False,
                    "error": result_state["error"],
                    "query": query,
                    "execution_time": (datetime.utcnow() - start_time).total_seconds()
                }
            
            final_results = result_state["final_results"]
            final_results["execution_time"] = (datetime.utcnow() - start_time).total_seconds()
            
            # Cache successful results
            self._cache_result(cache_key, final_results)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _understand_query(self, state: SearchState) -> SearchState:
        """Understand user query intent using LLM"""
        query = state["original_query"]
        
        try:
            # Create focused prompt for query understanding
            system_prompt = """You are an expert research assistant. Analyze the research query and extract structured intent.

Your task is to understand what the user is looking for and categorize their intent.

CRITICAL: For search_terms, extract ONLY the core research concepts/keywords that should be searched in academic databases. 
Do NOT include temporal words (latest, recent, new), structural words (papers, research, study), or common words (in, on, of, the, and).

Examples:
- "latest papers in crowd counting" → search_terms: ["crowd counting"]
- "recent advances in transformer architectures" → search_terms: ["transformer architectures", "transformer"]  
- "highly cited work on computer vision" → search_terms: ["computer vision"]
- "new research in machine learning optimization" → search_terms: ["machine learning optimization", "optimization"]

Query Types:
- paper_search: Looking for specific papers on a topic
- author_analysis: Asking about specific researchers or authors
- trend_analysis: Interested in trends, developments, or state-of-the-art
- recent_work: Specifically wants latest/recent publications
- highly_cited: Looking for influential/highly-cited work
- dataset_focused: Interested in datasets, benchmarks, or data

Respond in valid JSON format:
{
    "query_type": "paper_search|author_analysis|trend_analysis|recent_work|highly_cited|dataset_focused",
    "search_terms": ["core", "research", "concepts"],
    "field_of_study": "research field/domain",
    "temporal_focus": "recent|historical|null",
    "specific_authors": ["author names if mentioned"],
    "specific_venues": ["venue names if mentioned"],
    "search_strategy": "latest|cited|comprehensive"
}"""

            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Query: {query}")
            ])
            
            # Parse response
            intent_data = json.loads(response.content.strip())
            
            # Convert to QueryIntent object
            query_intent = QueryIntent(
                query_type=QueryType(intent_data["query_type"]),
                search_terms=intent_data["search_terms"],
                field_of_study=intent_data["field_of_study"],
                temporal_focus=intent_data.get("temporal_focus"),
                specific_authors=intent_data.get("specific_authors", []),
                specific_venues=intent_data.get("specific_venues", []),
                search_strategy=intent_data.get("search_strategy", "comprehensive")
            )
            
            state["query_intent"] = query_intent
            logger.info(f"Query understood: {query_intent.query_type} in {query_intent.field_of_study}")
            logger.info(f"Core search terms extracted: {query_intent.search_terms}")
            
        except Exception as e:
            logger.error(f"Query understanding failed: {str(e)}")
            # Fallback to basic intent with core term extraction
            # Extract meaningful terms from query, excluding common words
            stop_words = {
                'latest', 'recent', 'new', 'papers', 'research', 'study', 'work', 'article',
                'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'about',
                'using', 'use', 'used', 'based', 'via', 'towards', 'find', 'me',
                'of', 'in', 'on', 'to', 'a', 'an', 'by', 'at', 'as', 'is', 'are'
            }
            words = query.lower().split()
            meaningful_terms = [w for w in words if w not in stop_words and len(w) > 2]
            
            state["query_intent"] = QueryIntent(
                query_type=QueryType.PAPER_SEARCH,
                search_terms=meaningful_terms[:3],  # Max 3 terms for focused search
                field_of_study="General",
                search_strategy="comprehensive"
            )
        
        return state
    
    async def _select_services(self, state: SearchState) -> SearchState:
        """Select optimal services based on query intent"""
        intent = state["query_intent"]
        
        # Smart service selection based on intent
        if intent.query_type == QueryType.RECENT_WORK:
            # ArXiv is crucial for recent work
            primary = [DataSource.ARXIV, DataSource.OPENALEX]
            secondary = [DataSource.CROSSREF]
            configs = {
                DataSource.ARXIV: {"limit": 15, "sort_by": "date"},
                DataSource.OPENALEX: {"limit": 10, "sort_by": "date"}
            }
            
        elif intent.query_type == QueryType.HIGHLY_CITED:
            # OpenAlex excels at citation data
            primary = [DataSource.OPENALEX]
            secondary = [DataSource.CROSSREF, DataSource.ARXIV]
            configs = {
                DataSource.OPENALEX: {"limit": 15, "sort_by": "citations"},
                DataSource.CROSSREF: {"limit": 10, "sort_by": "citations"}
            }
            
        elif intent.query_type == QueryType.DATASET_FOCUSED:
            # Papers with Code for datasets
            primary = [DataSource.PAPERS_WITH_CODE, DataSource.ARXIV]
            secondary = [DataSource.OPENALEX]
            configs = {
                DataSource.PAPERS_WITH_CODE: {"limit": 10},
                DataSource.ARXIV: {"limit": 10, "subject_class": "cs.CV"}
            }
            
        else:
            # Default comprehensive search with smart prioritization
            if "computer vision" in intent.field_of_study.lower() or "cv" in intent.field_of_study.lower():
                primary = [DataSource.ARXIV, DataSource.OPENALEX]
                secondary = [DataSource.PAPERS_WITH_CODE]
                configs = {
                    DataSource.ARXIV: {"limit": 12, "subject_class": "cs.CV"},
                    DataSource.OPENALEX: {"limit": 12}
                }
            else:
                primary = [DataSource.OPENALEX, DataSource.ARXIV]
                secondary = [DataSource.CROSSREF]
                configs = {
                    DataSource.OPENALEX: {"limit": 12},
                    DataSource.ARXIV: {"limit": 12}
                }
        
        state["service_selection"] = ServiceSelection(
            primary_services=primary,
            secondary_services=secondary,
            service_configs=configs
        )
        
        logger.info(f"Selected services: Primary={primary}, Secondary={secondary}")
        return state
    
    async def _execute_search(self, state: SearchState) -> SearchState:
        """Execute search with selected services"""
        intent = state["query_intent"]
        selection = state["service_selection"]
        limit = state["execution_metadata"]["limit"]
        
        # Build focused search query from core terms only
        core_terms = [term for term in intent.search_terms if len(term) > 2]
        if not core_terms:
            # Fallback if no good terms
            core_terms = intent.search_terms[:2] if intent.search_terms else ["research"]
        
        # Create precise search query - join with quotes for phrase matching when appropriate
        if len(core_terms) == 1:
            search_query = core_terms[0]
        elif any(' ' in term for term in core_terms):
            # If we have multi-word terms, use them as phrases
            search_query = ' '.join(f'"{term}"' if ' ' in term else term for term in core_terms[:2])
        else:
            # Join single words
            search_query = ' '.join(core_terms[:3])  # Limit to 3 core terms max
        
        logger.info(f"Executing search with focused query: '{search_query}' (from terms: {core_terms})")
        
        results = {"papers": [], "metadata": {}}
        
        try:
            # Use existing research aggregator with focused parameters
            async with ResearchAggregatorService() as aggregator:
                search_result = await aggregator.comprehensive_paper_search(
                    query=search_query,
                    limit=limit,
                    include_semantics=DataSource.CROSSREF in selection.primary_services,
                    include_code=DataSource.PAPERS_WITH_CODE in selection.primary_services,
                    cross_reference=False,  # Disable for performance
                    search_strategy=intent.search_strategy
                )
                
                if search_result.get("success"):
                    raw_papers = search_result.get("papers", [])
                    
                    # Apply aggressive relevance filtering BEFORE ranking
                    filtered_papers = self._filter_irrelevant_papers(raw_papers, core_terms)
                    
                    logger.info(f"Filtered from {len(raw_papers)} to {len(filtered_papers)} relevant papers")
                    
                    results["papers"] = filtered_papers
                    results["metadata"] = {
                        "total_found": search_result.get("total_found", 0),
                        "source_statistics": search_result.get("source_statistics", {}),
                        "services_used": len(selection.primary_services),
                        "filtered_count": len(raw_papers) - len(filtered_papers)
                    }
                else:
                    logger.warning(f"Search failed: {search_result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            logger.error(f"Search execution failed: {str(e)}")
            state["error"] = str(e)
            return state
        
        state["search_results"] = results
        return state
    
    def _filter_irrelevant_papers(self, papers: List[Any], core_terms: List[str]) -> List[Any]:
        """Aggressively filter out papers that don't match core research terms"""
        if not core_terms:
            return papers
        
        filtered_papers = []
        
        for paper in papers:
            # Extract text for matching
            title = getattr(paper, 'title', '') or ''
            abstract = getattr(paper, 'abstract', '') or ''
            paper_text = f"{title} {abstract}".lower()
            
            # Check if paper has meaningful matches to core terms
            has_meaningful_match = False
            
            for term in core_terms:
                term_lower = term.lower()
                # For multi-word terms, require exact phrase match
                if ' ' in term_lower:
                    if term_lower in paper_text:
                        has_meaningful_match = True
                        break
                else:
                    # For single words, require word boundary match to avoid partial matches
                    import re
                    if re.search(r'\b' + re.escape(term_lower) + r'\b', paper_text):
                        has_meaningful_match = True
                        break
            
            if has_meaningful_match:
                filtered_papers.append(paper)
            else:
                # Log filtered out papers for debugging
                logger.debug(f"Filtered out irrelevant paper: {title[:50]}...")
        
        return filtered_papers
    
    async def _rank_results(self, state: SearchState) -> SearchState:
        """Apply semantic ranking to results"""
        intent = state["query_intent"]
        results = state["search_results"]
        papers = results.get("papers", [])
        
        if not papers:
            state["final_results"] = {
                "success": True,
                "query": state["original_query"],
                "papers": [],
                "total_found": 0,
                "query_intent": {
                    "type": intent.query_type.value,
                    "field": intent.field_of_study,
                    "strategy": intent.search_strategy
                },
                "metadata": results.get("metadata", {})
            }
            return state
        
        # Enhanced semantic ranking
        ranked_papers = self._semantic_rank_papers(papers, intent)
        
        state["final_results"] = {
            "success": True,
            "query": state["original_query"],
            "papers": ranked_papers,
            "total_found": len(ranked_papers),
            "query_intent": {
                "type": intent.query_type.value,
                "field": intent.field_of_study,
                "strategy": intent.search_strategy,
                "search_terms": intent.search_terms
            },
            "metadata": results.get("metadata", {})
        }
        
        return state
    
    def _semantic_rank_papers(self, papers: List[Any], intent: QueryIntent) -> List[Any]:
        """Apply semantic ranking based on query intent"""
        def calculate_semantic_score(paper) -> float:
            score = 0.0
            
            # Extract text for matching
            title = getattr(paper, 'title', '') or ''
            abstract = getattr(paper, 'abstract', '') or ''
            paper_text = f"{title} {abstract}".lower()
            
            # Term relevance (primary factor)
            term_matches = sum(1 for term in intent.search_terms 
                             if term.lower() in paper_text)
            if intent.search_terms:
                relevance_ratio = term_matches / len(intent.search_terms)
                score += relevance_ratio * 100
            
            # Penalize completely irrelevant papers
            if term_matches == 0:
                score -= 50
            
            # Strategy-specific scoring
            if intent.search_strategy == "latest":
                # Heavy weight on recency
                if hasattr(paper, 'publication_date') and paper.publication_date:
                    try:
                        if hasattr(paper.publication_date, 'year'):
                            years_old = datetime.now().year - paper.publication_date.year
                        else:
                            years_old = datetime.now().year - int(str(paper.publication_date)[:4])
                        score += max(0, 30 - (years_old * 5))
                    except:
                        pass
                        
            elif intent.search_strategy == "cited":
                # Heavy weight on citations
                if hasattr(paper, 'citation_count') and paper.citation_count:
                    score += min(paper.citation_count / 20, 25)
            
            # Source preference
            if hasattr(paper, 'source'):
                if paper.source == DataSource.ARXIV and intent.query_type == QueryType.RECENT_WORK:
                    score += 15
                elif paper.source == DataSource.OPENALEX:
                    score += 5
            
            # Field relevance
            if intent.field_of_study.lower() in paper_text:
                score += 10
            
            return score
        
        # Sort by semantic score
        scored_papers = [(p, calculate_semantic_score(p)) for p in papers]
        scored_papers.sort(key=lambda x: x[1], reverse=True)
        
        # Log top results for debugging
        if scored_papers:
            logger.info(f"Top 3 semantic matches for '{intent.query_type}':")
            for i, (paper, score) in enumerate(scored_papers[:3]):
                title = getattr(paper, 'title', 'No title')[:50]
                logger.info(f"  {i+1}. {score:.1f} pts - {title}...")
        
        return [paper for paper, score in scored_papers]
    
    def _generate_cache_key(self, query: str, limit: int) -> str:
        """Generate cache key for query"""
        key_data = f"{query}:{limit}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if still valid"""
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if datetime.utcnow() - cached_item["timestamp"] < self.cache_ttl:
                return cached_item["data"]
            else:
                del self.cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache successful result"""
        self.cache[cache_key] = {
            "data": result,
            "timestamp": datetime.utcnow()
        }
        
        # Simple cache cleanup (keep only last 100 items)
        if len(self.cache) > 100:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key] 