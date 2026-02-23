"""
MongoDB Connection Manager for AI Tutor System
Centralized MongoDB connection and collection access
"""

from pymongo import MongoClient
from typing import List
import atexit
import os
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse

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
        db_name = os.getenv('MONGODB_DB_NAME', 'ai_tutor')
        questions_db_name = os.getenv('MONGODB_QUESTIONS_DB_NAME', 'questions_db')
        is_production = (os.getenv('ENVIRONMENT') or os.getenv('APP_ENV') or os.getenv('NODE_ENV') or '').lower() in {
            'prod', 'production',
        }

        # Get connection string from environment variable
        mongo_uri = os.getenv('MONGODB_URI')
        if not mongo_uri:
            # In non-production, allow mongomock fallback when no URI is configured
            use_mongomock = os.getenv('MONGODB_USE_MONGOMOCK', 'false').lower() == 'true'
            if not is_production and use_mongomock:
                try:
                    import mongomock
                    logger.warning("[MONGODB] No MONGODB_URI set — using mongomock (in-memory)")
                    self._client = mongomock.MongoClient()
                    self._db = self._client[db_name]
                    self._questions_db = self._client[questions_db_name]
                    return
                except ImportError:
                    pass
            raise ValueError(
                "MONGODB_URI not found in environment variables. "
                "Please create a .env file with MONGODB_URI. "
                "See setup-local-env.sh for template values."
            )

        server_selection_timeout_ms = int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT_MS', '5000'))
        connect_timeout_ms = int(os.getenv('MONGODB_CONNECT_TIMEOUT_MS', '5000'))

        errors = []
        for candidate_uri in self._candidate_uris(mongo_uri, db_name):
            redacted_uri = self._redact_mongo_uri(candidate_uri)
            try:
                logger.info(f"[MONGODB] Attempting connection using {redacted_uri}")
                client = MongoClient(
                    candidate_uri,
                    serverSelectionTimeoutMS=server_selection_timeout_ms,
                    connectTimeoutMS=connect_timeout_ms,
                )
                client.admin.command('ping')

                self._client = client
                self._db = self._client[db_name]
                self._questions_db = self._client[questions_db_name]
                logger.info(f"[MONGODB] Connected to database: {db_name}")
                logger.info(f"[MONGODB] Connected to questions database: {questions_db_name}")
                return
            except Exception as e:
                errors.append((redacted_uri, e))
                logger.warning(f"[MONGODB] Connection attempt failed for {redacted_uri}: {e}")

        # ── Mongomock fallback for local dev when no real MongoDB is reachable ──
        use_mongomock = os.getenv('MONGODB_USE_MONGOMOCK', 'false').lower() == 'true'
        if not is_production and (use_mongomock or errors):
            try:
                import mongomock
                logger.warning("[MONGODB] All real connections failed — falling back to mongomock (in-memory)")
                self._client = mongomock.MongoClient()
                self._db = self._client[db_name]
                self._questions_db = self._client[questions_db_name]
                logger.info(f"[MONGODB] Mongomock connected: {db_name}, {questions_db_name}")
                return
            except ImportError:
                logger.warning("[MONGODB] mongomock not installed — cannot use in-memory fallback")

        if errors:
            summary = "; ".join([f"{uri}: {err}" for uri, err in errors])
            logger.error(f"[MONGODB] Connection failed for all candidates. {summary}")
            raise RuntimeError(f"MongoDB connection failed for all configured URIs. {summary}")

    def _candidate_uris(self, primary_uri: str, db_name: str) -> List[str]:
        """Build ordered MongoDB connection candidates."""
        candidates: List[str] = []

        # SRV resolution can fail in restricted local environments.
        # In non-production, try local Mongo automatically as a final fallback.
        is_production = (os.getenv('ENVIRONMENT') or os.getenv('APP_ENV') or os.getenv('NODE_ENV') or '').lower() in {
            'prod',
            'production',
        }
        local_fallback_enabled = os.getenv('MONGODB_ENABLE_LOCAL_FALLBACK', 'true').lower() == 'true'
        prefer_local = os.getenv('MONGODB_PREFER_LOCAL', 'true').lower() == 'true'
        local_uri = None
        if primary_uri.startswith('mongodb+srv://') and local_fallback_enabled and not is_production:
            local_uri = os.getenv('MONGODB_LOCAL_URI', f'mongodb://localhost:27017/{db_name}')
            if local_uri.endswith('/'):
                local_uri = f"{local_uri}{db_name}"
            elif self._uri_has_no_database(local_uri):
                local_uri = f"{local_uri}/{db_name}"

        fallback_uri = os.getenv('MONGODB_URI_FALLBACK')

        if prefer_local and local_uri:
            candidates.append(local_uri)
            candidates.append(primary_uri)
        else:
            candidates.append(primary_uri)
            if local_uri:
                candidates.append(local_uri)

        if fallback_uri:
            candidates.append(fallback_uri)

        deduped: List[str] = []
        seen = set()
        for candidate in candidates:
            if candidate and candidate not in seen:
                deduped.append(candidate)
                seen.add(candidate)
        return deduped

    @staticmethod
    def _uri_has_no_database(uri: str) -> bool:
        parsed = urlparse(uri)
        path = (parsed.path or '').strip()
        return path in ('', '/')

    @staticmethod
    def _redact_mongo_uri(uri: str) -> str:
        parsed = urlparse(uri)
        if parsed.username or parsed.password:
            netloc = parsed.hostname or ''
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            return parsed._replace(netloc=f"***:***@{netloc}").geturl()
        return uri
    
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
    def session_costs(self):
        """Get session_costs collection for tracking API usage and costs"""
        return self._db['session_costs']

    @property
    def question_attempts(self):
        """Get question_attempts collection for future-proof performance tracking"""
        return self._db['question_attempts']

    @property
    def ai_generated_questions(self):
        """Get ai_generated_questions collection for DASH + AI generation integration"""
        return self._db['ai_generated_questions']

    @property
    def ai_question_queue(self):
        """Get ai_question_queue collection for pre-generated question queue"""
        return self._db['ai_question_queue']

    @property
    def generated_curricula(self):
        """Get generated_curricula collection for curriculum generation registry/locking"""
        return self._db['generated_curricula']
    
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

# Ensure connections are cleaned up on process exit
atexit.register(mongo_db.close)
