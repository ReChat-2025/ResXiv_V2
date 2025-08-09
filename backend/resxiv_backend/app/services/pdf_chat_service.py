"""
PDF Chat Service - GPT-4o-mini Integration

Handles chat functionality with PDF documents, supporting both
existing papers and dropped files.
"""

import time
import uuid
import logging
import tempfile
import aiofiles
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.paper_repository import PaperRepository
from app.services.paper.paper_processing_service import PaperProcessingService
from app.models.conversation_models import ConversationType
from app.database.connection import get_mongodb_database

logger = logging.getLogger(__name__)

# Include the last 8 turns (16 messages) for context
HISTORY_TURNS = 8


class PDFChatService:
    """
    Service for chatting with PDF documents using GPT-4o-mini.
    
    Supports both existing papers and newly uploaded PDFs.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.agentic.openai_api_key)
        self.model = "gpt-4o-mini"
        self.conversation_repo = ConversationRepository(session)
        self.paper_repo = PaperRepository(session)
        self.processing_service = PaperProcessingService(session)
        self.mongo_db = None
        
    async def initialize(self):
        """Initialize MongoDB connection"""
        try:
            self.mongo_db = await get_mongodb_database()
            logger.info("PDF Chat Service initialized with MongoDB")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise ServiceError(
                "Failed to initialize chat service",
                ErrorCodes.INITIALIZATION_ERROR
            )
    
    @handle_service_errors("chat with paper")
    async def chat_with_paper(
        self,
        paper_id: str,
        project_id: str,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chat with an existing paper by UUID.
        
        Args:
            paper_id: UUID of the paper
            project_id: Project UUID containing the paper
            user_id: User UUID
            message: User's message about the paper
            conversation_id: Optional existing conversation ID
            
        Returns:
            Chat response with conversation details
        """
        start_time = time.time()
        
        # Verify paper exists and get content
        paper = await self.paper_repo.get_paper_by_id(paper_id)
        if not paper:
            raise ServiceError(
                f"Paper with ID {paper_id} not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Extract PDF content if not already available
        pdf_content = await self._get_paper_content(paper)
        
        # Get or create conversation
        if conversation_id and conversation_id.strip() and conversation_id != "string":
            try:
                conversation = await self.conversation_repo.get_by_id(uuid.UUID(conversation_id))
                if not conversation or conversation.type != ConversationType.PDF.value:
                    raise ServiceError(
                        "Invalid conversation ID for paper chat",
                        ErrorCodes.VALIDATION_ERROR
                    )
            except ValueError:
                raise ServiceError(
                    "Invalid conversation ID format - must be a valid UUID",
                    ErrorCodes.VALIDATION_ERROR
                )
        else:
            # Create new PDF conversation
            conversation = await self.conversation_repo.create(
                type=ConversationType.PDF,
                entity=uuid.UUID(paper_id),
                is_group=False,
                created_by=uuid.UUID(user_id)
            )
            await self.session.commit()
            conversation_id = str(conversation.id)
        
        # Get conversation history
        conversation_history = await self._get_conversation_history(conversation_id)
        
        # Generate AI response
        ai_response = await self._generate_chat_response(
            pdf_content=pdf_content,
            user_message=message,
            conversation_history=conversation_history,
            paper_metadata={
                "title": paper.title,
                "authors": paper.authors,
                "abstract": getattr(paper, 'abstract', None)
            }
        )
        
        # Save messages to MongoDB
        await self._save_chat_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=message,
            ai_response=ai_response,
            metadata={
                "paper_id": paper_id,
                "paper_title": paper.title,
                "conversation_type": "PDF"
            }
        )
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "response": ai_response,
            "conversation_id": conversation_id,
            "paper_id": paper_id,
            "processing_time": processing_time,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "paper_title": paper.title,
                "conversation_type": "PDF",
                "user_id": user_id
            }
        }
    
    @handle_service_errors("chat with dropped file")
    async def chat_with_dropped_file(
        self,
        file: Optional[UploadFile],
        project_id: str,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chat with a PDF in a project context. Works for both:
        - First turn with a newly uploaded file (stores PDF context)
        - Subsequent turns without re-upload (reuses stored context)
        
        Args:
            file: Uploaded PDF file (optional for continuation)
            project_id: Project UUID for access control and organization
            user_id: User UUID
            message: User's message about the file
            conversation_id: Optional existing conversation ID
            
        Returns:
            Chat response with conversation details
        """
        start_time = time.time()
        
        file_id: Optional[str] = None
        pdf_content: Optional[str] = None
        file_name: Optional[str] = None

        # Get or create conversation
        conversation = None
        if conversation_id and conversation_id.strip() and conversation_id != "string":
            try:
                candidate = await self.conversation_repo.get_by_id(uuid.UUID(conversation_id))
                if candidate and candidate.type == ConversationType.DROP.value:
                    conversation = candidate
                else:
                    logger.info("Provided conversation_id is missing or not DROP; creating a new DROP conversation")
            except ValueError:
                logger.info("Provided conversation_id is not a valid UUID; creating a new DROP conversation")
        if conversation is None:
            # Create new DROP conversation associated with project
            conversation = await self.conversation_repo.create(
                type=ConversationType.DROP,
                entity=uuid.UUID(project_id),  # Associate with project for access control
                is_group=False,
                created_by=uuid.UUID(user_id)
            )
            await self.session.commit()
            conversation_id = str(conversation.id)
        else:
            conversation_id = str(conversation.id)
        
        # If file is provided, extract and persist context; otherwise, reuse stored context
        if file is not None and getattr(file, 'filename', None):
            if not file.filename.lower().endswith('.pdf'):
                raise ServiceError(
                    "Only PDF files are supported",
                    ErrorCodes.VALIDATION_ERROR
                )
            file_id = str(uuid.uuid4())
            pdf_content = await self._extract_content_from_upload(file, file_id)
            file_name = file.filename
            # Persist context for future turns
            await self._ensure_drop_context(
                conversation_id=conversation_id,
                user_id=user_id,
                project_id=project_id,
                file_id=file_id,
                file_name=file_name,
                pdf_content=pdf_content
            )
        else:
            # Reuse stored context
            stored_content, ctx = await self._get_drop_context(conversation_id)
            pdf_content = stored_content
            file_id = ctx.get("file_id") if ctx else None
            file_name = ctx.get("file_name") if ctx else None
            if not pdf_content:
                raise ServiceError(
                    "No stored PDF context found for this conversation. Please upload the PDF again.",
                    ErrorCodes.NOT_FOUND_ERROR
                )
        
        # Get conversation history
        conversation_history = await self._get_conversation_history(conversation_id)
        
        # Generate AI response
        ai_response = await self._generate_chat_response(
            pdf_content=pdf_content,
            user_message=message,
            conversation_history=conversation_history,
            paper_metadata={
                "filename": file_name,
                "file_size": getattr(file, 'size', None)
            }
        )
        
        # Save messages to MongoDB
        await self._save_chat_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=message,
            ai_response=ai_response,
            metadata={
                "file_id": file_id,
                "file_name": file_name,
                "conversation_type": "DROP",
                "project_id": project_id
            }
        )
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "response": ai_response,
            "conversation_id": conversation_id,
            "file_id": file_id,
            "processing_time": processing_time,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "file_name": file_name,
                "conversation_type": "DROP",
                "project_id": project_id,
                "user_id": user_id
            }
        }

    async def _get_paper_content(self, paper) -> str:
        """Extract content from paper using existing processing service"""
        try:
            # Check if we have a stored PDF path
            if not paper.pdf_path:
                raise ServiceError(
                    "No PDF file found for this paper",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            # Get file path
            from app.services.paper.paper_storage_service import PaperStorageService
            storage_service = PaperStorageService(self.session)
            file_path = await storage_service.get_file_path(str(paper.id))
            
            if not file_path:
                raise ServiceError(
                    "PDF file not found on disk",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            # Extract text using PyPDF
            result = await self.processing_service.extract_text_with_pypdf(
                file_path, str(paper.id)
            )
            
            if not result.get("success"):
                raise ServiceError(
                    "Failed to extract text from PDF",
                    ErrorCodes.PROCESSING_ERROR
                )
            
            return result["text_content"]
            
        except Exception as e:
            logger.error(f"Failed to get paper content: {e}")
            raise ServiceError(
                "Failed to extract paper content",
                ErrorCodes.PROCESSING_ERROR
            )
    
    async def _extract_content_from_upload(self, file: UploadFile, file_id: str) -> str:
        """Extract content from uploaded PDF file"""
        try:
            import PyPDF2
            import io
            
            # Read file content
            content = await file.read()
            
            # Reset file pointer for potential reuse
            await file.seek(0)
            
            # Extract text using PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text_content = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(page_text.strip())
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
            
            full_text = '\n\n'.join(text_content)
            
            if not full_text or len(full_text.split()) < 50:
                raise ServiceError(
                    "Insufficient text content extracted from PDF",
                    ErrorCodes.PROCESSING_ERROR
                )
            
            logger.info(f"Extracted {len(full_text.split())} words from uploaded PDF")
            return full_text
            
        except Exception as e:
            logger.error(f"Failed to extract content from upload: {e}")
            raise ServiceError(
                "Failed to process uploaded PDF",
                ErrorCodes.PROCESSING_ERROR
            )
    
    async def _generate_chat_response(
        self,
        pdf_content: str,
        user_message: str,
        conversation_history: list,
        paper_metadata: Dict[str, Any]
    ) -> str:
        """Generate AI response using GPT-4o-mini"""
        try:
            # Prepare system prompt
            system_prompt = """You are a senior researcher and academic expert with extensive experience in peer review, research methodology, and scientific analysis. When discussing research papers, you approach them with the critical eye of a seasoned researcher who understands both the theoretical foundations and practical implications of academic work.

**Your Research Perspective:**
- Analyze papers through the lens of methodology, validity, and scientific rigor
- Identify research gaps, limitations, and areas for future investigation
- Provide insights on how this work fits into the broader research landscape
- Suggest potential follow-up studies, experimental designs, or theoretical extensions
- Critically evaluate claims, evidence, and conclusions
- Consider reproducibility, generalizability, and practical applications

**When Responding:**
- **Methodological Analysis**: Evaluate experimental design, data collection, statistical approaches, and validity
- **Research Contributions**: Identify novel contributions, theoretical advances, and practical implications
- **Critical Assessment**: Point out strengths, limitations, potential biases, and areas needing clarification
- **Future Directions**: Suggest specific research questions, experiments, or investigations that could extend this work
- **Contextual Insights**: Connect findings to related work, broader theoretical frameworks, and real-world applications
- **Research Questions**: Pose thought-provoking questions that could guide further investigation

**Research-Oriented Language:**
Use precise academic terminology and frame discussions in terms of:
- Research hypotheses and theoretical frameworks
- Experimental validity and reliability
- Statistical significance and effect sizes
- Generalizability and external validity
- Theoretical implications and practical applications
- Areas warranting further investigation

Always think like a researcher who is genuinely curious about advancing knowledge and understanding the deeper implications of the work."""

            # Prepare conversation context
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add paper context with research-focused framing
            paper_context = f"""
**RESEARCH PAPER FOR ANALYSIS:**

**Bibliographic Information:**
- Title: {paper_metadata.get('title', 'Uploaded PDF')}
- Authors: {', '.join(paper_metadata.get('authors', [])) if paper_metadata.get('authors') else 'Not specified'}

**Content for Research Analysis:**
{pdf_content[:8000]}  # Limit content to stay within token limits

**Research Analysis Instructions:**
As you analyze this paper, consider:
1. What research questions does this work address?
2. What methodological approaches are employed?
3. What are the key contributions and limitations?
4. How does this fit into the existing research landscape?
5. What future research directions does this suggest?
6. What aspects warrant deeper investigation or validation?
"""
            
            messages.append({
                "role": "system", 
                "content": f"Here is the research paper you'll be analyzing from a researcher's perspective:\n\n{paper_context}"
            })
            
            # Add conversation history (last 16 messages = last 8 turns)
            for msg in conversation_history[-HISTORY_TURNS*2:]:
                # Determine if it's an AI response based on metadata
                is_ai_response = msg.get("metadata", {}).get("ai_response", False)
                role = "assistant" if is_ai_response else "user"
                messages.append({
                    "role": role,
                    "content": msg.get("message", "")
                })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response optimized for research analysis
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000,  # Increased for comprehensive research analysis
                temperature=0.6,  # Slightly lower for more focused, analytical responses
                presence_penalty=0.2,  # Encourage exploration of diverse research aspects
                frequency_penalty=0.05  # Reduced to allow important terms to be repeated
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
            raise ServiceError(
                "Failed to generate response",
                ErrorCodes.PROCESSING_ERROR
            )
    
    async def _get_conversation_history(self, conversation_id: str) -> list:
        """Get conversation history from MongoDB"""
        try:
            if self.mongo_db is None:
                await self.initialize()
            
            messages = await self.mongo_db.messages.find(
                {"conversation_id": conversation_id}
            ).sort("timestamp", 1).to_list(length=50)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []  # Return empty list on error, don't fail the whole request
    
    async def _save_chat_messages(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        ai_response: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Save chat messages to MongoDB"""
        try:
            if self.mongo_db is None:
                await self.initialize()
            
            timestamp = datetime.utcnow()
            
            # Save user message
            user_msg = {
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4()),  # Add message_id for schema compatibility
                "sender_id": user_id,
                "message": user_message,
                "message_type": "text",
                "timestamp": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
                "metadata": metadata
            }
            
            # Save AI response (use system user ID for AI messages)
            ai_msg = {
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4()),  # Add message_id for schema compatibility
                "sender_id": user_id,  # Associate AI response with conversation owner
                "message": ai_response,
                "message_type": "text",
                "timestamp": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
                "metadata": {**metadata, "ai_response": True}
            }
            
            # Insert both messages
            await self.mongo_db.messages.insert_many([user_msg, ai_msg])
            
            logger.info(f"Saved chat messages for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save chat messages: {e}")
            # Don't raise error for message saving failure 

    async def _ensure_drop_context(
        self,
        conversation_id: str,
        user_id: str,
        project_id: str,
        file_id: str,
        file_name: str,
        pdf_content: str
    ) -> None:
        """Ensure a system message exists storing the PDF text for future turns."""
        try:
            if self.mongo_db is None:
                await self.initialize()
            existing = await self.mongo_db.messages.find_one({
                "conversation_id": conversation_id,
                "message_type": "system",
                "metadata.drop_pdf_context": True
            })
            if existing:
                return
            timestamp = datetime.utcnow()
            context_msg = {
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4()),
                "sender_id": user_id,
                "message": pdf_content,
                "message_type": "system",
                "timestamp": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
                "metadata": {
                    "drop_pdf_context": True,
                    "file_id": file_id,
                    "file_name": file_name,
                    "project_id": project_id
                }
            }
            await self.mongo_db.messages.insert_one(context_msg)
            logger.info(f"Stored drop PDF context for conversation {conversation_id}")
        except Exception as e:
            logger.warning(f"Failed to store drop PDF context: {e}")

    async def _get_drop_context(self, conversation_id: str) -> tuple[str | None, Dict[str, Any]]:
        """Fetch stored PDF text and metadata from the system context message."""
        try:
            if self.mongo_db is None:
                await self.initialize()
            doc = await self.mongo_db.messages.find_one({
                "conversation_id": conversation_id,
                "message_type": "system",
                "metadata.drop_pdf_context": True
            })
            if not doc:
                return None, {}
            return doc.get("message", None), (doc.get("metadata", {}) or {})
        except Exception as e:
            logger.warning(f"Failed to retrieve drop PDF context: {e}")
            return None, {} 