from __future__ import annotations

import threading
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure

from config_manager import ConfigManager

_client: Optional[MongoClient] = None
_lock = threading.Lock()


def get_client() -> MongoClient:
    """Return a singleton MongoDB client."""
    global _client

    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        config = ConfigManager()
        uri = config.get_database_uri()
        if not uri:
            raise ConfigurationError("MONGODB_URI is not set in the environment.")

        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        return _client


def get_database(name: Optional[str] = None):
    """Return the configured MongoDB database."""
    client = get_client()
    config = ConfigManager()
    db_name = name or config.get_database_name()
    return client[db_name]


def ping_database() -> bool:
    """Lightweight connection check."""
    try:
        client = get_client()
        client.admin.command("ping")
        return True
    except (ConnectionFailure, ConfigurationError):
        return False
