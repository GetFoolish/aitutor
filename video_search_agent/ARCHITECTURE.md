# System Architecture

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIDEO SEARCH AGENT                            │
│                   (main_agent.py)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WORKFLOW PIPELINE                           │
└─────────────────────────────────────────────────────────────────┘

[1] QUESTION LOADING
    ┌──────────────────────┐
    │ QuestionLoader       │
    │ - Load JSON files    │
    │ - Parse questions    │
    │ - Group by topic     │
    └──────────────────────┘
               │
               ▼
[2] QUERY GENERATION
    ┌──────────────────────┐
    │ QueryGenerator       │
    │ - Analyze topic      │
    │ - Use Claude LLM     │
    │ - Generate queries   │
    └──────────────────────┘
               │
               ▼
[3] VIDEO SEARCH
    ┌──────────────────────┐
    │ VideoSearcher        │
    │ - Search YouTube     │
    │ - Search Vimeo       │
    │ - Fetch metadata     │
    │ - Deduplicate        │
    └──────────────────────┘
               │
               ▼
[4] TRANSCRIPT FETCHING
    ┌──────────────────────┐
    │ TranscriptFetcher    │
    │ - Get YouTube text   │
    │ - Get Vimeo text     │
    │ - Fallback to desc   │
    └──────────────────────┘
               │
               ▼
[5] TOPIC MATCHING
    ┌──────────────────────┐
    │ TopicMatcher         │
    │ - Analyze content    │
    │ - Use Claude LLM     │
    │ - Score 0-100%       │
    │ - Extract insights   │
    └──────────────────────┘
               │
               ▼
[6] CATEGORIZATION & RANKING
    ┌──────────────────────┐
    │ VideoCategorizer     │
    │ - Detect language    │
    │ - Detect region      │
    │ - Calculate quality  │
    │ - Rank videos        │
    └──────────────────────┘
               │
               ▼
[7] OUTPUT GENERATION
    ┌──────────────────────┐
    │ JSON Files           │
    │ - Per topic          │
    │ - Combined results   │
    │ - Categorized views  │
    └──────────────────────┘
```

## Data Flow

```
Input Questions (JSON)
         │
         ├─> Extract Topics
         │
         └─> Generate Queries ──> Search APIs
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              YouTube API                          Vimeo API
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                              Video Metadata
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
           YouTube Transcript API              Vimeo Text Tracks
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                          Video + Transcript
                                      │
                              Claude LLM ──> Match Analysis
                                      │
                              Scored Videos
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                 │                 │
            Language Detection   Region Detection   Quality Calc
                    │                 │                 │
                    └─────────────────┬─────────────────┘
                                      │
                         Categorized & Ranked Results
                                      │
                                  JSON Output
```

## Module Dependencies

```
main_agent.py
    │
    ├── modules/question_loader.py
    │       └── Uses: json, pathlib, re
    │
    ├── modules/query_generator.py
    │       └── Uses: anthropic (Claude API)
    │
    ├── modules/video_searcher.py
    │       └── Uses: google-api-python-client, requests
    │
    ├── modules/transcript_fetcher.py
    │       └── Uses: youtube-transcript-api
    │
    ├── modules/topic_matcher.py
    │       └── Uses: anthropic (Claude API), re
    │
    └── modules/video_categorizer.py
            └── Uses: langdetect, re
```

## API Integration Points

### 1. Anthropic Claude API

**Used In:**
- `query_generator.py`: Generate search queries
- `topic_matcher.py`: Analyze and score videos

**Model:** Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)

**Request Pattern:**
```python
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}]
)
```

**Cost:** ~$3 per 1M input tokens, $15 per 1M output tokens

### 2. YouTube Data API v3

**Used In:**
- `video_searcher.py`: Search and get video details

**Endpoints:**
- `search().list()`: Search for videos
- `videos().list()`: Get detailed info

**Quota:** 10,000 units/day (free tier)

**Request Pattern:**
```python
youtube = build('youtube', 'v3', developerKey=api_key)
request = youtube.search().list(
    part="snippet",
    q=query,
    type="video",
    maxResults=10
)
```

### 3. YouTube Transcript API

**Used In:**
- `transcript_fetcher.py`: Fetch video transcripts

**Library:** `youtube-transcript-api` (unofficial but reliable)

**Request Pattern:**
```python
from youtube_transcript_api import YouTubeTranscriptApi

transcript = YouTubeTranscriptApi.get_transcript(video_id)
```

**Success Rate:** ~60-80% (not all videos have transcripts)

### 4. Vimeo API (Optional)

**Used In:**
- `video_searcher.py`: Search Vimeo videos

**Endpoint:** `https://api.vimeo.com/videos`

**Authentication:** Bearer token

**Request Pattern:**
```python
headers = {"Authorization": f"bearer {api_key}"}
response = requests.get(url, headers=headers, params=params)
```

## Component Details

### QuestionLoader
- **Input:** Directory path with JSON files
- **Output:** List of question dictionaries
- **Key Methods:**
  - `load_all_questions()`: Recursively load all JSONs
  - `group_by_topic()`: Organize by topic hierarchy
  - `_extract_question_data()`: Parse JSON structure
  - `_clean_content()`: Remove LaTeX/formatting

### QueryGenerator
- **Input:** Topic + sample questions
- **Output:** List of search query strings
- **Key Methods:**
  - `generate_queries()`: Main LLM call
  - `_generate_fallback_queries()`: Backup if LLM fails
  - `enhance_query_for_platform()`: Platform-specific tuning

### VideoSearcher
- **Input:** Search query
- **Output:** List of video metadata dicts
- **Key Methods:**
  - `search_youtube()`: YouTube API search
  - `search_vimeo()`: Vimeo API search
  - `search_all_platforms()`: Combined search
  - `_get_youtube_video_details()`: Extended metadata

### TranscriptFetcher
- **Input:** Video ID + platform
- **Output:** Transcript text
- **Key Methods:**
  - `fetch_youtube_transcript()`: Get YouTube text
  - `fetch_vimeo_transcript()`: Get Vimeo text (limited)
  - `get_transcript_with_fallback()`: Try transcript, use description

### TopicMatcher
- **Input:** Topic, questions, transcript, video metadata
- **Output:** Match score (0-100) + analysis
- **Key Methods:**
  - `calculate_match_score()`: Main LLM analysis
  - `batch_score_videos()`: Score multiple videos
  - `_parse_analysis()`: Extract structured data
  - `_calculate_fallback_score()`: Keyword-based backup

### VideoCategorizer
- **Input:** Video with transcript
- **Output:** Categorized + ranked video
- **Key Methods:**
  - `detect_language()`: Auto-detect language
  - `categorize_video()`: Add language/region
  - `rank_by_quality()`: Calculate quality score
  - `_calculate_quality_score()`: Weighted scoring
  - `_parse_duration()`: Parse ISO 8601 duration

## Configuration

### Environment Variables

```bash
ANTHROPIC_API_KEY="sk-ant-..."    # Required
YOUTUBE_API_KEY="AIza..."         # Required for YouTube
VIMEO_API_KEY="..."               # Optional
```

### Processing Parameters

```python
agent.process_topic(
    topic: str,
    questions: List[Dict],
    max_videos_per_query: int = 5,   # Videos per query
    num_queries: int = 3,            # Number of queries
    min_match_score: int = 40        # Minimum score to keep
)
```

### Quality Score Weights

```python
WEIGHTS = {
    'match_score': 0.40,      # 40% - Topic relevance
    'engagement': 0.30,       # 30% - Views & likes
    'transcript': 0.15,       # 15% - Availability
    'duration': 0.15          # 15% - Appropriate length
}
```

## Error Handling

### Graceful Degradation

1. **No Transcript**: Falls back to video description
2. **LLM Failure**: Uses keyword-based scoring
3. **API Quota**: Continues with available data
4. **Invalid Video**: Skips and continues processing
5. **Network Error**: Retries with exponential backoff

### Logging

All components log errors to console:
```python
print(f"Error processing video {video_id}: {error}")
```

Future: Implement proper logging framework (logging module)

## Performance Characteristics

### Time Complexity

- Question Loading: O(n) where n = number of JSON files
- Query Generation: O(1) per topic (LLM call)
- Video Search: O(q) where q = number of queries
- Transcript Fetching: O(v) where v = number of videos
- Topic Matching: O(v) with LLM calls
- Categorization: O(v)

**Overall:** O(t × (q + v)) where t = topics, q = queries, v = videos

### Space Complexity

- In-memory storage of all videos: O(v)
- Transcript storage: O(v × t_len) where t_len = transcript length
- Results storage: O(v)

**Peak Memory:** ~100MB for 1000 videos with transcripts

### Bottlenecks

1. **LLM API Calls** (slowest): 3-5s per video
2. **Transcript Fetching**: 1-3s per video
3. **Video Search**: 1-2s per query

**Mitigation:** Future parallel processing implementation

## Security Considerations

1. **API Keys:** Never commit to version control
2. **Input Validation:** Sanitize user-provided paths
3. **Rate Limiting:** Respect API quotas
4. **Error Messages:** Don't expose sensitive info
5. **Dependencies:** Keep libraries updated

## Testing Strategy

### Unit Tests (test_system.py)

- ✓ Module imports
- ✓ Question loading
- ✓ Video categorization
- ✓ Query generation (with API key)

### Integration Tests (Future)

- [ ] End-to-end pipeline
- [ ] API mocking for offline tests
- [ ] Error handling validation

### Manual Testing

- ✓ Single topic processing
- ✓ Batch processing
- ✓ Output file generation

## Deployment Considerations

### Production Readiness

- ✅ Modular architecture
- ✅ Error handling
- ✅ API key management
- ✅ Documentation
- ⚠️  No caching (future work)
- ⚠️  No parallel processing (future work)

### Scaling

**Current:** Single-threaded, processes 1 video at a time

**Future:**
- Add Redis caching for search results
- Implement multiprocessing for parallel analysis
- Add queue system for batch jobs
- Deploy as microservice with REST API

### Monitoring

**Current:** Console output

**Future:**
- Structured logging
- Metrics collection (Prometheus)
- Error tracking (Sentry)
- Performance monitoring (DataDog)

## Extension Points

### Easy to Add

1. **New Video Platforms:** Implement in `video_searcher.py`
2. **Custom Quality Metrics:** Modify `video_categorizer.py`
3. **Different LLMs:** Swap in `query_generator.py` & `topic_matcher.py`
4. **Export Formats:** Add exporters (CSV, Excel, etc.)

### Modification Points

1. **Scoring Weights:** Adjust in `_calculate_quality_score()`
2. **Search Filters:** Modify API calls in `video_searcher.py`
3. **Query Templates:** Update prompts in `query_generator.py`
4. **Topic Hierarchy:** Customize in `question_loader.py`

---

## Summary

This architecture provides:
- ✅ **Modularity:** Each component is independent
- ✅ **Scalability:** Can be parallelized and distributed
- ✅ **Extensibility:** Easy to add new features
- ✅ **Reliability:** Graceful degradation on errors
- ✅ **Maintainability:** Clear separation of concerns

**Status:** Production-ready for educational use cases.
