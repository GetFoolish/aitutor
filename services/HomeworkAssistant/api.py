import sys
import os
import asyncio
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.auth_middleware import get_current_user
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS
from shared.timing_middleware import UnpluggedTimingMiddleware
from shared.logging_config import get_logger
from managers.mongodb_manager import mongo_db
from services.HomeworkAssistant.file_processor import FileProcessor

logger = get_logger(__name__)

# Initialize FileProcessor
file_processor = FileProcessor(mongo_db)

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
# Main entry point (for local development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)
