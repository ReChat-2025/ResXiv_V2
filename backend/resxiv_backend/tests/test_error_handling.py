"""
Tests for Production Error Handling System
L6 Engineering Standards - Comprehensive Test Coverage
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import (
    handle_service_errors,
    ServiceError,
    ErrorCodes,
    handle_async_service_call,
    create_error_response
)


class TestServiceError:
    """Test cases for ServiceError exception"""
    
    def test_service_error_creation(self):
        error = ServiceError(
            message="Test error",
            error_code=ErrorCodes.VALIDATION_ERROR,
            details={"field": "value"},
            status_code=400
        )
        
        assert error.message == "Test error"
        assert error.error_code == ErrorCodes.VALIDATION_ERROR
        assert error.details == {"field": "value"}
        assert error.status_code == 400
    
    def test_service_error_defaults(self):
        error = ServiceError("Test error")
        
        assert error.error_code == ErrorCodes.INTERNAL_ERROR
        assert error.details == {}
        assert error.status_code == 500


class TestHandleServiceErrors:
    """Test cases for handle_service_errors decorator"""
    
    @pytest.mark.asyncio
    async def test_successful_operation(self):
        @handle_service_errors("test operation")
        async def test_func():
            return {"success": True, "data": "test"}
        
        result = await test_func()
        assert result == {"success": True, "data": "test"}
    
    @pytest.mark.asyncio
    async def test_service_result_failure(self):
        @handle_service_errors("test operation")
        async def test_func():
            return {"success": False, "error": "Operation failed"}
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert exc_info.value.detail["error"] == ErrorCodes.VALIDATION_ERROR
        assert exc_info.value.detail["message"] == "Operation failed"
        assert exc_info.value.detail["operation"] == "test operation"
    
    @pytest.mark.asyncio
    async def test_service_error_handling(self):
        @handle_service_errors("test operation")
        async def test_func():
            raise ServiceError(
                message="Custom error",
                error_code=ErrorCodes.NOT_FOUND,
                status_code=404
            )
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == ErrorCodes.NOT_FOUND
        assert exc_info.value.detail["message"] == "Custom error"
    
    @pytest.mark.asyncio
    async def test_value_error_handling(self):
        @handle_service_errors("test operation")
        async def test_func():
            raise ValueError("Invalid input")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert exc_info.value.detail["error"] == ErrorCodes.VALIDATION_ERROR
        assert exc_info.value.detail["message"] == "Invalid input"
    
    @pytest.mark.asyncio
    async def test_permission_error_handling(self):
        @handle_service_errors("test operation")
        async def test_func():
            raise PermissionError("Access denied")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail["error"] == ErrorCodes.AUTHORIZATION_ERROR
        assert exc_info.value.detail["message"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_file_not_found_error_handling(self):
        @handle_service_errors("test operation")
        async def test_func():
            raise FileNotFoundError("File missing")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail["error"] == ErrorCodes.NOT_FOUND
        assert exc_info.value.detail["message"] == "Resource not found"
    
    @pytest.mark.asyncio
    async def test_generic_exception_handling(self):
        @handle_service_errors("test operation")
        async def test_func():
            raise Exception("Unexpected error")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail["error"] == ErrorCodes.INTERNAL_ERROR
        assert exc_info.value.detail["message"] == "test operation failed"
    
    @pytest.mark.asyncio
    async def test_http_exception_passthrough(self):
        @handle_service_errors("test operation")
        async def test_func():
            raise HTTPException(status_code=418, detail="I'm a teapot")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 418
        assert exc_info.value.detail == "I'm a teapot"


class TestHandleAsyncServiceCall:
    """Test cases for handle_async_service_call utility"""
    
    @pytest.mark.asyncio
    async def test_successful_service_call(self):
        async def mock_service():
            return {"success": True, "data": "test"}
        
        result = await handle_async_service_call(mock_service, "test operation")
        assert result == {"success": True, "data": "test"}
    
    @pytest.mark.asyncio
    async def test_failed_service_call(self):
        async def mock_service():
            return {"success": False, "error": "Service failed"}
        
        with pytest.raises(ServiceError) as exc_info:
            await handle_async_service_call(mock_service, "test operation")
        
        assert exc_info.value.message == "Service failed"
        assert exc_info.value.error_code == ErrorCodes.VALIDATION_ERROR
    
    @pytest.mark.asyncio
    async def test_service_call_exception(self):
        async def mock_service():
            raise Exception("Unexpected error")
        
        with pytest.raises(ServiceError) as exc_info:
            await handle_async_service_call(mock_service, "test operation")
        
        assert exc_info.value.message == "test operation failed"
        assert exc_info.value.error_code == ErrorCodes.INTERNAL_ERROR


class TestCreateErrorResponse:
    """Test cases for create_error_response factory"""
    
    def test_create_basic_error_response(self):
        response = create_error_response(
            error_code=ErrorCodes.VALIDATION_ERROR,
            message="Test error",
            operation="test operation"
        )
        
        assert response.error == ErrorCodes.VALIDATION_ERROR
        assert response.message == "Test error"
        assert response.operation == "test operation"
        assert response.details is None
    
    def test_create_error_response_with_details(self):
        details = {"field": "value", "count": 42}
        response = create_error_response(
            error_code=ErrorCodes.NOT_FOUND,
            message="Resource not found",
            operation="get resource",
            details=details
        )
        
        assert response.error == ErrorCodes.NOT_FOUND
        assert response.message == "Resource not found"
        assert response.operation == "get resource"
        assert response.details == details


class TestErrorCodes:
    """Test cases for ErrorCodes enum"""
    
    def test_error_codes_exist(self):
        assert ErrorCodes.VALIDATION_ERROR == "validation_error"
        assert ErrorCodes.AUTHENTICATION_ERROR == "authentication_error"
        assert ErrorCodes.AUTHORIZATION_ERROR == "authorization_error"
        assert ErrorCodes.NOT_FOUND == "not_found"
        assert ErrorCodes.CONFLICT == "conflict"
        assert ErrorCodes.RATE_LIMIT_EXCEEDED == "rate_limit_exceeded"
        assert ErrorCodes.SERVICE_UNAVAILABLE == "service_unavailable"
        assert ErrorCodes.INTERNAL_ERROR == "internal_error" 