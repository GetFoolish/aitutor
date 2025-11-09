"""
Video Recommendations API
Integrates with the YouTube Video Search Agent to provide educational video recommendations
"""

import os
import sys
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')

# Add video_search_agent to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'video_search_agent'))

from main_agent import VideoSearchAgent

app = FastAPI(title="Video Recommendations API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize video search agent
video_agent = VideoSearchAgent(
    openrouter_api_key=os.getenv('OPENROUTER_API_KEY'),
    youtube_api_key=os.getenv('YOUTUBE_API_KEY'),
    vimeo_api_key=os.getenv('VIMEO_API_KEY')
)

# Cache directory for video results
CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)


class VideoRecommendationRequest(BaseModel):
    skill_name: str
    skill_description: Optional[str] = None
    questions: Optional[List[str]] = None
    max_videos: int = 3
    min_match_score: int = 60


class VideoResult(BaseModel):
    video_id: str
    title: str
    url: str
    thumbnail_url: str
    duration: int
    view_count: int
    channel_title: str
    description: str
    match_score: float
    transcript_available: bool
    language: str
    region: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "video_recommendations"}


@app.post("/recommend", response_model=List[VideoResult])
async def get_video_recommendations(request: VideoRecommendationRequest):
    """
    Get video recommendations for a specific skill or topic
    """
    try:
        # Check cache first
        cache_key = f"{request.skill_name.replace(' ', '_').lower()}.json"
        cache_file = CACHE_DIR / cache_key

        if cache_file.exists():
            print(f"[VideoRec] Loading cached results for {request.skill_name}")
            with open(cache_file, 'r') as f:
                cached_results = json.load(f)
                # Filter by min_match_score
                filtered = [
                    video for video in cached_results
                    if video.get('match_score', 0) >= request.min_match_score
                ]
                return filtered[:request.max_videos]

        # Prepare questions for the agent
        questions_list = []
        if request.questions:
            questions_list = [{"text": q} for q in request.questions]
        elif request.skill_description:
            questions_list = [{"text": request.skill_description}]

        # Search for videos
        print(f"[VideoRec] Searching videos for skill: {request.skill_name}")
        results = video_agent.process_topic(
            topic=request.skill_name,
            questions=questions_list,
            max_videos_per_query=5,
            num_queries=2,
            min_match_score=request.min_match_score
        )

        # Convert to VideoResult format
        video_results = []
        for video in results.get('videos', []):
            video_results.append(VideoResult(
                video_id=video['video_id'],
                title=video['title'],
                url=video['url'],
                thumbnail_url=video.get('thumbnail_url', ''),
                duration=video.get('duration', 0),
                view_count=video.get('view_count', 0),
                channel_title=video.get('channel_title', ''),
                description=video.get('description', ''),
                match_score=video.get('match_score', 0),
                transcript_available=video.get('transcript_available', False),
                language=video.get('language', 'en'),
                region=video.get('region', 'US')
            ))

        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump([v.dict() for v in video_results], f, indent=2)

        # Return top N videos
        return video_results[:request.max_videos]

    except Exception as e:
        print(f"[VideoRec] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/{skill_id}")
async def get_recommendations_by_skill_id(
    skill_id: str,
    max_videos: int = 3,
    min_match_score: int = 60
):
    """
    Get video recommendations for a skill by its ID
    This endpoint integrates with the DASH system to fetch skill metadata
    """
    # TODO: Integrate with DASHSystem to get skill name and description
    # For now, use skill_id as the topic
    skill_name = skill_id.replace('_', ' ').title()

    return await get_video_recommendations(VideoRecommendationRequest(
        skill_name=skill_name,
        max_videos=max_videos,
        min_match_score=min_match_score
    ))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
