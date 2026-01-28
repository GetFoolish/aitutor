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
from shared.rate_limiter import (
    check_rate_limit,
    UPLOAD_RATE_LIMITER,
    ASSIST_RATE_LIMITER,
    GENERAL_RATE_LIMITER
)
from managers.mongodb_manager import mongo_db
from services.HomeworkAssistant.file_processor import FileProcessor
from services.HomeworkAssistant.homework_assistant import HomeworkAssistant

logger = get_logger(__name__)

# Initialize FileProcessor and HomeworkAssistant
file_processor = FileProcessor(mongo_db)
homework_assistant = HomeworkAssistant(mongo_db)

app = FastAPI(
    title="Homework Assistant API",
    description="""
## AI-Powered Homework Assistant

The Homework Assistant API provides intelligent tutoring and guidance for students' homework questions using AI.

### Features
- **Multi-format file upload**: PDF, images, text files, Word documents
- **Intelligent OCR**: Extracts text from scanned homework using Google Gemini Vision AI
- **Socratic teaching method**: Guides students to understand concepts rather than just providing answers
- **Conversation history**: Maintains context across multiple questions about the same homework
- **Secure authentication**: JWT-based user authentication
- **Rate limiting**: Prevents abuse with tiered rate limits

### Authentication
All endpoints (except `/health`) require JWT authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### Rate Limits
- **Upload**: 10 files per 5 minutes
- **Assist**: 30 questions per minute
- **General operations**: 100 requests per minute

When rate limit is exceeded, the API returns HTTP 429 with a `Retry-After` header.

### Supported File Formats
- **PDF** (.pdf) - Supports both text and scanned/image PDFs
- **Images** (.jpg, .jpeg, .png, .gif, .bmp)
- **Text files** (.txt)
- **Word documents** (.doc, .docx)

Maximum file size: 10 MB

### API Documentation
- **Interactive Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`
    """,
    version="1.0.0",
    contact={
        "name": "AI Tutor Support",
        "email": "support@aitutor.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Service health check and monitoring"
        },
        {
            "name": "Homework Upload",
            "description": "Upload and process homework files"
        },
        {
            "name": "Homework Management",
            "description": "List, retrieve, and delete homework items"
        },
        {
            "name": "AI Assistance",
            "description": "Ask questions and get tutoring help"
        },
        {
            "name": "Files",
            "description": "Download and preview homework files"
        }
    ]
)

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


class SkillDetection(BaseModel):
    skill_name: str
    skill_id: str
    confidence: float
    question_numbers: List[int]
    description: str


class AnalyzeResponse(BaseModel):
    homework_id: str
    skills: List[SkillDetection]
    total_questions: int
    analyzed_at: str


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

@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check if the Homework Assistant service is running and healthy. Does not require authentication.",
    response_description="Service health status",
    responses={
        200: {
            "description": "Service is healthy and operational",
            "content": {
                "application/json": {
                    "example": {"status": "healthy", "service": "HomeworkAssistant"}
                }
            }
        }
    }
)
def health_check():
    """Health check endpoint for service monitoring"""
    return {"status": "healthy", "service": "HomeworkAssistant"}


# ============================================================================
# Homework Upload Endpoint
# ============================================================================

@app.post(
    "/homework/upload",
    response_model=UploadResponse,
    status_code=201,
    tags=["Homework Upload"],
    summary="Upload homework file",
    description="""
Upload a homework file for AI-powered assistance.

**Supported formats:**
- PDF (.pdf) - Text or scanned homework worksheets
- Images (.jpg, .jpeg, .png, .gif, .bmp) - Photos of homework
- Text files (.txt) - Plain text homework
- Word documents (.doc, .docx) - Formatted homework assignments

**File size limit:** 10 MB

**Processing:**
1. File is validated for type and size
2. Text is extracted using OCR (for images/PDFs) or direct parsing
3. File is stored securely in GridFS
4. Homework metadata is saved with unique ID

**Rate limit:** 10 uploads per 5 minutes

Returns a `homework_id` that can be used to ask questions about this homework.
    """,
    responses={
        201: {
            "description": "File uploaded and processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "homework_id": "a1b2c3d4-5e6f-7890-abcd-ef1234567890",
                        "file_type": "pdf",
                        "status": "uploaded",
                        "filename": "math_worksheet.pdf",
                        "file_size": 245760,
                        "uploaded_at": "2025-01-28T10:00:00"
                    }
                }
            }
        },
        400: {"description": "Invalid file (unsupported type, too large, or empty)"},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Server error during file processing"}
    }
)
async def upload_homework(
    http_request: Request,
    file: UploadFile = File(..., description="Homework file to upload (PDF, image, text, or Word document)")
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

    # Check rate limit for uploads (10 uploads per 5 minutes)
    check_rate_limit(http_request, UPLOAD_RATE_LIMITER, user_id)

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
# Homework Skill Analysis Endpoint
# ============================================================================

@app.post(
    "/homework/{homework_id}/analyze",
    response_model=AnalyzeResponse,
    status_code=200,
    tags=["Homework Upload"],
    summary="Analyze homework skills",
    description="""
Analyze uploaded homework to identify math skills being practiced.

**What it does:**
- Extracts all questions from the homework
- Identifies math skills (addition, counting, multiplication, etc.)
- Maps questions to specific skills with confidence scores
- Returns skill breakdown for grading panel

**Use case:**
After uploading homework, call this endpoint to populate the "Grading & Skills" panel
with skills detected from the homework questions.

**Rate limit:** 10 analyzes per minute
    """,
    responses={
        200: {
            "description": "Skills analyzed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "homework_id": "a1b2c3d4-5e6f-7890-abcd-ef1234567890",
                        "skills": [
                            {
                                "skill_name": "Single Digit Addition",
                                "skill_id": "xd61a2ef75a00d9db",
                                "confidence": 0.95,
                                "question_numbers": [1, 2, 3, 4],
                                "description": "Adding two single-digit numbers"
                            }
                        ],
                        "total_questions": 12,
                        "analyzed_at": "2025-01-28T10:00:00"
                    }
                }
            }
        },
        404: {"description": "Homework not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Analysis error"}
    }
)
async def analyze_homework_skills(
    homework_id: str,
    http_request: Request
):
    """
    Analyze homework to detect math skills

    Examines extracted text and questions to identify specific math skills
    being practiced (e.g., addition, counting, fractions) and maps them
    to the skill tracking system.

    Args:
        homework_id: ID of uploaded homework
        http_request: HTTP request for auth

    Returns:
        AnalyzeResponse with detected skills and question mappings
    """
    user_id = get_current_user(http_request)

    # Check rate limit
    check_rate_limit(http_request, UPLOAD_RATE_LIMITER, user_id)

    try:
        # Get homework from database
        homework = mongo_db.homework.find_one({
            "homework_id": homework_id,
            "user_id": user_id
        })

        if not homework:
            raise HTTPException(status_code=404, detail="Homework not found")

        extracted_text = homework.get("extracted_text", "")

        if not extracted_text or extracted_text.startswith("["):
            # No valid text extracted
            logger.warning(f"[HOMEWORK] No valid text to analyze for {homework_id}")
            return AnalyzeResponse(
                homework_id=homework_id,
                skills=[],
                total_questions=0,
                analyzed_at=datetime.now().isoformat()
            )

        # Use Gemini to analyze skills
        import google.generativeai as genai
        gemini_api_key = os.environ.get('GEMINI_API_KEY')

        if not gemini_api_key:
            logger.error("[HOMEWORK] GEMINI_API_KEY not set")
            raise HTTPException(status_code=500, detail="AI service not configured")

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = f"""Analyze these homework questions and identify the math skills being practiced.

HOMEWORK TEXT:
{extracted_text}

For each distinct skill, provide:
1. Skill name (e.g., "Single Digit Addition", "Counting Objects")
2. Question numbers that use this skill
3. Confidence score (0.0-1.0)
4. Brief description

Output as JSON array:
[
  {{
    "skill_name": "Single Digit Addition",
    "question_numbers": [1, 2, 3],
    "confidence": 0.95,
    "description": "Adding two single-digit numbers"
  }}
]

IMPORTANT: Only output the JSON array, nothing else."""

        response = model.generate_content(prompt)
        skills_text = response.text.strip()

        # Parse JSON response
        import json
        import re

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', skills_text, re.DOTALL)
        if json_match:
            skills_text = json_match.group(1)
        elif not skills_text.startswith('['):
            # Try to find JSON array in text
            json_match = re.search(r'\[.*\]', skills_text, re.DOTALL)
            if json_match:
                skills_text = json_match.group(0)

        try:
            skills_data = json.loads(skills_text)
        except json.JSONDecodeError as e:
            logger.error(f"[HOMEWORK] Failed to parse skills JSON: {e}\nResponse: {skills_text}")
            skills_data = []

        # Map to skill IDs (simple mapping for now)
        skill_id_map = {
            "single digit addition": "xd61a2ef75a00d9db",
            "counting": "counting_basic",
            "counting objects": "counting_objects",
            "double digit addition": "double_digit_add",
            "subtraction": "subtraction_basic",
            "multiplication": "multiplication_basic",
        }

        skills = []
        total_questions = 0

        for skill_data in skills_data:
            skill_name = skill_data.get("skill_name", "Unknown")
            skill_key = skill_name.lower()
            skill_id = skill_id_map.get(skill_key, f"skill_{skill_key.replace(' ', '_')}")

            question_nums = skill_data.get("question_numbers", [])
            total_questions = max(total_questions, max(question_nums) if question_nums else 0)

            skills.append(SkillDetection(
                skill_name=skill_name,
                skill_id=skill_id,
                confidence=skill_data.get("confidence", 0.8),
                question_numbers=question_nums,
                description=skill_data.get("description", "")
            ))

        # Update homework with analyzed skills
        mongo_db.homework.update_one(
            {"homework_id": homework_id},
            {
                "$set": {
                    "analyzed_skills": [skill.dict() for skill in skills],
                    "analyzed_at": datetime.now().isoformat()
                }
            }
        )

        logger.info(f"[HOMEWORK] Analyzed {len(skills)} skills from {homework_id}")

        return AnalyzeResponse(
            homework_id=homework_id,
            skills=skills,
            total_questions=total_questions,
            analyzed_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HOMEWORK] Error analyzing skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze skills: {str(e)}")


# ============================================================================
# Homework Assistance Endpoint
# ============================================================================

@app.post(
    "/homework/assist",
    response_model=AssistResponse,
    status_code=200,
    tags=["AI Assistance"],
    summary="Ask homework question",
    description="""
Get AI-powered tutoring help for your homework.

**Teaching approach:**
Uses the Socratic method to guide students toward understanding rather than just providing answers. The AI tutor will:
- Ask clarifying questions to understand your thinking
- Break down complex problems into simpler steps
- Guide you to discover the solution yourself
- Provide hints and explanations without giving direct answers

**Conversation history:**
Maintains context of your previous questions (last 5 turns) for more coherent tutoring.

**Rate limit:** 30 questions per minute

**Example workflow:**
1. Upload homework file → Get `homework_id`
2. Ask question: "I don't understand problem 3"
3. AI responds with guiding questions
4. Continue conversation with follow-up questions
    """,
    responses={
        200: {
            "description": "AI response generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Great question! Let's think about this step by step. What do you know about addition? Can you tell me what 2+2 means in your own words?",
                        "homework_id": "a1b2c3d4-5e6f-7890-abcd-ef1234567890",
                        "timestamp": "2025-01-28T10:05:00"
                    }
                }
            }
        },
        400: {"description": "Invalid request"},
        401: {"description": "Authentication required"},
        404: {"description": "Homework not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "AI service error"}
    }
)
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

    # Check rate limit for AI assistance (30 questions per minute)
    check_rate_limit(http_request, ASSIST_RATE_LIMITER, user_id)

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

@app.get(
    "/homework/list",
    response_model=HomeworkListResponse,
    status_code=200,
    tags=["Homework Management"],
    summary="List all homework",
    description="""
Retrieve a list of all homework files uploaded by the authenticated user.

**Returns:**
- Homework metadata (filename, type, size, status)
- Upload timestamp
- Homework ID for asking questions

**Does NOT include:**
- Full extracted text content
- Conversation history

Sorted by upload date (most recent first). Limited to 50 most recent items.

**Rate limit:** 100 requests per minute
    """,
    responses={
        200: {
            "description": "List retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "homework_items": [
                            {
                                "homework_id": "a1b2c3d4-...",
                                "filename": "math_worksheet.pdf",
                                "file_type": "pdf",
                                "file_size": 245760,
                                "status": "uploaded",
                                "uploaded_at": "2025-01-28T10:00:00"
                            }
                        ],
                        "total": 1
                    }
                }
            }
        },
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Server error"}
    }
)
async def list_homework(http_request: Request):
    """
    List all homework for the authenticated user

    Returns a list of uploaded homework files with metadata.
    Does not include full extracted text or conversation history.

    Returns:
        HomeworkListResponse with array of homework items and total count
    """
    user_id = get_current_user(http_request)

    # Check rate limit for general API calls (100 requests per minute)
    check_rate_limit(http_request, GENERAL_RATE_LIMITER, user_id)

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

@app.get(
    "/homework/{homework_id}",
    response_model=HomeworkDetailResponse,
    status_code=200,
    tags=["Homework Management"],
    summary="Get homework details",
    description="""
Retrieve detailed information about a specific homework assignment.

**Includes:**
- Homework metadata (filename, type, size, status)
- Full conversation history with AI tutor
- Extracted text content from the file (for reference)

**Use cases:**
- Review past conversations
- Check what was extracted from the file
- Get homework metadata for display

**Rate limit:** 100 requests per minute
    """,
    responses={
        200: {
            "description": "Homework details retrieved successfully"
        },
        401: {"description": "Authentication required"},
        404: {"description": "Homework not found or access denied"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Server error"}
    }
)
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

    # Check rate limit for general API calls (100 requests per minute)
    check_rate_limit(http_request, GENERAL_RATE_LIMITER, user_id)

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

@app.delete(
    "/homework/{homework_id}",
    response_model=DeleteResponse,
    status_code=200,
    tags=["Homework Management"],
    summary="Delete homework",
    description="""
Permanently delete a homework assignment and its associated file.

**What gets deleted:**
- Homework metadata (filename, status, timestamps)
- Conversation history with AI tutor
- Original uploaded file from GridFS storage
- Extracted text content

**Warning:** This action cannot be undone.

**Rate limit:** 100 requests per minute
    """,
    responses={
        200: {
            "description": "Homework deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Homework a1b2c3d4-... deleted successfully"
                    }
                }
            }
        },
        401: {"description": "Authentication required"},
        404: {"description": "Homework not found or already deleted"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Server error during deletion"}
    }
)
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

    # Check rate limit for general API calls (100 requests per minute)
    check_rate_limit(http_request, GENERAL_RATE_LIMITER, user_id)

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

@app.get(
    "/homework/{homework_id}/file",
    tags=["Files"],
    summary="Download homework file",
    description="""
Download the original uploaded homework file.

**Returns:**
- Raw file content with appropriate MIME type
- Content-Disposition header for inline display
- Cache-Control header (private, 1 hour)

**Use cases:**
- Preview PDFs in browser
- Display uploaded images
- Download original file

**Rate limit:** 100 requests per minute
    """,
    responses={
        200: {
            "description": "File retrieved successfully",
            "content": {
                "application/pdf": {},
                "image/jpeg": {},
                "image/png": {},
                "text/plain": {},
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        },
        401: {"description": "Authentication required"},
        404: {"description": "Homework or file not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Server error reading file"}
    }
)
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

    # Check rate limit for general API calls (100 requests per minute)
    check_rate_limit(http_request, GENERAL_RATE_LIMITER, user_id)

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


@app.get(
    "/homework/{homework_id}/thumbnail",
    tags=["Files"],
    summary="Get homework thumbnail",
    description="""
Get a PNG thumbnail image of a homework file.

**For PDFs:**
- Renders the specified page as a PNG image at 1.5x zoom
- Useful for displaying PDF pages in web UI with overlay annotations
- Page parameter is 0-indexed (0 = first page)

**For images:**
- Returns the original image as-is
- No rendering needed

**Benefits:**
- Consistent PNG format for all file types
- CSS percentage positioning works correctly on thumbnails
- Faster loading than full PDF viewer

**Parameters:**
- `page`: Page number to render (default: 0, first page)

**Rate limit:** 100 requests per minute
    """,
    responses={
        200: {
            "description": "Thumbnail generated successfully",
            "content": {
                "image/png": {}
            }
        },
        400: {"description": "Unsupported file type for thumbnails"},
        401: {"description": "Authentication required"},
        404: {"description": "Homework or file not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Error rendering thumbnail (PyMuPDF not installed)"}
    }
)
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

    # Check rate limit for general API calls (100 requests per minute)
    check_rate_limit(http_request, GENERAL_RATE_LIMITER, user_id)

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
