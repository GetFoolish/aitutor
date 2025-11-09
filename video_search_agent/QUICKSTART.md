># Quick Start Guide

## Setup Instructions

### 1. Install Dependencies

```bash
cd video_search_agent
pip3 install -r requirements.txt
```

This will install:
- `anthropic` - Claude LLM API
- `youtube-transcript-api` - For fetching YouTube transcripts
- `google-api-python-client` - For YouTube search
- `langdetect` - For language detection
- Other dependencies

### 2. Set Environment Variables

Create a `.env` file or export these in your terminal:

```bash
# Required for LLM-based analysis
export ANTHROPIC_API_KEY="sk-ant-..."

# Required for YouTube search
export YOUTUBE_API_KEY="AIza..."

# Optional for Vimeo search
export VIMEO_API_KEY="..."
```

**Get API Keys:**

- **Anthropic**: https://console.anthropic.com/ (sign up and get API key)
- **YouTube**: https://console.developers.google.com/ (enable YouTube Data API v3)
- **Vimeo**: https://developer.vimeo.com/ (optional)

### 3. Test the System

```bash
python3 test_system.py
```

This will verify:
- All modules can be imported
- Question loading works
- API keys are configured

### 4. Run Example

```bash
# Single topic example
python3 example_usage.py

# Process all topics (batch mode)
python3 example_usage.py batch
```

### 5. Run Main Agent

```bash
# Process questions from the provided directory
python3 main_agent.py "../files (1)"
```

Results will be saved to the `output/` directory.

## Quick API Key Setup

### Anthropic (Claude) - Required

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Click "Get API Keys"
4. Create a new key
5. Copy and export:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-your-key-here"
   ```

### YouTube Data API - Required for YouTube Search

1. Go to https://console.developers.google.com/
2. Create a new project (or select existing)
3. Enable "YouTube Data API v3"
4. Go to Credentials → Create Credentials → API Key
5. Copy and export:
   ```bash
   export YOUTUBE_API_KEY="AIzaYourKeyHere"
   ```

### Test Connection

```bash
# Test Anthropic
python3 -c "from anthropic import Anthropic; client = Anthropic(); print('✓ Anthropic connected')"

# Test YouTube API
python3 -c "from googleapiclient.discovery import build; youtube = build('youtube', 'v3', developerKey='YOUR_KEY'); print('✓ YouTube connected')"
```

## Minimal Working Example

```python
# minimal_example.py
import os
os.environ['ANTHROPIC_API_KEY'] = 'your-key'
os.environ['YOUTUBE_API_KEY'] = 'your-key'

from main_agent import VideoSearchAgent

agent = VideoSearchAgent()

topic = "Adding numbers within 20"
questions = [{"content": "Add 6 + 1"}]

results = agent.process_topic(topic, questions)
print(f"Found {len(results['all_videos'])} videos")
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'anthropic'"
```bash
pip3 install anthropic
```

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY="your-key-here"
# Or add to ~/.bashrc or ~/.zshrc for persistence
```

### "YouTube API quota exceeded"
- YouTube API has daily quotas
- Free tier: 10,000 units/day
- One search = ~100 units
- Solution: Wait 24h or request quota increase

### Dependencies fail to install
```bash
# Try upgrading pip first
pip3 install --upgrade pip

# Then retry
pip3 install -r requirements.txt
```

## What Happens When You Run It

1. **Loads questions** from the JSON files
2. **Groups by topic** (e.g., "Addition within 20")
3. **Generates smart search queries** using Claude LLM
4. **Searches YouTube** (and Vimeo if configured)
5. **Fetches transcripts** for found videos
6. **Analyzes relevance** using Claude to score each video
7. **Categorizes by language/region** automatically
8. **Ranks by quality** based on multiple factors
9. **Saves results** to JSON files in `output/`

## Output Location

All results are saved in the `output/` directory:

```
output/
├── Add_within_20_results.json
├── Place_value_results.json
├── ...
└── combined_results.json
```

Each file contains:
- Top recommended videos
- Match scores
- Quality rankings
- Language/region breakdowns

## Next Steps

1. Review the `output/` directory for results
2. Check `README.md` for full documentation
3. Customize parameters in `main_agent.py` or `example_usage.py`
4. Integrate with your educational platform

## Cost Estimates

### Anthropic (Claude Sonnet 3.5)
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens
- Per video analysis: ~1-2k input tokens = $0.003-0.006
- **10 videos**: ~$0.05
- **100 videos**: ~$0.50

### YouTube Data API
- Free tier: 10,000 units/day
- Search query: ~100 units
- Video details: ~1-5 units
- **Daily limit**: ~90-100 searches

Very affordable for educational use!

## Support

- Read `README.md` for detailed documentation
- Check module docstrings for API details
- Review `example_usage.py` for code examples
