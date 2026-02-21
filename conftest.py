"""
Root conftest.py - Ensures project root is on sys.path for all test files.

This allows test files in services/ subdirectories to use absolute imports
like `from services.DashSystem.content_v1 import ContentV1Engine`.
"""

import os
import sys

# Add project root to sys.path so absolute imports work from any test location
sys.path.insert(0, os.path.dirname(__file__))
