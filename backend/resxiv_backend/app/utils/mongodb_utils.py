"""
MongoDB Utilities - L6 Engineering Standards
Provides robust ObjectId validation and conversion utilities.
"""

import logging
from typing import Optional
from bson import ObjectId, errors as bson_errors
from app.core.error_handling import ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


def validate_object_id(object_id_str: str, field_name: str = "ID") -> ObjectId:
    """
    Validate and convert string to MongoDB ObjectId.
    
    Args:
        object_id_str: String representation of ObjectId
        field_name: Name of the field for error messages
        
    Returns:
        Valid ObjectId instance
        
    Raises:
        ServiceError: If the string is not a valid ObjectId
    """
    if not object_id_str:
        raise ServiceError(
            f"{field_name} cannot be empty",
            ErrorCodes.VALIDATION_ERROR,
            400
        )
    
    if not isinstance(object_id_str, str):
        raise ServiceError(
            f"{field_name} must be a string",
            ErrorCodes.VALIDATION_ERROR,
            400
        )
    
    try:
        return ObjectId(object_id_str)
    except (bson_errors.InvalidId, ValueError, TypeError) as e:
        logger.warning(f"Invalid {field_name} format: {object_id_str} - {str(e)}")
        raise ServiceError(
            f"Invalid {field_name} format. Must be a valid MongoDB ObjectId (24-character hex string).",
            ErrorCodes.VALIDATION_ERROR,
            400
        )


def safe_object_id_conversion(object_id_str: Optional[str]) -> Optional[ObjectId]:
    """
    Safely convert string to ObjectId without raising exceptions.
    
    Args:
        object_id_str: String representation of ObjectId
        
    Returns:
        ObjectId instance or None if invalid
    """
    if not object_id_str:
        return None
    
    try:
        return ObjectId(object_id_str)
    except (bson_errors.InvalidId, ValueError, TypeError):
        return None


def is_valid_object_id(object_id_str: str) -> bool:
    """
    Check if string is a valid ObjectId format.
    
    Args:
        object_id_str: String to validate
        
    Returns:
        True if valid ObjectId format, False otherwise
    """
    try:
        ObjectId(object_id_str)
        return True
    except (bson_errors.InvalidId, ValueError, TypeError):
        return False 