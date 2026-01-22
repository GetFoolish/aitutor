# Homework Feature Testing Guide

This document explains how to test the AI Tutor Homework feature locally.

## Prerequisites

- Python 3.10+ with pip
- Node.js 18+ with npm
- MongoDB running locally or accessible
- Tesseract OCR installed (`brew install tesseract` on macOS)
- Valid Google Gemini API credentials configured in Auth service

## Quick Start

### 1. Start All Services

```bash
cd /Users/gaganarora/Desktop/ai_tutor
./run_tutor.sh
```

This starts:
- **Auth Service** (port 8003) - Handles authentication and Gemini tokens
- **Homework Service** (port 8004) - Handles file uploads and OCR
- **Frontend** (port 3001) - React app with tutor UI

### 2. Alternative: Start Services Individually

If you need to debug specific services:

```bash
# Terminal 1: Auth Service
cd services/AuthService
FRONTEND_URL=http://localhost:3001 python app.py

# Terminal 2: Homework Service
cd services/HomeworkAssistant
python app.py

# Terminal 3: Frontend
cd frontend
npm run dev
```

## Port Configuration

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3001 | React UI |
| Auth | 8003 | OAuth & Gemini tokens |
| Homework | 8004 | File upload & OCR |
| DASH | 8000 | Dashboard API (optional) |
| TeachingAssistant | 8002 | Session tracking (optional) |

**Note:** Frontend is configured for port 3001 in `vite.config.ts`. If port 3001 is in use, Vite will auto-select another port.

## Testing the Homework Feature

### Step 1: Login
1. Open http://localhost:3001
2. Login with Google OAuth
3. You should see the main tutor interface

### Step 2: Grant Microphone Permission
1. When prompted, allow microphone access
2. Check browser console for: `[Audio] Microphone permission granted`
3. If denied, go to Chrome Settings > Site Settings > Microphone and allow localhost:3001

### Step 3: Upload Homework
1. Click the **Homework** section in the left sidebar (yellow header)
2. Click **Upload Homework** button
3. Select a file:
   - **PDF**: Division worksheets, math problems (text extracted via PyPDF2)
   - **Images**: PNG/JPG of worksheets (text extracted via Tesseract OCR)
   - **Text**: Plain .txt files
   - **Word**: .doc/.docx documents

### Step 4: Verify in Console
Open browser DevTools (F12) and watch for these logs:

```
[Homework] Uploading file: your-file.pdf
[Homework] Upload successful, homework_id: xxx
[HOMEWORK CONTEXT SENT TO TUTOR]: ...extracted content...
[TUTOR AUDIO] Received xxx bytes  <-- Tutor is responding!
[USER AUDIO] Sending xxx bytes    <-- Your voice is being captured
```

### Step 5: Talk to the Tutor
1. The tutor should acknowledge the homework and start helping
2. Speak to ask questions about specific problems
3. The tutor uses Socratic method - guides you with questions

## Supported File Types

| Type | Extensions | Extraction Method |
|------|------------|-------------------|
| PDF | .pdf | PyPDF2 text extraction |
| Images | .jpg, .jpeg, .png, .gif, .bmp | Tesseract OCR |
| Text | .txt | Direct read |
| Word | .doc, .docx | python-docx |

**Max file size:** 10MB

## Troubleshooting

### "NotFoundError: Requested device not found"
- **Cause:** Browser can't access microphone
- **Fix:**
  1. System Preferences > Privacy & Security > Microphone > Enable for Chrome
  2. Chrome site settings for localhost:3001 > Microphone > Allow
  3. Refresh page

### Session disconnects after ~10 minutes
- **Cause:** Gemini Live API has session limits
- **Status:** Session resumption is now enabled - reconnecting should preserve context

### OCR returns "[Image file: XXXxXXX pixels - No text detected]"
- **Cause:** Tesseract can't read the image
- **Fix:** Ensure image has clear, high-contrast text. Try a cleaner scan.

### Port already in use
- **Fix:** Kill existing processes
  ```bash
  lsof -ti :3001 | xargs kill -9
  lsof -ti :8003 | xargs kill -9
  lsof -ti :8004 | xargs kill -9
  ```

### Auth redirect goes to wrong port
- **Fix:** Start auth service with correct FRONTEND_URL:
  ```bash
  FRONTEND_URL=http://localhost:3001 python app.py
  ```

## Changes Made in This Branch

### Frontend Changes
1. **FloatingControlPanel.tsx** - Better audio device initialization, logging for audio flow
2. **GradingSidebar.tsx** - Homework section added above Grading & Skills
3. **audio-recorder.ts** - Fallback to default mic if specific device fails
4. **tutor-client.ts** - Added transcript logging for debugging
5. **tutor-service.ts** - Session resumption enabled, homework context injection
6. **use-tutor.ts** - Audio logging for debugging
7. **vite.config.ts** - Port set to 3001

### Backend Changes
1. **file_processor.py** - Implemented actual OCR with pytesseract (was placeholder)

## Console Logs to Verify Success

When everything works, you should see:

```
[Audio] Microphone permission granted
[Audio] Found 2 audio input devices
[Audio] Selected default device: MacBook Pro Microphone
[AudioRecorder] Successfully started recording
[Homework] Uploading file: Division_Worksheet.pdf
[Homework] Upload successful
[HOMEWORK CONTEXT SENT TO TUTOR]: ...
[TUTOR AUDIO] Received 46080 bytes
[USER AUDIO] Sending 5464 bytes to Gemini
[Session] Got resumption handle for reconnection
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│   Frontend      │────▶│   Auth Service   │
│   (port 3001)   │     │   (port 8003)    │
└────────┬────────┘     └──────────────────┘
         │                      │
         │              Gemini Token
         │                      │
         ▼                      ▼
┌─────────────────┐     ┌──────────────────┐
│  Gemini Live    │◀────│   Homework       │
│  API (Google)   │     │   Service        │
└─────────────────┘     │   (port 8004)    │
                        └──────────────────┘
                               │
                        ┌──────┴──────┐
                        │   MongoDB   │
                        │  + GridFS   │
                        └─────────────┘
```
