"""
Token Usage Tracker for TeachingAssistant Internal LLM Calls
Tracks Gemini 2.0 Flash-Lite API usage for cost calculation
"""

from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger

logger = get_logger(__name__)


def track_ta_tokens(session_id: str, input_tokens: int, output_tokens: int, call_type: str = "unknown"):
    """
    Track token usage for TeachingAssistant internal LLM calls.
    
    Args:
        session_id: The session ID
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        call_type: Type of call (e.g., "memory_extraction", "retrieval_analysis", "closing_generation")
    """
    try:
        if not session_id:
            logger.info("[TA_TOKEN_TRACKER] No session_id provided, skipping tracking")
            return
        
        # Update session_costs with token counts
        mongo_db.session_costs.update_one(
            {"session_id": session_id},
            {
                "$inc": {
                    "api_calls.teaching_assistant.count": 1,
                    "api_calls.teaching_assistant.input_tokens": input_tokens,
                    "api_calls.teaching_assistant.output_tokens": output_tokens,
                    "api_calls.teaching_assistant.total_tokens": input_tokens + output_tokens
                }
            },
            upsert=True
        )
        
        logger.info(
            f"[TA_TOKEN_TRACKER] Tracked {call_type} | "
            f"Session: {session_id[:8]}... | "
            f"Input: {input_tokens}, Output: {output_tokens}"
        )
    except Exception as e:
        logger.error(f"[TA_TOKEN_TRACKER] Failed to track tokens: {e}", exc_info=True)


def extract_and_track_tokens(response, session_id: str, call_type: str = "unknown"):
    """
    Extract token usage from Gemini response and track it.
    
    Args:
        response: Gemini API response object
        session_id: The session ID
        call_type: Type of call (e.g., "memory_extraction", "retrieval_analysis")
        
    Returns:
        Tuple of (input_tokens, output_tokens)
    """
    try:
        # Extract usage metadata from response
        usage = getattr(response, 'usage_metadata', None)
        if not usage:
            logger.info(f"[TA_TOKEN_TRACKER] No usage_metadata in response for {call_type}")
            return (0, 0)
        
        # Get token counts (different field names in different SDK versions)
        input_tokens = (
            getattr(usage, 'prompt_token_count', 0) or 
            getattr(usage, 'input_token_count', 0) or 
            0
        )
        output_tokens = (
            getattr(usage, 'candidates_token_count', 0) or 
            getattr(usage, 'output_token_count', 0) or 
            0
        )
        
        # Track the tokens
        if input_tokens > 0 or output_tokens > 0:
            track_ta_tokens(session_id, input_tokens, output_tokens, call_type)
        
        return (input_tokens, output_tokens)
    except Exception as e:
        logger.error(f"[TA_TOKEN_TRACKER] Error extracting tokens: {e}", exc_info=True)
        return (0, 0)

