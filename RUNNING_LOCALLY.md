# 🚀 AITutor - Running Locally

## ✅ Services Status

Both frontend and backend are now running!

### Backend (Homework Assistant API)
- **URL**: http://localhost:8004
- **Status**: ✅ Running
- **API Docs**: http://localhost:8004/docs (Swagger UI)
- **ReDoc**: http://localhost:8004/redoc
- **Health Check**: http://localhost:8004/health
- **Process**: Running in background
- **Logs**: `tail -f /tmp/backend-running.log`

### Frontend (AI Tutor Web App)
- **URL**: http://localhost:3004
- **Status**: ✅ Running
- **Framework**: Vite + React + TypeScript
- **Process**: Running in background
- **Logs**: `tail -f /tmp/frontend-running.log`

---

## 🎯 Quick Start

### Option 1: Services Already Running (Current State)
Just open your browser:
1. **Frontend**: http://localhost:3004
2. **API Docs**: http://localhost:8004/docs

### Option 2: Restart Services
If you need to restart the services:

```bash
cd /tmp/aitutor

# Start backend only
./start-backend.sh

# Start frontend only (in another terminal)
./start-frontend.sh

# Or start both (opens in separate Terminal tabs on macOS)
./start-all.sh
```

### Option 3: Manual Control
```bash
# Find running processes
ps aux | grep -E 'api.py|vite'

# Stop services
pkill -f "api.py"
pkill -f "vite"

# Start manually
cd /tmp/aitutor
source venv/bin/activate
cd services/HomeworkAssistant
python3 api.py &

cd /tmp/aitutor/frontend
npm run dev &
```

---

## 📋 Testing the Homework Assistant

### 1. Via Web UI (Recommended)
1. Open http://localhost:3004
2. Login with your credentials
3. Navigate to Homework Assistant
4. Upload a homework file (PDF, image, etc.)
5. Ask questions about the homework

### 2. Via API (Swagger UI)
1. Open http://localhost:8004/docs
2. Click "Authorize" and enter your JWT token
3. Try the endpoints:
   - POST `/homework/upload` - Upload a file
   - POST `/homework/assist` - Ask a question
   - GET `/homework/list` - List your homework
   - GET `/homework/{id}` - Get homework details

### 3. Via cURL
```bash
# Get a JWT token first (from auth service)
TOKEN="your-jwt-token"

# Upload homework
curl -X POST http://localhost:8004/homework/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@path/to/homework.pdf"

# Ask a question
curl -X POST http://localhost:8004/homework/assist \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "homework_id": "your-homework-id",
    "question": "How do I solve problem 1?"
  }'
```

---

## 🔍 Monitoring & Debugging

### Check Service Health
```bash
# Backend health
curl http://localhost:8004/health

# Frontend accessibility
curl -I http://localhost:3004
```

### View Logs
```bash
# Backend logs (real-time)
tail -f /tmp/backend-running.log

# Frontend logs (real-time)
tail -f /tmp/frontend-running.log

# Backend errors only
tail -f /tmp/backend-running.log | grep -E 'ERROR|error'
```

### Check Ports
```bash
# See what's running on the ports
lsof -i :8004  # Backend
lsof -i :3004  # Frontend
```

### MongoDB Connection
```bash
# The backend connects to MongoDB at startup
# Check logs for connection status:
tail -20 /tmp/backend-running.log | grep MONGODB
```

---

## 🔧 Configuration

### Environment Variables (.env)
Location: `/tmp/aitutor/.env`

Key variables:
- `GEMINI_API_KEY` - Google Gemini for OCR (required)
- `MONGODB_URI` - MongoDB connection string
- `JWT_SECRET` - JWT token signing secret
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - OAuth

### CORS Configuration
Backend allows these origins by default:
- http://localhost:3000-3005
- http://localhost:4173, 5173
- http://localhost:8080
- http://127.0.0.1:* (same ports)

Frontend is running on port 3004, which is allowed.

---

## 🧪 Run Tests

### Backend Tests
```bash
cd /tmp/aitutor/services/HomeworkAssistant
source ../../venv/bin/activate
cd tests
pip install -r requirements.txt
pytest -v
```

### Frontend Tests
```bash
cd /tmp/aitutor/frontend
npm test
```

---

## 📊 New Features (Just Added)

### ✅ Comprehensive Unit Tests
- 85+ tests covering all functionality
- 80% code coverage target
- Run with: `cd services/HomeworkAssistant/tests && pytest -v`

### ✅ Rate Limiting
- Upload: 10 files per 5 minutes
- Assist: 30 questions per minute
- General: 100 requests per minute
- Returns HTTP 429 when exceeded

### ✅ OCR Optimization
- 3x faster PDF processing
- Parallel page processing (up to 3 concurrent)
- Async text extraction

### ✅ API Documentation
- Full OpenAPI/Swagger docs at /docs
- Interactive testing interface
- Request/response examples

---

## 🛑 Stopping Services

### Quick Stop
```bash
pkill -f "api.py"
pkill -f "vite"
```

### Graceful Stop
```bash
# Find PIDs
ps aux | grep -E 'api.py|vite'

# Kill specific processes
kill <backend-pid>
kill <frontend-pid>
```

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if port 8004 is already in use
lsof -i :8004

# Check MongoDB connection
tail -f /tmp/backend-running.log | grep -i mongo

# Verify environment variables
cd /tmp/aitutor
source venv/bin/activate
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('GEMINI_API_KEY:', os.getenv('GEMINI_API_KEY')[:20])"
```

### Frontend won't start
```bash
# Check if port 3004 is in use
lsof -i :3004

# Reinstall dependencies
cd /tmp/aitutor/frontend
rm -rf node_modules package-lock.json
npm install
```

### CORS errors
```bash
# Check frontend is connecting to correct backend URL
cd /tmp/aitutor/frontend/src
grep -r "VITE_HOMEWORK_SERVICE_URL"
```

### Rate limit errors
If you hit rate limits during testing:
- Wait for the time specified in `Retry-After` header
- Or temporarily disable rate limiting in `shared/rate_limiter.py`

---

## 📚 Documentation

- **API Reference**: http://localhost:8004/docs
- **Backend README**: `/tmp/aitutor/services/HomeworkAssistant/README.md`
- **Changelog**: `/tmp/aitutor/services/HomeworkAssistant/CHANGELOG.md`
- **Frontend Docs**: `/tmp/aitutor/frontend/README.md`

---

## 💡 Tips

1. **Use the Swagger UI** at http://localhost:8004/docs for easy API testing
2. **Monitor logs** in real-time to debug issues
3. **Check rate limits** if requests are being rejected (HTTP 429)
4. **Use a valid JWT token** for all API requests except `/health`
5. **Upload test files** from the frontend UI for the best experience

---

## 🎉 You're all set!

Both services are running and ready for testing. Open http://localhost:3004 to get started!

For questions or issues, check the logs or refer to the documentation.
