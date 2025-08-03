"""
LaTeX Editor Service - GPT-4o Mini Integration

Provides AI-powered LaTeX editing capabilities for research documents.
Supports both text-based and image-based input for LaTeX content editing.
"""

import time
import uuid
import logging
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime

from openai import AsyncOpenAI
from fastapi import UploadFile
from PIL import Image
import io

from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import get_settings
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.conversation_repository import ConversationRepository
from app.models.conversation_models import ConversationType
from app.database.mongodb import get_mongodb_database

logger = logging.getLogger(__name__)


class LaTeXEditorService:
    """
    Service for AI-powered LaTeX editing using GPT-4o mini.
    
    Supports research-focused editing with project context and conversation management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.agentic.openai_api_key)
        self.model = "gpt-4o-mini"
        self.conversation_repo = ConversationRepository(session)
        self.mongo_db = None
        
    async def initialize(self):
        """Initialize MongoDB connection"""
        try:
            self.mongo_db = await get_mongodb_database()
            logger.info("LaTeX Editor Service initialized with MongoDB")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise ServiceError(
                "Failed to initialize LaTeX editor service",
                ErrorCodes.INITIALIZATION_ERROR
            )
    
    @handle_service_errors("edit LaTeX content")
    async def edit_latex_content(
        self,
        prompt: str,
        project_id: str,
        user_id: str,
        latex_content: Optional[str] = None,
        image_file: Optional[UploadFile] = None,
        edit_type: str = "general",
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Edit LaTeX content based on user prompt and edit type.
        
        Args:
            prompt: User's editing instructions
            project_id: Project context ID
            user_id: User requesting the edit
            latex_content: Existing LaTeX content to edit
            image_file: Optional image containing LaTeX content
            edit_type: Type of editing to perform
            conversation_id: Optional conversation for context
            
        Returns:
            Dictionary containing edited content and metadata
        """
        start_time = time.time()
        
        try:
            # Handle conversation management
            if not conversation_id:
                # Create new LaTeX editing conversation
                conversation = await self.conversation_repo.create(
                    type=ConversationType.AI,  # Use AI type for LaTeX editing
                    entity=uuid.UUID(project_id),
                    is_group=False,
                    created_by=uuid.UUID(user_id)
                )
                await self.session.commit()
                conversation_id = str(conversation.id)
                logger.info(f"Created new LaTeX editing conversation {conversation_id}")
            
            # Extract LaTeX content from image if provided
            if image_file and not latex_content:
                latex_content = await self._extract_latex_from_image(image_file)
            
            # Validate input
            if not latex_content and not image_file:
                raise ServiceError(
                    "Either LaTeX content or image must be provided",
                    ErrorCodes.VALIDATION_ERROR
                )
            
            # Generate edited content using GPT-4o mini
            edit_result = await self._generate_latex_edit(
                prompt=prompt,
                latex_content=latex_content,
                edit_type=edit_type
            )
            
            # Store conversation message
            await self._store_editing_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                prompt=prompt,
                original_content=latex_content or "[Image input]",
                edited_content=edit_result["edited_content"],
                changes_made=edit_result["changes_made"]
            )
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "edited_content": edit_result["edited_content"],
                "changes_made": edit_result["changes_made"],
                "suggestions": edit_result["suggestions"],
                "conversation_id": conversation_id,
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "edit_type": edit_type,
                    "original_length": len(latex_content) if latex_content else 0,
                    "edited_length": len(edit_result["edited_content"]),
                    "model_used": self.model,
                    "project_id": project_id,
                    "has_image_input": image_file is not None
                }
            }
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"LaTeX editing failed: {e}")
            raise ServiceError(
                "Failed to edit LaTeX content",
                ErrorCodes.AGENTIC_PROCESSING_ERROR
            )
    
    async def _extract_latex_from_image(self, image_file: UploadFile) -> str:
        """Extract LaTeX content from uploaded image using GPT-4o mini vision."""
        try:
            # Read and validate image
            image_data = await image_file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to base64 for GPT-4o mini
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Use GPT-4o mini vision to extract LaTeX
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a LaTeX expert. Extract the LaTeX content from the provided image. 
                        If the image contains mathematical equations, convert them to proper LaTeX syntax.
                        If it contains text, preserve the academic writing style.
                        Return only the LaTeX content without explanations."""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please extract the LaTeX content from this image:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract LaTeX from image: {e}")
            raise ServiceError(
                "Failed to extract LaTeX content from image",
                ErrorCodes.PROCESSING_ERROR
            )
    
    async def _generate_latex_edit(
        self,
        prompt: str,
        latex_content: str,
        edit_type: str
    ) -> Dict[str, Any]:
        """Generate edited LaTeX content using GPT-4o mini."""
        
        # Create specialized system prompt based on edit type
        system_prompts = {
            "general": "You are a research writing assistant specializing in LaTeX document editing. Help improve academic papers with proper LaTeX formatting.",
            "formatting": "You are a LaTeX formatting expert. Focus on proper LaTeX syntax, document structure, and typographic conventions for academic papers.",
            "content": "You are an academic writing coach. Improve the clarity, flow, and scholarly quality of research content while maintaining LaTeX formatting.",
            "structure": "You are a document structure specialist. Optimize section organization, cross-references, and overall document hierarchy in LaTeX.",
            "citations": "You are a citation and bibliography expert. Improve citation style, reference formatting, and bibliography management in LaTeX.",
            "grammar": "You are an academic proofreader. Fix grammar, spelling, and punctuation while preserving LaTeX commands and academic tone."
        }
        
        system_prompt = system_prompts.get(edit_type, system_prompts["general"])
        
        user_prompt = f"""Edit the following LaTeX content based on these instructions: {prompt}

Original LaTeX content:
```latex
{latex_content}
```

Please:
1. Apply the requested edits while maintaining proper LaTeX syntax
2. Preserve all necessary LaTeX commands and environments
3. Ensure academic writing standards are maintained
4. Keep the content suitable for research publication

Return your response in JSON format with:
- "edited_content": The improved LaTeX content
- "changes_made": Array of specific changes you made
- "suggestions": Array of additional improvement recommendations

Focus on research-quality improvements such as:
- Academic tone and clarity
- Proper mathematical notation
- Citation and reference formatting
- Section structure and organization
- Figure and table integration
- Cross-referencing consistency"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.3  # Lower temperature for more consistent edits
            )
            
            # Parse JSON response
            import json
            response_content = response.choices[0].message.content.strip()
            
            # Extract JSON from response (handle potential markdown formatting)
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.rfind("```")
                response_content = response_content[json_start:json_end].strip()
            
            result = json.loads(response_content)
            
            # Validate response structure
            required_keys = ["edited_content", "changes_made", "suggestions"]
            for key in required_keys:
                if key not in result:
                    result[key] = [] if key != "edited_content" else latex_content
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse GPT response as JSON: {e}")
            # Fallback: return original content with error message
            return {
                "edited_content": latex_content,
                "changes_made": ["Error parsing AI response - content returned unchanged"],
                "suggestions": ["Please try again with a different prompt"]
            }
        except Exception as e:
            logger.error(f"Failed to generate LaTeX edit: {e}")
            raise ServiceError(
                "Failed to generate edited content",
                ErrorCodes.AI_PROCESSING_ERROR
            )
    
    async def _store_editing_conversation(
        self,
        conversation_id: str,
        user_id: str,
        prompt: str,
        original_content: str,
        edited_content: str,
        changes_made: List[str]
    ):
        """Store editing conversation in MongoDB."""
        try:
            if not self.mongo_db:
                logger.warning("MongoDB not available, skipping conversation storage")
                return
            
            messages_collection = self.mongo_db.conversation_messages
            
            # Store user message
            user_message = {
                "conversation_id": conversation_id,
                "sender_id": user_id,
                "sender_type": "user",
                "content": f"Edit request: {prompt}\n\nOriginal content: {original_content[:500]}...",
                "timestamp": datetime.utcnow(),
                "message_type": "latex_edit_request"
            }
            
            # Store AI response
            ai_message = {
                "conversation_id": conversation_id,
                "sender_type": "ai",
                "content": edited_content,
                "timestamp": datetime.utcnow(),
                "message_type": "latex_edit_response",
                "metadata": {
                    "changes_made": changes_made,
                    "model": self.model
                }
            }
            
            await messages_collection.insert_many([user_message, ai_message])
            logger.info(f"Stored LaTeX editing conversation: {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to store editing conversation: {e}")
            # Don't raise error - conversation storage is not critical 