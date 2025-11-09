# 🚀 OpenRouter Quick Start

## 1️⃣ Install Dependencies (1 minute)
```bash
cd /Users/gaganarora/Desktop/projects/ai_tutor
pip install -r requirements.txt
```

## 2️⃣ Your Credentials Are Already Set! ✅
Your `.env` file has been created with:
- ✅ OpenRouter API Key
- ✅ Free Nvidia Model
- ✅ YouTube API Key
- ✅ Google API Key
- ✅ MongoDB Connection

## 3️⃣ Test Video Recommendations (2 minutes)

### Start the API:
```bash
cd VideoRecommendations
python video_recommendations_api.py
```

### Test it (in new terminal):
```bash
curl -X POST http://localhost:8002/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "Basic Addition",
    "max_videos": 3
  }'
```

## 4️⃣ Expected Response:
```json
[
  {
    "video_id": "abc123",
    "title": "Learn Addition for Kids",
    "url": "https://youtube.com/watch?v=abc123",
    "match_score": 85.5,
    "transcript_available": true
  }
]
```

## ✅ That's It!

### What You're Using:
- **Model**: Nvidia Nemotron Nano 12B
- **Cost**: FREE 🎉
- **Rate Limit**: ~20 requests/minute

### Need More?
- Upgrade at: https://openrouter.ai/settings/credits
- Or switch models in `.env` file

---

## 🎯 Quick Commands

```bash
# Check .env is configured
cat .env | grep OPENROUTER

# Install/update dependencies
pip install -r requirements.txt

# Start video recommendations API
python VideoRecommendations/video_recommendations_api.py

# Test the API
curl http://localhost:8002/health
```

---

## 📞 Having Issues?

1. **Check .env file exists**: `cat .env`
2. **Verify OpenRouter key**: https://openrouter.ai/keys
3. **Check dependencies installed**: `pip list | grep openai`
4. **Read full guide**: `OPENROUTER_MIGRATION_GUIDE.md`

---

**You're all set to use FREE AI-powered video recommendations!** 🚀
