"""
Agentic System Models - L6 Engineering Standards

Pydantic models for agentic system request/response handling.
Provides comprehensive validation and type safety.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from fastapi import UploadFile
import uuid


class AgenticRequest(BaseModel):
    """
    Production-grade request model for agentic processing.
    
    Includes comprehensive validation and sanitization.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User message to process through the agentic system"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID for context continuity"
    )
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context data for processing"
    )
    preferences: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="User preferences for agent selection and behavior"
    )
    
    @validator('message')
    def validate_message(cls, v):
        """Validate and sanitize message content"""
        if not v.strip():
            raise ValueError('Message cannot be empty or whitespace only')
        
        # Basic sanitization
        sanitized = v.strip()
        
        # Check for potential security issues
        if len(sanitized.split()) > 1000:  # Reasonable word limit
            raise ValueError('Message too long - exceeds 1000 words')
            
        return sanitized
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        """Validate conversation ID format"""
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Conversation ID cannot be empty string')
        
        if v is not None:
            # Validate UUID format if provided
            try:
                uuid.UUID(v)
            except ValueError:
                # Allow string IDs for backward compatibility
                if not v.isalnum() and not all(c in v for c in '-_'):
                    raise ValueError('Invalid conversation ID format')
        
        return v
    
    @validator('context')
    def validate_context(cls, v):
        """Validate context data"""
        if v is None:
            return {}
        
        # Limit context size to prevent abuse
        if len(str(v)) > 10000:  # 10KB limit
            raise ValueError('Context data too large')
        
        return v

    class Config:
        schema_extra = {
            "example": {
                "message": "Can you help me search for papers about machine learning?",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "context": {"user_intent": "research"},
                "preferences": {"response_style": "detailed"}
            }
        }


class PaperChatRequest(BaseModel):
    """Request model for paper chat functionality"""
    paper_id: str = Field(..., description="UUID of the paper to chat with")
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User message about the paper"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID to continue existing chat"
    )
    
    @validator('paper_id')
    def validate_paper_id(cls, v):
        """Validate paper UUID format"""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Invalid paper ID format - must be UUID')
        return v
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message content"""
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "paper_id": "1cc36034-44e7-4263-83a6-1429ddaf942d",
                "message": "What are the main contributions of this paper?",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class DropChatRequest(BaseModel):
    """Request model for drop chat functionality"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User message about the dropped file"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID to continue existing chat"
    )
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message content"""
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "message": "Can you summarize this paper for me?",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class PaperChatResponse(BaseModel):
    """Response model for paper chat"""
    success: bool = Field(..., description="Operation success status")
    response: str = Field(..., description="AI response about the paper")
    conversation_id: str = Field(..., description="Conversation ID for continuity")
    paper_id: str = Field(..., description="Paper ID that was discussed")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "response": "This paper introduces a lightweight feature fusion architecture for crowd counting...",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "paper_id": "1cc36034-44e7-4263-83a6-1429ddaf942d",
                "processing_time": 2.34,
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {
                    "paper_title": "A Lightweight Feature Fusion Architecture",
                    "conversation_type": "PDF"
                }
            }
        }


class DropChatResponse(BaseModel):
    """Response model for drop chat"""
    success: bool = Field(..., description="Operation success status")
    response: str = Field(..., description="AI response about the dropped file")
    conversation_id: str = Field(..., description="Conversation ID for continuity")
    file_id: str = Field(..., description="Temporary file ID for the uploaded PDF")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "response": "Based on the uploaded PDF, this appears to be a research paper about...",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "file_id": "temp_file_123",
                "processing_time": 3.45,
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {
                    "file_name": "research_paper.pdf",
                    "conversation_type": "DROP"
                }
            }
        }


class SimpleChatRequest(BaseModel):
    """Request model for simple AI chat functionality"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User message for AI conversation"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID to continue existing chat"
    )
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message content"""
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "message": "Hello, can you help me with my research?",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class SimpleChatResponse(BaseModel):
    """Response model for simple AI chat"""
    success: bool = Field(..., description="Operation success status")
    response: str = Field(..., description="AI response message")
    conversation_id: str = Field(..., description="Conversation ID for continuity")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "response": "Hello! I'd be happy to help you with your research. What specific area are you working on?",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "processing_time": 1.23,
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {
                    "conversation_type": "AI"
                }
            }
        }


class AgenticResponse(BaseModel):
    """
    Structured response model for agentic operations.
    
    Provides consistent response format with comprehensive metadata.
    """
    success: bool = Field(..., description="Operation success status")
    response: str = Field(..., description="Agent response message")
    agent: Optional[str] = Field(None, description="Agent that handled the request")
    intent: Optional[str] = Field(None, description="Detected user intent")
    tool_calls: int = Field(0, description="Number of tool calls executed")
    conversation_id: str = Field(..., description="Conversation ID for continuity")
    processing_time: float = Field(..., description="Total processing time in seconds")
    timestamp: str = Field(..., description="Response timestamp (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator('processing_time')
    def validate_processing_time(cls, v):
        """Ensure processing time is reasonable"""
        if v < 0:
            raise ValueError('Processing time cannot be negative')
        if v > 300:  # 5 minutes max
            raise ValueError('Processing time too high - indicates system issues')
        return v

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('Invalid timestamp format - must be ISO format')
        return v

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "response": "I found 15 relevant papers about machine learning. Here are the top 3...",
                "agent": "research_agent",
                "intent": "paper_search",
                "tool_calls": 2,
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "processing_time": 2.34,
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {
                    "project_id": "proj_123",
                    "papers_found": 15,
                    "search_terms": ["machine learning", "AI"]
                }
            }
        }


class ConversationHistoryResponse(BaseModel):
    """
    Response model for conversation history retrieval.
    
    Includes pagination support and metadata.
    """
    success: bool = Field(..., description="Operation success status")
    conversation_id: str = Field(..., description="Conversation identifier")
    messages: List[Dict[str, Any]] = Field(..., description="List of conversation messages")
    total_messages: int = Field(..., description="Total number of messages in conversation")
    project_id: Optional[str] = Field(None, description="Associated project ID")
    has_more: bool = Field(False, description="Whether more messages are available")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")

    @validator('total_messages')
    def validate_total_messages(cls, v):
        """Ensure total messages count is reasonable"""
        if v < 0:
            raise ValueError('Total messages cannot be negative')
        return v

    @validator('messages')
    def validate_messages(cls, v):
        """Validate message structure"""
        for msg in v:
            if not isinstance(msg, dict):
                raise ValueError('Each message must be a dictionary')
            
            # Ensure required fields exist
            required_fields = ['message_id', 'content', 'timestamp', 'sender_type']
            for field in required_fields:
                if field not in msg:
                    raise ValueError(f'Message missing required field: {field}')
        
        return v

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "messages": [
                    {
                        "message_id": "msg_001",
                        "content": "Hello, can you help me with research?",
                        "timestamp": "2024-01-15T10:00:00Z",
                        "sender_type": "user",
                        "sender_id": "user_123"
                    },
                    {
                        "message_id": "msg_002", 
                        "content": "Of course! I can help you search for papers...",
                        "timestamp": "2024-01-15T10:00:05Z",
                        "sender_type": "agent",
                        "agent_name": "research_agent"
                    }
                ],
                "total_messages": 2,
                "project_id": "proj_123",
                "has_more": False
            }
        }


class AgenticCapabilitiesResponse(BaseModel):
    """
    Response model for agentic system capabilities.
    
    Returns available agents, tools, and features.
    """
    success: bool = Field(..., description="Operation success status")
    capabilities: Dict[str, Any] = Field(..., description="System capabilities")
    project_id: Optional[str] = Field(None, description="Project context")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "capabilities": {
                    "agents": [
                        {
                            "name": "research_agent",
                            "description": "Research papers and academic content",
                            "capabilities": ["paper_search", "citation_analysis"]
                        }
                    ],
                    "tools": ["paper_search", "add_paper", "create_task"],
                    "project_context": {
                        "project_id": "proj_123",
                        "user_role": "member",
                        "permissions": {
                            "can_read": True,
                            "can_write": True,
                            "can_admin": False
                        }
                    }
                },
                "project_id": "proj_123"
            }
        }


class AgenticErrorResponse(BaseModel):
    """
    Standardized error response model.
    
    Provides consistent error information for debugging.
    """
    success: bool = Field(False, description="Always false for error responses")
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error_code": "AGENTIC_PROCESSING_ERROR",
                "error_message": "Failed to process agentic request",
                "details": {
                    "agent": "research_agent",
                    "step": "tool_execution",
                    "tool": "paper_search"
                },
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "req_abc123"
            }
        } 


class LaTeXEditorRequest(BaseModel):
    """Request model for LaTeX editor functionality"""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="Research editing instructions for the LaTeX content"
    )
    latex_content: Optional[str] = Field(
        None,
        max_length=100000,
        description="Existing LaTeX content to edit (optional if image provided)"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID to continue existing editing session"
    )
    edit_type: str = Field(
        default="general",
        description="Type of edit: general, formatting, content, structure, citations"
    )
    
    @validator('prompt')
    def validate_prompt(cls, v):
        """Validate prompt content"""
        if not v.strip():
            raise ValueError('Prompt cannot be empty')
        return v.strip()
    
    @validator('edit_type')
    def validate_edit_type(cls, v):
        """Validate edit type"""
        allowed_types = ["general", "formatting", "content", "structure", "citations", "grammar"]
        if v not in allowed_types:
            raise ValueError(f'Edit type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('latex_content')
    def validate_latex_content(cls, v):
        """Validate LaTeX content"""
        if v is not None and not v.strip():
            return None  # Convert empty string to None
        return v

    class Config:
        schema_extra = {
            "example": {
                "prompt": "Improve the academic writing style and fix any grammatical errors in this introduction section",
                "latex_content": "\\section{Introduction}\nThis paper presents a new method for...",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "edit_type": "content"
            }
        }


class LaTeXEditorResponse(BaseModel):
    """Response model for LaTeX editor"""
    success: bool = Field(..., description="Operation success status")
    edited_content: str = Field(..., description="AI-edited LaTeX content")
    changes_made: List[str] = Field(..., description="List of specific changes made")
    suggestions: List[str] = Field(default_factory=list, description="Additional improvement suggestions")
    conversation_id: str = Field(..., description="Conversation ID for continuity")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "edited_content": "\\section{Introduction}\n\\label{sec:introduction}\nThis paper presents a novel method for...",
                "changes_made": [
                    "Added section label for better referencing",
                    "Improved academic tone by changing 'new' to 'novel'",
                    "Fixed grammar and punctuation"
                ],
                "suggestions": [
                    "Consider adding a brief overview of the paper structure",
                    "Add citation to related work for context"
                ],
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "processing_time": 3.24,
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {
                    "edit_type": "content",
                    "original_length": 156,
                    "edited_length": 178,
                    "model_used": "gpt-4o-mini"
                }
            }
        } 