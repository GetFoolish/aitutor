"""
Storage Module for Question Bank Generator
Contains database adapters for storing generated questions.
"""

from .base_storage import BaseStorage
from .mongodb_storage import MongoDBStorage

__all__ = ['BaseStorage', 'MongoDBStorage']
