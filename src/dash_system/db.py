from typing import Optional
from pymongo import MongoClient, ASCENDING
from .config import settings

_client: Optional[MongoClient] = None

def get_client() -> MongoClient:
    """Get MongoDB client, create if needed"""
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri)
    return _client

def get_db():
    return get_client()[settings.mongodb_db]

def get_collections():
    db = get_db()
    return db.skills, db.questions, db.users

def ensure_indexes() -> None:
    """Create database indexes for better performance"""
    skills, questions, users = get_collections()
    
    # Skills collection indexes
    skills.create_index([("learning_path", ASCENDING)], name="skills_learning_path_idx")

    # Questions collection indexes - these help with finding questions by skill
    questions.create_index([("skill_ids", ASCENDING)], name="questions_skill_ids_idx")
    questions.create_index([("learning_path", ASCENDING)], name="questions_learning_path_idx")
    questions.create_index([("tags", ASCENDING)], name="questions_tags_idx")

    # Users collection indexes - sparse because not all users have question history
    users.create_index([("question_history.question_id", ASCENDING)], name="users_question_history_qid_idx", sparse=True)
