"""
Cost Tracking API Endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from managers.mongodb_manager import mongo_db
from shared.auth_middleware import get_current_user
from shared.logging_config import get_logger
from bson import ObjectId
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/cost", tags=["cost-tracking"])


def convert_mongodb_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = convert_mongodb_doc(value)
            elif isinstance(value, list):
                result[key] = [convert_mongodb_doc(item) for item in value]
            else:
                result[key] = value
        return result
    elif isinstance(doc, list):
        return [convert_mongodb_doc(item) for item in doc]
    return doc


@router.get("/session/{session_id}")
async def get_session_costs(session_id: str, request: Request):
    """Get costs for a specific session"""
    user_id = get_current_user(request)

    session_cost = mongo_db.session_costs.find_one({"session_id": session_id})

    if not session_cost:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_cost["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return convert_mongodb_doc(session_cost)


@router.get("/user")
async def get_user_costs(request: Request, limit: int = 10):
    """Get all costs for all users (admin view)"""
    # Authentication check - user must be logged in
    get_current_user(request)

    # Return all sessions, not filtered by user_id
    sessions = list(mongo_db.session_costs.find(
        {}
    ).sort("started_at", -1).limit(limit))

    converted_sessions = [convert_mongodb_doc(session) for session in sessions]

    return {"sessions": converted_sessions}


@router.get("/analytics")
async def get_cost_analytics(request: Request):
    """Cost analytics endpoint (simple - accessible from frontend)"""
    # No admin check - keep it simple as requested
    
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_sessions": {"$sum": 1},
                "avg_cost": {"$avg": "$total_estimated_cost"},
                "total_cost": {"$sum": "$total_estimated_cost"}
            }
        }
    ]

    results = list(mongo_db.session_costs.aggregate(pipeline))

    return results[0] if results else {"total_sessions": 0, "avg_cost": 0, "total_cost": 0}
