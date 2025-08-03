"""
Comprehensive Tests for Paper Endpoints
L6 Engineering Standards - Production-ready test coverage
"""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io

from app.main import app
from app.core.error_handling import ErrorCodes


class TestPaperUploadEndpoints:
    """Test suite for paper upload functionality"""
    
    @pytest.fixture
    def mock_file(self):
        """Create a mock PDF file for testing"""
        file_content = b"Mock PDF content"
        return UploadFile(
            filename="test_paper.pdf",
            file=io.BytesIO(file_content),
            content_type="application/pdf"
        )
    
    @pytest.fixture
    def project_id(self):
        return str(uuid.uuid4())
    
    @pytest.fixture
    def mock_user(self):
        return {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "username": "testuser"
        }
    
    @pytest.fixture
    def mock_project_access(self):
        return {
            "can_read": True,
            "can_write": True,
            "can_admin": False,
            "can_own": False
        }
    
    @pytest.mark.asyncio
    async def test_upload_paper_success(
        self, 
        client: TestClient, 
        mock_file: UploadFile, 
        project_id: str,
        mock_user: dict,
        mock_project_access: dict
    ):
        """Test successful paper upload"""
        with patch('api.v1.endpoints.core.paper_upload.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_upload.verify_project_access') as mock_access, \
             patch('api.v1.endpoints.core.paper_upload.PaperService') as mock_service:
            
            # Setup mocks
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.upload_paper.return_value = {
                "success": True,
                "message": "Paper uploaded successfully",
                "paper_id": str(uuid.uuid4()),
                "processing_status": "completed",
                "diagnostic_status": "pending"
            }
            
            # Make request
            response = client.post(
                f"/api/v1/papers/{project_id}/upload",
                files={"file": ("test.pdf", mock_file.file, "application/pdf")},
                data={
                    "title": "Test Paper",
                    "process_with_grobid": True,
                    "run_diagnostics": True,
                    "private_uploaded": False
                }
            )
            
            # Assertions
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert "paper_id" in data
            assert data["processing_status"] == "completed"
            
            # Verify service was called correctly
            mock_service_instance.upload_paper.assert_called_once()
            call_args = mock_service_instance.upload_paper.call_args
            assert call_args.kwargs["project_id"] == uuid.UUID(project_id)
            assert call_args.kwargs["user_id"] == mock_user["user_id"]
    
    @pytest.mark.asyncio
    async def test_upload_paper_no_write_permission(
        self, 
        client: TestClient, 
        mock_file: UploadFile, 
        project_id: str,
        mock_user: dict
    ):
        """Test paper upload without write permission"""
        mock_project_access = {
            "can_read": True,
            "can_write": False,
            "can_admin": False,
            "can_own": False
        }
        
        with patch('api.v1.endpoints.core.paper_upload.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_upload.verify_project_access') as mock_access:
            
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            response = client.post(
                f"/api/v1/papers/{project_id}/upload",
                files={"file": ("test.pdf", mock_file.file, "application/pdf")}
            )
            
            assert response.status_code == 403
            data = response.json()
            assert ErrorCodes.AUTHORIZATION_ERROR in data["detail"]["error_code"]
    
    @pytest.mark.asyncio
    async def test_upload_paper_service_error(
        self, 
        client: TestClient, 
        mock_file: UploadFile, 
        project_id: str,
        mock_user: dict,
        mock_project_access: dict
    ):
        """Test paper upload with service error"""
        with patch('api.v1.endpoints.core.paper_upload.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_upload.verify_project_access') as mock_access, \
             patch('api.v1.endpoints.core.paper_upload.PaperService') as mock_service:
            
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.upload_paper.return_value = {
                "success": False,
                "error": "File processing failed",
                "error_code": ErrorCodes.OPERATION_FAILED
            }
            
            response = client.post(
                f"/api/v1/papers/{project_id}/upload",
                files={"file": ("test.pdf", mock_file.file, "application/pdf")}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert ErrorCodes.OPERATION_FAILED in data["detail"]["error_code"]


class TestPaperCRUDEndpoints:
    """Test suite for paper CRUD operations"""
    
    @pytest.fixture
    def project_id(self):
        return str(uuid.uuid4())
    
    @pytest.fixture
    def paper_id(self):
        return str(uuid.uuid4())
    
    @pytest.fixture
    def mock_user(self):
        return {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "username": "testuser"
        }
    
    @pytest.fixture
    def mock_project_access(self):
        return {
            "can_read": True,
            "can_write": True,
            "can_admin": False,
            "can_own": False
        }
    
    @pytest.mark.asyncio
    async def test_get_project_papers_success(
        self, 
        client: TestClient, 
        project_id: str,
        mock_user: dict,
        mock_project_access: dict
    ):
        """Test successful retrieval of project papers"""
        with patch('api.v1.endpoints.core.paper_crud.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_crud.verify_project_access') as mock_access, \
             patch('api.v1.endpoints.core.paper_crud.PaperService') as mock_service:
            
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.list_project_papers.return_value = {
                "papers": [
                    {
                        "id": str(uuid.uuid4()),
                        "title": "Test Paper 1",
                        "authors": ["Author 1"],
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "total": 1
            }
            
            response = client.get(
                f"/api/v1/papers/{project_id}/papers",
                params={"page": 1, "size": 20}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["papers"]) == 1
            assert data["total"] == 1
            assert data["page"] == 1
            assert data["size"] == 20
    
    @pytest.mark.asyncio
    async def test_get_paper_success(
        self, 
        client: TestClient, 
        project_id: str,
        paper_id: str,
        mock_user: dict,
        mock_project_access: dict
    ):
        """Test successful retrieval of specific paper"""
        with patch('api.v1.endpoints.core.paper_crud.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_crud.verify_project_access') as mock_access, \
             patch('api.v1.endpoints.core.paper_crud.PaperService') as mock_service:
            
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_paper.return_value = {
                "success": True,
                "paper": {
                    "id": paper_id,
                    "title": "Test Paper",
                    "authors": ["Author 1"],
                    "abstract": "Test abstract",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            }
            
            response = client.get(f"/api/v1/papers/{project_id}/papers/{paper_id}")
            
            assert response.status_code == 200
            paper_data = response.json()
            assert paper_data["id"] == paper_id
            assert paper_data["title"] == "Test Paper"
    
    @pytest.mark.asyncio
    async def test_get_paper_not_found(
        self, 
        client: TestClient, 
        project_id: str,
        paper_id: str,
        mock_user: dict,
        mock_project_access: dict
    ):
        """Test retrieval of non-existent paper"""
        with patch('api.v1.endpoints.core.paper_crud.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_crud.verify_project_access') as mock_access, \
             patch('api.v1.endpoints.core.paper_crud.PaperService') as mock_service:
            
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_paper.return_value = {
                "success": False,
                "error": "Paper not found"
            }
            
            response = client.get(f"/api/v1/papers/{project_id}/papers/{paper_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert ErrorCodes.NOT_FOUND in data["detail"]["error_code"]
    
    @pytest.mark.asyncio
    async def test_delete_paper_success(
        self, 
        client: TestClient, 
        project_id: str,
        paper_id: str,
        mock_user: dict,
        mock_project_access: dict
    ):
        """Test successful paper deletion"""
        with patch('api.v1.endpoints.core.paper_crud.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_crud.verify_project_access') as mock_access, \
             patch('api.v1.endpoints.core.paper_crud.PaperService') as mock_service:
            
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.delete_paper.return_value = {
                "success": True,
                "message": "Paper deleted successfully"
            }
            
            response = client.delete(
                f"/api/v1/papers/{project_id}/papers/{paper_id}",
                params={"hard_delete": False}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Paper deleted successfully" in data["message"]


class TestArXivEndpoints:
    """Test suite for ArXiv integration"""
    
    @pytest.fixture
    def mock_user(self):
        return {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "username": "testuser"
        }
    
    @pytest.mark.asyncio
    async def test_search_arxiv_success(
        self, 
        client: TestClient, 
        mock_user: dict
    ):
        """Test successful ArXiv search"""
        with patch('api.v1.endpoints.core.paper_arxiv.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_arxiv.PaperService') as mock_service:
            
            mock_auth.return_value = mock_user
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.search_arxiv.return_value = {
                "papers": [
                    {
                        "arxiv_id": "2301.12345",
                        "title": "Test ArXiv Paper",
                        "authors": ["Author 1", "Author 2"],
                        "abstract": "Test abstract",
                        "published": "2023-01-01"
                    }
                ],
                "total": 1
            }
            
            search_request = {
                "query": "machine learning",
                "max_results": 10,
                "sort_by": "relevance",
                "sort_order": "descending",
                "categories": ["cs.LG"]
            }
            
            response = client.post("/api/v1/papers/arxiv/search", json=search_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["papers"]) == 1
            assert data["query"] == "machine learning"
            assert data["search_metadata"]["max_results"] == 10
    
    @pytest.mark.asyncio
    async def test_download_arxiv_paper_success(
        self, 
        client: TestClient, 
        mock_user: dict
    ):
        """Test successful ArXiv paper download"""
        project_id = str(uuid.uuid4())
        
        with patch('api.v1.endpoints.core.paper_arxiv.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_arxiv.PaperService') as mock_service:
            
            mock_auth.return_value = mock_user
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.download_arxiv_paper.return_value = {
                "success": True,
                "message": "Paper downloaded successfully",
                "paper_id": str(uuid.uuid4()),
                "processing_status": "completed",
                "diagnostic_status": "pending"
            }
            
            download_request = {
                "arxiv_id": "2301.12345",
                "project_id": project_id,
                "process_with_grobid": True,
                "run_diagnostics": True
            }
            
            response = client.post("/api/v1/papers/arxiv/download", json=download_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["arxiv_id"] == "2301.12345"
            assert "paper_id" in data
    
    @pytest.mark.asyncio
    async def test_get_arxiv_categories_success(
        self, 
        client: TestClient, 
        mock_user: dict
    ):
        """Test successful retrieval of ArXiv categories"""
        with patch('api.v1.endpoints.core.paper_arxiv.get_current_user_required') as mock_auth:
            mock_auth.return_value = mock_user
            
            response = client.get("/api/v1/papers/arxiv/categories")
            
            assert response.status_code == 200
            categories = response.json()
            assert isinstance(categories, list)
            assert len(categories) > 0
            assert all("id" in cat and "name" in cat for cat in categories)


class TestErrorHandling:
    """Test suite for error handling across all endpoints"""
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to protected endpoints"""
        project_id = str(uuid.uuid4())
        
        with patch('api.v1.endpoints.core.paper_crud.get_current_user_required') as mock_auth:
            mock_auth.side_effect = HTTPException(status_code=401, detail="Unauthorized")
            
            response = client.get(f"/api/v1/papers/{project_id}/papers")
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_validation_error(self, client: TestClient):
        """Test validation error handling"""
        # Test with invalid UUID
        response = client.get("/api/v1/papers/invalid-uuid/papers")
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_database_error_handling(
        self, 
        client: TestClient, 
        mock_user: dict,
        mock_project_access: dict
    ):
        """Test database error handling"""
        project_id = str(uuid.uuid4())
        
        with patch('api.v1.endpoints.core.paper_crud.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_crud.verify_project_access') as mock_access, \
             patch('api.v1.endpoints.core.paper_crud.PaperService') as mock_service:
            
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.list_project_papers.side_effect = Exception("Database connection failed")
            
            response = client.get(f"/api/v1/papers/{project_id}/papers")
            
            assert response.status_code == 500
            data = response.json()
            assert ErrorCodes.OPERATION_FAILED in data["detail"]["error_code"]


@pytest.fixture
def client():
    """Create test client"""
    from fastapi.testclient import TestClient
    return TestClient(app)


# Integration tests
class TestPaperWorkflow:
    """Integration tests for complete paper workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_paper_lifecycle(
        self, 
        client: TestClient,
        mock_user: dict,
        mock_project_access: dict
    ):
        """Test complete paper lifecycle: upload -> process -> get -> delete"""
        project_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        
        # Mock file for upload
        file_content = b"Mock PDF content"
        mock_file = UploadFile(
            filename="test_paper.pdf",
            file=io.BytesIO(file_content),
            content_type="application/pdf"
        )
        
        with patch('api.v1.endpoints.core.paper_upload.get_current_user_required') as mock_auth, \
             patch('api.v1.endpoints.core.paper_upload.verify_project_access') as mock_access, \
             patch('api.v1.endpoints.core.paper_upload.PaperService') as mock_upload_service, \
             patch('api.v1.endpoints.core.paper_crud.PaperService') as mock_crud_service:
            
            # Setup mocks
            mock_auth.return_value = mock_user
            mock_access.return_value = mock_project_access
            
            # Upload service mock
            mock_upload_instance = AsyncMock()
            mock_upload_service.return_value = mock_upload_instance
            mock_upload_instance.upload_paper.return_value = {
                "success": True,
                "message": "Paper uploaded successfully",
                "paper_id": paper_id,
                "processing_status": "completed"
            }
            
            # CRUD service mock
            mock_crud_instance = AsyncMock()
            mock_crud_service.return_value = mock_crud_instance
            mock_crud_instance.get_paper.return_value = {
                "success": True,
                "paper": {
                    "id": paper_id,
                    "title": "Test Paper",
                    "authors": ["Author 1"]
                }
            }
            mock_crud_instance.delete_paper.return_value = {
                "success": True,
                "message": "Paper deleted successfully"
            }
            
            # 1. Upload paper
            upload_response = client.post(
                f"/api/v1/papers/{project_id}/upload",
                files={"file": ("test.pdf", mock_file.file, "application/pdf")},
                data={"title": "Test Paper"}
            )
            assert upload_response.status_code == 201
            upload_data = upload_response.json()
            assert upload_data["success"] is True
            
            # 2. Get paper
            get_response = client.get(f"/api/v1/papers/{project_id}/papers/{paper_id}")
            assert get_response.status_code == 200
            paper_data = get_response.json()
            assert paper_data["id"] == paper_id
            
            # 3. Delete paper
            delete_response = client.delete(f"/api/v1/papers/{project_id}/papers/{paper_id}")
            assert delete_response.status_code == 200
            delete_data = delete_response.json()
            assert delete_data["success"] is True 