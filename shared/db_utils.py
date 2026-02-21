"""
Database Query Optimization Utilities
Provides helpers for pagination, indexing recommendations, and query monitoring.
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import time


@dataclass
class PaginationParams:
    """Standard pagination parameters (Phase 4)"""
    page: int = 1
    limit: int = 20
    max_limit: int = 100
    
    def __post_init__(self):
        # Enforce limits
        if self.limit > self.max_limit:
            self.limit = self.max_limit
        if self.limit < 1:
            self.limit = 1
        if self.page < 1:
            self.page = 1
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.limit
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "page": self.page,
            "limit": self.limit,
            "offset": self.offset
        }


@dataclass
class PaginatedResponse:
    """Standard paginated response format"""
    items: List[Any]
    total: int
    page: int
    limit: int
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        return (self.total + self.limit - 1) // self.limit
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page"""
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page"""
        return self.page > 1
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "items": self.items,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "limit": self.limit,
                "total_pages": self.total_pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev
            }
        }


class QueryMonitor:
    """
    Monitor slow queries and provide indexing recommendations.
    Phase 4: Inventory high-traffic queries and add/fix indexes
    """
    
    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.slow_queries: List[Dict[str, Any]] = []
    
    def monitor_query(self, query_name: str, execution_time: float, params: dict = None):
        """Record query execution time"""
        if execution_time > self.slow_query_threshold:
            self.slow_queries.append({
                "query_name": query_name,
                "execution_time": execution_time,
                "params": params,
                "timestamp": time.time()
            })
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries"""
        return sorted(
            self.slow_queries,
            key=lambda x: x["execution_time"],
            reverse=True
        )[:limit]
    
    def get_recommendations(self) -> List[str]:
        """Get indexing recommendations based on slow queries"""
        recommendations = []
        
        # Analyze slow queries
        query_counts = {}
        for query in self.slow_queries:
            name = query["query_name"]
            query_counts[name] = query_counts.get(name, 0) + 1
        
        # Generate recommendations
        for query_name, count in sorted(query_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 5:
                recommendations.append(
                    f"Consider adding index for '{query_name}' (executed {count} times slowly)"
                )
        
        return recommendations


# Global query monitor instance
query_monitor = QueryMonitor()


def paginate(
    items: List[Any],
    total: int,
    page: int = 1,
    limit: int = 20
) -> PaginatedResponse:
    """
    Helper function to create paginated responses.
    
    Usage:
        results = db.query().all()
        total = db.query().count()
        return paginate(results, total, page=1, limit=20)
    """
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit
    )


# Common index recommendations for MongoDB/PostgreSQL
INDEX_RECOMMENDATIONS = {
    "users": [
        {"field": "email", "type": "unique"},
        {"field": "created_at", "type": "btree"},
    ],
    "sessions": [
        {"field": "user_id", "type": "btree"},
        {"field": "created_at", "type": "btree"},
        {"field": ["user_id", "created_at"], "type": "compound"},
    ],
    "questions": [
        {"field": "difficulty", "type": "btree"},
        {"field": "topic", "type": "btree"},
        {"field": ["topic", "difficulty"], "type": "compound"},
    ]
}
