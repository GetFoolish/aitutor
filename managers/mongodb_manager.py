"""
MongoDB Connection Manager for AI Tutor System
Centralized MongoDB connection and collection access
"""

from pymongo import MongoClient
from typing import Optional
import os
import logging
from dotenv import load_dotenv

from shared.logging_config import get_logger

logger = get_logger(__name__)


# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class MongoDBManager:
    """Singleton MongoDB connection manager"""
    
    _instance = None
    _client = None
    _db = None
    _questions_db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish MongoDB connection"""
        try:
            # Get connection string from environment variable
            mongo_uri = os.getenv('MONGODB_URI')
            if not mongo_uri:
                raise ValueError(
                    "MONGODB_URI not found in environment variables. "
                    "Please create a .env file with MONGODB_URI. "
                    "See .env.example for template."
                )
            
            db_name = os.getenv('MONGODB_DB_NAME', 'ai_tutor')
            questions_db_name = os.getenv('MONGODB_QUESTIONS_DB_NAME', 'questions_db')
            
            self._client = MongoClient(mongo_uri)
            self._db = self._client[db_name]
            self._questions_db = self._client[questions_db_name]
            
            # Test connection
            self._client.admin.command('ping')
            logger.info(f"[MONGODB] Connected to database: {db_name}")
            logger.info(f"[MONGODB] Connected to questions database: {questions_db_name}")
            
        except Exception as e:
            logger.error(f"[MONGODB] Connection failed: {e}")
            raise
    
    @property
    def db(self):
        """Get main database instance"""
        return self._db
    
    @property
    def questions_db(self):
        """Get questions database instance"""
        return self._questions_db
    
    # Main database collections (ai_tutor)
    @property
    def users(self):
        """Get users collection"""
        return self._db['users']
    
    @property
    def perseus_questions(self):
        """Get perseus_questions collection"""
        return self._db['perseus_questions']
    
    @property
    def dash_questions(self):
        """Get dash_questions collection"""
        return self._db['dash_questions']
    
    @property
    def skills(self):
        """Get skills collection"""
        return self._db['skills']
    
    @property
    def generated_skills(self):
        """Get generated_skills collection"""
        return self._db['generated_skills']
    
    @property
    def scraped_questions(self):
        """Get scraped_questions collection (deprecated - use questions_db)"""
        return self._db['scraped_questions']

    @property
    def subject_assessments(self):
        """Get subject_assessments collection"""
        return self._db['subject_assessments']

    @property
    def sessions(self):
        """Get sessions collection for active tutoring session state"""
        return self._db['sessions']
    
    @property
    def question_attempts(self):
        """Get question_attempts collection for future-proof performance tracking"""
        return self._db['question_attempts']
    
    # Questions database collections (questions_db) - Khan Academy data
    @property
    def regions(self):
        """Get regions collection from questions_db"""
        return self._questions_db['regions']
    
    @property
    def courses(self):
        """Get courses collection from questions_db"""
        return self._questions_db['courses']
    
    @property
    def units(self):
        """Get units collection from questions_db"""
        return self._questions_db['units']
    
    @property
    def lessons(self):
        """Get lessons collection from questions_db"""
        return self._questions_db['lessons']
    
    @property
    def exercises(self):
        """Get exercises collection from questions_db"""
        return self._questions_db['exercises']
    
    @property
    def questions(self):
        """Get questions collection from questions_db"""
        return self._questions_db['questions']
    
    def test_connection(self):
        """Test if MongoDB connection is working"""
        try:
            self._client.admin.command('ping')
            collections = self._db.list_collection_names()
            questions_collections = self._questions_db.list_collection_names()
            logger.info(f"[MONGODB] Connection OK. Main DB collections: {collections}")
            logger.info(f"[MONGODB] Questions DB collections: {questions_collections}")
            return True
        except Exception as e:
            logger.error(f"[MONGODB] Connection test failed: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            logger.info("[MONGODB] Connection closed")

# Create global instance
mongo_db = MongoDBManager()
