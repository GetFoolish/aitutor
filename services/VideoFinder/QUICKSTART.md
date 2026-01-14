# VideoFinder Quick Start

Find educational YouTube videos using Gemini AI in 3 minutes!

## 🚀 Setup (2 minutes)

### 1. Install Dependencies
```bash
pip install -r VideoFinder/requirements.txt
```

### 2. Get API Keys

**Gemini API (Free):**
1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy your key

**YouTube Data API v3 (Free):**
1. Go to: https://console.cloud.google.com/apis/credentials
2. Create a project (if needed)
3. Enable "YouTube Data API v3"
4. Create credentials → API Key
5. Copy your key

### 3. Set Environment Variables
```bash
export GOOGLE_API_KEY="your-gemini-key-here"
export YOUTUBE_API_KEY="your-youtube-key-here"
```

## ▶️ Run (1 minute)

```bash
# Basic usage - finds videos for all questions in folder
python VideoFinder/find_videos.py path/to/questions/folder

# Specify output file
python VideoFinder/find_videos.py questions/ --output my_results.json

# Limit videos per topic
python VideoFinder/find_videos.py questions/ --max-videos 5
```

## 📂 Input Format

Your questions folder should contain JSON files like:

```json
{
  "topic": "Addition within 20",
  "questions": [
    {"content": "What is 5 + 3?"},
    {"content": "Add 12 + 7"}
  ]
}
```

## 📊 Output

Results saved as JSON:
```json
{
  "total_topics": 2,
  "total_questions": 10,
  "topics": [
    {
      "topic": "Addition within 20",
      "videos": [
        {
          "title": "Addition Tutorial",
          "url": "https://youtube.com/watch?v=...",
          "quality_score": 87.5,
          "match_score": 85,
          "view_count": 125000,
          "transcript": "..."
        }
      ]
    }
  ]
}
```

## ✅ That's It!

See `VideoFinder/README.md` for full documentation.

## 🐛 Troubleshooting

**"GOOGLE_API_KEY not set"**
```bash
export GOOGLE_API_KEY="your-key"
```

**"No JSON files found"**
- Check folder path is correct
- Ensure files have .json extension

**"Quota exceeded"**
- YouTube API has 10,000 units/day limit
- Wait 24 hours or request increase

## 💡 Example

```bash
# 1. Create test questions
mkdir test_questions
cat > test_questions/math.json << 'EOF'
{
  "topic": "Multiplication",
  "questions": [
    {"content": "What is 3 × 4?"},
    {"content": "How to multiply?"}
  ]
}
EOF

# 2. Set API keys
export GOOGLE_API_KEY="your-gemini-key"
export YOUTUBE_API_KEY="your-youtube-key"

# 3. Run!
python VideoFinder/find_videos.py test_questions

# 4. Check results
cat video_results.json
```

Done! 🎉
