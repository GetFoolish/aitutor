# AI Tutor - Quick Start Guide

## 🚀 Get Up and Running in 5 Minutes

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB running
- API keys (see below)

---

## Step 1: Environment Variables

Create `.env` in project root:

```bash
# Required for basic functionality
ANTHROPIC_API_KEY=sk-ant-xxx
YOUTUBE_API_KEY=AIzaSyxxx
MONGODB_URI=mongodb://localhost:27017/ai_tutor

# Required for auth
JWT_SECRET_KEY=your-secret-key-min-32-chars
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx

# Required for payments
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Optional
VIMEO_API_KEY=xxx
PINECONE_API_KEY=xxx
PINECONE_ENVIRONMENT=xxx
```

---

## Step 2: Install Dependencies

### Backend
```bash
cd /Users/gaganarora/Desktop/projects/ai_tutor
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
```

---

## Step 3: Start Services

Open **5 terminal windows** and run:

### Terminal 1: Auth API
```bash
cd SherlockEDApi
python run_backend.py
# Running on http://localhost:8001
```

### Terminal 2: DASH API
```bash
cd DashSystem
python dash_api.py
# Running on http://localhost:8000
```

### Terminal 3: Video Recommendations API
```bash
cd VideoRecommendations
python video_recommendations_api.py
# Running on http://localhost:8002
```

### Terminal 4: Pipecat Voice Pipeline
```bash
python pipecat_pipeline/26c_gemini_live_video.py
# Running on http://localhost:7860
```

### Terminal 5: MediaMixer
```bash
cd MediaMixer
python media_mixer.py
# Running on ws://localhost:8765 and ws://localhost:8766
```

---

## Step 4: Start Frontend

### Terminal 6: Frontend Dev Server
```bash
cd frontend
npm run dev
# Running on http://localhost:5173
```

---

## Step 5: Test the Application

1. **Open Browser**: http://localhost:5173

2. **Create Account:**
   - Click "Sign Up"
   - Enter name, email, password
   - You'll get 100 free credits

3. **Test Features:**
   - ✅ Click yellow Loom button (bottom-right) → Opens menu
   - ✅ Answer a question → Submits to DASH
   - ✅ Expand "Helpful Videos" → Shows YouTube recommendations
   - ✅ Click avatar menu (top-right) → Go to Account page
   - ✅ Try "Buy Credits" → Opens Stripe checkout

4. **Test Pages:**
   - Navigate to: http://localhost:5173/account
   - Navigate to: http://localhost:5173/terms-of-service
   - Navigate to: http://localhost:5173/privacy-policy

---

## 🎯 Quick Feature Tests

### Test Loom Button Animation
1. Connect to voice (click Connect in right panel)
2. Wait for bot to speak
3. Watch yellow pulsing rings animate around button

### Test Avatar Video Feed
1. Enable camera or screen share from Loom button menu
2. Small draggable video window appears top-left
3. Drag it anywhere, click expand button to resize

### Test Video Recommendations
1. Answer any question
2. Scroll down to "Helpful Videos" section
3. Expand accordion
4. Click video thumbnail to play in modal

### Test Payment Flow
1. Click "Buy Credits" in header
2. Select a package (use Stripe test card: 4242 4242 4242 4242)
3. Complete checkout
4. Should redirect to success page
5. Credits should be added to account

---

## 🔍 API Endpoints to Test

### Auth API (Port 8001)
```bash
# Health check
curl http://localhost:8001/docs

# Create account (no auth needed)
curl -X POST http://localhost:8001/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }'
```

### Video Recommendations (Port 8002)
```bash
# Get videos for a skill
curl -X POST http://localhost:8002/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "Addition",
    "max_videos": 3
  }'
```

### DASH API (Port 8000)
```bash
# Get next question (replace USER_ID)
curl http://localhost:8000/next-question/USER_ID

# Get skill states
curl http://localhost:8000/skill-states/USER_ID
```

---

## 🐛 Common Issues

### Issue: MongoDB Connection Failed
**Solution:**
```bash
# Make sure MongoDB is running
mongod --dbpath /path/to/data
```

### Issue: Module Not Found
**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: Port Already in Use
**Solution:**
```bash
# Find and kill process on port (e.g., 8001)
lsof -ti:8001 | xargs kill -9
```

### Issue: CORS Error in Browser
**Solution:**
- Check all backends are running
- Verify URLs in frontend code match backend ports
- Clear browser cache

### Issue: Video Recommendations Not Loading
**Solution:**
- Verify YOUTUBE_API_KEY is set
- Check port 8002 is running
- Look at browser console for errors

### Issue: Stripe Webhook Not Working Locally
**Solution:**
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Forward webhooks to local server
stripe listen --forward-to localhost:8001/payments/webhook

# Use webhook signing secret from output
```

---

## 📊 Verify Everything is Working

Run this checklist:

```bash
# Check all services are running
curl http://localhost:8001/docs  # Auth API docs
curl http://localhost:8000/docs  # DASH API docs
curl http://localhost:8002/health  # Video API health

# Check frontend is accessible
curl http://localhost:5173

# Check MediaMixer WebSockets (should see "Upgrade required")
curl http://localhost:8765
curl http://localhost:8766
```

All should return 200 or show HTML/JSON (except WebSocket endpoints).

---

## 🎉 Success Indicators

You know it's working when:

1. ✅ Frontend loads at localhost:5173
2. ✅ Login page appears (black theme)
3. ✅ Can create account and login
4. ✅ Questions load in main panel
5. ✅ Loom button visible bottom-right
6. ✅ Credits shown in header
7. ✅ Can click "Buy Credits" (Stripe modal opens)
8. ✅ Video recommendations load below questions
9. ✅ All 5 backend terminals show no errors

---

## 🔧 Development Tips

### Hot Reload
- **Frontend**: Auto-reloads on file changes
- **Backend**: Restart Python processes manually

### Debug Mode
```bash
# Add to any Python file for debugging
import pdb; pdb.set_trace()
```

### Check Logs
```bash
# View backend logs in terminal
# Each service logs to its own terminal window

# Frontend logs
# Open browser DevTools (F12) → Console tab
```

### Test Stripe Locally
Use test cards: https://stripe.com/docs/testing
- Success: 4242 4242 4242 4242
- Decline: 4000 0000 0000 0002
- 3D Secure: 4000 0025 0000 3155

---

## 📞 Need Help?

1. **Check logs** in all terminal windows
2. **Check browser console** (F12)
3. **Verify all services running** (see checklist above)
4. **Check environment variables** are set correctly
5. **Read IMPLEMENTATION_SUMMARY.md** for detailed info

---

## 🎯 Next Steps

Once everything works:

1. **Customize** the app for your needs
2. **Add real API keys** (replace test keys)
3. **Deploy** to production
4. **Set up domain** and SSL certificates
5. **Configure Stripe webhooks** for production
6. **Add monitoring** (Sentry, LogRocket)

---

**Ready to learn?** Open http://localhost:5173 and start tutoring! 🚀
