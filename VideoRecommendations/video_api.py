"""
Video Recommendation API Service
Wraps the VideoSearchAgent to provide REST API for skill-based video recommendations
"""

import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json

# Add video_search_agent to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'video_search_agent'))

from main_agent import VideoSearchAgent
from loguru import logger

app = FastAPI(title="Video Recommendation API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize VideoSearchAgent
try:
    video_agent = VideoSearchAgent()
    logger.info("✓ VideoSearchAgent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize VideoSearchAgent: {e}")
    video_agent = None


class RecommendationRequest(BaseModel):
    skill_name: str
    max_videos: int = 3
    min_match_score: int = 60


@app.get("/recommendations/{skill_id}")
async def get_recommendations_by_skill_id(
    skill_id: str,
    max_videos: int = 3,
    min_match_score: int = 60
):
    """
    Get video recommendations for a specific skill ID.
    Maps skill_id to a human-readable topic for video search.
    """
    if not video_agent:
        raise HTTPException(status_code=503, detail="Video agent not initialized")

    # Map skill_id to readable topic
    # Example: "counting_1_10" -> "counting numbers 1 to 10"
    skill_name = skill_id.replace("_", " ")

    try:
        logger.info(f"Searching videos for skill: {skill_name}")

        # Use the video agent to process the topic
        results = video_agent.process_topic(
            topic=skill_name,
            max_videos=max_videos,
            min_match_score=min_match_score
        )

        if not results or "videos" not in results:
            return {"videos": []}

        return {"videos": results["videos"]}

    except Exception as e:
        logger.error(f"Error fetching videos for skill {skill_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend")
async def recommend_by_skill_name(request: RecommendationRequest):
    """
    Get video recommendations by skill name directly.
    """
    if not video_agent:
        raise HTTPException(status_code=503, detail="Video agent not initialized")

    try:
        logger.info(f"Searching videos for topic: {request.skill_name}")

        results = video_agent.process_topic(
            topic=request.skill_name,
            max_videos=request.max_videos,
            min_match_score=request.min_match_score
        )

        if not results or "videos" not in results:
            return {"videos": []}

        return {"videos": results["videos"]}

    except Exception as e:
        logger.error(f"Error fetching videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "video_agent_ready": video_agent is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
