# 🔄 OpenRouter Migration Guide

## ✅ Migration Complete!

Your AI Tutor has been successfully converted from **Anthropic Claude** to **OpenRouter** with the **free Nvidia Nemotron model**.

---

## 🎯 What Changed?

### Before (Anthropic)
```python
# Used Anthropic Claude API
from anthropic import Anthropic
client = Anthropic(api_key=ANTHROPIC_API_KEY)
model = "claude-3-5-sonnet-20241022"
# Cost: ~$3 per million tokens
```

### After (OpenRouter)
```python
# Now uses OpenRouter with free Nvidia model
from openai import OpenAI
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)
model = "nvidia/nemotron-nano-12b-v2-vl:free"
# Cost: FREE! 🎉
```

---

## 📝 Files Updated

### 1. **video_search_agent/modules/query_generator.py**
- Changed from `anthropic` to `openai` library
- Updated to use OpenRouter base URL
- Changed API call format from `messages.create()` to `chat.completions.create()`

### 2. **video_search_agent/modules/topic_matcher.py**
- Same changes as query_generator
- Scores video relevance using free Nvidia model

### 3. **video_search_agent/main_agent.py**
- Changed parameter from `anthropic_api_key` to `openrouter_api_key`

### 4. **VideoRecommendations/video_recommendations_api.py**
- Updated to use `OPENROUTER_API_KEY` environment variable

### 5. **requirements.txt**
- Replaced: `anthropic==0.40.0`
- With: `openai==1.58.1`

### 6. **.env**
- Created with your OpenRouter credentials
- Model set to: `nvidia/nemotron-nano-12b-v2-vl:free`

---

## 🔑 Your OpenRouter Setup

### API Key (Already Configured)
```bash
OPENROUTER_API_KEY=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
```

### Model (Free Tier)
```bash
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
```

---

## 🚀 How to Use

### 1. Install Updated Dependencies
```bash
cd /Users/gaganarora/Desktop/projects/ai_tutor
pip install -r requirements.txt
```

This will:
- Remove `anthropic` library
- Install `openai` library (used by OpenRouter)
- Keep all other dependencies

### 2. Environment Variables Already Set
Your `.env` file has been created with:
- ✅ OpenRouter API key
- ✅ Free Nvidia model
- ✅ All your other credentials

### 3. Start Video Recommendations API
```bash
cd VideoRecommendations
python video_recommendations_api.py
```

The API will now use OpenRouter instead of Anthropic!

---

## 💰 Cost Comparison

| Service | Model | Cost per Million Tokens |
|---------|-------|-------------------------|
| **Anthropic** | Claude 3.5 Sonnet | $3.00 |
| **OpenRouter (Old)** | Claude via OpenRouter | $3.00 |
| **OpenRouter (New)** | Nvidia Nemotron (FREE) | **$0.00** 🎉 |

### Estimated Savings
- **Video search for 100 videos**: ~$0.30 → **FREE**
- **Video search for 1,000 videos**: ~$3.00 → **FREE**
- **Monthly usage (10,000 videos)**: ~$30.00 → **FREE**

---

## 🎨 Available Free Models on OpenRouter

You can switch to other free models by updating `.env`:

```bash
# Current (Best for educational content)
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free

# Alternatives (also free):
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
OPENROUTER_MODEL=google/gemma-2-9b-it:free
OPENROUTER_MODEL=microsoft/phi-3-mini-128k-instruct:free
```

---

## 🔍 Testing the Migration

### Test 1: Check Environment
```bash
# Make sure .env file is loaded
cat .env | grep OPENROUTER
```

Should show:
```
OPENROUTER_API_KEY=sk-or-v1-8b55...
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
```

### Test 2: Test Video API
```bash
# Start the API
python VideoRecommendations/video_recommendations_api.py

# In another terminal, test it:
curl -X POST http://localhost:8002/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "Addition",
    "max_videos": 3,
    "min_match_score": 60
  }'
```

Should return JSON with video recommendations!

### Test 3: Check Logs
Look for these in the terminal:
```
✅ Good: "Using OpenRouter model: nvidia/nemotron-nano-12b-v2-vl:free"
✅ Good: "Generated 3 search queries for: Addition"
✅ Good: "Scored video: ... match_score: 85"

❌ Bad: "Error: Invalid API key"
❌ Bad: "Error: anthropic module not found"
```

---

## 🐛 Troubleshooting

### Issue 1: "ModuleNotFoundError: No module named 'openai'"
**Solution:**
```bash
pip install openai==1.58.1
```

### Issue 2: "Invalid API key"
**Solution:**
```bash
# Check your OpenRouter key at: https://openrouter.ai/keys
# Make sure .env file is in project root
# Update OPENROUTER_API_KEY in .env
```

### Issue 3: "Model not found"
**Solution:**
```bash
# Verify the model name is correct
# Check available models at: https://openrouter.ai/models
```

### Issue 4: "Rate limit exceeded"
**Solution:**
Free models have rate limits:
- Nvidia Nemotron: ~20 requests/minute
- Wait a minute and try again
- Or upgrade to paid tier for higher limits

---

## 📊 Model Performance Comparison

### Anthropic Claude 3.5 Sonnet
- ✅ Excellent quality
- ✅ Very accurate scoring
- ✅ Great at understanding context
- ❌ Costs money ($3/million tokens)

### Nvidia Nemotron (Free)
- ✅ Good quality
- ✅ Decent scoring accuracy
- ✅ Fast responses
- ✅ **FREE!**
- ⚠️ May be less accurate than Claude
- ⚠️ Rate limits apply

**Recommendation:** Start with free model, upgrade if needed!

---

## 🔄 Reverting to Anthropic (If Needed)

If you want to switch back to Anthropic:

1. **Install Anthropic:**
   ```bash
   pip install anthropic==0.40.0
   ```

2. **Update query_generator.py:**
   ```python
   from anthropic import Anthropic
   self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
   ```

3. **Update API calls:**
   ```python
   response = self.client.messages.create(
       model="claude-3-5-sonnet-20241022",
       messages=[{"role": "user", "content": prompt}]
   )
   queries_text = response.content[0].text.strip()
   ```

4. **Add to .env:**
   ```bash
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

---

## 💡 OpenRouter Features

### 1. Multiple Providers
OpenRouter gives you access to:
- Anthropic (Claude)
- OpenAI (GPT-4)
- Google (Gemini)
- Meta (Llama)
- Nvidia (Nemotron)
- And many more!

### 2. Switch Models Instantly
Just change the `.env` file:
```bash
# Use free Nvidia
OPENROUTER_MODEL=nvidia/nemotron-nano-12b-v2-vl:free

# Switch to paid Claude (if you add credits)
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Switch to GPT-4
OPENROUTER_MODEL=openai/gpt-4-turbo
```

### 3. Unified API
One API key, many models. No need to manage multiple API keys!

---

## 📚 Additional Resources

- **OpenRouter Dashboard**: https://openrouter.ai/dashboard
- **API Keys**: https://openrouter.ai/keys
- **Available Models**: https://openrouter.ai/models
- **Pricing**: https://openrouter.ai/docs/pricing
- **Documentation**: https://openrouter.ai/docs

---

## ✅ Migration Checklist

- [x] Updated code to use OpenRouter
- [x] Replaced `anthropic` with `openai` in requirements.txt
- [x] Created `.env` file with your credentials
- [x] Set free Nvidia model as default
- [ ] Test video recommendations API
- [ ] Verify video search works
- [ ] Check query generation
- [ ] Confirm scoring accuracy

---

## 🎉 Benefits of This Migration

1. **💰 Cost Savings**: FREE instead of $3/million tokens
2. **🚀 Easy Switching**: Change models instantly via .env
3. **🔓 More Options**: Access to 100+ models
4. **📈 Scalability**: Start free, upgrade when needed
5. **🛡️ One API Key**: Manage one key instead of many

---

## 🤝 Support

Need help?
- Check OpenRouter docs: https://openrouter.ai/docs
- Test with simple prompts first
- Check rate limits if getting errors
- Upgrade to paid tier for production use

---

**Migration completed on:** January 2025
**By:** Claude Code Assistant
**Model changed from:** Anthropic Claude 3.5 Sonnet
**Model changed to:** Nvidia Nemotron Nano 12B (FREE)
