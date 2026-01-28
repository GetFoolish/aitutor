# Changelog

All notable changes to the Homework Assistant service.

## [1.1.0] - 2025-01-28

### Added
- **Comprehensive unit tests** (85+ tests, 80% coverage target)
  - API endpoint tests for all 8 endpoints
  - File processor tests (validation, extraction, storage, retrieval)
  - Homework assistant tests (question answering, Socratic method, conversation history)
  - Test configuration with pytest and coverage reporting
  - Mock-based testing for external dependencies (MongoDB, Gemini API)

- **Rate limiting** across all endpoints
  - Upload endpoint: 10 uploads per 5 minutes (prevents OCR abuse)
  - Assist endpoint: 30 questions per minute (prevents AI API abuse)
  - General endpoints: 100 requests per minute (list, get, delete, download, thumbnail)
  - Sliding window algorithm with automatic cleanup
  - Per-user tracking for authenticated requests, per-IP for unauthenticated
  - Returns HTTP 429 with Retry-After header when limits exceeded

- **Comprehensive API documentation**
  - Enhanced OpenAPI/Swagger metadata with detailed service description
  - API endpoint tags for logical grouping (Health, Upload, Management, AI Assistance, Files)
  - Detailed descriptions, examples, and response codes for all endpoints
  - Parameter descriptions and validation details
  - Rate limit information and authentication requirements
  - Interactive Swagger UI at `/docs` and ReDoc at `/redoc`

- **README.md** with complete service documentation
  - Installation and configuration instructions
  - API endpoint reference table
  - Testing guide with examples
  - Architecture overview
  - Security features documentation
  - Troubleshooting and monitoring guide

- **CHANGELOG.md** to track version history

### Improved
- **OCR processing optimization**
  - Parallel PDF page processing using ThreadPoolExecutor
  - Up to 3 concurrent pages processed simultaneously
  - Reduces multi-page PDF processing time by up to 3x
  - Pages pre-rendered then processed concurrently
  - Results sorted by page number to maintain correct order
  - Text extraction runs in thread pool to avoid blocking async event loop

- **Authentication verification**
  - Confirmed JWT authentication is correctly implemented on all endpoints
  - Verified `get_current_user` middleware is called at lines 172, 222, 265, 373 in api.py
  - Validated JWT middleware properly validates tokens and extracts user_id
  - 401 errors are expected behavior for unauthenticated requests (correct security)

- **File validation confirmation**
  - Verified file type validation for .pdf, .jpg, .png, .docx, .txt extensions
  - Confirmed 10MB file size limit enforcement
  - Clear error messages for unsupported types and oversized files

### Fixed
- None (all features were already working correctly; this release adds tests, optimizations, and documentation)

### Security
- Rate limiting prevents abuse and excessive API costs
- Authentication required on all endpoints except health check
- User isolation ensures users can only access their own homework
- File validation prevents malicious uploads
- Request timeout protection (30 seconds)

### Performance
- PDF OCR processing is now up to 3x faster for multi-page documents
- Async text extraction prevents blocking
- Parallel page processing maximizes throughput
- In-memory rate limiting with O(1) lookups

### Documentation
- Complete OpenAPI/Swagger documentation
- README with installation, usage, and testing guides
- Inline code documentation for all functions
- Test examples and coverage reports

## [1.0.0] - 2025-01-XX

### Initial Release
- Multi-format file upload (PDF, images, text, Word)
- Google Gemini Vision OCR for scanned homework
- AI-powered homework assistance with Socratic teaching method
- Conversation history (last 5 turns)
- JWT authentication
- MongoDB with GridFS storage
- File download and thumbnail generation
- CORS and middleware configuration
- Health check endpoint
