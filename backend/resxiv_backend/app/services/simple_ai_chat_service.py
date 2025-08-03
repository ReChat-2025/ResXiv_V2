"""
Simple AI Chat Service - L6 Engineering Standards

Focused service for basic GPT conversation handling.
No complex orchestration - just simple AI chat with conversation persistence.
"""

import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.conversation_repository import ConversationRepository
from app.models.conversation_models import ConversationType
from app.database.connection import DatabaseManager
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class SimpleAIChatService:
    """
    Simple AI chat service for basic GPT conversations.
    
    Single Responsibility: AI chat conversation management
    - Creates/manages AI conversations (type=AI)
    - Stores messages in MongoDB
    - Uses configurable OpenAI GPT model for responses
    - No complex tool orchestration
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.agentic.openai_api_key)
        self.mongo_db = None
        
    async def initialize(self):
        """Initialize MongoDB connection"""
        try:
            from app.database.connection import db_manager
            self.mongo_db = db_manager.mongodb_client.resxiv_chat
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB for simple AI chat: {e}")
            raise ServiceError(
                "Failed to initialize chat service",
                ErrorCodes.DATABASE_CONNECTION_ERROR
            )
    
    @handle_service_errors("simple AI chat")
    async def chat(
        self,
        user_id: str,
        project_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process simple AI chat request within project context.
        
        Args:
            user_id: User ID
            project_id: Project ID for scoping
            message: User message
            conversation_id: Optional existing conversation ID
            
        Returns:
            Chat response with conversation data
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing AI chat for user {user_id}, project {project_id}, conversation_id: {conversation_id}")
            
            if self.mongo_db is None:
                await self.initialize()
            
            project_uuid = uuid.UUID(project_id)
            
            # Get or create conversation
            conversation = None
            
            if conversation_id:
                try:
                    conv_uuid = uuid.UUID(conversation_id)
                    existing_conversation = await self.conversation_repo.get_conversation_by_id(conv_uuid)
                    
                    # Validate the existing conversation
                    if (existing_conversation and 
                        existing_conversation.type == ConversationType.AI and
                        existing_conversation.entity == project_uuid and
                        str(existing_conversation.created_by) == user_id):
                        
                        conversation = existing_conversation
                        conversation_id = str(conversation.id)  # Ensure conversation_id is properly set
                        logger.info(f"Using existing AI conversation {conversation_id}")
                    else:
                        # Log why we're not using the provided conversation_id
                        if not existing_conversation:
                            logger.warning(f"Conversation {conversation_id} not found, creating new AI conversation")
                        elif existing_conversation.type != ConversationType.AI:
                            logger.warning(f"Conversation {conversation_id} is type {existing_conversation.type}, not AI. Creating new AI conversation")
                        elif existing_conversation.entity != project_uuid:
                            logger.warning(f"Conversation {conversation_id} belongs to different project, creating new AI conversation")
                        else:
                            logger.warning(f"User {user_id} doesn't have access to conversation {conversation_id}, creating new AI conversation")
                            
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid conversation_id format '{conversation_id}': {e}. Creating new AI conversation")
            
            # Create new AI conversation if we don't have a valid one
            if not conversation:
                conversation = await self.conversation_repo.create(
                    type=ConversationType.AI,
                    entity=project_uuid,  # AI conversations belong to projects
                    is_group=False,
                    created_by=uuid.UUID(user_id)
                )
                await self.session.commit()
                conversation_id = str(conversation.id)
                logger.info(f"Created new AI conversation {conversation_id} for project {project_id}")
            
            # Get conversation history for context
            history = await self._get_conversation_history(conversation_id)
            
            # Generate AI response
            ai_response = await self._generate_ai_response(message, history)
            
            # Save messages to MongoDB
            await self._save_chat_messages(
                conversation_id=conversation_id,
                user_id=user_id,
                project_id=project_id,
                user_message=message,
                ai_response=ai_response
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"AI chat completed successfully for conversation {conversation_id} in {processing_time:.3f}s")
            
            return {
                "success": True,
                "response": ai_response,
                "conversation_id": conversation_id,
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "conversation_type": "AI",
                    "model": self.settings.agentic.agentic_model,
                    "project_id": project_id
                }
            }
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Simple AI chat failed: {e}")
            raise ServiceError(
                "Failed to process AI chat request",
                ErrorCodes.AGENTIC_PROCESSING_ERROR
            )
    
    async def _get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get recent conversation history for context"""
        try:
            messages = await self.mongo_db.messages.find(
                {"conversation_id": conversation_id},
                {"message": 1, "sender_id": 1, "timestamp": 1, "metadata": 1}
            ).sort("timestamp", -1).limit(10).to_list(length=10)
            
            # Reverse to get chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.warning(f"Failed to get conversation history: {e}")
            return []
    
    async def _generate_ai_response(
        self,
        user_message: str,
        history: List[Dict[str, Any]]
    ) -> str:
        """Generate AI response using OpenAI GPT"""
        try:
            # Build messages for OpenAI
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant for ResXiv, a research platform. "
                        "You are currently helping within a specific research project context. "
                        "Assist users with research-related questions, project discussions, "
                        "general inquiries, and provide helpful, accurate responses. "
                        "Be concise but informative."
                    )
                }
            ]
            
            # Add conversation history
            for msg in history[-6:]:  # Last 6 messages for context
                is_ai_response = msg.get("metadata", {}).get("ai_response", False)
                role = "assistant" if is_ai_response else "user"
                messages.append({
                    "role": role,
                    "content": msg["message"]
                })
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            response = await self.client.chat.completions.create(
                model=self.settings.agentic.agentic_model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
            raise ServiceError(
                "Failed to generate AI response",
                ErrorCodes.EXTERNAL_API_ERROR
            )
    
    async def _save_chat_messages(
        self,
        conversation_id: str,
        user_id: str,
        project_id: str,
        user_message: str,
        ai_response: str
    ) -> None:
        """Save chat messages to MongoDB"""
        try:
            timestamp = datetime.utcnow()
            
            # Save user message
            user_msg = {
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4()),
                "sender_id": user_id,
                "message": user_message,
                "message_type": "text",
                "timestamp": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
                "metadata": {
                    "conversation_type": "AI",
                    "project_id": project_id
                }
            }
            
            # Save AI response
            ai_msg = {
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4()),
                "sender_id": user_id,  # Associate with conversation owner
                "message": ai_response,
                "message_type": "text",
                "timestamp": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
                "metadata": {
                    "conversation_type": "AI",
                    "ai_response": True,
                    "model": self.settings.agentic.agentic_model,
                    "project_id": project_id
                }
            }
            
            # Insert both messages
            await self.mongo_db.messages.insert_many([user_msg, ai_msg])
            
            logger.info(f"Saved AI chat messages for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save AI chat messages: {e}")
            # Don't raise error for message saving failure 