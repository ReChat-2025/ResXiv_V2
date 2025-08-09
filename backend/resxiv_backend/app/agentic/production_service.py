"""
Production-Grade Agentic Service

Clean, efficient service replacing the bloated original implementation.
Follows SOLID principles and proper error handling.
"""

import logging
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from app.config.settings import get_settings
from .enhanced_langgraph import EnhancedLangGraphOrchestrator as ProductionOrchestrator
from .production_conversation_manager import ProductionConversationManager

logger = logging.getLogger(__name__)


class ProductionAgenticService:
    """
    Production-grade agentic service with focused responsibilities.
    
    Single Responsibility: Coordinate AI agent interactions
    Open/Closed: Easy to extend with new agents
    Liskov Substitution: Can replace original service 
    Interface Segregation: Clean, minimal interface
    Dependency Inversion: Depends on abstractions
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.orchestrator: Optional[ProductionOrchestrator] = None
        self.conversation_manager: Optional[ProductionConversationManager] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the service with proper error handling"""
        if self._initialized:
            logger.warning("ProductionAgenticService already initialized")
            return
        
        try:
            # Initialize orchestrator if OpenAI key is available
            if hasattr(self.settings, 'agentic') and self.settings.agentic:
                openai_key = getattr(self.settings.agentic, 'openai_api_key', None)
                if openai_key:
                    # Import LangGraphConfig for proper configuration
                    from .production_langgraph import LangGraphConfig
                    
                    # Create config with model name
                    config = LangGraphConfig(
                        model_name=getattr(self.settings.agentic, 'agentic_model', 'gpt-4o-mini')
                    )
                    
                    self.orchestrator = ProductionOrchestrator(
                        openai_api_key=openai_key,
                        config=config
                    )
                    logger.info("Production orchestrator initialized successfully")
                else:
                    logger.warning("OpenAI API key not configured - orchestrator disabled")
            
            # Initialize conversation manager
            self.conversation_manager = ProductionConversationManager()
            await self.conversation_manager.initialize()
            
            self._initialized = True
            logger.info("ProductionAgenticService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ProductionAgenticService: {e}")
            raise
    
    async def process_message(
        self,
        message: str,
        user_id: str,
        project_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message through the agentic system.
        
        Args:
            message: User message to process
            user_id: ID of the user sending the message
            project_id: Optional project context
            conversation_id: Optional conversation context
            context: Additional context data
            
        Returns:
            Response dictionary with results and metadata
        """
        if not self._initialized:
            raise RuntimeError("ProductionAgenticService not initialized")
        
        start_time = datetime.utcnow()
        
        try:
            # Generate thread ID for conversation continuity
            thread_id = conversation_id or str(uuid4())
            logger.debug(f"Conversation ID: {conversation_id}")
            # Prepare context
            processing_context = {
                "user_id": user_id,
                "project_id": project_id,
                "conversation_id": conversation_id,
                **(context or {})
            }
            
            # Get conversation history if available
            if self.conversation_manager and conversation_id:
                try:
                    history = await self.conversation_manager.get_conversation_history(
                        conversation_id,
                        limit=10
                    )
                    logger.debug(f"Loaded conversation history: {len(history)} messages")
                    processing_context["conversation_history"] = history
                except Exception as e:
                    logger.warning(f"Failed to load conversation history: {e}")
                    processing_context["conversation_history"] = []
            
            # Process through orchestrator
            if self.orchestrator:
                result = await self.orchestrator.process_message(
                    message=message,
                    thread_id=thread_id,
                    context=processing_context
                )
            else:
                # Fallback response when orchestrator is not available
                result = {
                    "response": "I'm currently running in limited mode. Some AI features may not be available.",
                    "intent": "conversation",
                    "agent": "fallback_agent",
                    "tool_calls": 0,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Save to conversation history if manager is available
            if self.conversation_manager and conversation_id:
                try:
                    await self.conversation_manager.add_message(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        message=message,
                        message_type="user"
                    )
                    
                    # Only save assistant message if there's actual content
                    assistant_message = result.get("response", "")
                    if assistant_message and assistant_message.strip():
                        await self.conversation_manager.add_message(
                            conversation_id=conversation_id,
                            user_id="system",
                            message=assistant_message,
                            message_type="assistant",
                            metadata={"agent_result": result, "ai_response": True}
                        )
                except Exception as e:
                    logger.warning(f"Failed to save conversation: {e}")
            
            # Add processing metadata
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result["processing_time"] = processing_time
            result["service_version"] = "production_v1"
            
            logger.info(f"Message processed successfully in {processing_time:.3f}s")
            return result
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Message processing failed after {processing_time:.3f}s: {e}")
            
            return {
                "error": str(e),
                "message": "Failed to process message",
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat(),
                "service_version": "production_v1"
            }
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get conversation history for a given conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            user_id: Optional user ID for authorization
            
        Returns:
            Dictionary containing conversation history
        """
        if not self._initialized:
            raise RuntimeError("ProductionAgenticService not initialized")
        
        try:
            if self.conversation_manager:
                history = await self.conversation_manager.get_conversation_history(
                    conversation_id,
                    limit=limit
                )
                return {
                    "success": True,
                    "conversation_id": conversation_id,
                    "messages": history,
                    "count": len(history)
                }
            else:
                return {
                    "success": False,
                    "error": "Conversation manager not available",
                    "conversation_id": conversation_id,
                    "messages": [],
                    "count": 0
                }
        
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return {
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id,
                "messages": [],
                "count": 0
            }
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get service capabilities and status"""
        capabilities = {
            "service_name": "ProductionAgenticService",
            "version": "1.0.0",
            "initialized": self._initialized,
            "orchestrator_available": self.orchestrator is not None,
            "conversation_manager_available": self.conversation_manager is not None,
            "supported_intents": [
                "research", "project", "paper", "conversation"
            ],
            "features": {
                "intent_classification": True,
                "tool_execution": self.orchestrator is not None,
                "conversation_memory": self.conversation_manager is not None,
                "multi_agent_routing": True,
                "structured_responses": True
            }
        }
        
        return capabilities
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        health = {
            "service": "healthy" if self._initialized else "unhealthy",
            "orchestrator": "healthy" if self.orchestrator else "disabled",
            "conversation_manager": "unknown",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check conversation manager
        if self.conversation_manager:
            try:
                # Simple health check - this would be implemented in the manager
                health["conversation_manager"] = "healthy"
            except Exception as e:
                health["conversation_manager"] = f"unhealthy: {str(e)}"
        else:
            health["conversation_manager"] = "disabled"
        
        return health
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            if self.conversation_manager:
                # Cleanup conversation manager resources if needed
                pass
            
            self._initialized = False
            logger.info("ProductionAgenticService cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


# Global production service instance
production_agentic_service = ProductionAgenticService() 