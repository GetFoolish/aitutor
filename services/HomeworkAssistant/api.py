import sys
import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.auth_middleware import get_current_user
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS
from shared.timing_middleware import UnpluggedTimingMiddleware
from shared.logging_config import get_logger
from managers.mongodb_manager import mongo_db
from services.HomeworkAssistant.file_processor import FileProcessor
from services.HomeworkAssistant.homework_assistant import HomeworkAssistant

logger = get_logger(__name__)

# Initialize FileProcessor and HomeworkAssistant
file_processor = FileProcessor(mongo_db)
homework_assistant = HomeworkAssistant(mongo_db)

app = FastAPI(title="Homework Assistant API")

# Add timing middleware for performance monitoring
app.add_middleware(UnpluggedTimingMiddleware)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)

# Configure CORS with secure origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],
)

# Request timeout middleware
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=30.0)
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={"detail": "Request timeout"}
        )

# Cache control middleware for static responses
@app.middleware("http")
async def cache_control_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/health":
        response.headers["Cache-Control"] = "public, max-age=60"
    else:
        response.headers["Cache-Control"] = "no-cache"
    return response

# Explicit OPTIONS handler for Cloud Run compatibility
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS preflight requests explicitly for Cloud Run"""
    from fastapi.responses import Response
    # Use first allowed origin or * if none configured
    origin = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*"
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(ALLOWED_METHODS),
            "Access-Control-Allow-Headers": "*",
        }
    )


# ============================================================================
# Request/Response Models
# ============================================================================

class UploadResponse(BaseModel):
    homework_id: str
    file_type: str
    status: str
    filename: str
    file_size: int
    uploaded_at: str


class AssistRequest(BaseModel):
    homework_id: str
    question: str


class AssistResponse(BaseModel):
    response: str
    homework_id: str
    timestamp: str


class HomeworkItem(BaseModel):
    homework_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    uploaded_at: str


class HomeworkListResponse(BaseModel):
    homework_items: List[HomeworkItem]
    total: int


class HomeworkDetailResponse(BaseModel):
    homework_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    uploaded_at: str
    conversation_history: List[dict]
    extracted_text: Optional[str] = None  # Text content extracted from the file


class DeleteResponse(BaseModel):
    success: bool
    message: str


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint for service monitoring"""
    return {"status": "healthy", "service": "HomeworkAssistant"}


# ============================================================================
# Homework Upload Endpoint
# ============================================================================

@app.post("/homework/upload", response_model=UploadResponse, status_code=201)
async def upload_homework(
    http_request: Request,
    file: UploadFile = File(...)
):
    """
    Upload homework file with multi-format support

    Supported formats:
    - PDF (.pdf)
    - Images (.jpg, .jpeg, .png, .gif, .bmp)
    - Text files (.txt)
    - Word documents (.doc, .docx)

    Args:
        file: Uploaded file (multipart/form-data)

    Returns:
        UploadResponse with homework_id, file_type, and status
    """
    user_id = get_current_user(http_request)

    try:
        # Read file content
        file_content = await file.read()

        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Process and store file
        result = await file_processor.process_and_store_file(
            filename=file.filename,
            file_content=file_content,
            user_id=user_id
        )

        logger.info(f"[HOMEWORK] File uploaded successfully: {result['homework_id']} by user {user_id}")

        return UploadResponse(**result)

    except ValueError as e:
        # Validation errors (file size, type, etc.)
        logger.warning(f"[HOMEWORK] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[HOMEWORK] Error in upload_homework: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


# ============================================================================
# Homework Assistance Endpoint
# ============================================================================

@app.post("/homework/assist", response_model=AssistResponse, status_code=200)
async def homework_assist(
    http_request: Request,
    request: AssistRequest
):
    """
    Get AI assistance for homework questions

    Ask questions about uploaded homework and receive AI-powered guidance.
    Maintains conversation history for follow-up questions.

    Args:
        request: AssistRequest with homework_id and question

    Returns:
        AssistResponse with AI response, homework_id, and timestamp
    """
    user_id = get_current_user(http_request)

    try:
        # Get AI response
        result = homework_assistant.ask_question(
            homework_id=request.homework_id,
            user_id=user_id,
            question=request.question
        )

        # Check for errors
        if "error" in result and result["error"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

        logger.info(f"[HOMEWORK] Provided assistance for {request.homework_id} by user {user_id}")

        return AssistResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HOMEWORK] Error in homework_assist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")


# ============================================================================
# Homework List Endpoint
# ============================================================================

@app.get("/homework/list", response_model=HomeworkListResponse, status_code=200)
async def list_homework(http_request: Request):
    """
    List all homework for the authenticated user

    Returns a list of uploaded homework files with metadata.
    Does not include full extracted text or conversation history.

    Returns:
        HomeworkListResponse with array of homework items and total count
    """
    user_id = get_current_user(http_request)

    try:
        # Get homework list from FileProcessor
        homework_list = file_processor.list_homework(user_id, limit=50)

        # Convert to response model
        homework_items = []
        for homework in homework_list:
            homework_items.append(HomeworkItem(
                homework_id=homework["homework_id"],
                filename=homework["filename"],
                file_type=homework["file_type"],
                file_size=homework["file_size"],
                status=homework["status"],
                uploaded_at=homework["uploaded_at"].isoformat() if isinstance(homework["uploaded_at"], datetime) else homework["uploaded_at"]
            ))

        logger.info(f"[HOMEWORK] Listed {len(homework_items)} homework items for user {user_id}")

        return HomeworkListResponse(
            homework_items=homework_items,
            total=len(homework_items)
        )

    except Exception as e:
        logger.error(f"[HOMEWORK] Error in list_homework: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list homework: {str(e)}")


# ============================================================================
# Homework Detail Endpoint
# ============================================================================

@app.get("/homework/{homework_id}", response_model=HomeworkDetailResponse, status_code=200)
async def get_homework(
    http_request: Request,
    homework_id: str
):
    """
    Get detailed information about a specific homework

    Includes conversation history but not the full extracted text content.

    Args:
        homework_id: Homework ID

    Returns:
        HomeworkDetailResponse with homework details and conversation history
    """
    user_id = get_current_user(http_request)

    try:
        # Get homework from FileProcessor
        homework = file_processor.get_homework(homework_id, user_id)

        if not homework:
            logger.warning(f"[HOMEWORK] Homework not found: {homework_id} for user {user_id}")
            raise HTTPException(status_code=404, detail="Homework not found")

        # Convert conversation history timestamps to ISO format
        conversation_history = []
        for turn in homework.get("conversation_history", []):
            turn_copy = turn.copy()
            if "timestamp" in turn_copy and isinstance(turn_copy["timestamp"], datetime):
                turn_copy["timestamp"] = turn_copy["timestamp"].isoformat()
            conversation_history.append(turn_copy)

        logger.info(f"[HOMEWORK] Retrieved homework details for {homework_id} by user {user_id}")

        return HomeworkDetailResponse(
            homework_id=homework["homework_id"],
            filename=homework["filename"],
            file_type=homework["file_type"],
            file_size=homework["file_size"],
            status=homework["status"],
            uploaded_at=homework["uploaded_at"].isoformat() if isinstance(homework["uploaded_at"], datetime) else homework["uploaded_at"],
            conversation_history=conversation_history,
            extracted_text=homework.get("extracted_text", None)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HOMEWORK] Error in get_homework: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve homework: {str(e)}")


# ============================================================================
# Homework Delete Endpoint
# ============================================================================

@app.delete("/homework/{homework_id}", response_model=DeleteResponse, status_code=200)
async def delete_homework(
    http_request: Request,
    homework_id: str
):
    """
    Delete a homework and its associated file

    Removes the homework document and GridFS file from MongoDB.

    Args:
        homework_id: Homework ID

    Returns:
        DeleteResponse with success status and message
    """
    user_id = get_current_user(http_request)

    try:
        # Delete homework via FileProcessor
        success = file_processor.delete_homework(homework_id, user_id)

        if not success:
            logger.warning(f"[HOMEWORK] Homework not found for deletion: {homework_id} for user {user_id}")
            raise HTTPException(status_code=404, detail="Homework not found")

        logger.info(f"[HOMEWORK] Deleted homework {homework_id} for user {user_id}")

        return DeleteResponse(
            success=True,
            message=f"Homework {homework_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HOMEWORK] Error in delete_homework: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete homework: {str(e)}")


# ============================================================================
# Homework File Download Endpoint
# ============================================================================

@app.get("/homework/{homework_id}/file")
async def download_homework_file(
    http_request: Request,
    homework_id: str
):
    """
    Download the original uploaded homework file

    Returns the file content with appropriate content-type header.
    Used for previewing images and PDFs in the frontend.

    Args:
        homework_id: Homework ID

    Returns:
        File content with appropriate headers
    """
    user_id = get_current_user(http_request)

    try:
        # Get homework metadata
        homework = file_processor.get_homework(homework_id, user_id)

        if not homework:
            logger.warning(f"[HOMEWORK] Homework not found: {homework_id} for user {user_id}")
            raise HTTPException(status_code=404, detail="Homework not found")

        # Get file from GridFS
        if 'file_id' not in homework:
            raise HTTPException(status_code=404, detail="File not found")

        try:
            grid_out = file_processor.fs.get(homework['file_id'])
            file_content = grid_out.read()
        except Exception as e:
            logger.error(f"[HOMEWORK] Error reading file from GridFS: {e}")
            raise HTTPException(status_code=404, detail="File not found in storage")

        # Determine content type
        content_type = grid_out.content_type or 'application/octet-stream'

        logger.info(f"[HOMEWORK] Downloaded file for {homework_id} by user {user_id}")

        # Return file with appropriate headers
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type=content_type,
            headers={
                'Content-Disposition': f'inline; filename="{homework["filename"]}"',
                'Cache-Control': 'private, max-age=3600'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HOMEWORK] Error in download_homework_file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@app.get("/homework/{homework_id}/thumbnail")
async def get_homework_thumbnail(
    http_request: Request,
    homework_id: str,
    page: int = 0
):
    """
    Get a PNG thumbnail of a homework file (renders PDF first page as image).
    This allows overlay positioning to work correctly with CSS percentages.

    Args:
        homework_id: Homework ID
        page: Page number (0-indexed, default 0)

    Returns:
        PNG image of the page
    """
    user_id = get_current_user(http_request)

    try:
        # Get homework metadata
        homework = file_processor.get_homework(homework_id, user_id)

        if not homework:
            raise HTTPException(status_code=404, detail="Homework not found")

        # Get file from GridFS
        if 'file_id' not in homework:
            raise HTTPException(status_code=404, detail="File not found")

        try:
            grid_out = file_processor.fs.get(homework['file_id'])
            file_content = grid_out.read()
        except Exception as e:
            logger.error(f"[HOMEWORK] Error reading file from GridFS: {e}")
            raise HTTPException(status_code=404, detail="File not found in storage")

        file_type = homework.get('file_type', '').lower()

        # For images, return as-is
        # Note: file_type is 'image' (the category) not the extension like 'jpg'
        if file_type in ['image', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
            from fastapi.responses import Response
            content_type = grid_out.content_type or 'image/png'
            return Response(content=file_content, media_type=content_type)

        # For PDFs, render to image using PyMuPDF
        if file_type == 'pdf':
            try:
                import fitz  # PyMuPDF

                pdf_doc = fitz.open(stream=file_content, filetype="pdf")
                if page >= len(pdf_doc):
                    page = 0

                pdf_page = pdf_doc[page]
                # Render at 1.5x zoom for good quality thumbnail
                mat = fitz.Matrix(1.5, 1.5)
                pix = pdf_page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                pdf_doc.close()

                logger.info(f"[HOMEWORK] Generated thumbnail for {homework_id} page {page}")

                from fastapi.responses import Response
                return Response(
                    content=img_bytes,
                    media_type="image/png",
                    headers={'Cache-Control': 'private, max-age=3600'}
                )

            except ImportError:
                raise HTTPException(status_code=500, detail="PyMuPDF not installed for PDF thumbnails")
            except Exception as e:
                logger.error(f"[HOMEWORK] Error rendering PDF thumbnail: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to render thumbnail: {str(e)}")

        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HOMEWORK] Error in get_homework_thumbnail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get thumbnail: {str(e)}")


# ============================================================================
# Main entry point (for local development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)
