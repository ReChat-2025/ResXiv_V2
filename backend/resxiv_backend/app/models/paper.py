"""
Paper Pydantic Models

All Pydantic models related to paper management, validation,
and API request/response handling.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid
from enum import Enum


class PaperStatus(str, Enum):
    """Paper processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiagnosticStatus(str, Enum):
    """Diagnostic processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Base Paper Models

class AuthorInfo(BaseModel):
    """Author information model"""
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    email: Optional[str] = Field(None, description="Email address")
    affiliation: Optional[str] = Field(None, description="Institution affiliation")


class PaperUpload(BaseModel):
    """Paper upload request model"""
    project_id: uuid.UUID = Field(..., description="Project ID to add paper to")
    title: Optional[str] = Field(None, description="Paper title (will be extracted if not provided)")
    process_with_grobid: bool = Field(True, description="Whether to process with GROBID")
    run_diagnostics: bool = Field(True, description="Whether to run LLM diagnostics")
    private_uploaded: bool = Field(False, description="Whether paper is privately uploaded")
    
    @validator("title")
    def validate_title(cls, v):
        if v and len(v) > 500:
            raise ValueError("Title must be less than 500 characters")
        return v


class PaperUpdate(BaseModel):
    """Paper update request model"""
    title: Optional[str] = Field(None, description="Updated paper title")
    authors: Optional[List[str]] = Field(None, description="Updated authors list")
    keywords: Optional[List[str]] = Field(None, description="Updated keywords")
    abstract: Optional[str] = Field(None, description="Updated abstract")
    doi: Optional[str] = Field(None, description="DOI")
    
    @validator("title")
    def validate_title(cls, v):
        if v and len(v) > 500:
            raise ValueError("Title must be less than 500 characters")
        return v
    
    @validator("keywords")
    def validate_keywords(cls, v):
        if v and len(v) > 20:
            raise ValueError("Maximum 20 keywords allowed")
        return v
    
    @validator("abstract")
    def validate_abstract(cls, v):
        if v and len(v) > 5000:
            raise ValueError("Abstract must be less than 5000 characters")
        return v


class PaperCreate(BaseModel):
    """Paper creation model (internal use)"""
    title: str = Field(..., description="Paper title")
    pdf_path: Optional[str] = Field(None, description="PDF file path")
    bib_path: Optional[str] = Field(None, description="BIB file path") 
    xml_path: Optional[str] = Field(None, description="XML file path")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type")
    checksum: Optional[str] = Field(None, description="File checksum")
    private_uploaded: bool = Field(False, description="Private upload flag")
    authors: List[str] = Field(default=[], description="Authors list")
    keywords: List[str] = Field(default=[], description="Keywords list")
    arxiv_id: Optional[str] = Field(None, description="ArXiv ID")
    doi: Optional[str] = Field(None, description="DOI")
    abstract: Optional[str] = Field(None, description="Abstract")
    safe_title: Optional[str] = Field(None, description="Safe title for file storage")


# Diagnostic Models

class DiagnosticCreate(BaseModel):
    """Diagnostic creation model"""
    paper_id: uuid.UUID = Field(..., description="Paper ID")
    abstract: Optional[str] = Field(None, description="Extracted abstract")
    summary: Optional[str] = Field(None, description="Paper summary")
    method: Optional[str] = Field(None, description="Methodology")
    dataset: Optional[str] = Field(None, description="Dataset information")
    highlights: Optional[str] = Field(None, description="Key highlights")
    weakness: Optional[str] = Field(None, description="Weaknesses")
    future_scope: Optional[str] = Field(None, description="Future scope")
    strengths: Optional[str] = Field(None, description="Strengths")
    contributions: Optional[str] = Field(None, description="Main contributions")
    limitations: Optional[str] = Field(None, description="Limitations")


class DiagnosticUpdate(BaseModel):
    """Diagnostic update model"""
    abstract: Optional[str] = Field(None, description="Updated abstract")
    summary: Optional[str] = Field(None, description="Updated summary")
    method: Optional[str] = Field(None, description="Updated methodology")
    dataset: Optional[str] = Field(None, description="Updated dataset information")
    highlights: Optional[str] = Field(None, description="Updated highlights")
    weakness: Optional[str] = Field(None, description="Updated weaknesses")
    future_scope: Optional[str] = Field(None, description="Updated future scope")
    strengths: Optional[str] = Field(None, description="Updated strengths")
    contributions: Optional[str] = Field(None, description="Updated contributions")
    limitations: Optional[str] = Field(None, description="Updated limitations")


# Response Models

class DiagnosticResponse(BaseModel):
    """Diagnostic response model"""
    id: uuid.UUID
    paper_id: uuid.UUID
    abstract: Optional[str]
    summary: Optional[str]
    method: Optional[str]
    dataset: Optional[str]
    highlights: Optional[str]
    weakness: Optional[str]
    future_scope: Optional[str]
    strengths: Optional[str]
    contributions: Optional[str]
    limitations: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaperResponse(BaseModel):
    """Paper response model"""
    id: uuid.UUID
    title: str
    date_added: datetime
    last_modified: datetime
    pdf_path: Optional[str]
    bib_path: Optional[str]
    xml_path: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    checksum: Optional[str]
    private_uploaded: bool
    authors: List[str]
    keywords: List[str]
    arxiv_id: Optional[str]
    doi: Optional[str]
    abstract: Optional[str]
    safe_title: Optional[str]
    created_at: datetime
    updated_at: datetime
    diagnostics: Optional[DiagnosticResponse]
    
    class Config:
        from_attributes = True


class PaperListResponse(BaseModel):
    """Paper list response model"""
    papers: List[PaperResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class PaperUploadResponse(BaseModel):
    """Paper upload response model"""
    success: bool
    message: str
    paper: Optional[PaperResponse]
    processing_status: PaperStatus
    diagnostic_status: Optional[DiagnosticStatus]


# ArXiv Models

class ArXivSearchRequest(BaseModel):
    """ArXiv search request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")
    sort_by: str = Field(default="relevance", description="Sort criteria")
    sort_order: str = Field(default="descending", description="Sort order")
    categories: Optional[List[str]] = Field(None, description="ArXiv categories to filter")
    
    @validator("sort_by")
    def validate_sort_by(cls, v):
        valid_sorts = ["relevance", "lastUpdatedDate", "submittedDate"]
        if v not in valid_sorts:
            raise ValueError(f"sort_by must be one of {valid_sorts}")
        return v
    
    @validator("sort_order")
    def validate_sort_order(cls, v):
        valid_orders = ["ascending", "descending"]
        if v not in valid_orders:
            raise ValueError(f"sort_order must be one of {valid_orders}")
        return v


class ArXivPaper(BaseModel):
    """ArXiv paper model"""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published: datetime
    updated: datetime
    pdf_url: str
    doi: Optional[str]


class ArXivSearchResponse(BaseModel):
    """ArXiv search response model"""
    query: str
    total_results: int
    start_index: int
    items_per_page: int
    papers: List[ArXivPaper]
    timestamp: datetime


class ArXivDownloadRequest(BaseModel):
    """ArXiv download request model"""
    project_id: uuid.UUID = Field(..., description="Project ID to add paper to")
    arxiv_id: str = Field(..., description="ArXiv ID to download")
    process_with_grobid: bool = Field(True, description="Whether to process with GROBID")
    run_diagnostics: bool = Field(True, description="Whether to run LLM diagnostics")


# Processing Models

class ProcessingRequest(BaseModel):
    """Paper processing request model"""
    paper_id: uuid.UUID = Field(..., description="Paper ID to process")
    force_reprocess: bool = Field(False, description="Force reprocessing even if already processed")


class DiagnosticRequest(BaseModel):
    """Diagnostic generation request model"""
    paper_id: uuid.UUID = Field(..., description="Paper ID for diagnostics")
    diagnostic_type: str = Field(default="ai", description="Type of diagnostic to run")
    force_regenerate: bool = Field(False, description="Force regeneration even if diagnostics exist")
    include_sections: List[str] = Field(
        default=["summary", "method", "strengths", "limitations", "contributions"],
        description="Sections to include in diagnostics"
    )


# Bulk Operations

class BulkPaperOperation(BaseModel):
    """Bulk paper operation model"""
    paper_ids: List[uuid.UUID] = Field(..., description="List of paper IDs")
    operation: str = Field(..., description="Operation to perform")
    
    @validator("operation")
    def validate_operation(cls, v):
        valid_operations = ["delete", "process", "diagnostics", "archive"]
        if v not in valid_operations:
            raise ValueError(f"operation must be one of {valid_operations}")
        return v


class BulkOperationResponse(BaseModel):
    """Bulk operation response model"""
    success: bool
    message: str
    total_requested: int
    successful: int
    failed: int
    results: List[Dict[str, Any]] 