"""
Memory module for TeachingAssistant
"""
from pathlib import Path

def get_memory_data_dir(user_id: str = None) -> Path:
    """
    Get the base directory for memory data storage.
    Returns: Path to services/TeachingAssistant/Memory/data/
    """
    # Get project root (aitutor directory)
    # __file__ is at: aitutor/services/TeachingAssistant/Memory/__init__.py
    # Go up 4 levels to get to aitutor/
    project_root = Path(__file__).parent.parent.parent.parent
    memory_data_dir = project_root / "services" / "TeachingAssistant" / "Memory" / "data"
    
    if user_id:
        return memory_data_dir / user_id
    return memory_data_dir

