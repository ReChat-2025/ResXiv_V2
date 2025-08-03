"""
Centralized Error Handler - L6 Engineering Standards
Eliminates DRY violations by providing unified error handling patterns.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable, Type, Union
from functools import wraps
from datetime import datetime

from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.core.error_handling import ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


class EndpointErrorHandler:
    """
    Centralized error handler for API endpoints.
    Single source of truth for error response formatting.
    """
    
    @staticmethod
    def create_error_response(
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """
        Create standardized error response.
        
        Args:
            error_code: Error identifier
            message: Human-readable error message
            status_code: HTTP status code
            details: Additional error details
            request: FastAPI request object
            
        Returns:
            Standardized JSON error response
        """
        response_data = {
            "error": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code
        }
        
        if details:
            response_data["details"] = details
            
        if request:
            response_data["path"] = request.url.path
            response_data["correlation_id"] = getattr(
                request.state, 'correlation_id', None
            )
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    @staticmethod
    def handle_service_error(
        error: ServiceError,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """Handle ServiceError exceptions."""
        return EndpointErrorHandler.create_error_response(
            error_code=error.error_code.value,
            message=error.message,
            status_code=error.status_code,
            request=request
        )
    
    @staticmethod
    def handle_validation_error(
        error: ValidationError,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        return EndpointErrorHandler.create_error_response(
            error_code="validation_error",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": error.errors()},
            request=request
        )
    
    @staticmethod
    def handle_database_error(
        error: SQLAlchemyError,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """Handle database errors."""
        logger.error(f"Database error: {error}")
        return EndpointErrorHandler.create_error_response(
            error_code="database_error",
            message="Database operation failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request=request
        )
    
    @staticmethod
    def handle_generic_error(
        error: Exception,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """Handle unexpected errors."""
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return EndpointErrorHandler.create_error_response(
            error_code="internal_error",
            message="An unexpected error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request=request
        )


def handle_endpoint_errors(
    operation_name: str,
    success_status: int = 200,
    log_success: bool = True
):
    """
    Decorator for unified endpoint error handling.
    
    Eliminates repeated try/catch patterns across endpoints.
    
    Args:
        operation_name: Description of the operation for logging
        success_status: HTTP status for successful operations
        log_success: Whether to log successful operations
        
    Usage:
        @handle_endpoint_errors("create project", success_status=201)
        async def create_project_endpoint(...):
            # endpoint logic
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                    break
            
            try:
                if log_success:
                    logger.info(f"Starting {operation_name}")
                
                result = await func(*args, **kwargs)
                
                if log_success:
                    logger.info(f"Completed {operation_name} successfully")
                
                # Handle service result pattern
                if isinstance(result, dict) and "success" in result:
                    if not result["success"]:
                        return EndpointErrorHandler.create_error_response(
                            error_code="operation_failed",
                            message=result.get("error", f"{operation_name} failed"),
                            status_code=400,
                            request=request
                        )
                
                return result
                
            except ServiceError as e:
                logger.warning(f"Service error in {operation_name}: {e.message}")
                return EndpointErrorHandler.handle_service_error(e, request)
                
            except ValidationError as e:
                logger.warning(f"Validation error in {operation_name}: {e}")
                return EndpointErrorHandler.handle_validation_error(e, request)
                
            except SQLAlchemyError as e:
                logger.error(f"Database error in {operation_name}: {e}")
                return EndpointErrorHandler.handle_database_error(e, request)
                
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name}: {e}")
                return EndpointErrorHandler.handle_generic_error(e, request)
        
        return wrapper
    return decorator


def require_project_access(
    access_type: str = "read",
    error_message: Optional[str] = None
):
    """
    Decorator for project access validation.
    
    Eliminates repeated access control checks.
    
    Args:
        access_type: Required access level (read/write/admin/owner)
        error_message: Custom error message
        
    Usage:
        @require_project_access("write")
        async def upload_file_endpoint(...):
            # endpoint logic with guaranteed write access
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get project_access from kwargs (injected by dependency)
            project_access = kwargs.get('project_access', {})
            
            access_key = f"can_{access_type}"
            has_access = project_access.get(access_key, False)
            
            if not has_access:
                message = error_message or f"Insufficient permissions: {access_type} access required"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=message
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_service_result(operation_name: str):
    """
    Decorator for service result validation.
    
    Handles common service response patterns.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if isinstance(result, dict) and "success" in result:
                if not result["success"]:
                    error_message = result.get("error", f"{operation_name} failed")
                    error_code = result.get("error_code", "OPERATION_FAILED")
                    
                    # Map error codes to HTTP status codes
                    status_mapping = {
                        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
                        "ACCESS_DENIED": status.HTTP_403_FORBIDDEN,
                        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
                        "DUPLICATE_RESOURCE": status.HTTP_409_CONFLICT,
                    }
                    
                    http_status = status_mapping.get(
                        error_code, 
                        status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                    
                    raise HTTPException(
                        status_code=http_status,
                        detail=error_message
                    )
            
            return result
        
        return wrapper
    return decorator 