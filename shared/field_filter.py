"""
API Response Field Filtering Utility
Phase 3: Backend & API Optimization - Payload Reduction

Allows clients to specify which fields they need, reducing bandwidth and improving performance.
"""
from typing import Any, Optional, Set
from pydantic import BaseModel


def filter_fields(data: Any, fields: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None) -> Any:
    """
    Filter dictionary or list of dictionaries to include only specified fields.
    
    Args:
        data: Dictionary or list of dictionaries to filter
        fields: Set of field names to include (if None, include all)
        exclude: Set of field names to exclude
    
    Returns:
        Filtered data with only requested fields
    
    Usage:
        # Include only specific fields
        filtered = filter_fields(user_data, fields={'user_id', 'name', 'email'})
        
        # Exclude specific fields
        filtered = filter_fields(user_data, exclude={'password_hash', 'internal_id'})
    """
    if data is None:
        return None
    
    # Handle list of items
    if isinstance(data, list):
        return [filter_fields(item, fields, exclude) for item in data]
    
    # Handle single dictionary
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Skip if in exclude list
            if exclude and key in exclude:
                continue
            
            # Skip if fields specified and key not in fields
            if fields and key not in fields:
                continue
            
            # Recursively filter nested objects
            if isinstance(value, (dict, list)):
                result[key] = filter_fields(value, fields, exclude)
            else:
                result[key] = value
        
        return result
    
    # Return as-is for non-dict/list types
    return data


def parse_fields_query(fields_str: Optional[str]) -> Optional[Set[str]]:
    """
    Parse comma-separated fields string into a set.
    
    Args:
        fields_str: Comma-separated string like "user_id,name,email"
    
    Returns:
        Set of field names, or None if no fields specified
    
    Usage:
        fields = parse_fields_query(request.query_params.get('fields'))
        filtered_data = filter_fields(data, fields=fields)
    """
    if not fields_str:
        return None
    
    return set(f.strip() for f in fields_str.split(',') if f.strip())


# Pydantic model for responses with field filtering support
class FilterableResponse(BaseModel):
    """Base model that supports field filtering"""
    
    def dict_filtered(self, fields: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None, **kwargs):
        """
        Convert to dict with field filtering applied.
        
        Args:
            fields: Set of fields to include
            exclude: Set of fields to exclude
            **kwargs: Additional arguments to pass to dict()
        
        Returns:
            Filtered dictionary
        """
        full_dict = self.dict(**kwargs)
        return filter_fields(full_dict, fields=fields, exclude=exclude)
    
    class Config:
        # Allow filtering in JSON responses
        json_encoders = {
            # Add custom encoders if needed
        }


# Common field sets for different use cases
FIELD_SETS = {
    # Minimal user info (for listings)
    'user_minimal': {'user_id', 'name', 'current_grade'},
    
    # Basic user info (for cards/previews)
    'user_basic': {'user_id', 'name', 'email', 'current_grade', 'picture'},
    
    # Full user profile
    'user_full': {
        'user_id', 'name', 'email', 'age', 'current_grade', 'user_type',
        'picture', 'subjects', 'learning_goals', 'interests', 'learning_style',
        'created_at', 'last_login'
    },
    
    # Question minimal (for lists)
    'question_minimal': {'question_id', 'skill_ids', 'difficulty'},
    
    # Question with metadata
    'question_with_meta': {
        'question_id', 'skill_ids', 'difficulty', 'expected_time_seconds',
        'skill_names', 'slug'
    },
    
    # Skill state summary
    'skill_summary': {
        'name', 'memory_strength', 'accuracy', 'practice_count'
    },
    
    # Skill state detailed
    'skill_detailed': {
        'name', 'memory_strength', 'probability', 'practice_count',
        'correct_count', 'accuracy', 'last_practice_time'
    }
}


def get_field_set(preset: str) -> Set[str]:
    """
    Get predefined field set by name.
    
    Args:
        preset: Name of preset field set (e.g., 'user_minimal')
    
    Returns:
        Set of field names
    
    Raises:
        ValueError: If preset not found
    """
    if preset not in FIELD_SETS:
        raise ValueError(f"Unknown field preset: {preset}. Available: {list(FIELD_SETS.keys())}")
    
    return FIELD_SETS[preset].copy()


# Decorator for FastAPI endpoints to auto-filter responses
def filterable_response(default_exclude: Optional[Set[str]] = None):
    """
    Decorator to make endpoint responses filterable via query parameters.
    
    Usage:
        @app.get("/users/{user_id}")
        @filterable_response(default_exclude={'password_hash', 'internal_notes'})
        def get_user(user_id: str, fields: Optional[str] = Query(None)):
            user = get_user_from_db(user_id)
            return user  # Will be automatically filtered
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get fields from query params if available
            fields_param = kwargs.get('fields')
            exclude_param = kwargs.get('exclude')
            
            # Parse field sets
            fields = parse_fields_query(fields_param) if fields_param else None
            exclude = parse_fields_query(exclude_param) if exclude_param else default_exclude
            
            # Call original function
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Filter response
            return filter_fields(result, fields=fields, exclude=exclude)
        
        return wrapper
    return decorator


# Example usage in FastAPI:
"""
from fastapi import Query
from shared.field_filter import filter_fields, parse_fields_query, FIELD_SETS

@app.get("/api/users/{user_id}")
def get_user(
    user_id: str,
    fields: Optional[str] = Query(None, description="Comma-separated fields to include"),
    preset: Optional[str] = Query(None, description="Preset field set (user_minimal, user_basic, user_full)")
):
    user_data = user_manager.get_user(user_id)
    
    if preset:
        field_set = FIELD_SETS.get(preset)
        return filter_fields(user_data, fields=field_set)
    
    if fields:
        field_set = parse_fields_query(fields)
        return filter_fields(user_data, fields=field_set)
    
    return user_data
"""
