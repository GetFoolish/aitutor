from typing import Dict
from .db import get_collections

# Global cache for skills - loaded once at startup for speed
SKILLS_CACHE: Dict[str, dict] = {}


def init_skills_cache() -> int:
    """Load all skills into memory for fast lookups"""
    skills, _, _ = get_collections()
    global SKILLS_CACHE
    SKILLS_CACHE = {doc["_id"]: doc for doc in skills.find({}, {"_id": 1, "difficulty": 1, "forgetting_rate": 1, "prerequisites": 1, "learning_path": 1, "name": 1})}
    return len(SKILLS_CACHE)
