# AI Tutor - Complete Setup Guide

This guide ensures you can run the entire AI Tutor platform locally without issues.

## Quick Start (TL;DR)

```bash
# 1. Clone the repository
git clone https://github.com/GetFoolish/aitutor.git
cd aitutor

# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env and add your API keys

# 3. Run the development setup script
chmod +x dev.sh
./dev.sh
```

That's it! All services will start automatically.

---

## Prerequisites

### Required Software

- **Python 3.8+** - Backend services
- **Node.js 18+** - Frontend application
- **npm or yarn** - Package management
- **MongoDB** - Database (can use local or MongoDB Atlas)

### Required API Keys

Before starting, you need these API keys:

1. **Google Gemini API Key** (Required)
   - Get it from: https://makersuite.google.com/app/apikey
   - Used for: OCR, AI tutoring

2. **MongoDB URI** (Required)
   - Local: `mongodb://localhost:27017/ai_tutor`
   - Or use MongoDB Atlas (free tier): https://www.mongodb.com/atlas

3. **JWT Secret** (Required)
   - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

4. **Google OAuth Credentials** (Required for login)
   - Get from: https://console.cloud.google.com/apis/credentials
   - Create OAuth 2.0 Client ID
   - Add authorized redirect URI: `http://localhost:8003/auth/callback`

5. **Other Optional Keys** (see .env.example for full list)
   - Stripe (payments)
   - ImageKit (image hosting)
   - Pinecone (vector search)
   - Daily.co (video calls)

---

## Step-by-Step Setup

### 1. Clone Repository

```bash
git clone https://github.com/GetFoolish/aitutor.git
cd aitutor
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vim, code, etc.
```

**Minimum required variables:**

```env
# Google Gemini (for AI features)
GEMINI_API_KEY=your_gemini_api_key_here

# MongoDB
MONGODB_URI=mongodb://localhost:27017/ai_tutor
MONGODB_DB_NAME=ai_tutor

# Authentication
JWT_SECRET=your_secure_random_secret_here
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
```

### 3. Run Setup Script

```bash
# Make the script executable
chmod +x dev.sh stop.sh

# Start all services
./dev.sh
```

The script will:
- ✅ Check prerequisites (Python, Node.js, MongoDB)
- ✅ Verify environment variables
- ✅ Create Python virtual environment
- ✅ Install Python dependencies
- ✅ Install frontend dependencies
- ✅ Start all backend services
- ✅ Start frontend development server

### 4. Access the Application

After the setup completes, open:

**http://localhost:3000**

You should see the login page. Use Google OAuth to sign in.

---

## Services Overview

The platform runs 5 services:

| Service | Port | Purpose |
|---------|------|---------|
| **Frontend** | 3000 | Web UI (React + Vite) |
| **Dash System** | 8000 | Question bank & assessment |
| **Teaching Assistant** | 8002 | AI tutoring engine |
| **Auth Service** | 8003 | User authentication (OAuth + JWT) |
| **Homework Assistant** | 8004 | Homework help with OCR |

All services must be running for full functionality.

---

## Common Issues & Solutions

### Issue: "Failed to connect" errors in browser

**Cause**: One or more services not running

**Solution**:
```bash
# Check which services are running
ps aux | grep -E 'api.py|auth_api.py|dash_api.py|vite'

# Restart all services
./stop.sh
./dev.sh
```

### Issue: "PORT already in use"

**Cause**: Port conflict with another application

**Solution**:
```bash
# Find what's using the port (example: port 3000)
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or change the port in .env:
FRONTEND_PORT=3001
AUTH_SERVICE_PORT=8013
# etc.
```

### Issue: "GEMINI_API_KEY not set"

**Cause**: Missing or invalid .env file

**Solution**:
```bash
# Make sure .env exists
ls -la .env

# Check if variables are set
source .env
echo $GEMINI_API_KEY

# If empty, edit .env and add your key
```

### Issue: "MongoDB connection failed"

**Cause**: MongoDB not running or wrong URI

**Solutions**:

**Option 1: Use MongoDB Atlas (cloud)**
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/ai_tutor
```

**Option 2: Install MongoDB locally**
```bash
# macOS
brew install mongodb-community
brew services start mongodb-community

# Ubuntu/Debian
sudo apt-get install mongodb
sudo systemctl start mongodb

# Verify it's running
mongosh --eval "db.version()"
```

### Issue: Frontend shows "localhost refused to connect"

**Cause**: Port mismatch in configuration

**Solution**:
```bash
# Check frontend port in vite.config.ts
cat frontend/vite.config.ts | grep port

# Should be 3000. If not, change it to:
port: 3000,

# Restart frontend
pkill -f vite
cd frontend && npm run dev
```

---

## Manual Setup (Alternative)

If you prefer to run services individually:

### Backend Services

```bash
# Activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start each service in a separate terminal

# Terminal 1: Auth Service (port 8003)
cd services/AuthService
python3 auth_api.py

# Terminal 2: Homework Assistant (port 8004)
cd services/HomeworkAssistant
python3 api.py

# Terminal 3: Dash System (port 8000)
cd services/DashSystem
python3 dash_api.py

# Terminal 4: Teaching Assistant (port 8002)
cd services/TeachingAssistant
python3 api.py
```

### Frontend

```bash
# Terminal 5: Frontend (port 3000)
cd frontend
npm install
npm run dev
```

---

## Stopping Services

```bash
# Use the stop script
./stop.sh

# Or manually kill processes
pkill -f "api.py"
pkill -f "auth_api.py"
pkill -f "dash_api.py"
pkill -f "vite"
```

---

## Logs

View real-time logs for debugging:

```bash
# All services log to logs/ directory
tail -f logs/auth-service.log
tail -f logs/homework-service.log
tail -f logs/frontend.log
tail -f logs/dash-system.log
tail -f logs/teaching-assistant.log

# Or view all logs together
tail -f logs/*.log
```

---

## Development Workflow

### Making Changes

```bash
# Backend changes - auto-reload is enabled
# Just edit the Python files and save

# Frontend changes - Vite hot-reloads automatically
# Edit React/TypeScript files in frontend/src/
```

### Running Tests

```bash
# Backend tests
cd services/HomeworkAssistant
source ../../venv/bin/activate
cd tests
pip install -r requirements.txt
pytest -v

# Frontend tests
cd frontend
npm test
```

---

## Production Deployment

For production, use Docker:

```bash
# Build and start with Docker Compose
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

See `docker-compose.yml` for service configuration.

---

## Getting Help

1. **Check logs first**: `tail -f logs/*.log`
2. **Verify environment**: Check `.env` has all required keys
3. **Restart services**: `./stop.sh && ./dev.sh`
4. **Check GitHub issues**: https://github.com/GetFoolish/aitutor/issues
5. **Read service READMEs**: Each service has specific documentation

---

## Architecture Overview

```
┌─────────────────┐
│  Frontend       │  Port 3000
│  (React + Vite) │
└────────┬────────┘
         │
         ├─────────> Auth Service (8003)        - Login/OAuth
         ├─────────> Homework Assistant (8004)  - OCR + AI Help
         ├─────────> Dash System (8000)         - Questions
         └─────────> Teaching Assistant (8002)  - AI Tutor
                              │
                              ▼
                        MongoDB Database
```

---

## Next Steps

1. ✅ Complete setup and start services
2. ✅ Open http://localhost:3000
3. ✅ Sign in with Google
4. ✅ Try uploading homework
5. ✅ Test the AI tutor
6. ✅ Explore the dashboard

---

## Contributing

See `CONTRIBUTING.md` for development guidelines.

---

## License

See `LICENSE` file for details.
