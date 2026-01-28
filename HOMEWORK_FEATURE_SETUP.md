# Homework Feature - Setup & Testing Guide

This document covers the setup and testing of the Homework Upload feature, which allows users to upload worksheets (PDF, PNG, JPG) and have the AI extract and present math problems for practice.

## Prerequisites

### Required Dependencies

The homework service requires these Python packages:

```bash
cd /path/to/aitutor-homework
source .venv/bin/activate
pip install google-generativeai pymupdf pytesseract
```

- **google-generativeai**: Gemini Vision API for OCR
- **pymupdf (fitz)**: PDF rendering and page extraction
- **pytesseract**: Fallback OCR (requires Tesseract installed on system)

### Environment Variables

Ensure `.env` has:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Get a key from: https://aistudio.google.com/apikey

**Important**: The HomeworkAssistant service loads `.env` via `dotenv`. If you see OCR failures, verify the API key is valid and not expired.

## Architecture

### Backend (HomeworkAssistant Service)

**Port**: 8004

**Key Files**:
- `services/HomeworkAssistant/api.py` - FastAPI endpoints
- `services/HomeworkAssistant/file_processor.py` - File upload, OCR, text extraction

**Flow**:
1. User uploads file → `POST /homework/upload`
2. File validated (type, size)
3. OCR extracts math problems with bounding boxes
4. File stored in MongoDB GridFS
5. Metadata + extracted text stored in `homework` collection

### Frontend (HomeworkView Component)

**Key Files**:
- `frontend/src/components/homework-view/HomeworkView.tsx` - Main component
- `frontend/src/components/homework-panel/HomeworkUpload.tsx` - Upload UI
- `frontend/src/services/homework-service.ts` - API client

**Flow**:
1. User uploads via drag-drop or file picker
2. Service extracts questions from `extracted_text`
3. Questions parsed via `parseQuestionsFromText()`
4. Each question displayed with answer input

## Supported Worksheet Types

### 1. Number-Based Worksheets
Standard math problems with printed digits:
```
3 + 4 = ___
12 - 5 = ___
```

### 2. Picture-Based Worksheets (Count & Add)
Problems with images that need counting:
```
🍎🍎🍎 + 🍎🍎 = ___  → extracted as "3 + 2 ="
```

The Gemini Vision prompt automatically detects picture-based worksheets and counts the images.

## Testing the Feature

### 1. Start the Services

```bash
# Terminal 1: Start homework service
cd /path/to/aitutor-homework
source .venv/bin/activate
python -m services.HomeworkAssistant.api

# Terminal 2: Start frontend
cd /path/to/aitutor-homework/frontend
npm run dev
```

### 2. Test Upload Flow

1. Navigate to the app (http://localhost:3000)
2. Login with test credentials
3. Click "HOMEWORK" button in header
4. Upload a test file:
   - **PDF**: Any math worksheet PDF
   - **PNG/JPG**: Picture counting worksheet

### 3. Verify Extraction

Check the service logs for OCR output:
```bash
tail -f logs/homework_service.log
```

You should see:
```
[OCR] Processing image with Gemini Vision: 600x800 pixels
[OCR] Gemini Vision extracted 281 characters
```

### 4. Test Cases

| Test | File Type | Expected Result |
|------|-----------|-----------------|
| Basic PDF | PDF with "3+4=" style problems | Questions extracted with numbers |
| Picture worksheet | PNG with counting images | Pictures counted, converted to numbers |
| Large file | >10MB | Error: "File size exceeds maximum" |
| Invalid type | .exe, .zip | Error: "Unsupported file type" |

### 5. Database Verification

Check MongoDB for stored homework:
```python
from managers.mongodb_manager import mongo_db
homework = list(mongo_db.db['homework'].find().limit(5))
for h in homework:
    print(h.get('homework_id'), h.get('file_type'))
    print(h.get('extracted_text')[:200])
```

## Troubleshooting

### "OCR library not available"
- Missing `google-generativeai` package
- Install: `pip install google-generativeai`

### "API key expired"
- Gemini API key invalid or expired
- Get new key from https://aistudio.google.com/apikey
- Update `.env` and restart service

### Questions show "+ =" without numbers
- OCR prompt not detecting picture worksheets correctly
- Check `file_processor.py` has the updated prompt that handles counting

### Thumbnail 500 errors
- Missing `pymupdf` for PDF rendering
- Install: `pip install pymupdf`

### Frontend shows old data after fix
- Vite HMR may not have reloaded
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/homework/upload` | Upload new homework file |
| GET | `/homework/list` | List user's homework |
| GET | `/homework/{id}` | Get homework details + extracted text |
| GET | `/homework/{id}/thumbnail` | Get rendered thumbnail (PNG) |
| GET | `/homework/{id}/file` | Download original file |
| DELETE | `/homework/{id}` | Delete homework |
| POST | `/homework/assist` | Ask AI question about homework |

## Recent Changes (2026-01-28)

1. **Added dotenv loading** to `api.py` - was missing, causing API key to not load
2. **Updated OCR prompt** in `file_processor.py` - now handles picture-based counting worksheets
3. **Reduced font size** in `HomeworkView.tsx` - smaller, cleaner display
4. **Left-aligned questions** - was centered, now left-aligned
