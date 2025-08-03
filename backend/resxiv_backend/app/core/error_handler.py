"""
Production-Grade Centralized Error Handler
L6 Engineering Standards Implementation

Security Features:
- No sensitive data in client responses
- Detailed logging for internal debugging
- Correlation ID tracking for issue resolution
- Standardized error formats
"""

import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import traceback

logger = logging.getLogger(__name__)

class ProductionErrorHandler:
    """Centralized error handling with security considerations"""
    
    @staticmethod
    def create_correlation_id() -> str:
        """Generate unique correlation ID for error tracking"""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_correlation_id(request: Request) -> str:
        """Get or create correlation ID from request"""
        return getattr(request.state, 'correlation_id', ProductionErrorHandler.create_correlation_id())
    
    @staticmethod
    def log_error(
        error: Exception,
        correlation_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log error with full context for internal debugging"""
        error_context = {
            "correlation_id": correlation_id,
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            **(context or {})
        }
        
        logger.error(f"Internal error occurred", extra=error_context, exc_info=True)
    
    @staticmethod
    def create_client_response(
        error_code: str,
        message: str,
        correlation_id: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """Create secure client-facing error response"""
        response_data = {
            "error": error_code,
            "message": message,
            "correlation_id": correlation_id
        }
        
        if details:
            response_data["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    @staticmethod
    def handle_internal_error(request: Request, exception: Exception) -> JSONResponse:
        """Handle internal server errors with security considerations"""
        correlation_id = ProductionErrorHandler.get_correlation_id(request)
        
        # Log full details internally
        ProductionErrorHandler.log_error(
            exception,
            correlation_id,
            {
                "request_method": request.method,
                "request_path": str(request.url.path),
                "request_params": dict(request.query_params),
                "client_host": request.client.host if request.client else "unknown"
            }
        )
        
        # Return minimal info to client for security
        return ProductionErrorHandler.create_client_response(
            error_code="internal_server_error",
            message="An unexpected error occurred",
            correlation_id=correlation_id,
            status_code=500
        )
    
    @staticmethod
    def handle_database_error(request: Request, exception: SQLAlchemyError) -> JSONResponse:
        """Handle database errors securely"""
        correlation_id = ProductionErrorHandler.get_correlation_id(request)
        
        # Log database error details internally
        ProductionErrorHandler.log_error(
            exception,
            correlation_id,
            {"error_category": "database_error"}
        )
        
        # Generic response to client (no database details)
        return ProductionErrorHandler.create_client_response(
            error_code="service_unavailable",
            message="Service temporarily unavailable",
            correlation_id=correlation_id,
            status_code=503
        )
    
    @staticmethod
    def handle_validation_error(
        request: Request,
        exception: Exception,
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """Handle validation errors"""
        correlation_id = ProductionErrorHandler.get_correlation_id(request)
        
        # Log validation error
        ProductionErrorHandler.log_error(
            exception,
            correlation_id,
            {"error_category": "validation_error", "validation_details": details}
        )
        
        return ProductionErrorHandler.create_client_response(
            error_code="validation_failed",
            message="Request validation failed",
            correlation_id=correlation_id,
            status_code=422,
            details=details
        )
    
    @staticmethod
    def handle_not_found_error(request: Request, resource_type: str) -> JSONResponse:
        """Handle resource not found errors"""
        correlation_id = ProductionErrorHandler.get_correlation_id(request)
        
        return ProductionErrorHandler.create_client_response(
            error_code="resource_not_found",
            message=f"{resource_type} not found",
            correlation_id=correlation_id,
            status_code=404
        )
    
    @staticmethod
    def handle_permission_error(request: Request, action: str) -> JSONResponse:
        """Handle permission/authorization errors"""
        correlation_id = ProductionErrorHandler.get_correlation_id(request)
        
        # Log access attempt
        logger.warning(
            f"Permission denied for action: {action}",
            extra={
                "correlation_id": correlation_id,
                "request_path": str(request.url.path),
                "client_host": request.client.host if request.client else "unknown"
            }
        )
        
        return ProductionErrorHandler.create_client_response(
            error_code="access_denied",
            message="Insufficient permissions",
            correlation_id=correlation_id,
            status_code=403
        )

class ErrorCategories:
    """Standard error categories for consistent handling"""
    
    VALIDATION = "validation_error"
    NOT_FOUND = "resource_not_found"
    PERMISSION = "access_denied"
    DATABASE = "database_error"
    INTERNAL = "internal_server_error"
    RATE_LIMIT = "rate_limit_exceeded"
    SERVICE_UNAVAILABLE = "service_unavailable" 