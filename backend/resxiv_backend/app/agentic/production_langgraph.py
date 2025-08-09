"""
Production LangGraph Orchestrator - Single Source of Truth
L6 Engineering Standards - Consolidated, Production-Ready Implementation

Replaces the multiple fragmented implementations with one robust system.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, List, Optional, Literal, TypedDict, Annotated
from datetime import datetime
from enum import Enum
import uuid
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.services.research_aggregator_service import ResearchAggregatorService, DataSource
from app.database.connection import db_manager
from app.services.conversation.conversation_project_service import ConversationProjectService

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Supported task types for routing"""
    RESEARCH = "research"
    PROJECT_MANAGEMENT = "project_management"
    PAPER_PROCESSING = "paper_processing"
    CONVERSATION = "conversation"
    ANALYSIS = "analysis"
    FILE_PROCESSING = "file_processing"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentState(TypedDict):
    """Strongly typed state for LangGraph workflow"""
    # Core message handling
    messages: Annotated[List[Dict[str, Any]], "The conversation messages"]
    
    # Task and context
    task_type: Optional[str]
    user_intent: Optional[str]
    context: Dict[str, Any]
    
    # Execution control
    current_agent: Optional[str]
    tool_calls_count: int
    max_tool_calls: int
    
    # Results and status
    status: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    
    # Metadata
    session_id: str
    created_at: datetime
    updated_at: datetime


@dataclass
class LangGraphConfig:
    """Configuration for LangGraph orchestrator"""
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tool_calls: int = 15
    max_retries: int = 3
    timeout_seconds: int = 300
    enable_memory: bool = True


class ProductionLangGraphOrchestrator:
    """
    Production-grade LangGraph orchestrator implementing L6 patterns.
    
    Single source of truth for all agentic workflows with:
    - Type-safe state management
    - Proper error handling and recovery
    - Tool orchestration with limits
    - Memory persistence
    - Performance monitoring
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        config: Optional[LangGraphConfig] = None
    ):
        self.config = config or LangGraphConfig()
        
        # Get settings for proper environment configuration
        from app.config.settings import get_settings
        settings = get_settings()
        
        # Use OpenAI key from settings with fallbacks
        if openai_api_key:
            self.openai_api_key = openai_api_key
        elif settings.agentic.openai_api_key:
            self.openai_api_key = settings.agentic.openai_api_key
        else:
            import os
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "test-key-for-development")
        
        # Use model from settings
        self.model_name = settings.agentic.agentic_model or self.config.model_name
        
        # Initialize LLM with proper configuration
        try:
            self.llm = ChatOpenAI(
                api_key=self.openai_api_key,
                model=self.model_name,
                temperature=self.config.temperature,
                timeout=30
            )
            logger.info(f"LLM initialized successfully with model: {self.model_name}")
        except Exception as e:
            logger.warning(f"LLM initialization failed (using mock): {e}")
            # Create a mock LLM for testing that doesn't require real API access
            self.llm = None
        
        # State persistence
        self.checkpointer = MemorySaver() if self.config.enable_memory else None
        
        # Build and compile workflow
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_feedback"]  # Human-in-the-loop capability
        )
        
        logger.info(f"LangGraph orchestrator initialized with model: {self.model_name}")
    
    async def _safe_llm_call(self, messages: list, fallback_response: str = "Unable to process request - LLM not available") -> str:
        """Safely call LLM with fallback for testing environments"""
        if self.llm is None:
            logger.warning("LLM not available, using fallback response")
            return fallback_response
        
        try:
            response = await self.llm.ainvoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return fallback_response
    
    def _build_workflow(self) -> StateGraph:
        """Build the production LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Core processing nodes
        workflow.add_node("intent_classifier", self._classify_intent)
        workflow.add_node("task_router", self._route_task)
        workflow.add_node("research_agent", self._handle_research)
        workflow.add_node("project_agent", self._handle_project)
        workflow.add_node("paper_agent", self._handle_paper)
        workflow.add_node("conversation_agent", self._handle_conversation)
        workflow.add_node("analysis_agent", self._handle_analysis)
        workflow.add_node("file_agent", self._handle_file)
        workflow.add_node("tool_executor", self._execute_tools)
        workflow.add_node("response_formatter", self._format_response)
        workflow.add_node("error_handler", self._handle_error)
        workflow.add_node("human_feedback", self._request_human_feedback)
        
        # Entry point
        workflow.add_edge(START, "intent_classifier")
        
        # Intent classification to task routing
        workflow.add_edge("intent_classifier", "task_router")
        
        # Task-based routing
        workflow.add_conditional_edges(
            "task_router",
            self._route_by_task_type,
            {
                TaskType.RESEARCH: "research_agent",
                TaskType.PROJECT_MANAGEMENT: "project_agent",
                TaskType.PAPER_PROCESSING: "paper_agent",
                TaskType.CONVERSATION: "conversation_agent",
                TaskType.ANALYSIS: "analysis_agent",
                TaskType.FILE_PROCESSING: "file_agent",
                "error": "error_handler"
            }
        )
        
        # Agent processing with tool execution capability
        agent_nodes = [
            "research_agent", "project_agent", "paper_agent",
            "conversation_agent", "analysis_agent", "file_agent"
        ]
        
        for agent in agent_nodes:
            workflow.add_conditional_edges(
                agent,
                self._should_use_tools,
                {
                    "tools": "tool_executor",
                    "response": "response_formatter",
                    "human": "human_feedback",
                    "error": "error_handler"
                }
            )
        
        # Tool execution results
        workflow.add_conditional_edges(
            "tool_executor",
            self._handle_tool_results,
            {
                "continue": "response_formatter",
                "retry": "task_router",
                "error": "error_handler"
            }
        )
        
        # Terminal nodes
        workflow.add_edge("response_formatter", END)
        workflow.add_edge("error_handler", END)
        workflow.add_edge("human_feedback", END)
        
        return workflow
    
    @handle_service_errors("intent classification")
    async def _classify_intent(self, state: AgentState) -> AgentState:
        """Intelligent LLM-based intent classification"""
        if not state["messages"]:
            state["error"] = "No messages to process"
            return state
        
        last_message = state["messages"][-1].get("content", "")
        
        # Use LLM for intelligent intent classification
        classification_prompt = f"""
Classify the following user query into one of these task types:

1. RESEARCH - Questions about papers, authors, research trends, citations, academic information
2. PROJECT_MANAGEMENT - Project organization, task management, team coordination
3. PAPER_PROCESSING - Uploading, processing, extracting content from papers
4. ANALYSIS - Data analysis, comparison, evaluation of research
5. FILE_PROCESSING - File operations, downloads, data management
6. CONVERSATION - General chat, greetings, unclear queries

User Query: "{last_message}"

Examples:
- "Who are the most popular authors in crowd counting?" → RESEARCH
- "Find papers about deep learning" → RESEARCH  
- "What are the latest trends in NLP?" → RESEARCH
- "Create a new project for my research" → PROJECT_MANAGEMENT
- "Upload this PDF paper" → PAPER_PROCESSING
- "Compare these two datasets" → ANALYSIS
- "Download project files" → FILE_PROCESSING
- "Hello, how are you?" → CONVERSATION

Respond with ONLY the task type (e.g., "RESEARCH").
"""

        try:
            # Get classification from LLM using safe call
            response_content = await self._safe_llm_call([
                {"role": "system", "content": "You are an expert at classifying research-related queries."},
                {"role": "user", "content": classification_prompt}
            ], fallback_response="RESEARCH")  # Default to RESEARCH for tests
            
            classified_task = response_content.strip().upper()
            # Heuristic overrides
            msg_lower = last_message.lower()

            # 1. If request is about adding/finding papers from arxiv, treat as RESEARCH
            if (
                ("paper" in msg_lower or "papers" in msg_lower or "arxiv" in msg_lower)
                and ("add" in msg_lower or "find" in msg_lower or "search" in msg_lower)
            ):
                classified_task = "RESEARCH"

            # 2. Chat summary queries should route to project management
            elif (
                ("chat" in msg_lower or "conversation" in msg_lower)
                and ("summary" in msg_lower or "summarise" in msg_lower or "summarize" in msg_lower)
            ):
                classified_task = "PROJECT_MANAGEMENT"
            
            # Validate classification
            valid_tasks = [t.value.upper() for t in TaskType]
            if classified_task in valid_tasks:
                task_type = TaskType(classified_task.lower())
            else:
                # Fallback to keyword-based classification
                task_type = self._fallback_classification(last_message)
            
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}, using fallback")
            task_type = self._fallback_classification(last_message)
        
        state["task_type"] = task_type.value
        state["user_intent"] = last_message
        state["updated_at"] = datetime.now()
        
        logger.info(f"Classified intent as: {task_type.value}")
        return state
    
    def _fallback_classification(self, message: str) -> TaskType:
        """Fallback keyword-based classification"""
        message_lower = message.lower()
        
        # Enhanced research keywords
        research_keywords = [
            "authors", "papers", "research", "find", "search", "study", "investigate",
            "popular", "who are", "what are", "trends", "recent", "latest", "citations",
            "literature", "academic", "scholar", "publication", "journal", "conference"
        ]
        
        project_keywords = [
            "project", "task", "manage", "organize", "plan", "team",
            "chat", "conversation", "group chat", "summary", "summarise", "summarize"
        ]
        paper_keywords = ["upload", "pdf", "process", "extract", "document"]
        analysis_keywords = ["analyze", "compare", "evaluate", "statistics", "data"]
        file_keywords = ["file", "download", "save", "export", "import"]
        
        # Score based on keyword matches
        research_score = sum(1 for keyword in research_keywords if keyword in message_lower)
        project_score = sum(1 for keyword in project_keywords if keyword in message_lower)
        paper_score = sum(1 for keyword in paper_keywords if keyword in message_lower)
        analysis_score = sum(1 for keyword in analysis_keywords if keyword in message_lower)
        file_score = sum(1 for keyword in file_keywords if keyword in message_lower)
        
        scores = {
            TaskType.RESEARCH: research_score,
            TaskType.PROJECT_MANAGEMENT: project_score,
            TaskType.PAPER_PROCESSING: paper_score,
            TaskType.ANALYSIS: analysis_score,
            TaskType.FILE_PROCESSING: file_score
        }
        
        max_score = max(scores.values())
        if max_score > 0:
            return max(scores, key=scores.get)
        
        return TaskType.CONVERSATION
    
    @handle_service_errors("task routing")
    async def _route_task(self, state: AgentState) -> AgentState:
        """Route to appropriate specialist agent"""
        state["current_agent"] = f"{state['task_type']}_agent"
        state["updated_at"] = datetime.now()
        return state
    
    def _route_by_task_type(self, state: AgentState) -> str:
        """Conditional routing based on task type"""
        task_type = state.get("task_type")
        if task_type in [t.value for t in TaskType]:
            return TaskType(task_type)
        return "error"
    
    def _should_use_tools(self, state: AgentState) -> str:
        """Determine if tools should be used"""
        if state.get("error"):
            return "error"
        
        # Check if agent already processed everything and has a response ready
        if state.get("context", {}).get("response_ready"):
            return "response"
        
        if state.get("tool_calls_count", 0) >= state.get("max_tool_calls", 15):
            logger.warning("Maximum tool calls reached")
            return "response"
        
        # Check if agent determined tools are needed
        if state.get("context", {}).get("needs_tools", False):
            return "tools"
        
        # Check if human feedback is required
        if state.get("context", {}).get("needs_human", False):
            return "human"
        
        return "response"
    
    def _handle_tool_results(self, state: AgentState) -> str:
        """Handle tool execution results"""
        if state.get("error"):
            return "error"
        
        tool_results = state.get("context", {}).get("tool_results", [])
        if not tool_results:
            return "error"
        
        # Check if more tools needed
        if state.get("context", {}).get("needs_more_tools", False):
            return "retry"
        
        return "continue"
    
    # Specialist agent implementations
    @handle_service_errors("research processing")
    async def _handle_research(self, state: AgentState) -> AgentState:
        """Intelligent research agent that analyzes queries and executes research tools"""
        user_query = state.get("user_intent", "")
        
        # Use LLM to analyze the research query and determine search strategy
        analysis_prompt = f"""
You are an expert research assistant. Analyze this research query and determine the best search strategy:

Query: "{user_query}"

Determine:
1. What type of research information is needed (papers, authors, trends, etc.)
2. What search terms would be most effective
3. Whether this requires paper search, author analysis, or trend analysis

Respond in JSON format:
{{
    "research_type": "author_search|paper_search|trend_analysis",
    "search_terms": ["term1", "term2", "term3"],
    "focus_area": "brief description of the research domain",
    "strategy": "brief description of search strategy"
}}

For "Who are the most popular authors in crowd counting?", you would focus on:
- research_type: "author_search"  
- search_terms: ["crowd counting", "crowd analysis", "crowd estimation"]
- focus_area: "Computer Vision - Crowd Counting and Analysis"
- strategy: "Search for recent papers in crowd counting and identify highly cited authors"
"""

        try:
            # Get research strategy from LLM
            strategy_response = await self.llm.ainvoke([
                {"role": "system", "content": "You are an expert research strategist. Always respond in valid JSON format."},
                {"role": "user", "content": analysis_prompt}
            ])
            
            # Robust JSON parsing with fallback
            strategy = self._parse_llm_json_response(strategy_response.content.strip(), user_query)
            # NEW: If user requested only arXiv, set flag and remove any 'arxiv' term
            if "from arxiv" in user_query.lower():
                state["context"]["arxiv_only"] = True
                if "search_terms" in strategy:
                    strategy["search_terms"] = [t for t in strategy["search_terms"] if t.lower() != "arxiv"]
            
            # Execute research based on strategy
            research_results = await self._execute_research_strategy(strategy, state)

            # Generate intelligent response using LLM and research results
            response_text = await self._generate_research_response(user_query, strategy, research_results)

            # ===========================
            # INTELLIGENT INTENT DETECTION: Check if user wants to add papers to project
            # ===========================
            project_id = state["context"].get("project_id") if state.get("context") else None
            user_id = state["context"].get("user_id") if state.get("context") else None

            if project_id and user_id:
                # Use LLM to detect intent to add papers to project
                intent_prompt = f"""
Analyze this user query and determine if they want to add/download/save papers to their project:

Query: "{user_query}"

Respond with JSON:
{{
    "wants_to_add_papers": true/false,
    "max_papers": number (extract from query, default 5)
}}

Examples:
- "Add relevant papers to my project" -> {{"wants_to_add_papers": true, "max_papers": 5}}
- "Download 3 papers about AI" -> {{"wants_to_add_papers": true, "max_papers": 3}}
- "Find papers about ML" -> {{"wants_to_add_papers": false, "max_papers": 0}}
- "Save the top 10 papers" -> {{"wants_to_add_papers": true, "max_papers": 10}}
"""
                
                try:
                    intent_response = await self.llm.ainvoke([
                        {"role": "system", "content": "You are an expert at understanding user intent. Always respond in valid JSON format."},
                        {"role": "user", "content": intent_prompt}
                    ])
                    
                    intent_data = self._parse_llm_json_response(intent_response.content.strip(), user_query)
                    logger.info(f"Intent detection result: {intent_data}")
                    
                    if intent_data.get("wants_to_add_papers", False):
                        logger.info(f"User wants to add papers, proceeding with download. Max papers: {intent_data.get('max_papers', 5)}")
                        try:
                            from app.services.paper.paper_service_integrated import PaperService
                            from app.models.paper import PaperCreate

                            # Get max papers from LLM intent analysis
                            max_to_add = max(1, min(intent_data.get("max_papers", 5), 20))  # safety bounds 1–20
                            logger.info(f"Processing {len(research_results.get('papers', []))} papers, will download max {max_to_add}")

                            added_count = 0
                            for paper in research_results["papers"][:max_to_add]:
                                logger.info(f"Processing paper {added_count + 1} of {max_to_add}")
                                # Extract paper data in a unified way
                                try:
                                    # Enhanced Debug: Log paper type and structure
                                    logger.info(f"PAPER DEBUG: type={type(paper)}")
                                    if hasattr(paper, '__dict__'):
                                        logger.info(f"PAPER ATTRS: {list(paper.__dict__.keys())}")
                                    
                                    # Skip if paper is not a valid object/dict
                                    if isinstance(paper, str):
                                        logger.warning(f"Skipping invalid paper (string): {paper[:100]}")
                                        continue
                                    elif paper is None:
                                        logger.warning("Skipping None paper")
                                        continue
                                    
                                    # Extract arXiv ID safely
                                    arxiv_id = None
                                    if hasattr(paper, "arxiv_id"):
                                        arxiv_id = paper.arxiv_id
                                    elif isinstance(paper, dict) and "arxiv_id" in paper:
                                        arxiv_id = paper["arxiv_id"]
                                    
                                    # Extract key paper metadata for debugging and fallback
                                    title = getattr(paper, 'title', None) or (paper.get('title') if isinstance(paper, dict) else None)
                                    doi = getattr(paper, 'doi', None) or (paper.get('doi') if isinstance(paper, dict) else None)
                                    url = getattr(paper, 'url', None) or (paper.get('url') if isinstance(paper, dict) else None)
                                    
                                    logger.info(f"PAPER METADATA: title='{title}', arxiv_id='{arxiv_id}', doi='{doi}', url='{url}'")
                                    
                                    # Extract title safely
                                    if not title:
                                        if hasattr(paper, "title"):
                                            title = paper.title
                                        elif isinstance(paper, dict) and "title" in paper:
                                            title = paper["title"]
                                    
                                    # Extract authors safely
                                    authors = []
                                    if hasattr(paper, "authors") and paper.authors:
                                        authors = [getattr(a, "name", str(a)) for a in paper.authors if a]
                                    elif isinstance(paper, dict) and "authors" in paper and paper["authors"]:
                                        for a in paper["authors"]:
                                            if isinstance(a, dict) and "name" in a:
                                                authors.append(a["name"])
                                            elif hasattr(a, "name"):
                                                authors.append(a.name)
                                            else:
                                                authors.append(str(a))
                                    
                                    # Extract abstract safely
                                    abstract = getattr(paper, 'abstract', None) or (paper.get('abstract') if isinstance(paper, dict) else None) or ""
                                    
                                    # Extract published date safely  
                                    published_date = getattr(paper, 'published_date', None) or (paper.get('published_date') if isinstance(paper, dict) else None)
                                
                                except Exception as paper_parse_err:
                                    logger.error(f"Failed to parse paper: {paper_parse_err}, paper type: {type(paper)}")
                                    continue

                                # Use separate session for each paper to prevent transaction abort issues
                                async with db_manager.get_postgres_session() as paper_session:
                                    try:
                                        if arxiv_id:
                                            # arXiv paper - use existing download method
                                            logger.info(f"Downloading arXiv paper: {arxiv_id} - {title}")
                                            paper_service_individual = PaperService(paper_session)
                                            create_res = await paper_service_individual.download_arxiv_paper(
                                                arxiv_id=arxiv_id,
                                                project_id=uuid.UUID(project_id),
                                                user_id=uuid.UUID(user_id),
                                                process_with_grobid=True,
                                                run_diagnostics=True
                                            )
                                            success_msg = f"arXiv paper {arxiv_id}"
                                            
                                            if create_res.get("success"):
                                                added_count += 1
                                                logger.info(f"Successfully added {success_msg} to project")
                                                # Increment tool call count
                                                state["tool_calls_count"] = state.get("tool_calls_count", 0) + 1
                                            else:
                                                logger.warning(f"Failed to add {success_msg}: {create_res.get('error', 'Unknown error')}")
                                        else:
                                            # Skip non-arXiv papers (no metadata-only entries)
                                            logger.info(f"Skipping non-arXiv paper (metadata-only): {title}")
                                            continue
                                            
                                    except Exception as download_err:
                                        logger.error(f"Error adding paper '{title}': {str(download_err)}")
                                        continue

                            if added_count:
                                response_text += f"\n\n✅ Added {added_count} arXiv papers to your project (with full PDF download and processing)."
                            else:
                                total_papers = len(research_results.get('papers', []))
                                response_text += f"\n\n📄 Found {total_papers} papers, but none were from arXiv. Only arXiv papers can be downloaded and processed. Try searching specifically for arXiv papers in your field."
                                logger.warning(f"No arXiv papers found to add to project. Found {total_papers} non-arXiv papers.")
                        except Exception as save_err:
                            logger.warning(f"Failed to add papers to project: {save_err}")
                    else:
                        logger.info(f"Intent detection indicates user does not want to add papers. Intent data: {intent_data}")
                                
                except Exception as intent_err:
                    logger.warning(f"Failed to parse intent: {intent_err}")

            # Save results and response
            state["result"] = {
                "message": response_text,
                "research_results": research_results
            }
        except Exception as e:
            logger.error(f"Research processing failed: {e}")
            state["error"] = str(e)
        
        state["updated_at"] = datetime.now()
        return state

    async def _execute_research_strategy(self, strategy: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Execute research strategy using available tools"""
        research_type = strategy.get("research_type", "paper_search")
        search_terms = strategy.get("search_terms", [])
        user_query_raw = state.get("user_intent", "")
        # Heuristic: detect "papers by <name>" patterns to force author search
        import re
        author_pattern = re.compile(r"\b(papers|publications|works|articles)\s+by\s+([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)", re.IGNORECASE)
        if research_type not in ["author_search", "author_analysis"] and author_pattern.search(user_query_raw):
            research_type = "author_search"
            # Use the captured author name as the sole search term
            match = author_pattern.search(user_query_raw)
            if match:
                search_terms = [match.group(2)]
        
        logger.info(f"Research: Executing strategy with {len(search_terms)} terms: {search_terms}")
        
        results = {"papers": [], "authors": [], "metadata": {}}
        
        try:
            # Import research services
            from app.services.research_aggregator_service import ResearchAggregatorService
            
            async with ResearchAggregatorService() as aggregator:
                # --------------- AUTHOR ANALYSIS PATH -----------------
                if research_type in ["author_search", "author_analysis"]:
                    author_term = search_terms[0] if search_terms else user_query_raw
                    try:
                        state["tool_calls_count"] = state.get("tool_calls_count", 0) + 1
                        logger.info(f"Research: Performing author deep dive for '{author_term}'")
                        author_result = await aggregator.author_deep_dive(author_query=author_term)
                        results["metadata"]["author_query"] = author_term
                        if author_result.get("success"):
                            if author_result.get("author_profile"):
                                results["authors"].append(author_result["author_profile"])
                            # Include papers if available
                            if author_result.get("papers"):
                                results["papers"].extend(author_result["papers"])
                        else:
                            logger.warning(f"Author deep dive failed for '{author_term}' – {author_result.get('error')}")
                    except Exception as auth_err:
                        logger.error(f"Author deep dive error: {auth_err}")
                    # We skip paper-search loop for author analysis
                # --------------- PAPER SEARCH PATH -------------------
                else:
                    # Execute searches for each term
                    for term in search_terms[:3]:  # Limit to 3 terms to avoid rate limits
                        try:
                            # Increment tool call count
                            state["tool_calls_count"] = state.get("tool_calls_count", 0) + 1
                            logger.info(f"Research: Searching for term: '{term}' (type: {type(term)})")
                            
                            # Ensure term is a string
                            search_query = str(term).strip()
                            if not search_query:
                                logger.warning(f"Empty search term: '{term}', skipping")
                                continue
                                
                            search_result = await aggregator.comprehensive_paper_search(
                                query=search_query,
                                limit=10,  # Get top 10 papers per term
                                include_semantics=True,
                                include_code=True,
                                cross_reference=True
                            )
                            
                            logger.info(f"Research: Search result structure: success={search_result.get('success')}, keys={list(search_result.keys())}")
                            
                            # Even if some services fail, we should still get papers from successful services
                            papers = search_result.get("papers", [])
                            
                            # NEW: If the user explicitly asks for arXiv sources, keep only arXiv papers
                            if state.get("messages") and isinstance(state["messages"], list):
                                last_msg = state["messages"][-1].get("content", "").lower()
                                if "arxiv" in last_msg:
                                    papers = [p for p in papers if getattr(p, "source", None) == DataSource.ARXIV]
                                    logger.info(f"Research: Filtered to {len(papers)} arXiv papers after user request")
                            
                            logger.info(f"Research: Found {len(papers)} papers for term '{search_query}' (ignoring success flag)")
                            
                            if papers:  # Check if we have papers, regardless of success flag
                                
                                results["papers"].extend(papers)
                                
                                # Extract author information from papers
                                for paper in papers:
                                    authors = paper.get("authors", []) if isinstance(paper, dict) else getattr(paper, 'authors', [])
                                    for author in authors:
                                        if author not in results["authors"]:
                                            results["authors"].append(author)
                            else:
                                logger.warning(f"Research: No papers found for term '{search_query}'")
                        
                        except Exception as e:
                            logger.error(f"Search for term '{term}' failed: {e}")
                            import traceback
                            logger.error(f"Search error traceback: {traceback.format_exc()}")
                            continue
            
            # Deduplicate and rank results
            logger.info(f"Research: Processing {len(results['papers'])} papers, {len(results['authors'])} authors")
            
            results["papers"] = self._deduplicate_papers(results["papers"])
            results["authors"] = self._rank_authors_by_popularity(results["authors"], results["papers"])
            # NEW: filter globally to only arXiv papers if requested
            if state.get("context", {}).get("arxiv_only"):
                results["papers"] = [p for p in results["papers"] if getattr(p, "source", None) == DataSource.ARXIV]
           
            # If the query is about latest/recent work, sort by publication date and cap at 20
            query_lower = state.get("user_intent", "").lower()
            if any(word in query_lower for word in ["latest", "recent", "new", "newly released"]):
                # Separate papers with publication date
                dated = [p for p in results["papers"] if getattr(p, "publication_date", None)]
                undated = [p for p in results["papers"] if not getattr(p, "publication_date", None)]
                dated.sort(key=lambda p: p.publication_date, reverse=True)
                sorted_papers = dated + undated  # Put undated at the end
                # Ensure at least some ArXiv papers are included (since most new work appears there)
                arxiv_papers = [p for p in sorted_papers if getattr(p, "source", None) == DataSource.ARXIV]
                non_arxiv = [p for p in sorted_papers if getattr(p, "source", None) != DataSource.ARXIV]
                # Keep up to 5 ArXiv papers (or all if fewer) in the final list
                final_list = arxiv_papers[:5] + non_arxiv
                results["papers"] = final_list[:20]  # Cap at 20
            else:
                # For non-recent queries, just cap at 20 after dedup/ranking
                results["papers"] = results["papers"][:20]
            
            results["metadata"] = {
                "total_papers": len(results["papers"]),
                "total_authors": len(results["authors"]),
                "search_terms": search_terms,
                "research_type": research_type
            }
            
        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            results["error"] = str(e)
        
        return results

    def _deduplicate_papers(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers based on title similarity"""
        unique_papers = []
        seen_titles = set()
        
        for paper in papers:
            # Handle both dict and Pydantic model formats
            if hasattr(paper, 'title'):
                title = (paper.title or "").lower().strip()
            else:
                title = paper.get("title", "").lower().strip()
                
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(paper)
        
        # Sort by citation count if available
        def get_citation_count(paper):
            if hasattr(paper, 'citation_count'):
                return paper.citation_count or 0
            else:
                return paper.get("citation_count", 0)
        
        return sorted(unique_papers, key=get_citation_count, reverse=True)

    def _rank_authors_by_popularity(self, authors: List[Dict], papers: List[Dict]) -> List[Dict]:
        """Rank authors by paper count and citations"""
        author_stats = {}
        
        for paper in papers:
            # Handle both dict and Pydantic model formats
            if hasattr(paper, 'citation_count'):
                citation_count = paper.citation_count or 0
                paper_authors = paper.authors or []
            else:
                citation_count = paper.get("citation_count", 0)
                paper_authors = paper.get("authors", [])
            
            for author in paper_authors:
                # Handle both dict and Pydantic model formats for authors
                if hasattr(author, 'name'):
                    author_name = author.name or "Unknown"
                    affiliation = author.affiliation or "Unknown"
                else:
                    author_name = author.get("name", "Unknown")
                    affiliation = author.get("affiliation", "Unknown")
                
                if author_name not in author_stats:
                    author_stats[author_name] = {
                        "name": author_name,
                        "paper_count": 0,
                        "total_citations": 0,
                        "affiliations": set(),
                        "h_index_estimate": 0
                    }
                
                author_stats[author_name]["paper_count"] += 1
                author_stats[author_name]["total_citations"] += citation_count
                
                if affiliation and affiliation != "Unknown":
                    author_stats[author_name]["affiliations"].add(affiliation)
        
        # Calculate popularity score (paper count + citations/100)
        ranked_authors = []
        for stats in author_stats.values():
            stats["affiliations"] = list(stats["affiliations"])
            stats["popularity_score"] = stats["paper_count"] + (stats["total_citations"] / 100)
            ranked_authors.append(stats)
        
        return sorted(ranked_authors, key=lambda a: a["popularity_score"], reverse=True)

    async def _generate_research_response(self, query: str, strategy: Dict, results: Dict) -> str:
        """Generate intelligent response using LLM and research results"""
        
        # Prepare research context for LLM
        top_papers = results.get("papers", [])[:5]  # Top 5 papers
        top_authors = results.get("authors", [])[:10]  # Top 10 authors
        
        context_summary = f"""
Research Query: {query}
Research Strategy: {strategy.get("strategy", "General search")}
Focus Area: {strategy.get("focus_area", "Unknown")}

Top Papers Found:
"""
        for i, paper in enumerate(top_papers, 1):
            # Handle both dict and Pydantic model formats
            if hasattr(paper, 'title'):
                title = paper.title or "Unknown Title"
                authors = [a.name if hasattr(a, 'name') else a.get('name', 'Unknown') for a in (paper.authors or [])]
                citations = paper.citation_count or 0
            else:
                title = paper.get("title", "Unknown Title")
                authors = [a.get("name", "Unknown") for a in paper.get("authors", [])]
                citations = paper.get("citation_count", 0)
            context_summary += f"{i}. {title} - Authors: {', '.join(authors[:3])} - Citations: {citations}\n"

        if top_authors:
            context_summary += f"\nTop Authors by Popularity:\n"
            for i, author in enumerate(top_authors[:5], 1):
                # Handle both dict and Pydantic model formats
                if hasattr(author, 'name'):
                    name = author.name or "Unknown"
                    papers = getattr(author, 'paper_count', 0) or 0
                    citations = getattr(author, 'total_citations', author.citation_count if hasattr(author, 'citation_count') else 0) or 0
                    affiliation_str = author.affiliation or "Unknown"
                else:
                    name = author.get("name", "Unknown")
                    papers = author.get("paper_count", 0)
                    citations = author.get("total_citations", 0)
                    affiliations = author.get("affiliations", [])
                    affiliation_str = affiliations[0] if affiliations else "Unknown"
                context_summary += f"{i}. {name} - {papers} papers, {citations} citations - {affiliation_str}\n"

        response_prompt = f"""
Based on the research results below, provide a comprehensive and informative answer to the user's question.

{context_summary}

Please provide:
1. A direct answer to the user's question
2. Key insights from the research
3. Notable findings or trends
4. Specific examples with details

Make the response informative, well-structured, and cite specific numbers/details from the research data.
Answer the question: "{query}"
"""

        try:
            response = await self.llm.ainvoke([
                {"role": "system", "content": "You are an expert research assistant providing detailed, accurate responses based on research data."},
                {"role": "user", "content": response_prompt}
            ])
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            # Fallback response
            if top_authors:
                author_list = [f"{a['name']} ({a['paper_count']} papers, {a['total_citations']} citations)" 
                              for a in top_authors[:5]]
                return f"Based on recent research, the most popular authors in {strategy.get('focus_area', 'this field')} are:\n\n" + "\n".join([f"{i+1}. {author}" for i, author in enumerate(author_list)])
            else:
                return f"I found {len(top_papers)} relevant papers but couldn't extract specific author popularity data. Please try a more specific query."

    @handle_service_errors("project processing")
    async def _handle_project(self, state: AgentState) -> AgentState:
        """Handle project management tasks"""
        user_query = state.get("user_intent", "").lower()
        state["context"]["agent_type"] = "project"

        # Default: nothing special, just acknowledge
        summary_response = None

        # Check if user wants a summary of all group chats / project conversations
        if any(word in user_query for word in ["summarise", "summarize", "summary"]) and "chat" in user_query:
            try:
                project_id = state["context"].get("project_id")
                user_id = state["context"].get("user_id")

                if project_id and user_id:
                    # Increment tool call count
                    state["tool_calls_count"] = state.get("tool_calls_count", 0) + 1

                    # Fetch conversations from Postgres
                    async with db_manager.get_postgres_session() as session:
                        conv_service = ConversationProjectService(session)
                        convs_result = await conv_service.get_project_conversations(
                            project_id=uuid.UUID(project_id),
                            user_id=uuid.UUID(user_id),
                            include_archived=False
                        )

                    convs = convs_result.get("conversations", [])

                    if not convs:
                        summary_response = "There are no group conversations in this project yet."
                    else:
                        # Build detailed summary per conversation
                        from app.repositories.message_repository import MessageRepository
                        msg_repo = MessageRepository(db_manager)

                        summary_lines = []
                        for i, conv in enumerate(convs, 1):
                            title = getattr(conv, "title", None) or "Untitled Chat"
                            created = getattr(conv, "created_at", None)

                            # Fetch last message content (if any) from MongoDB
                            last_msg = await msg_repo.messages.find_one(
                                {"conversation_id": str(conv.id)}, sort=[("timestamp", -1)]
                            )
                            last_preview = (last_msg.get("message")[:60] + "…") if last_msg else "No messages yet"

                            count = await msg_repo.messages.count_documents({"conversation_id": str(conv.id)})

                            summary_lines.append(
                                f"{i}. {title} – {count} messages (last: '{last_preview}')"
                            )

                        summary_response = "Here is a summary of all project group chats:\n\n" + "\n".join(summary_lines)

                        # If user asks for content summary of a single chat and there's only one conversation, generate LLM summary
                        summarize_content = any(w in user_query for w in ["content", "discuss", "discussion", "topics"])

                        # If only one conversation, default to content summary even if keywords not explicit
                        if len(convs) == 1 and not summarize_content:
                            summarize_content = True

                        if summarize_content and len(convs) == 1:
                            conv_id = convs[0].id
                            # Fetch last 100 messages for summarization
                            msgs_cursor = msg_repo.messages.find({"conversation_id": str(conv_id)}).sort("timestamp", -1).limit(100)
                            messages = await msgs_cursor.to_list(length=100)
                            # Build transcript
                            transcript = "\n".join([
                                f"{m.get('sender_name') or m.get('sender_id')}: {m.get('message')}" for m in reversed(messages)
                            ])

                            summary_prompt = f"""You are an expert meeting assistant.
Summarise the following chat transcript into key points, decisions, and action items in bullet form (max 8 bullets).

Transcript:
{transcript}
"""

                            try:
                                llm_resp = await self.llm.ainvoke([
                                    {"role": "system", "content": "You summarise chat transcripts."},
                                    {"role": "user", "content": summary_prompt}
                                ])
                                summary_response += "\n\nChat content summary:\n" + llm_resp.content.strip()
                            except Exception as e:
                                logger.error(f"LLM summarisation failed: {e}")

                else:
                    summary_response = "Project or user context missing – cannot fetch group chats."

            except Exception as e:
                logger.error(f"Failed to summarise group chats: {e}")
                summary_response = "I couldn't access the project conversations due to an internal error."

        # If we generated a summary, store it as result
        if summary_response:
            state["result"] = {
                "message": summary_response,
                "type": "project_chat_summary"
            }
            state["context"]["response_ready"] = True

        state["updated_at"] = datetime.now()
        return state
    
    @handle_service_errors("paper processing")
    async def _handle_paper(self, state: AgentState) -> AgentState:
        """Handle paper processing tasks"""
        state["context"]["agent_type"] = "paper"
        state["context"]["needs_tools"] = True  # Paper processing needs tools
        state["updated_at"] = datetime.now()
        return state
    
    @handle_service_errors("conversation processing")
    async def _handle_conversation(self, state: AgentState) -> AgentState:
        """Intelligent conversation agent for general queries"""
        # Always derive the actual user query from the latest user message,
        # not from the intent label which can be categorical.
        user_query = ""
        try:
            for m in reversed(state.get("messages") or []):
                if isinstance(m, dict) and m.get("role") == "user":
                    user_query = m.get("content", "")
                    break
        except Exception:
            user_query = ""
        
        # Build chat messages including prior conversation history (if any)
        messages_payload = [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI research assistant. Be conversational but professional. "
                    "Leverage the provided conversation history to maintain context and continuity. "
                    "If the user asks about prior messages or a recap, use the provided conversation history to summarize them."
                ),
            }
        ]

        history = (state.get("context", {}) or {}).get("conversation_history", []) or []

        # If the user is asking about past messages, provide a deterministic recap without an LLM call
        query_lower = (user_query or "").lower()
        recap_triggers = [
            "what were my last messages", "what was my last chat", "recap of our chat",
            "summarize our chat", "summary of our chat", "what did we talk about",
            "what were my previous messages", "what were my last few messages"
        ]
        if history and any(trigger in query_lower for trigger in recap_triggers):
            try:
                # Summarize the last up to 8 messages succinctly (thematic summary via LLM)
                recent = history[-8:]
                transcript_lines = []
                for msg in recent:
                    content = (msg.get("content") or msg.get("message") or "").strip()
                    if not content:
                        continue
                    is_assistant = (
                        (msg.get("message_type") == "assistant")
                        or (msg.get("sender_type") == "agent")
                        or (msg.get("metadata", {}).get("ai_response") is True)
                    )
                    role = "Assistant" if is_assistant else "You"
                    snippet = content if len(content) <= 300 else content[:297] + "..."
                    transcript_lines.append(f"{role}: {snippet}")

                # If transcript is empty, return no-history message
                if not transcript_lines:
                    state["result"] = {
                        "message": "I couldn’t find prior messages in this conversation.",
                        "type": "conversation_recap",
                    }
                    state["context"]["response_ready"] = True
                    state["context"]["agent_type"] = "conversation"
                    state["updated_at"] = datetime.now()
                    return state

                thematic_prompt = (
                    "You are an expert conversation summarizer. Given the recent chat transcript, "
                    "identify 1-5 thematic segments that group similar user intents, and for each user theme, "
                    "infer the corresponding assistant response theme (overall gist of the assistant’s replies).\n\n"
                    "Output in the following plain-text format (no JSON):\n\n"
                    "Here’s a thematic summary of our recent messages:\n\n"
                    "1) User theme: <short phrase>\n"
                    "   Assistant theme: <short phrase>\n"
                    "   Representative messages:\n"
                    "   - You: \"<short user snippet>\"\n"
                    "   - Assistant: \"<short assistant snippet>\"\n\n"
                    "2) ... (and so on if applicable)\n\n"
                    "Transcript:\n" + "\n".join(transcript_lines)
                )

                # Try LLM-based thematic summary
                try:
                    llm_resp = await self.llm.ainvoke([
                        {"role": "system", "content": "You are precise and concise. Produce clean, readable summaries."},
                        {"role": "user", "content": thematic_prompt},
                    ])
                    llm_text = (getattr(llm_resp, "content", "") or str(llm_resp)).strip()
                    if llm_text:
                        state["result"] = {
                            "message": llm_text,
                            "type": "conversation_recap",
                        }
                        state["context"]["response_ready"] = True
                        state["context"]["agent_type"] = "conversation"
                        state["updated_at"] = datetime.now()
                        return state
                except Exception as e:
                    logger.warning(f"LLM thematic summary failed, falling back to deterministic recap: {e}")

                # Deterministic fallback: bullet recap
                lines = ["Here’s a brief recap of our recent messages:"]
                lines.extend([f"- {t}" for t in transcript_lines])
                state["result"] = {
                    "message": "\n".join(lines),
                    "type": "conversation_recap",
                }
                state["context"]["response_ready"] = True
                state["context"]["agent_type"] = "conversation"
                state["updated_at"] = datetime.now()
                return state
            except Exception as e:
                logger.warning(f"Failed to build recap: {e}. Falling back to normal conversation flow.")

        # Include last few messages to control token growth
        for msg in history[-8:]:
            try:
                content = msg.get("content") or msg.get("message") or ""
                # Prefer explicit message_type; fallback to sender_type or ai_response flag
                is_assistant = (
                    (msg.get("message_type") == "assistant")
                    or (msg.get("sender_type") == "agent")
                    or (msg.get("metadata", {}).get("ai_response") is True)
                )
                role = "assistant" if is_assistant else "user"
                if content:
                    messages_payload.append({"role": role, "content": content})
            except Exception:
                continue

        # Append current user query with clear instruction to utilize history when asked
        if user_query:
            conversation_prompt = f"""
You are an AI research assistant helping with academic research.

User Query: "{user_query}"

Guidelines:
- If the user requests a recap/what was said previously, use the conversation history (provided in earlier messages) to summarize recent turns.
- Otherwise, provide a helpful, conversational response. If research-related but unclear, offer to help with:
  - Searching for papers and research
  - Finding authors and citations  
  - Analyzing research trends
  - Managing research projects
  - Processing papers and documents

Be friendly, professional, and specific.
"""
            messages_payload.append({"role": "user", "content": conversation_prompt})
        else:
            # No user content found; ask a clarifying question
            messages_payload.append({
                "role": "user",
                "content": "The user message is missing. Ask a brief clarifying question to proceed."
            })

        try:
            response = await self.llm.ainvoke(messages_payload)

            state["result"] = {
                "message": (getattr(response, "content", "") or str(response)).strip(),
                "type": "conversation_response",
            }
            state["context"]["response_ready"] = True

        except Exception as e:
            logger.error(f"Conversation processing failed: {e}")
            state["result"] = {
                "message": "How can I assist you with your research today? I can help you search for papers, find authors, analyze research trends, and manage your research projects.",
                "type": "conversation_response",
            }

        state["context"]["agent_type"] = "conversation"
        state["updated_at"] = datetime.now()
        return state
    
    @handle_service_errors("analysis processing")
    async def _handle_analysis(self, state: AgentState) -> AgentState:
        """Handle analysis tasks"""
        state["context"]["agent_type"] = "analysis"
        state["context"]["needs_tools"] = True  # Analysis typically needs tools
        state["updated_at"] = datetime.now()
        return state
    
    @handle_service_errors("file processing")
    async def _handle_file(self, state: AgentState) -> AgentState:
        """Handle file processing tasks"""
        state["context"]["agent_type"] = "file"
        state["context"]["needs_tools"] = True  # File processing needs tools
        state["updated_at"] = datetime.now()
        return state
    
    @handle_service_errors("tool execution")
    async def _execute_tools(self, state: AgentState) -> AgentState:
        """Execute tools when needed (fallback for agents that didn't handle tools internally)"""
        state["tool_calls_count"] = state.get("tool_calls_count", 0) + 1
        
        agent_type = state.get("context", {}).get("agent_type", "unknown")
        search_query = state.get("context", {}).get("search_query", state.get("user_intent", ""))
        
        try:
            if agent_type == "research" and search_query:
                # Fallback research tool execution
                from app.services.research_aggregator_service import ResearchAggregatorService
                
                try:
                    async with ResearchAggregatorService() as aggregator:
                        search_result = await aggregator.comprehensive_paper_search(
                            query=search_query,
                            limit=10,  # Increased limit for better results
                            include_semantics=True,
                            include_code=True
                        )
                        
                        # Extract papers with fallback handling
                        papers = []
                        if search_result and isinstance(search_result, dict):
                            papers = search_result.get("papers", [])
                            if not papers:
                                # Try alternative keys that might contain papers
                                papers = search_result.get("results", [])
                        
                        # Always provide some result, even if search partially failed
                        search_stats = search_result.get("source_statistics", {}) if search_result else {}
                        
                        state["context"]["tool_results"] = [
                            {
                                "tool": "research_search",
                                "query": search_query,
                                "papers_found": len(papers),
                                "top_papers": papers[:5],  # Return top 5
                                "source_stats": search_stats,
                                "execution_time": search_result.get("execution_time", 0) if search_result else 0,
                                "timestamp": datetime.now().isoformat(),
                                "success": len(papers) > 0
                            }
                        ]
                        
                        logger.info(f"Research search completed: {len(papers)} papers found for '{search_query}'")
                        
                except Exception as search_error:
                    logger.error(f"Research search failed: {search_error}")
                    state["context"]["tool_results"] = [
                        {
                            "tool": "research_search",
                            "query": search_query,
                            "error": f"Search service error: {str(search_error)}",
                            "papers_found": 0,
                            "timestamp": datetime.now().isoformat(),
                            "success": False
                        }
                    ]
            else:
                # Generic placeholder for other tool types
                state["context"]["tool_results"] = [
                    {
                        "tool": f"{agent_type}_tool",
                        "result": f"Tool execution completed for {agent_type}",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
        
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            state["context"]["tool_results"] = [
                {
                    "tool": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            ]
        
        state["updated_at"] = datetime.now()
        return state
    
    @handle_service_errors("response formatting")
    async def _format_response(self, state: AgentState) -> AgentState:
        """Smart response formatter that uses agent results"""
        state["status"] = WorkflowStatus.COMPLETED.value
        
        # Check if agent already generated a response
        if state.get("result") and state["result"].get("message"):
            # Agent already generated an intelligent response, use it
            response_message = state["result"]["message"]
        else:
            # Fallback: Generate response based on context
            agent_type = state.get("context", {}).get("agent_type", "assistant")
            user_query = state.get("user_intent", "")
            
            if agent_type == "research":
                response_message = await self._generate_fallback_research_response(user_query, state)
            elif agent_type == "project":
                response_message = "I can help you manage your research projects, organize tasks, and coordinate team activities. What specific project management task would you like assistance with?"
            elif agent_type == "paper":
                response_message = "I can help you process research papers, extract key information, and organize your document library. Would you like to upload a paper or work with existing documents?"
            elif agent_type == "analysis":
                response_message = "I can help you analyze research data, compare studies, and evaluate findings. What type of analysis would you like to perform?"
            elif agent_type == "file":
                response_message = "I can assist with file operations, downloads, and data management for your research. What files would you like to work with?"
            else:
                response_message = "How can I further assist you with your research today? I can help you search for papers, analyze literature, manage projects, and process documents."
        
        # Update the final result
        if not state.get("result"):
            state["result"] = {}
        
        state["result"]["message"] = response_message
        state["updated_at"] = datetime.now()
        
        return state
    
    async def _generate_fallback_research_response(self, query: str, state: AgentState) -> str:
        """Generate fallback research response when main processing fails"""
        try:
            fallback_prompt = f"""
The user asked a research question but we couldn't process it fully: "{query}"

Provide a helpful response that:
1. Acknowledges their research question
2. Explains what type of information we typically help with
3. Suggests how they might rephrase or be more specific
4. Offers alternative ways to assist with their research

Be helpful and encouraging while explaining our research capabilities.
"""
            
            response = await self.llm.ainvoke([
                {"role": "system", "content": "You are a helpful research assistant explaining your capabilities."},
                {"role": "user", "content": fallback_prompt}
            ])
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Fallback response generation failed: {e}")
            return f"I'd be happy to help you research '{query}'. I can search for papers, identify key authors, analyze research trends, and provide insights on academic topics. Could you provide more specific details about what information you're looking for?"
    
    def _parse_llm_json_response(self, response_text: str, user_query: str) -> Dict[str, Any]:
        """Robust JSON parsing with intelligent fallbacks"""
        import json
        import re
        
        try:
            # First attempt: direct JSON parsing
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        try:
            # Second attempt: extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL | re.IGNORECASE)
            if json_match:
                return json.loads(json_match.group(1))
        except (json.JSONDecodeError, AttributeError):
            pass
        
        try:
            # Third attempt: find any JSON-like structure
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Fallback: Create strategy from query analysis
        logger.warning(f"Failed to parse LLM JSON response, using fallback strategy for: {user_query}")
        return self._create_fallback_strategy(user_query)
    
    def _create_fallback_strategy(self, user_query: str) -> Dict[str, Any]:
        """Create fallback research strategy when JSON parsing fails"""
        import re
        
        query_lower = user_query.lower()
        
        # Determine research type based on keywords
        if any(word in query_lower for word in ["author", "who", "researcher", "scientist"]):
            research_type = "author_search"
        elif any(word in query_lower for word in ["trend", "recent", "latest", "emerging"]):
            research_type = "trend_analysis"
        else:
            research_type = "paper_search"
        
        # Extract potential search terms
        search_terms = []
        
        # Remove common words and extract meaningful terms
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by", "are", "is", "who", "what", "how", "when", "where", "why"}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query_lower)
        meaningful_words = [word for word in words if word not in stop_words]
        
        # Take up to 3 most relevant terms
        search_terms = meaningful_words[:3]
        
        # If no meaningful terms, use the whole query as one term
        if not search_terms:
            search_terms = [user_query.strip()]
        
        return {
            "research_type": research_type,
            "search_terms": search_terms,
            "focus_area": f"Research related to: {', '.join(search_terms)}",
            "strategy": f"Search for {research_type.replace('_', ' ')} using terms: {', '.join(search_terms)}"
        }
    
    def _generate_fallback_response(self, user_query: str, research_results: Dict[str, Any]) -> str:
        """Generate fallback response when LLM response generation fails"""
        papers = research_results.get("papers", [])
        authors = research_results.get("authors", [])
        
        if authors:
            # Generate author-focused response
            top_authors = authors[:5]
            response = f"Based on my research analysis for '{user_query}', here are the most prominent authors I found:\n\n"
            
            for i, author in enumerate(top_authors, 1):
                name = author.get("name", "Unknown")
                paper_count = author.get("paper_count", 0)
                citations = author.get("total_citations", 0)
                affiliations = author.get("affiliations", [])
                affiliation = affiliations[0] if affiliations else "Unknown affiliation"
                
                response += f"{i}. **{name}**\n"
                response += f"   - {paper_count} papers found\n"
                response += f"   - {citations} total citations\n"
                response += f"   - Affiliation: {affiliation}\n\n"
            
            response += f"This analysis is based on {len(papers)} research papers across multiple academic databases."
            return response
            
        elif papers:
            # Generate paper-focused response
            top_papers = papers[:5]
            response = f"I found {len(papers)} relevant papers for '{user_query}'. Here are the most cited:\n\n"
            
            for i, paper in enumerate(top_papers, 1):
                title = paper.get("title", "Unknown Title")
                authors_list = [a.get("name", "Unknown") for a in paper.get("authors", [])]
                citations = paper.get("citation_count", 0)
                
                response += f"{i}. **{title}**\n"
                response += f"   - Authors: {', '.join(authors_list[:3])}\n"
                response += f"   - Citations: {citations}\n\n"
            
            return response
        else:
            return f"I searched for information about '{user_query}' but couldn't find specific results. Please try rephrasing your question or being more specific about what you're looking for."

    @handle_service_errors("error handling")
    async def _handle_error(self, state: AgentState) -> AgentState:
        """Handle workflow errors"""
        state["status"] = WorkflowStatus.FAILED.value
        if not state.get("error"):
            state["error"] = "Unknown workflow error"
        
        state["result"] = {
            "error": state["error"],
            "status": "failed"
        }
        state["updated_at"] = datetime.now()
        return state
    
    @handle_service_errors("human feedback")
    async def _request_human_feedback(self, state: AgentState) -> AgentState:
        """Request human feedback (human-in-the-loop)"""
        state["status"] = "awaiting_feedback"
        state["result"] = {
            "message": "Human feedback required",
            "context": state.get("context", {})
        }
        state["updated_at"] = datetime.now()
        return state
    
    # Public interface
    @handle_service_errors("workflow execution")
    async def execute(
        self,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the LangGraph workflow"""
        
        session_id = session_id or str(uuid.uuid4())
        
        initial_state: AgentState = {
            "messages": messages,
            "task_type": None,
            "user_intent": None,
            "context": context or {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": self.config.max_tool_calls,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": session_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        try:
            # Execute workflow
            config = {"configurable": {"thread_id": session_id}}
            result = await self.app.ainvoke(initial_state, config=config)
            
            return {
                "success": True,
                "session_id": session_id,
                "status": result.get("status"),
                "result": result.get("result"),
                "metadata": {
                    "tool_calls": result.get("tool_calls_count", 0),
                    "agent_type": result.get("context", {}).get("agent_type"),
                    "execution_time": (
                        result.get("updated_at", datetime.now()) - 
                        result.get("created_at", datetime.now())
                    ).total_seconds()
                }
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "status": WorkflowStatus.FAILED.value
            }
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for a session"""
        if not self.checkpointer:
            return None
        
        try:
            config = {"configurable": {"thread_id": session_id}}
            checkpoint = await self.app.aget_state(config)
            return checkpoint.values if checkpoint else None
        except Exception as e:
            logger.error(f"Failed to get session state: {str(e)}")
            return None
    
    async def resume_session(
        self,
        session_id: str,
        additional_messages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Resume an existing session"""
        current_state = await self.get_session_state(session_id)
        if not current_state:
            raise ServiceError(
                "Session not found",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        if additional_messages:
            current_state["messages"].extend(additional_messages)
        
        return await self.execute(
            current_state["messages"],
            session_id,
            current_state.get("context")
        )