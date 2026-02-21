"""
Pytest configuration for AI Tutor project.

Configures Python path and provides common fixtures.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path so imports work correctly
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Ensure services and managers are importable
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """
    Configure pytest before test collection.
    """
    # Add project root to sys.path for all test modules
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
