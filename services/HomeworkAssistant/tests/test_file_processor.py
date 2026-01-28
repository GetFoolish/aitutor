"""
Unit tests for FileProcessor
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import io
from PIL import Image
import uuid

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.HomeworkAssistant.file_processor import FileProcessor, MAX_FILE_SIZE


@pytest.fixture
def mock_mongo_db():
    """Mock MongoDB connection"""
    mock_db = Mock()
    mock_db.db = Mock()
    mock_db.db.__getitem__ = Mock(return_value=Mock())
    return mock_db


@pytest.fixture
def file_processor(mock_mongo_db):
    """Create FileProcessor instance with mocked DB"""
    with patch('gridfs.GridFS'):
        processor = FileProcessor(mock_mongo_db)
        processor.homework_collection = Mock()
        processor.fs = Mock()
        return processor


class TestFileValidation:
    """Tests for file validation"""

    def test_validate_pdf_file(self, file_processor):
        """Test validation of valid PDF file"""
        is_valid, file_type, error_msg = file_processor.validate_file(
            "test.pdf", 1024
        )

        assert is_valid is True
        assert file_type == "pdf"
        assert error_msg is None

    def test_validate_image_files(self, file_processor):
        """Test validation of image files"""
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
            is_valid, file_type, error_msg = file_processor.validate_file(
                f"test{ext}", 1024
            )

            assert is_valid is True
            assert file_type == "image"
            assert error_msg is None

    def test_validate_text_file(self, file_processor):
        """Test validation of text file"""
        is_valid, file_type, error_msg = file_processor.validate_file(
            "test.txt", 1024
        )

        assert is_valid is True
        assert file_type == "text"
        assert error_msg is None

    def test_validate_word_files(self, file_processor):
        """Test validation of Word document files"""
        for ext in [".doc", ".docx"]:
            is_valid, file_type, error_msg = file_processor.validate_file(
                f"test{ext}", 1024
            )

            assert is_valid is True
            assert file_type == "document"
            assert error_msg is None

    def test_validate_unsupported_file(self, file_processor):
        """Test validation rejects unsupported file types"""
        is_valid, file_type, error_msg = file_processor.validate_file(
            "test.exe", 1024
        )

        assert is_valid is False
        assert file_type is None
        assert "Unsupported file type" in error_msg

    def test_validate_file_too_large(self, file_processor):
        """Test validation rejects files exceeding size limit"""
        large_size = MAX_FILE_SIZE + 1

        is_valid, file_type, error_msg = file_processor.validate_file(
            "test.pdf", large_size
        )

        assert is_valid is False
        assert file_type is None
        assert "exceeds maximum" in error_msg

    def test_validate_case_insensitive_extension(self, file_processor):
        """Test validation handles uppercase extensions"""
        is_valid, file_type, error_msg = file_processor.validate_file(
            "TEST.PDF", 1024
        )

        assert is_valid is True
        assert file_type == "pdf"


class TestTextExtraction:
    """Tests for text extraction from various file types"""

    def test_extract_text_from_plain_text(self, file_processor):
        """Test extraction from plain text file"""
        content = b"Hello, this is a test file."
        result = file_processor.extract_text_from_file(content, "text", "test.txt")

        assert result == "Hello, this is a test file."

    @patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    @patch('services.HomeworkAssistant.file_processor.PyPDF2')
    def test_extract_text_from_pdf_pypdf2(self, mock_pypdf2, file_processor):
        """Test PDF text extraction with PyPDF2 fallback"""
        # Mock PyPDF2 reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Page 1 content"
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_pypdf2.PdfReader.return_value = mock_reader

        content = b"%PDF-1.4 fake pdf"
        result = file_processor.extract_text_from_pdf(content)

        assert "Page 1 content" in result

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.file_processor.genai')
    @patch('services.HomeworkAssistant.file_processor.fitz')
    def test_extract_text_from_pdf_gemini(self, mock_fitz, mock_genai, file_processor):
        """Test PDF text extraction with Gemini Vision"""
        # Mock PyMuPDF
        mock_page = Mock()
        mock_pix = Mock()
        mock_pix.tobytes.return_value = b"fake image"
        mock_page.get_pixmap.return_value = mock_pix
        mock_pdf = Mock()
        mock_pdf.__len__.return_value = 1
        mock_pdf.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_pdf

        # Mock Gemini
        mock_response = Mock()
        mock_response.text = "LAYOUT: 2x3\nPROBLEM 1: 2+2=4"
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        content = b"%PDF-1.4 fake pdf"
        result = file_processor.extract_text_from_pdf(content)

        assert "PROBLEM 1: 2+2=4" in result
        assert "Page 1" in result

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('services.HomeworkAssistant.file_processor.genai')
    def test_extract_text_from_image_gemini(self, mock_genai, file_processor):
        """Test image text extraction with Gemini Vision"""
        # Create fake image
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        content = img_bytes.getvalue()

        # Mock Gemini
        mock_response = Mock()
        mock_response.text = "LAYOUT: 1x5\nPROBLEM 1: 10+5=15"
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = file_processor.extract_text_from_image(content)

        assert "PROBLEM 1: 10+5=15" in result

    @patch('services.HomeworkAssistant.file_processor.docx')
    def test_extract_text_from_word_doc(self, mock_docx, file_processor):
        """Test text extraction from Word document"""
        # Mock python-docx
        mock_para1 = Mock()
        mock_para1.text = "First paragraph"
        mock_para2 = Mock()
        mock_para2.text = "Second paragraph"
        mock_doc = Mock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_docx.Document.return_value = mock_doc

        content = b"fake docx content"
        result = file_processor.extract_text_from_document(content)

        assert "First paragraph" in result
        assert "Second paragraph" in result


class TestProcessAndStoreFile:
    """Tests for file processing and storage"""

    @pytest.mark.asyncio
    async def test_process_and_store_success(self, file_processor):
        """Test successful file processing and storage"""
        # Mock GridFS put
        file_processor.fs.put.return_value = "gridfs_file_id"

        # Mock text extraction
        with patch.object(file_processor, 'extract_text_from_file', return_value="Extracted text"):
            content = b"fake pdf content"
            result = await file_processor.process_and_store_file(
                filename="test.pdf",
                file_content=content,
                user_id="user123"
            )

            # Verify homework_collection.insert_one was called
            assert file_processor.homework_collection.insert_one.called

            # Verify result
            assert "homework_id" in result
            assert result["file_type"] == "pdf"
            assert result["status"] == "uploaded"
            assert result["filename"] == "test.pdf"
            assert result["file_size"] == len(content)

    @pytest.mark.asyncio
    async def test_process_invalid_file_raises_error(self, file_processor):
        """Test processing invalid file raises ValueError"""
        content = b"fake content"

        with pytest.raises(ValueError) as exc_info:
            await file_processor.process_and_store_file(
                filename="test.exe",
                file_content=content,
                user_id="user123"
            )

        assert "Unsupported file type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_large_file_raises_error(self, file_processor):
        """Test processing oversized file raises ValueError"""
        # Create file larger than MAX_FILE_SIZE
        large_content = b"x" * (MAX_FILE_SIZE + 1)

        with pytest.raises(ValueError) as exc_info:
            await file_processor.process_and_store_file(
                filename="large.pdf",
                file_content=large_content,
                user_id="user123"
            )

        assert "exceeds maximum" in str(exc_info.value)


class TestHomeworkRetrieval:
    """Tests for homework retrieval operations"""

    def test_get_homework_success(self, file_processor):
        """Test successful homework retrieval"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "filename": "test.pdf"
        }
        file_processor.homework_collection.find_one.return_value = mock_homework

        result = file_processor.get_homework("hw123", "user123")

        assert result == mock_homework
        file_processor.homework_collection.find_one.assert_called_once_with({
            "homework_id": "hw123",
            "user_id": "user123"
        })

    def test_get_homework_not_found(self, file_processor):
        """Test homework retrieval when not found"""
        file_processor.homework_collection.find_one.return_value = None

        result = file_processor.get_homework("nonexistent", "user123")

        assert result is None

    def test_list_homework_success(self, file_processor):
        """Test successful homework listing"""
        mock_cursor = [
            {
                "_id": "mongo_id_1",
                "homework_id": "hw1",
                "user_id": "user123",
                "filename": "test1.pdf",
                "extracted_text": "Long text content..."
            },
            {
                "_id": "mongo_id_2",
                "homework_id": "hw2",
                "user_id": "user123",
                "filename": "test2.jpg",
                "extracted_text": "More text..."
            }
        ]

        mock_find = Mock()
        mock_find.sort.return_value.limit.return_value = mock_cursor
        file_processor.homework_collection.find.return_value = mock_find

        result = file_processor.list_homework("user123", limit=50)

        assert len(result) == 2
        assert result[0]["homework_id"] == "hw1"
        # Verify _id and extracted_text are removed
        assert "_id" not in result[0]
        assert "extracted_text" not in result[0]

    def test_list_homework_empty(self, file_processor):
        """Test homework listing when empty"""
        mock_find = Mock()
        mock_find.sort.return_value.limit.return_value = []
        file_processor.homework_collection.find.return_value = mock_find

        result = file_processor.list_homework("user123")

        assert result == []


class TestHomeworkDeletion:
    """Tests for homework deletion"""

    def test_delete_homework_success(self, file_processor):
        """Test successful homework deletion"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123",
            "file_id": "gridfs_file_id"
        }

        file_processor.get_homework = Mock(return_value=mock_homework)

        mock_delete_result = Mock()
        mock_delete_result.deleted_count = 1
        file_processor.homework_collection.delete_one.return_value = mock_delete_result

        result = file_processor.delete_homework("hw123", "user123")

        assert result is True
        file_processor.fs.delete.assert_called_once_with("gridfs_file_id")

    def test_delete_homework_not_found(self, file_processor):
        """Test deletion when homework doesn't exist"""
        file_processor.get_homework = Mock(return_value=None)

        result = file_processor.delete_homework("nonexistent", "user123")

        assert result is False
        file_processor.fs.delete.assert_not_called()

    def test_delete_homework_without_file(self, file_processor):
        """Test deletion when homework has no GridFS file"""
        mock_homework = {
            "homework_id": "hw123",
            "user_id": "user123"
            # No file_id
        }

        file_processor.get_homework = Mock(return_value=mock_homework)

        mock_delete_result = Mock()
        mock_delete_result.deleted_count = 1
        file_processor.homework_collection.delete_one.return_value = mock_delete_result

        result = file_processor.delete_homework("hw123", "user123")

        assert result is True
        # GridFS delete should not be called
        file_processor.fs.delete.assert_not_called()


class TestContentTypeMapping:
    """Tests for content type mapping"""

    def test_get_content_type_pdf(self, file_processor):
        """Test content type for PDF"""
        assert file_processor._get_content_type("pdf") == "application/pdf"

    def test_get_content_type_image(self, file_processor):
        """Test content type for images"""
        assert file_processor._get_content_type("image") == "image/jpeg"

    def test_get_content_type_text(self, file_processor):
        """Test content type for text files"""
        assert file_processor._get_content_type("text") == "text/plain"

    def test_get_content_type_document(self, file_processor):
        """Test content type for Word documents"""
        content_type = file_processor._get_content_type("document")
        assert "officedocument" in content_type

    def test_get_content_type_unknown(self, file_processor):
        """Test content type for unknown types defaults to octet-stream"""
        assert file_processor._get_content_type("unknown") == "application/octet-stream"
