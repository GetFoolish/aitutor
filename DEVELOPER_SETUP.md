# Developer Setup Guide - Homework Feature

This guide walks you through testing the AI Tutor Homework feature locally from the `v1-homework` branch.

## Clone & Checkout

```bash
git clone https://github.com/GetFoolish/aitutor.git
cd aitutor
git checkout v1-homework
```

## Prerequisites

| Requirement | Version | Installation |
|-------------|---------|--------------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 20+ | `nvm install 20` or [nodejs.org](https://nodejs.org/) |
| MongoDB | Atlas or local | [MongoDB Atlas](https://cloud.mongodb.com) (free tier works) |
| Tesseract OCR | Latest | `brew install tesseract` (macOS) / `apt install tesseract-ocr` (Linux) |

## Setup Steps

### 1. Create Python Virtual Environment

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install --force
cd ..
```

### 3. Configure Environment Variables

```bash
./setup-local-env.sh
```

Then edit the `.env` file with your credentials:

```bash
# Required - Get from https://cloud.mongodb.com
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/ai_tutor

# Required - Get from https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_API_KEY=your_gemini_api_key

# Required - Get from https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret

# Required - Generate with: node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
JWT_SECRET=your_jwt_secret_min_32_chars
```

### 4. Start All Services

```bash
./run_tutor.sh
```

This starts:
- **Frontend** - http://localhost:3001
- **Auth Service** - http://localhost:8003
- **Homework Service** - http://localhost:8004
- DASH API, TeachingAssistant, etc.

## Testing the Homework Feature

### Step 1: Login
1. Open http://localhost:3001
2. Click "Sign in with Google"
3. Complete OAuth flow

### Step 2: Allow Microphone Access
- Grant microphone permission when prompted
- Check console for: `[Audio] Microphone permission granted`

### Step 3: Upload Homework
1. Look for the **Homework** section in the left sidebar (yellow header)
2. Click **Upload Homework**
3. Select a file:
   - PDF (math worksheets, problem sets)
   - Images (PNG/JPG of handwritten work)
   - Text files (.txt)
   - Word docs (.doc/.docx)

### Step 4: Verify It Works
Open browser DevTools (F12 > Console) and look for:

```
[Homework] Uploading file: your-file.pdf
[Homework] Upload successful, homework_id: xxx
[HOMEWORK CONTEXT SENT TO TUTOR]: ...extracted content...
[TUTOR AUDIO] Received xxx bytes
```

### Step 5: Talk to the Tutor
- The tutor acknowledges your homework and offers to help
- Ask questions about specific problems
- The tutor uses Socratic method (guides with questions, doesn't give direct answers)

## Troubleshooting

### Microphone Not Working
```
NotFoundError: Requested device not found
```
**Fix:**
1. macOS: System Preferences > Privacy & Security > Microphone > Enable Chrome
2. Chrome: Site Settings > localhost:3001 > Microphone > Allow
3. Refresh the page

### Port Already in Use
```bash
# Kill processes on specific ports
lsof -ti :3001 | xargs kill -9
lsof -ti :8003 | xargs kill -9
lsof -ti :8004 | xargs kill -9
```

### OCR Returns No Text
If you see `[Image file: XXXxXXX pixels - No text detected]`:
- Ensure Tesseract is installed: `tesseract --version`
- Try a clearer, higher-contrast image
- PDFs with selectable text work better than scanned images

### Auth Redirect Wrong Port
Ensure `FRONTEND_URL` matches in `.env`:
```bash
FRONTEND_URL=http://localhost:3001
```

## Running Services Individually (for debugging)

```bash
# Terminal 1: Auth Service
cd services/AuthService
FRONTEND_URL=http://localhost:3001 python app.py

# Terminal 2: Homework Service
cd services/HomeworkAssistant
python api.py

# Terminal 3: Frontend
cd frontend
npm run dev
```

## Service Ports Reference

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3001 | React UI with tutor |
| Auth | 8003 | OAuth & Gemini tokens |
| Homework | 8004 | File upload & OCR |
| DASH | 8000 | Dashboard API |
| TeachingAssistant | 8002 | Session tracking |

## Logs

All service logs are written to the `logs/` directory:
- `logs/frontend.log`
- `logs/auth_service.log`
- `logs/homework_service.log`
- `logs/dash_api.log`

## What's New in This Branch

### Frontend
- Homework upload panel in sidebar
- HomeworkView component for displaying extracted content
- Audio recorder improvements (microphone fallback)
- Session resumption for Gemini Live API

### Backend
- `services/HomeworkAssistant/` - New service for file processing
- Tesseract OCR integration for images
- PyPDF2 text extraction for PDFs
- python-docx for Word documents

## Questions?

Open an issue at https://github.com/GetFoolish/aitutor/issues
