# LLM-Based Educational Video Search Agent

An intelligent agent that searches for educational videos on YouTube and Vimeo, analyzes their relevance to educational topics, and ranks them by quality.

## Features

- **Intelligent Query Generation**: Uses Claude LLM to generate diverse, effective search queries based on educational topics
- **Multi-Platform Search**: Searches both YouTube and Vimeo
- **Transcript Analysis**: Fetches and analyzes video transcripts for content matching
- **Topic Matching with Scoring**: Uses LLM to calculate percentage match scores (0-100%) for how well videos match topics
- **Categorization**: Automatically categorizes videos by:
  - Language (auto-detected from transcripts)
  - Region (detected from channel and metadata)
- **Quality Ranking**: Ranks videos based on:
  - Topic match score (40%)
  - Engagement metrics: views, likes (30%)
  - Transcript availability (15%)
  - Appropriate video duration (15%)
- **Batch Processing**: Process entire directories of educational questions

## Architecture

```
video_search_agent/
├── main_agent.py                 # Main orchestrator
├── example_usage.py              # Usage examples
├── requirements.txt              # Python dependencies
├── modules/
│   ├── question_loader.py        # Loads questions from JSON files
│   ├── query_generator.py        # Generates search queries with LLM
│   ├── video_searcher.py         # Searches YouTube & Vimeo
│   ├── transcript_fetcher.py     # Fetches video transcripts
│   ├── topic_matcher.py          # Matches videos to topics with scoring
│   └── video_categorizer.py      # Categorizes and ranks videos
├── data/                          # Cached data (optional)
└── output/                        # Results JSON files
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Keys

```bash
# Required: Anthropic API key for Claude
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Required for YouTube: Get from Google Cloud Console
export YOUTUBE_API_KEY="your-youtube-api-key"

# Optional for Vimeo
export VIMEO_API_KEY="your-vimeo-api-key"
```

#### Getting API Keys:

**Anthropic (Claude):**
- Sign up at https://console.anthropic.com/
- Create an API key in the dashboard

**YouTube Data API:**
- Go to https://console.developers.google.com/
- Create a new project
- Enable "YouTube Data API v3"
- Create credentials (API Key)

**Vimeo (Optional):**
- Sign up at https://developer.vimeo.com/
- Create a new app
- Get your access token

## Usage

### Quick Start - Single Topic

```python
from main_agent import VideoSearchAgent

# Initialize agent
agent = VideoSearchAgent()

# Define topic and questions
topic = "Adding numbers within 20"
questions = [
    {"content": "Add 6 + 1 using a number line"},
    {"content": "What is 12 + 7?"},
]

# Process topic
results = agent.process_topic(
    topic=topic,
    questions=questions,
    max_videos_per_query=5,
    num_queries=3,
    min_match_score=40
)

# Access results
for video in results['top_videos']:
    print(f"{video['title']} - Score: {video['quality_score']}")
```

### Batch Process All Topics

```python
from main_agent import VideoSearchAgent

agent = VideoSearchAgent()

# Process entire directory
results = agent.process_all_topics(
    questions_dir="../files (1)",
    output_dir="output",
    max_videos_per_query=5,
    num_queries=3,
    min_match_score=40
)
```

### Command Line Usage

```bash
# Process all topics in directory
python main_agent.py ../files\ \(1\)

# Run example
python example_usage.py

# Run batch example
python example_usage.py batch
```

## Output Format

Results are saved as JSON files in the `output/` directory:

```json
{
  "topic": "Add and subtract within 20 > Add within 20",
  "queries_used": [
    "adding numbers within 20 for kids",
    "basic addition tutorial",
    "number line addition"
  ],
  "total_videos_found": 15,
  "videos_after_filtering": 8,
  "top_videos": [
    {
      "platform": "youtube",
      "video_id": "abc123",
      "url": "https://www.youtube.com/watch?v=abc123",
      "title": "Adding Numbers 1-20 | Easy Tutorial",
      "quality_score": 87.5,
      "match_score": 85,
      "relevance": "High",
      "teaching_style": "Visual/Conceptual",
      "language_name": "English",
      "region": "US",
      "view_count": 125000,
      "like_count": 3200,
      "transcript": "Today we're learning addition..."
    }
  ],
  "by_language": {
    "English": [...],
    "Spanish": [...]
  },
  "by_region": {
    "US": [...],
    "UK": [...]
  }
}
```

## How It Works

### 1. Question Loading
Loads educational questions from JSON files, extracting:
- Question content
- Topic hierarchy
- Problem type

### 2. Query Generation
Uses Claude LLM to generate intelligent search queries:
- Analyzes topic and sample questions
- Creates diverse queries targeting different aspects
- Considers different teaching styles and age groups

### 3. Video Search
Searches YouTube and Vimeo:
- Uses platform APIs for optimal results
- Filters by relevance and video type
- Retrieves metadata (views, likes, duration, etc.)

### 4. Transcript Fetching
Fetches video transcripts:
- YouTube: Uses youtube-transcript-api
- Falls back to video descriptions if transcripts unavailable
- Handles multiple languages

### 5. Topic Matching & Scoring
Uses Claude LLM to analyze each video:
- Compares transcript to topic and questions
- Scores relevance (0-100%)
- Identifies teaching style
- Assesses content coverage
- Notes quality indicators

### 6. Categorization
Automatically categorizes videos:
- **Language**: Auto-detects from transcript using langdetect
- **Region**: Identifies from channel name and metadata

### 7. Quality Ranking
Calculates comprehensive quality score:
- **40%**: Topic match score
- **30%**: Engagement (views, like ratio)
- **15%**: Transcript availability
- **15%**: Duration appropriateness (5-20 min ideal)

## Quality Metrics Explained

### Match Score (0-100%)
How well the video content matches the educational topic:
- **70-100%**: Directly teaches the topic
- **50-69%**: Related content, partially helpful
- **30-49%**: Tangentially related
- **0-29%**: Not relevant

### Quality Score (0-100)
Overall video quality for educational purposes:
- **80-100**: Excellent - Highly relevant, good engagement, complete transcript
- **60-79**: Good - Relevant with some quality indicators
- **40-59**: Fair - Acceptable but missing some quality factors
- **0-39**: Poor - Low relevance or quality

### Relevance Levels
- **High**: Video directly addresses the topic
- **Medium**: Video covers related concepts
- **Low**: Video barely mentions the topic

## Configuration Options

```python
agent.process_topic(
    topic=topic,
    questions=questions,

    # Search parameters
    max_videos_per_query=5,    # Videos per search query
    num_queries=3,             # Number of search queries to generate

    # Filtering
    min_match_score=40,        # Minimum match score (0-100)
)
```

## Performance Tips

1. **Start Small**: Test with 1-2 topics before batch processing
2. **API Rate Limits**: YouTube API has daily quotas (default: 10,000 units/day)
3. **Transcripts**: Not all videos have transcripts; expect 60-80% availability
4. **LLM Costs**: Each video analysis uses ~1-2k tokens with Claude
5. **Caching**: Consider caching search results to avoid repeated API calls

## Limitations

1. **API Dependencies**: Requires valid API keys for full functionality
2. **Transcript Availability**: ~20-40% of videos lack transcripts
3. **Language**: Optimized for English content (but supports others)
4. **Rate Limits**: Subject to API rate limits and quotas
5. **Cost**: LLM analysis incurs API costs (Claude Sonnet: ~$3/1M input tokens)

## Future Enhancements

- [ ] Add caching layer for video metadata and transcripts
- [ ] Support more video platforms (Vimeo fully, Khan Academy, etc.)
- [ ] Implement parallel processing for faster batch operations
- [ ] Add video content summarization
- [ ] Create web UI for results exploration
- [ ] Add export to CSV/Excel formats
- [ ] Implement video download capability
- [ ] Add support for playlists
- [ ] Machine learning-based quality prediction

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### "YouTube API error: quotaExceeded"
You've hit the daily YouTube API quota. Wait 24 hours or request quota increase.

### "No transcript found"
Many videos don't have transcripts. The agent falls back to descriptions.

### Low match scores
Try:
- Adjusting search queries manually
- Lowering `min_match_score` threshold
- Increasing `num_queries` for more diverse results

## License

MIT License - Feel free to use and modify for your educational projects.

## Support

For issues or questions:
1. Check this README
2. Review example_usage.py
3. Check module docstrings for detailed API documentation

## Credits

Built with:
- Anthropic Claude for intelligent analysis
- YouTube Data API for video search
- youtube-transcript-api for transcript fetching
- langdetect for language detection
