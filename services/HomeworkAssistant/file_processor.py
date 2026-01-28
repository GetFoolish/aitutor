"""
File Processing Module for Homework Assistant
Handles multi-format file uploads and text extraction
"""

import os
import io
import uuid
from typing import Dict, Optional, Tuple
from datetime import datetime
from PIL import Image
import gridfs
from pymongo import MongoClient

from shared.logging_config import get_logger

logger = get_logger(__name__)

# Supported file types
SUPPORTED_EXTENSIONS = {
    'pdf': ['.pdf'],
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
    'text': ['.txt'],
    'document': ['.doc', '.docx']
}

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes


class FileProcessor:
    """Handles file upload, processing, and storage for homework files"""

    def __init__(self, mongo_db):
        """
        Initialize FileProcessor with MongoDB connection

        Args:
            mongo_db: MongoDBManager instance
        """
        self.mongo_db = mongo_db
        self.db = mongo_db.db
        self.fs = gridfs.GridFS(self.db)
        self.homework_collection = self.db['homework']

    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate file extension and size

        Args:
            filename: Name of the file
            file_size: Size of file in bytes

        Returns:
            Tuple of (is_valid, file_type, error_message)
        """
        # Check file size
        if file_size > MAX_FILE_SIZE:
            return False, None, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024)}MB"

        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()

        for file_type, extensions in SUPPORTED_EXTENSIONS.items():
            if file_ext in extensions:
                return True, file_type, None

        supported = ', '.join([ext for exts in SUPPORTED_EXTENSIONS.values() for ext in exts])
        return False, None, f"Unsupported file type. Supported formats: {supported}"

    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """
        Extract text from PDF file using Gemini Vision (for scanned/image PDFs) or PyPDF2 (for text PDFs)

        Args:
            file_content: Binary content of PDF file

        Returns:
            Extracted text content
        """
        # First, try to convert PDF to images and use Gemini Vision (best for homework/worksheets)
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if gemini_api_key:
            try:
                import fitz  # PyMuPDF
                import google.generativeai as genai
                import base64

                genai.configure(api_key=gemini_api_key)

                # Open PDF with PyMuPDF
                pdf_doc = fitz.open(stream=file_content, filetype="pdf")
                logger.info(f"[PDF-OCR] Processing PDF with {len(pdf_doc)} page(s) using Gemini Vision")

                all_text = []
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc[page_num]
                    # Render page to image (higher resolution for better OCR)
                    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                    pix = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")

                    # Convert to base64
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                    # Use Gemini Vision to extract text
                    model = genai.GenerativeModel('gemini-2.0-flash')

                    prompt = """Analyze this homework/worksheet page and extract ALL math problems with their EXACT visual positions.

CRITICAL RULES:
1. Read EXACTLY what is printed on the page - do NOT guess or complete partial equations
2. If you see "4 =" then output "4 =" - do NOT assume it should be "3+4="
3. The equation text MUST match EXACTLY what appears at the bounding box location

FIRST, output the layout:
LAYOUT: [columns]x[rows] starting at [top_margin]% from top, bottom at [bottom_margin]%

Then for EACH problem, output its VISUAL bounding box as percentages:
PROBLEM [num]: [equation] | BBOX: [left]%, [top]%, [right]%, [bottom]%

BBOX coordinates are percentages of page dimensions:
- LEFT% = distance from left edge (0-100)
- TOP% = distance from top edge (0-100)
- RIGHT% = distance from left edge to right side of problem
- BOTTOM% = distance from top edge to bottom of problem

IMPORTANT:
- Read problems in order: left column first (top to bottom), then right column (top to bottom)
- OR if numbered, follow the numbers on the worksheet
- Transcribe EXACTLY what is printed - blanks, boxes, partial equations
- If format is "__ + __ = __" with some numbers filled, write exactly that
- Be thorough and don't miss any problems
- This is page """ + str(page_num + 1)

                    response = model.generate_content([
                        prompt,
                        {"mime_type": "image/png", "data": img_base64}
                    ])

                    page_text = response.text.strip()
                    if page_text:
                        all_text.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    logger.info(f"[PDF-OCR] Page {page_num + 1}: extracted {len(page_text)} characters")

                num_pages = len(pdf_doc)
                pdf_doc.close()

                if all_text:
                    combined_text = "\n\n".join(all_text)
                    logger.info(f"[PDF-OCR] Total extracted: {len(combined_text)} characters from {num_pages} pages")
                    return combined_text

            except ImportError as e:
                logger.warning(f"[PDF-OCR] PyMuPDF not installed, falling back to PyPDF2: {e}")
            except Exception as e:
                logger.warning(f"[PDF-OCR] Gemini Vision PDF processing failed, falling back to PyPDF2: {e}")

        # Fallback to PyPDF2 for text-based PDFs
        try:
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text_content = []
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)

                result = "\n".join(text_content)
                if result.strip():
                    logger.info(f"[PDF] PyPDF2 extracted {len(result)} characters")
                    return result
                else:
                    logger.warning("[PDF] PyPDF2 found no text - PDF may contain only images")
                    return "[PDF contains images - install PyMuPDF for OCR support: pip install pymupdf]"

            except ImportError:
                logger.warning("PyPDF2 not installed, PDF text extraction not available")
                return "[PDF content - text extraction not available]"
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return f"[Error extracting PDF content: {str(e)}]"

    def extract_text_from_image(self, file_content: bytes) -> str:
        """
        Extract text from image file using Gemini Vision API (preferred) or Tesseract as fallback

        Args:
            file_content: Binary content of image file

        Returns:
            Extracted text from the image
        """
        # Try Gemini Vision API first (much better for math worksheets)
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if gemini_api_key:
            try:
                import google.generativeai as genai
                import base64

                genai.configure(api_key=gemini_api_key)

                # Open image to get dimensions
                img = Image.open(io.BytesIO(file_content))
                width, height = img.size
                logger.info(f"[OCR] Processing image with Gemini Vision: {width}x{height} pixels")

                # Convert image to base64
                img_base64 = base64.b64encode(file_content).decode('utf-8')

                # Use Gemini Vision to extract text
                model = genai.GenerativeModel('gemini-2.0-flash')

                prompt = """Analyze this homework/worksheet image and extract ALL math problems with their EXACT visual positions.

WORKSHEET TYPES:
1. NUMBER-BASED: Problems like "3 + 4 =" with printed digits
2. PICTURE-BASED (Count & Add): Problems with pictures/icons (fruits, animals, shapes) that must be COUNTED

FOR PICTURE-BASED WORKSHEETS:
- COUNT the pictures on each side of the + or - sign
- Convert picture counts to numbers
- Example: 🍎🍎🍎 + 🍎🍎 = ___ becomes "3 + 2 ="
- Output the COUNTED numbers, not descriptions of pictures

FIRST, output the layout:
LAYOUT: [columns]x[rows] starting at [top_margin]% from top, bottom at [bottom_margin]%

Then for EACH problem, output its VISUAL bounding box as percentages:
PROBLEM [num]: [equation] | BBOX: [left]%, [top]%, [right]%, [bottom]%

BBOX coordinates are percentages of image dimensions:
- LEFT% = distance from left edge (0-100)
- TOP% = distance from top edge (0-100)
- RIGHT% = distance from left edge to right side of problem
- BOTTOM% = distance from top edge to bottom of problem

Example for picture-based worksheet:
LAYOUT: 1x5 starting at 20% from top, bottom at 90%
PROBLEM 1: 3 + 2 = | BBOX: 5%, 20%, 95%, 30%
PROBLEM 2: 4 + 1 = | BBOX: 5%, 32%, 95%, 42%

Example for number-based worksheet:
LAYOUT: 2x6 starting at 24% from top, bottom at 95%
PROBLEM 1: 84 + 2 = | BBOX: 5%, 24%, 48%, 32%
PROBLEM 2: 30 + 4 = | BBOX: 52%, 24%, 95%, 32%

IMPORTANT:
- For pictures: COUNT them and output as numbers (e.g., 3 apples + 2 apples = "3 + 2 =")
- Read problems in order: top to bottom, left to right
- Include the = sign in each equation
- Be thorough and don't miss any problems"""

                response = model.generate_content([
                    prompt,
                    {"mime_type": "image/png", "data": img_base64}
                ])

                extracted_text = response.text.strip()
                logger.info(f"[OCR] Gemini Vision extracted {len(extracted_text)} characters")
                return extracted_text

            except Exception as e:
                logger.warning(f"[OCR] Gemini Vision failed, falling back to Tesseract: {e}")

        # Fallback to Tesseract
        try:
            import pytesseract

            # Open the image
            img = Image.open(io.BytesIO(file_content))
            width, height = img.size
            logger.info(f"[OCR] Processing image with Tesseract: {width}x{height} pixels")

            # Perform OCR
            extracted_text = pytesseract.image_to_string(img)

            if extracted_text.strip():
                logger.info(f"[OCR] Tesseract extracted {len(extracted_text)} characters")
                return extracted_text.strip()
            else:
                logger.warning("[OCR] No text found in image")
                return f"[Image file: {width}x{height} pixels - No text detected by OCR]"

        except ImportError:
            logger.warning("pytesseract not installed, OCR not available")
            try:
                img = Image.open(io.BytesIO(file_content))
                width, height = img.size
                return f"[Image file: {width}x{height} pixels - OCR library not available]"
            except:
                return "[Image file - could not process]"
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return f"[Error processing image: {str(e)}]"

    def extract_text_from_document(self, file_content: bytes) -> str:
        """
        Extract text from Word document

        Args:
            file_content: Binary content of Word document

        Returns:
            Extracted text content
        """
        try:
            # Try python-docx
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_content))
                text_content = []
                for para in doc.paragraphs:
                    text_content.append(para.text)
                return "\n".join(text_content)
            except ImportError:
                logger.warning("python-docx not installed, Word document processing not available")
                return "[Word document content - text extraction not available]"
        except Exception as e:
            logger.error(f"Error extracting text from document: {e}")
            return f"[Error extracting document content: {str(e)}]"

    def extract_text_from_file(self, file_content: bytes, file_type: str, filename: str) -> str:
        """
        Extract text content from file based on file type

        Args:
            file_content: Binary content of file
            file_type: Type of file (pdf, image, text, document)
            filename: Original filename

        Returns:
            Extracted text content
        """
        try:
            if file_type == 'pdf':
                return self.extract_text_from_pdf(file_content)
            elif file_type == 'image':
                return self.extract_text_from_image(file_content)
            elif file_type == 'text':
                return file_content.decode('utf-8', errors='ignore')
            elif file_type == 'document':
                return self.extract_text_from_document(file_content)
            else:
                return "[Unknown file type]"
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}")
            return f"[Error processing file: {str(e)}]"

    async def process_and_store_file(
        self,
        filename: str,
        file_content: bytes,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Process uploaded file and store in MongoDB with GridFS

        Args:
            filename: Original filename
            file_content: Binary content of file
            user_id: ID of user uploading the file
            metadata: Optional additional metadata

        Returns:
            Dictionary with homework_id, file_type, and status
        """
        try:
            # Validate file
            is_valid, file_type, error_msg = self.validate_file(filename, len(file_content))
            if not is_valid:
                raise ValueError(error_msg)

            # Generate unique homework ID
            homework_id = str(uuid.uuid4())

            # Extract text content from file
            extracted_text = self.extract_text_from_file(file_content, file_type, filename)

            # Store file in GridFS (for large files)
            file_id = self.fs.put(
                file_content,
                filename=filename,
                content_type=self._get_content_type(file_type),
                homework_id=homework_id,
                user_id=user_id
            )

            # Store homework metadata in collection
            homework_doc = {
                "homework_id": homework_id,
                "user_id": user_id,
                "filename": filename,
                "file_type": file_type,
                "file_size": len(file_content),
                "file_id": file_id,  # GridFS file reference
                "extracted_text": extracted_text,
                "status": "uploaded",
                "uploaded_at": datetime.utcnow(),
                "conversation_history": [],  # For AI chat history
                "metadata": metadata or {}
            }

            self.homework_collection.insert_one(homework_doc)

            logger.info(f"[HOMEWORK] File uploaded successfully: {homework_id} by user {user_id}")

            return {
                "homework_id": homework_id,
                "file_type": file_type,
                "status": "uploaded",
                "filename": filename,
                "file_size": len(file_content),
                "uploaded_at": homework_doc["uploaded_at"].isoformat()
            }

        except Exception as e:
            logger.error(f"[HOMEWORK] Error processing file: {e}", exc_info=True)
            raise

    def _get_content_type(self, file_type: str) -> str:
        """Get MIME content type for file type"""
        content_types = {
            'pdf': 'application/pdf',
            'image': 'image/jpeg',
            'text': 'text/plain',
            'document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        return content_types.get(file_type, 'application/octet-stream')

    def get_homework(self, homework_id: str, user_id: str) -> Optional[Dict]:
        """
        Retrieve homework by ID

        Args:
            homework_id: Homework ID
            user_id: User ID (for authorization)

        Returns:
            Homework document or None
        """
        return self.homework_collection.find_one({
            "homework_id": homework_id,
            "user_id": user_id
        })

    def list_homework(self, user_id: str, limit: int = 50) -> list:
        """
        List all homework for a user

        Args:
            user_id: User ID
            limit: Maximum number of items to return

        Returns:
            List of homework documents
        """
        cursor = self.homework_collection.find(
            {"user_id": user_id}
        ).sort("uploaded_at", -1).limit(limit)

        homework_list = []
        for doc in cursor:
            doc.pop('_id', None)  # Remove MongoDB _id
            doc.pop('extracted_text', None)  # Don't send full text in list
            homework_list.append(doc)

        return homework_list

    def delete_homework(self, homework_id: str, user_id: str) -> bool:
        """
        Delete homework and associated file

        Args:
            homework_id: Homework ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted successfully
        """
        try:
            # Find homework document
            homework = self.get_homework(homework_id, user_id)
            if not homework:
                return False

            # Delete file from GridFS
            if 'file_id' in homework:
                self.fs.delete(homework['file_id'])

            # Delete homework document
            result = self.homework_collection.delete_one({
                "homework_id": homework_id,
                "user_id": user_id
            })

            logger.info(f"[HOMEWORK] Deleted homework {homework_id} for user {user_id}")
            return result.deleted_count > 0

        except Exception as e:
            logger.error(f"[HOMEWORK] Error deleting homework: {e}", exc_info=True)
            return False
