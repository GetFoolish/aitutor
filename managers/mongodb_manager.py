"""
MongoDB Connection Manager for AI Tutor System
Centralized MongoDB connection and collection access
"""

from pymongo import MongoClient, ReadPreference
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
    _connected = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Don't connect on initialization - use lazy connection
        # This prevents connection errors during module import
        pass
    
    def _connect(self):
        """Establish MongoDB connection"""
        if self._connected and self._client is not None:
            return
        
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
            
            # Configure MongoDB client with SSL/TLS options for Windows compatibility
            # Add connection options to handle SSL handshake issues and replica set problems
            client_options = {
                'serverSelectionTimeoutMS': 30000,  # 30 seconds
                'connectTimeoutMS': 20000,  # 20 seconds
                'socketTimeoutMS': 20000,  # 20 seconds
                'retryWrites': True,
                'retryReads': True,
                # Allow reading from secondaries if primary is unavailable
                'read_preference': ReadPreference.PRIMARY_PREFERRED,  # Try primary first, fallback to secondary
            }
            
            # For Windows SSL compatibility, configure TLS options
            # Use certifi for CA certificates if available (recommended for Windows)
            try:
                import certifi
                client_options['tlsCAFile'] = certifi.where()
                logger.debug("[MONGODB] Using certifi for CA certificates")
            except ImportError:
                logger.debug("[MONGODB] certifi not available, using system certificates")
            
            # Create client with options
            self._client = MongoClient(mongo_uri, **client_options)
            self._db = self._client[db_name]
            
            # Test connection - this is where SSL handshake errors and replica set issues occur
            try:
                # Try to ping with primary preference
                self._client.admin.command('ping')
                self._connected = True
                logger.info(f"[MONGODB] Connected to database: {db_name}")
            except Exception as ping_error:
                error_str = str(ping_error).lower()
                
                # Handle SSL/TLS errors
                if 'ssl' in error_str or 'tls' in error_str or 'handshake' in error_str:
                    logger.warning(f"[MONGODB] SSL handshake failed: {ping_error}")
                    logger.info("[MONGODB] Attempting alternative connection method...")
                    
                    # Close the failed client
                    try:
                        self._client.close()
                    except:
                        pass
                    
                    # Try with explicit TLS configuration and certifi
                    alt_options = client_options.copy()
                    alt_options['tls'] = True
                    try:
                        import certifi
                        alt_options['tlsCAFile'] = certifi.where()
                    except ImportError:
                        pass
                    
                    # Retry connection
                    self._client = MongoClient(mongo_uri, **alt_options)
                    self._db = self._client[db_name]
                    self._client.admin.command('ping')
                    self._connected = True
                    logger.info(f"[MONGODB] Connected to database: {db_name} (using alternative method)")
                
                # Handle replica set issues (no primary available)
                elif 'primary' in error_str or 'replica' in error_str or 'topology' in error_str:
                    logger.warning(f"[MONGODB] Replica set issue detected: {ping_error}")
                    logger.info("[MONGODB] Attempting connection with secondary read preference...")
                    
                    # Close the failed client
                    try:
                        self._client.close()
                    except:
                        pass
                    
                    # Try with secondaryPreferred (allows reading from secondaries)
                    alt_options = client_options.copy()
                    alt_options['read_preference'] = ReadPreference.SECONDARY_PREFERRED  # Prefer secondary, fallback to primary
                    
                    try:
                        # Retry connection
                        self._client = MongoClient(mongo_uri, **alt_options)
                        self._db = self._client[db_name]
                        
                        # Try a simple read operation instead of ping (ping requires primary)
                        # Use a read operation that works with secondaries
                        self._db.list_collection_names()
                        self._connected = True
                        logger.info(f"[MONGODB] Connected to database: {db_name} (using secondary read preference)")
                    except Exception as secondary_error:
                        # If secondaryPreferred also fails, try with nearest (any available node)
                        logger.warning(f"[MONGODB] Secondary read also failed: {secondary_error}")
                        logger.info("[MONGODB] Attempting connection with nearest read preference...")
                        
                        try:
                            self._client.close()
                        except:
                            pass
                        
                        alt_options['read_preference'] = ReadPreference.NEAREST  # Use any available node
                        self._client = MongoClient(mongo_uri, **alt_options)
                        self._db = self._client[db_name]
                        self._db.list_collection_names()
                        self._connected = True
                        logger.info(f"[MONGODB] Connected to database: {db_name} (using nearest read preference)")
                else:
                    # Re-raise if it's not a known error type
                    raise
            
        except Exception as e:
            logger.error(f"[MONGODB] Connection failed: {e}")
            self._connected = False
            raise
    
    @property
    def db(self):
        """Get database instance (lazy connection)"""
        if not self._connected:
            self._connect()
        return self._db
    
    @property
    def users(self):
        """Get users collection"""
        if not self._connected:
            self._connect()
        return self._db['users']
    
    @property
    def perseus_questions(self):
        """Get perseus_questions collection"""
        if not self._connected:
            self._connect()
        return self._db['perseus_questions']
    
    @property
    def dash_questions(self):
        """Get dash_questions collection"""
        if not self._connected:
            self._connect()
        return self._db['dash_questions']
    
    @property
    def skills(self):
        """Get skills collection"""
        if not self._connected:
            self._connect()
        return self._db['skills']
    
    @property
    def generated_skills(self):
        """Get generated_skills collection"""
        if not self._connected:
            self._connect()
        return self._db['generated_skills']
    
    @property
    def scraped_questions(self):
        """Get scraped_questions collection"""
        if not self._connected:
            self._connect()
        return self._db['scraped_questions']
    
    def test_connection(self):
        """Test if MongoDB connection is working"""
        try:
            if not self._connected:
                self._connect()
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

# Create global instance (lazy connection - won't connect until first use)
mongo_db = MongoDBManager()

