"""
Managers Package
Shared infrastructure managers for the AI Tutor system
"""

from .mongodb_manager import mongo_db, MongoDBManager
from .user_manager import UserManager, UserProfile, SkillState, QuestionAttempt
from .config_manager import ConfigManager

__all__ = [
    'mongo_db',
    'MongoDBManager',
    'UserManager',
    'UserProfile',
    'SkillState',
    'QuestionAttempt',
    'ConfigManager',
]

