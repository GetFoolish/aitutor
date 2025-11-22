"""
MongoDB Connection Manager for AI Tutor System
Centralized MongoDB connection and collection access
"""

from pymongo import MongoClient
from typing import Optional
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class MongoDBManager:
    """Singleton MongoDB connection manager"""
    
    _instance = None
    _client = None
    _db = None
    
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
            
            self._client = MongoClient(mongo_uri)
            self._db = self._client[db_name]
            
            # Test connection
            self._client.admin.command('ping')
            logger.info(f"[MONGODB] Connected to database: {db_name}")
            
        except Exception as e:
            logger.error(f"[MONGODB] Connection failed: {e}")
            raise
    
    @property
    def db(self):
        """Get database instance"""
        return self._db
    
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
    
    def test_connection(self):
        """Test if MongoDB connection is working"""
        try:
            self._client.admin.command('ping')
            collections = self._db.list_collection_names()
            logger.info(f"[MONGODB] Connection OK. Collections: {collections}")
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

