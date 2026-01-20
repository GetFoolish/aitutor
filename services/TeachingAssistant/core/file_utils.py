"""
File utilities for TeachingAssistant
Centralized file I/O operations with proper error handling.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


def load_json_file(file_path: Path, default: Optional[Dict] = None) -> Optional[Dict]:
    """
    Safely load JSON file with error handling.
    
    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or fails to load
        
    Returns:
        Loaded JSON data or default value
    """
    if not file_path.exists():
        logger.debug(f"JSON file not found: {file_path}")
        return default
    
    try:
        with file_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in file {file_path}: {e}")
        return default
    except Exception as e:
        logger.warning(f"Failed to load JSON from {file_path}: {e}")
        return default


def save_json_file(
    file_path: Path,
    data: Dict[str, Any],
    create_dirs: bool = True,
    indent: int = 2
) -> bool:
    """
    Safely save data to JSON file with error handling.
    
    Args:
        file_path: Path to save the JSON file
        data: Dictionary data to save
        create_dirs: Whether to create parent directories if they don't exist
        indent: JSON indentation level
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with file_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        logger.debug(f"Successfully saved JSON to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False


def ensure_directory(dir_path: Path) -> bool:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        dir_path: Path to the directory
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {dir_path}: {e}")
        return False


def file_exists(file_path: Path) -> bool:
    """
    Check if file exists with proper error handling.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file exists and is a file
    """
    try:
        return file_path.exists() and file_path.is_file()
    except Exception as e:
        logger.warning(f"Error checking file existence {file_path}: {e}")
        return False
