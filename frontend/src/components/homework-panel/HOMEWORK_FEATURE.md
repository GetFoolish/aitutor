# Homework Feature Implementation

## Overview
The Homework feature allows students to upload their homework files (worksheets, assignments, etc.) and get AI-powered tutoring assistance. The AI tutor extracts text from uploaded files and provides contextual help.

## Supported File Formats
| Format | Extensions | Max Size |
|--------|------------|----------|
| PDF | .pdf | 10MB |
| Images | .jpg, .jpeg, .png | 10MB |
| Word Documents | .doc, .docx | 10MB |
| Text Files | .txt | 10MB |

## Architecture

### Frontend Components
- **`HomeworkPanel.tsx`** - Main panel component that orchestrates file upload and AI integration
- **`HomeworkUpload.tsx`** - File upload UI with drag-and-drop support
- **`HomeworkChat.tsx`** - Chat interface for homework-related conversations

### Backend Service
- **HomeworkAssistant API** - FastAPI service running on port `8004`
- Handles file uploads, text extraction (OCR for images, PDF parsing)
- Stores homework data in MongoDB

## Local Development Setup

### 1. Start the HomeworkAssistant Service
```bash
cd services/HomeworkAssistant
python api.py
```
The service will start on `http://localhost:8004`

### 2. Verify Service is Running
```bash
curl http://localhost:8004/health
```

### 3. Start the Frontend
```bash
cd frontend
npm run dev
```

### 4. Environment Variables
Ensure these are set in your `.env` file:
```env
VITE_HOMEWORK_API_URL=http://localhost:8004
```

## Feature Flow

1. **User clicks "HOMEWORK" button** in the FloatingControlPanel
2. **Homework panel opens** - positioned relative to the floating panel location
3. **User uploads a file** via drag-and-drop or file picker
4. **File is sent to HomeworkAssistant API** for processing
5. **Text is extracted** from the file (OCR for images, parsing for PDFs)
6. **Extracted content is injected** into the AI tutor's context
7. **AI tutor can now help** with the specific homework content

## UI Components

### FloatingControlPanel Integration
The Homework button is located in the bottom action bar of the FloatingControlPanel:
- **Icon**: Upload icon from lucide-react
- **Color**: Yellow (#FFD93D) when active
- **Position**: Replaces the "MORE" button

### Homework Panel Positioning
The panel automatically positions itself based on the floating control panel's location:
- Opens to the **right** if panel is on the left side of screen
- Opens to the **left** if panel is on the right side of screen
- Aligns **top** or **bottom** based on vertical position

## API Endpoints

### HomeworkAssistant Service (Port 8004)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/homework/upload` | POST | Upload homework file |
| `/homework/list` | GET | List user's homework |
| `/homework/{id}/file` | GET | Download homework file |
| `/homework/{id}` | DELETE | Delete homework |

## Testing the Feature

1. Open the app at `http://localhost:3000`
2. Log in with your credentials
3. Click the yellow **HOMEWORK** button in the floating control panel
4. Upload a homework file (try a math worksheet image or PDF)
5. The AI tutor will automatically receive the homework context
6. Start a tutoring session to get help with the uploaded homework

## Troubleshooting

### "Network Error" when uploading
- Ensure HomeworkAssistant service is running on port 8004
- Check CORS settings allow localhost:3000

### File upload fails
- Verify file is under 10MB
- Check file format is supported
- Look at browser console for detailed error

### AI tutor doesn't see homework
- Ensure tutor session is connected before or after upload
- Check console logs for "Successfully sent homework to tutor" message

## Files Changed
- `frontend/src/components/floating-control-panel/FloatingControlPanel.tsx` - Added homework button and panel
- `frontend/src/components/homework-panel/HomeworkPanel.tsx` - Main panel component
- `frontend/src/components/homework-panel/HomeworkUpload.tsx` - File upload component
- `frontend/src/components/homework-panel/HomeworkChat.tsx` - Chat component
- `services/HomeworkAssistant/` - Backend API service
