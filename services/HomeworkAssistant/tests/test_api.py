"""
Unit tests for Homework Assistant API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import io

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.HomeworkAssistant.api import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication to return test user ID"""
    with patch('services.HomeworkAssistant.api.get_current_user') as mock:
        mock.return_value = "test_user_123"
        yield mock


@pytest.fixture
def mock_file_processor():
    """Mock FileProcessor"""
    with patch('services.HomeworkAssistant.api.file_processor') as mock:
        yield mock


@pytest.fixture
def mock_homework_assistant():
    """Mock HomeworkAssistant"""
    with patch('services.HomeworkAssistant.api.homework_assistant') as mock:
        yield mock


class TestHealthCheck:
    """Tests for health check endpoint"""

    def test_health_check(self, client):
        """Test health check returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "HomeworkAssistant"}


class TestUploadHomework:
    """Tests for homework upload endpoint"""

    def test_upload_pdf_success(self, client, mock_auth, mock_file_processor):
        """Test successful PDF upload"""
        # Mock the process_and_store_file response
        mock_file_processor.process_and_store_file.return_value = {
            "homework_id": "hw123",
            "file_type": "pdf",
            "status": "uploaded",
            "filename": "test.pdf",
            "file_size": 1024,
            "uploaded_at": "2025-01-28T10:00:00"
        }

        # Create fake PDF file
        file_content = b"%PDF-1.4 fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

        response = client.post("/homework/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["homework_id"] == "hw123"
        assert data["file_type"] == "pdf"
        assert data["status"] == "uploaded"
        assert data["filename"] == "test.pdf"

    def test_upload_empty_file(self, client, mock_auth):
        """Test upload with empty file returns 400"""
        files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        response = client.post("/homework/upload", files=files)

        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]

    def test_upload_invalid_file_type(self, client, mock_auth, mock_file_processor):
        """Test upload with unsupported file type"""
        mock_file_processor.process_and_store_file.side_effect = ValueError(
            "Unsupported file type"
        )

        files = {"file": ("test.exe", io.BytesIO(b"binary"), "application/x-executable")}
        response = client.post("/homework/upload", files=files)

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_file_too_large(self, client, mock_auth, mock_file_processor):
        """Test upload with file exceeding size limit"""
        mock_file_processor.process_and_store_file.side_effect = ValueError(
            "File size exceeds maximum allowed size of 10MB"
        )

        # Create large file (11MB)
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
        response = client.post("/homework/upload", files=files)

        assert response.status_code == 400
        assert "File size exceeds" in response.json()["detail"]


class TestHomeworkAssist:
    """Tests for homework assistance endpoint"""

    def test_ask_question_success(self, client, mock_auth, mock_homework_assistant):
        """Test successful question answering"""
        mock_homework_assistant.ask_question.return_value = {
            "response": "The answer is 42",
            "homework_id": "hw123",
            "timestamp": "2025-01-28T10:00:00"
        }

        request_data = {
            "homework_id": "hw123",
            "question": "What is 6 x 7?"
        }

        response = client.post("/homework/assist", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "The answer is 42"
        assert data["homework_id"] == "hw123"

    def test_ask_question_homework_not_found(self, client, mock_auth, mock_homework_assistant):
        """Test question with non-existent homework returns 404"""
        mock_homework_assistant.ask_question.return_value = {
            "error": "Homework not found"
        }

        request_data = {
            "homework_id": "nonexistent",
            "question": "What is this?"
        }

        response = client.post("/homework/assist", json=request_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestListHomework:
    """Tests for homework list endpoint"""

    def test_list_homework_success(self, client, mock_auth, mock_file_processor):
        """Test successful homework listing"""
        mock_file_processor.list_homework.return_value = [
            {
                "homework_id": "hw1",
                "filename": "math.pdf",
                "file_type": "pdf",
                "file_size": 2048,
                "status": "uploaded",
                "uploaded_at": datetime(2025, 1, 28, 10, 0, 0)
            },
            {
                "homework_id": "hw2",
                "filename": "science.jpg",
                "file_type": "image",
                "file_size": 1024,
                "status": "uploaded",
                "uploaded_at": datetime(2025, 1, 27, 15, 30, 0)
            }
        ]

        response = client.get("/homework/list")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["homework_items"]) == 2
        assert data["homework_items"][0]["homework_id"] == "hw1"

    def test_list_homework_empty(self, client, mock_auth, mock_file_processor):
        """Test listing homework when none exist"""
        mock_file_processor.list_homework.return_value = []

        response = client.get("/homework/list")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["homework_items"] == []


class TestGetHomework:
    """Tests for homework detail endpoint"""

    def test_get_homework_success(self, client, mock_auth, mock_file_processor):
        """Test successful homework retrieval"""
        mock_file_processor.get_homework.return_value = {
            "homework_id": "hw123",
            "filename": "test.pdf",
            "file_type": "pdf",
            "file_size": 2048,
            "status": "uploaded",
            "uploaded_at": datetime(2025, 1, 28, 10, 0, 0),
            "conversation_history": [
                {
                    "role": "user",
                    "content": "What is 2+2?",
                    "timestamp": datetime(2025, 1, 28, 10, 5, 0)
                },
                {
                    "role": "assistant",
                    "content": "2+2=4",
                    "timestamp": datetime(2025, 1, 28, 10, 5, 5)
                }
            ],
            "extracted_text": "Math worksheet content"
        }

        response = client.get("/homework/hw123")

        assert response.status_code == 200
        data = response.json()
        assert data["homework_id"] == "hw123"
        assert data["filename"] == "test.pdf"
        assert len(data["conversation_history"]) == 2

    def test_get_homework_not_found(self, client, mock_auth, mock_file_processor):
        """Test retrieval of non-existent homework returns 404"""
        mock_file_processor.get_homework.return_value = None

        response = client.get("/homework/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestDeleteHomework:
    """Tests for homework deletion endpoint"""

    def test_delete_homework_success(self, client, mock_auth, mock_file_processor):
        """Test successful homework deletion"""
        mock_file_processor.delete_homework.return_value = True

        response = client.delete("/homework/hw123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]

    def test_delete_homework_not_found(self, client, mock_auth, mock_file_processor):
        """Test deletion of non-existent homework returns 404"""
        mock_file_processor.delete_homework.return_value = False

        response = client.delete("/homework/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestDownloadHomeworkFile:
    """Tests for homework file download endpoint"""

    def test_download_file_success(self, client, mock_auth, mock_file_processor):
        """Test successful file download"""
        # Mock homework metadata
        mock_file_processor.get_homework.return_value = {
            "homework_id": "hw123",
            "filename": "test.pdf",
            "file_id": "gridfs_file_id"
        }

        # Mock GridFS file
        mock_grid_out = Mock()
        mock_grid_out.read.return_value = b"PDF content"
        mock_grid_out.content_type = "application/pdf"
        mock_file_processor.fs.get.return_value = mock_grid_out

        response = client.get("/homework/hw123/file")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"PDF content" in response.content

    def test_download_file_not_found(self, client, mock_auth, mock_file_processor):
        """Test download when file doesn't exist returns 404"""
        mock_file_processor.get_homework.return_value = None

        response = client.get("/homework/nonexistent/file")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestGetHomeworkThumbnail:
    """Tests for homework thumbnail endpoint"""

    def test_get_thumbnail_for_image(self, client, mock_auth, mock_file_processor):
        """Test thumbnail generation for image files"""
        # Mock homework metadata
        mock_file_processor.get_homework.return_value = {
            "homework_id": "hw123",
            "file_type": "image",
            "file_id": "gridfs_file_id"
        }

        # Mock GridFS file
        mock_grid_out = Mock()
        mock_grid_out.read.return_value = b"fake image data"
        mock_grid_out.content_type = "image/jpeg"
        mock_file_processor.fs.get.return_value = mock_grid_out

        response = client.get("/homework/hw123/thumbnail")

        assert response.status_code == 200
        assert "image" in response.headers["content-type"]

    @patch('services.HomeworkAssistant.api.fitz')
    def test_get_thumbnail_for_pdf(self, mock_fitz, client, mock_auth, mock_file_processor):
        """Test thumbnail generation for PDF files"""
        # Mock homework metadata
        mock_file_processor.get_homework.return_value = {
            "homework_id": "hw123",
            "file_type": "pdf",
            "file_id": "gridfs_file_id"
        }

        # Mock GridFS file
        mock_grid_out = Mock()
        mock_grid_out.read.return_value = b"fake pdf data"
        mock_file_processor.fs.get.return_value = mock_grid_out

        # Mock PyMuPDF
        mock_pdf = Mock()
        mock_page = Mock()
        mock_pix = Mock()
        mock_pix.tobytes.return_value = b"fake png data"
        mock_page.get_pixmap.return_value = mock_pix
        mock_pdf.__getitem__.return_value = mock_page
        mock_pdf.__len__.return_value = 1
        mock_fitz.open.return_value = mock_pdf

        response = client.get("/homework/hw123/thumbnail")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"


class TestCORSAndMiddleware:
    """Tests for CORS and middleware configuration"""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses"""
        response = client.get("/health")

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_options_preflight(self, client):
        """Test OPTIONS preflight requests work"""
        response = client.options("/homework/upload")

        assert response.status_code == 200
        assert "access-control-allow-methods" in response.headers

    def test_cache_control_health(self, client):
        """Test health endpoint has cache control"""
        response = client.get("/health")

        assert "cache-control" in response.headers
        assert "max-age=60" in response.headers["cache-control"]
