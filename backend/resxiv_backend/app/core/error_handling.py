"""
Production-Grade Error Handling System
L6 Engineering Standards - Centralized Error Management

Eliminates 50+ DRY violations across the codebase.
"""

import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable, Type, Union
from enum import Enum
from fastapi import HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorCodes(str, Enum):
    """Standardized error codes for consistent API responses"""
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found"
    NOT_FOUND = "not_found"  # Compatibility
    CONFLICT = "conflict"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_ERROR = "rate_limit_exceeded"  # Compatibility
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"
    # Paper service error codes
    STORAGE_ERROR = "storage_error"
    PROCESSING_ERROR = "processing_error"
    SEARCH_ERROR = "search_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    INITIALIZATION_ERROR = "initialization_error"
    CREATION_ERROR = "creation_error"
    UPDATE_ERROR = "update_error"
    DELETION_ERROR = "deletion_error"
    # Agentic system error codes
    AGENTIC_PROCESSING_ERROR = "agentic_processing_error"


class ServiceError(Exception):
    """Custom service error with structured information"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCodes = ErrorCodes.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)


def handle_service_errors(
    operation_name: str,
    success_status: int = 200,
    error_mappings: Optional[Dict[Type[Exception], tuple]] = None
):
    """
    Centralized error handling decorator that eliminates DRY violations.
    
    Args:
        operation_name: Human-readable operation name for logging
        success_status: HTTP status code for successful operations
        error_mappings: Custom exception to HTTP status mappings
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                
                # Handle service result pattern
                if isinstance(result, dict) and "success" in result:
                    if not result["success"]:
                        error_msg = result.get("error", f"{operation_name} failed")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "error": ErrorCodes.VALIDATION_ERROR,
                                "message": error_msg,
                                "operation": operation_name
                            }
                        )
                
                return result
                
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
                
            except ServiceError as e:
                logger.error(f"{operation_name} service error: {e.message}")
                raise HTTPException(
                    status_code=e.status_code,
                    detail={
                        "error": e.error_code,
                        "message": e.message,
                        "operation": operation_name,
                        "details": e.details
                    }
                )
                
            except ValueError as e:
                logger.warning(f"{operation_name} validation error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": ErrorCodes.VALIDATION_ERROR,
                        "message": str(e),
                        "operation": operation_name
                    }
                )
                
            except PermissionError as e:
                logger.warning(f"{operation_name} permission error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": ErrorCodes.AUTHORIZATION_ERROR,
                        "message": "Insufficient permissions",
                        "operation": operation_name
                    }
                )
                
            except FileNotFoundError as e:
                logger.warning(f"{operation_name} not found: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": ErrorCodes.NOT_FOUND,
                        "message": "Resource not found",
                        "operation": operation_name
                    }
                )
                
            except Exception as e:
                logger.error(f"{operation_name} unexpected error: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": ErrorCodes.INTERNAL_ERROR,
                        "message": f"{operation_name} failed",
                        "operation": operation_name
                    }
                )
        
        return wrapper
    return decorator


def handle_async_service_call(
    service_method: Callable,
    operation_name: str,
    *args,
    **kwargs
) -> Any:
    """
    Utility function for consistent service call error handling.
    """
    async def _call():
        try:
            result = await service_method(*args, **kwargs)
            
            if isinstance(result, dict) and "success" in result:
                if not result["success"]:
                    raise ServiceError(
                        message=result.get("error", f"{operation_name} failed"),
                        error_code=ErrorCodes.VALIDATION_ERROR,
                        status_code=400
                    )
            
            return result
            
        except Exception as e:
            if isinstance(e, ServiceError):
                raise
            
            logger.error(f"Service call failed for {operation_name}: {str(e)}")
            raise ServiceError(
                message=f"{operation_name} failed",
                error_code=ErrorCodes.INTERNAL_ERROR,
                details={"original_error": str(e)}
            )
    
    return _call()


class ErrorResponseModel(BaseModel):
    """Standardized error response model"""
    error: ErrorCodes
    message: str
    operation: str
    details: Optional[Dict[str, Any]] = None


def create_error_response(
    error_code: ErrorCodes,
    message: str,
    operation: str,
    details: Optional[Dict[str, Any]] = None
) -> ErrorResponseModel:
    """Factory function for creating standardized error responses"""
    return ErrorResponseModel(
        error=error_code,
        message=message,
        operation=operation,
        details=details
    ) 