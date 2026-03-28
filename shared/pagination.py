"""
Cursor-Based Pagination Utility
Phase 4: Database & Data Access

Implements efficient cursor-based pagination for large datasets.
Better than offset-based pagination for performance and consistency.
"""
from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel, Field
from datetime import datetime
import base64
import json


T = TypeVar('T')


class PaginationCursor(BaseModel):
    """Encoded cursor for pagination"""
    last_id: str
    last_value: Optional[Any] = None  # For sorting by other fields
    
    def encode(self) -> str:
        """Encode cursor to base64 string"""
        cursor_dict = self.dict()
        cursor_json = json.dumps(cursor_dict, default=str)
        return base64.b64encode(cursor_json.encode()).decode()
    
    @classmethod
    def decode(cls, cursor_str: str) -> 'PaginationCursor':
        """Decode cursor from base64 string"""
        try:
            cursor_json = base64.b64decode(cursor_str.encode()).decode()
            cursor_dict = json.loads(cursor_json)
            return cls(**cursor_dict)
        except Exception:
            raise ValueError("Invalid cursor")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response format"""
    items: List[T]
    has_more: bool
    next_cursor: Optional[str] = None
    total_count: Optional[int] = None  # Optional, expensive to compute
    page_size: int
    
    class Config:
        arbitrary_types_allowed = True


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    cursor: Optional[str] = Field(None, description="Pagination cursor from previous response")
    limit: int = Field(20, ge=1, le=100, description="Number of items per page")
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


def paginate_query(
    collection,
    query: Dict[str, Any],
    cursor: Optional[str] = None,
    limit: int = 20,
    sort_field: str = "_id",
    sort_descending: bool = True
) -> PaginatedResponse:
    """
    Apply cursor-based pagination to MongoDB query.
    
    Args:
        collection: MongoDB collection
        query: Base query filter
        cursor: Pagination cursor from previous response
        limit: Number of items to return
        sort_field: Field to sort by (must be indexed!)
        sort_descending: Sort in descending order
    
    Returns:
        PaginatedResponse with items and next cursor
    
    Usage:
        result = paginate_query(
            collection=mongo_db.questions,
            query={"skill_ids": "algebra_1"},
            cursor=request.cursor,
            limit=20,
            sort_field="difficulty",
            sort_descending=False
        )
    """
    # Parse cursor if provided
    if cursor:
        try:
            parsed_cursor = PaginationCursor.decode(cursor)
            
            # Add cursor condition to query
            if sort_descending:
                query[sort_field] = {"$lt": parsed_cursor.last_value}
            else:
                query[sort_field] = {"$gt": parsed_cursor.last_value}
                
        except ValueError:
            # Invalid cursor, start from beginning
            pass
    
    # Fetch one extra item to check if there are more results
    sort_direction = -1 if sort_descending else 1
    items = list(
        collection.find(query)
        .sort(sort_field, sort_direction)
        .limit(limit + 1)
    )
    
    # Check if there are more results
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]  # Remove the extra item
    
    # Generate next cursor
    next_cursor = None
    if has_more and items:
        last_item = items[-1]
        cursor_obj = PaginationCursor(
            last_id=str(last_item.get("_id", "")),
            last_value=last_item.get(sort_field)
        )
        next_cursor = cursor_obj.encode()
    
    return PaginatedResponse(
        items=items,
        has_more=has_more,
        next_cursor=next_cursor,
        page_size=len(items)
    )


def paginate_list(
    items: List[T],
    cursor: Optional[str] = None,
    limit: int = 20
) -> PaginatedResponse[T]:
    """
    Apply cursor-based pagination to in-memory list.
    
    Args:
        items: List of items to paginate
        cursor: Pagination cursor (base64 encoded index)
        limit: Number of items per page
    
    Returns:
        PaginatedResponse with items and next cursor
    
    Usage:
        skills = get_all_skills()
        result = paginate_list(skills, cursor=request.cursor, limit=10)
    """
    start_index = 0
    
    # Decode cursor to get start index
    if cursor:
        try:
            cursor_data = base64.b64decode(cursor.encode()).decode()
            start_index = int(cursor_data)
        except Exception:
            start_index = 0
    
    # Slice items
    end_index = start_index + limit
    page_items = items[start_index:end_index]
    
    # Check if more items exist
    has_more = end_index < len(items)
    
    # Generate next cursor
    next_cursor = None
    if has_more:
        next_cursor = base64.b64encode(str(end_index).encode()).decode()
    
    return PaginatedResponse(
        items=page_items,
        has_more=has_more,
        next_cursor=next_cursor,
        total_count=len(items),
        page_size=len(page_items)
    )


# FastAPI example usage:
"""
from fastapi import Query
from shared.pagination import PaginationParams, paginate_query

@app.get("/api/questions")
def list_questions(
    skill_id: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    query = {}
    if skill_id:
        query["skill_ids"] = skill_id
    
    result = paginate_query(
        collection=mongo_db.questions,
        query=query,
        cursor=cursor,
        limit=limit,
        sort_field="difficulty",
        sort_descending=False
    )
    
    return {
        "questions": result.items,
        "has_more": result.has_more,
        "next_cursor": result.next_cursor,
        "count": result.page_size
    }
"""
