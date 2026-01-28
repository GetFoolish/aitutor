# Homework Assistant Service

AI-powered homework tutoring service using Google Gemini Vision for OCR and intelligent question answering.

## Features

### Core Functionality
- **Multi-format file upload**: PDF, images, text files, Word documents
- **Intelligent OCR**: Extracts text from scanned homework using Google Gemini Vision AI
- **Socratic teaching method**: Guides students to understand concepts rather than just providing answers
- **Conversation history**: Maintains context across multiple questions (last 5 turns)
- **Secure authentication**: JWT-based user authentication
- **Rate limiting**: Prevents abuse with tiered rate limits

### Recent Improvements (2025-01-28)

✅ **Authentication** - Verified JWT authentication is correctly implemented on all endpoints
✅ **File Validation** - Comprehensive file type and size validation (10MB limit)
✅ **Unit Tests** - Added 85+ unit tests with 80% coverage target
✅ **Rate Limiting** - Multi-tier rate limiting (upload: 10/5min, assist: 30/min, general: 100/min)
✅ **OCR Optimization** - Parallel PDF page processing (3x faster for multi-page documents)
✅ **API Documentation** - Comprehensive OpenAPI/Swagger docs with examples

## API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8004/docs`
- **ReDoc**: `http://localhost:8004/redoc`
- **OpenAPI JSON**: `http://localhost:8004/openapi.json`

### Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/health` | GET | Service health check | N/A |
| `/homework/upload` | POST | Upload homework file | 10 per 5 min |
| `/homework/list` | GET | List all homework | 100 per min |
| `/homework/{id}` | GET | Get homework details | 100 per min |
| `/homework/{id}` | DELETE | Delete homework | 100 per min |
| `/homework/{id}/file` | GET | Download original file | 100 per min |
| `/homework/{id}/thumbnail` | GET | Get PNG thumbnail | 100 per min |
| `/homework/assist` | POST | Ask homework question | 30 per min |

## Installation

### Prerequisites
- Python 3.8+
- MongoDB with GridFS support
- Google Gemini API key

### Dependencies

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```bash
# Google Gemini API (Required for OCR)
GEMINI_API_KEY=your_gemini_api_key

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=ai_tutor

# Authentication
JWT_SECRET=your_secure_random_secret_key

# Optional: Configure allowed origins
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Running the Service

### Development Mode

```bash
python api.py
```

Service will start on `http://localhost:8004`

### Production Mode

```bash
uvicorn api:app --host 0.0.0.0 --port 8004 --workers 4
```

## Testing

### Run Unit Tests

```bash
# Install test dependencies
cd tests
pip install -r requirements.txt

# Run tests with coverage
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py

# Generate HTML coverage report
pytest --cov-report=html
```

### Test Coverage

Current test suite includes 85+ tests covering:
- ✅ All API endpoints (upload, assist, list, get, delete, download, thumbnail)
- ✅ File validation (type, size, extension)
- ✅ Text extraction (PDF, image, text, Word)
- ✅ Homework storage and retrieval
- ✅ Question answering and conversation history
- ✅ Error handling and edge cases
- ✅ CORS and middleware configuration

Target coverage: 80%

### Integration Tests

```bash
# Start MongoDB
docker run -d -p 27017:27017 mongo:latest

# Set environment variables
export GEMINI_API_KEY=your_key
export MONGODB_URI=mongodb://localhost:27017
export JWT_SECRET=test_secret

# Run integration tests
pytest tests/ -v --integration
```

## Architecture

### File Processing Pipeline

1. **Upload** → File validation (type, size)
2. **Storage** → GridFS for file content
3. **Extraction** → OCR with Gemini Vision (parallel for PDFs)
4. **Database** → MongoDB for metadata and conversation history

### Rate Limiting

Uses sliding window algorithm with in-memory storage:
- **Per-user** tracking for authenticated requests
- **Per-IP** tracking for unauthenticated requests
- Automatic cleanup of old entries
- Returns 429 with `Retry-After` header when exceeded

### OCR Optimization

- **Parallel processing**: Up to 3 concurrent PDF pages
- **Async execution**: Text extraction runs in thread pool
- **Smart fallbacks**: PyPDF2 for text PDFs, Tesseract for images

## Supported File Formats

| Format | Extensions | Processing Method |
|--------|-----------|-------------------|
| PDF | `.pdf` | Gemini Vision (parallel pages) or PyPDF2 |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp` | Gemini Vision or Tesseract OCR |
| Text | `.txt` | Direct UTF-8 decoding |
| Word | `.doc`, `.docx` | python-docx |

**File size limit**: 10 MB

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created (file uploaded) |
| 400 | Bad request (invalid file, validation error) |
| 401 | Unauthorized (missing/invalid JWT token) |
| 404 | Not found (homework doesn't exist) |
| 429 | Too many requests (rate limit exceeded) |
| 500 | Internal server error |
| 504 | Gateway timeout (request took > 30s) |

## Security

- **Authentication**: JWT tokens required for all endpoints (except `/health`)
- **Rate limiting**: Prevents abuse and API cost overruns
- **File validation**: Strict type and size checking
- **User isolation**: Users can only access their own homework
- **CORS**: Configurable allowed origins
- **Timeout protection**: 30-second request timeout

## Monitoring

### Health Check

```bash
curl http://localhost:8004/health
```

Response:
```json
{
  "status": "healthy",
  "service": "HomeworkAssistant"
}
```

### Logs

The service uses structured logging with different levels:
- `INFO`: Normal operations (uploads, questions, deletions)
- `WARNING`: Rate limits, validation errors
- `ERROR`: Unexpected failures, API errors

## Development

### Adding New Features

1. Update `api.py` with new endpoint
2. Add corresponding tests in `tests/test_api.py`
3. Update OpenAPI documentation with tags and descriptions
4. Run tests to ensure coverage target is met
5. Update this README

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Keep functions focused and under 50 lines
- Use descriptive variable names

## License

MIT License - See LICENSE file for details

## Support

For issues or questions, please open an issue on the repository.
