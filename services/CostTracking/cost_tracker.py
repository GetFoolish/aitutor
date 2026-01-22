"""
Cost Tracker - Tracks API call costs for sessions
"""

import os
import asyncio
from datetime import datetime
from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger

logger = get_logger(__name__)


class CostTracker:
    """Track API call costs for a session"""

    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.started_at = datetime.utcnow()

    def start_session(self):
        """Initialize session cost tracking in MongoDB"""
        mongo_db.session_costs.insert_one({
            "session_id": self.session_id,
            "user_id": self.user_id,
            "started_at": self.started_at,
            "ended_at": None,
            "status": "active",
            "api_calls": {
                "tutor_api": {
                    "count": 0,
                    "estimated_cost": 0.0,
                    "prompt_tokens": 0,  # Fresh (non-cached) prompt tokens
                    "cached_content_tokens": 0,  # Cached tokens (90% discount)
                    "output_tokens": 0,  # Output tokens (candidates)
                    "thinking_tokens": 0,  # Thinking tokens (billed as output)
                    "total_tokens": 0,
                    # Modality-based tracking
                    "text_input_tokens": 0,
                    "audio_input_tokens": 0,
                    "video_input_tokens": 0,
                    # Last cumulative values (for delta calculation)
                    "last_cumulative_prompt_tokens": 0,
                    "last_cumulative_candidates_tokens": 0,
                    "last_cumulative_total_tokens": 0,
                    "last_cumulative_cached_tokens": 0,
                    "last_cumulative_thought_tokens": 0,
                    "last_cumulative_text_tokens": 0,
                    "last_cumulative_audio_tokens": 0,
                    "last_cumulative_video_tokens": 0
                },
                "teaching_assistant": {
                    "count": 0,
                    "estimated_cost": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                },
                "dash_api": {"count": 0, "estimated_cost": 0.0}
            },
            "tutor_token_usage": [],
            "total_estimated_cost": 0.0,
            "snapshots": []
        })
        logger.info(f"[COST_TRACKER] Started tracking costs for session {self.session_id}")

    def increment_api_call(self, api_type: str):
        """Increment API call counter for this session"""
        mongo_db.session_costs.update_one(
            {"session_id": self.session_id},
            {"$inc": {f"api_calls.{api_type}.count": 1}}
        )

    async def update_costs(self):
        """Periodic update of cost estimates - runs every interval"""
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()

        # Determine next interval based on elapsed time
        interval = self._get_interval(elapsed)

        # Fetch current API counts
        session = mongo_db.session_costs.find_one({"session_id": self.session_id})

        if not session:
            return

        # Calculate costs
        total_cost = self._calculate_total_cost(session["api_calls"])

        # Update MongoDB
        mongo_db.session_costs.update_one(
            {"session_id": self.session_id},
            {
                "$set": {"total_estimated_cost": total_cost},
                "$push": {
                    "snapshots": {
                        "timestamp": datetime.utcnow(),
                        "interval": f"{interval}s",
                        "api_counts": session["api_calls"],
                        "total_cost": total_cost
                    }
                }
            }
        )

        logger.debug(f"[COST_TRACKER] Updated costs for session {self.session_id}")

        # Schedule next update
        await asyncio.sleep(interval)
        await self.update_costs()

    def _get_interval(self, elapsed: float) -> int:
        """Determine update interval based on session duration"""
        from services.shared.pricing_config import COST_TRACKING_INTERVALS

        for threshold, interval in sorted(COST_TRACKING_INTERVALS.items()):
            if elapsed < threshold:
                return interval
        return 300  # Default to 5 minutes

    def _calculate_total_cost(self, api_calls: dict) -> float:
        """
        Calculate total cost from API calls and token usage
        Uses granular token tracking with cached token discount and modality-based pricing
        """
        from services.shared.pricing_config import API_PRICING, GEMINI_TOKEN_PRICING, GEMINI_FLASH_LITE_PRICING

        total = 0.0
        
        # TeachingAssistant (Gemini Flash-Lite) - token-based
        ta_data = api_calls.get("teaching_assistant", {})
        ta_input_tokens = ta_data.get("input_tokens", 0)
        ta_output_tokens = ta_data.get("output_tokens", 0)
        
        if ta_input_tokens > 0:
            ta_input_cost = (ta_input_tokens / 1_000_000) * GEMINI_FLASH_LITE_PRICING["input"]
            total += ta_input_cost
            logger.debug(f"[COST_CALC] TA input tokens: {ta_input_tokens} = ${round(ta_input_cost, 6)}")
        
        if ta_output_tokens > 0:
            ta_output_cost = (ta_output_tokens / 1_000_000) * GEMINI_FLASH_LITE_PRICING["output"]
            total += ta_output_cost
            logger.debug(f"[COST_CALC] TA output tokens: {ta_output_tokens} = ${round(ta_output_cost, 6)}")
        
        # Tutor API (Gemini Live) - token-based with granular tracking
        tutor_data = api_calls.get("tutor_api", {})
        
        # Get token counts
        fresh_prompt_tokens = tutor_data.get("prompt_tokens", 0)  # Fresh (non-cached) tokens
        cached_tokens = tutor_data.get("cached_content_tokens", 0)  # Cached tokens (90% discount)
        output_tokens = tutor_data.get("output_tokens", 0)  # Output tokens
        thinking_tokens = tutor_data.get("thinking_tokens", 0)  # Thinking tokens (billed as output)
        
        # Modality-based token counts (for accurate pricing)
        text_tokens = tutor_data.get("text_input_tokens", 0)
        audio_tokens = tutor_data.get("audio_input_tokens", 0)
        video_tokens = tutor_data.get("video_input_tokens", 0)
        
        # Calculate costs with modality-based pricing
        # Text input tokens: $0.50/1M
        if text_tokens > 0:
            text_cost = (text_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["text_input"]
            total += text_cost
            logger.debug(f"[COST_CALC] Text tokens: {text_tokens} = ${round(text_cost, 6)}")
        
        # Audio/Video input tokens: $3.00/1M (for non-cached portion)
        # If we have modality breakdown, use it; otherwise use fresh_prompt_tokens as audio
        if audio_tokens > 0 or video_tokens > 0:
            # Use modality breakdown if available
            media_tokens = audio_tokens + video_tokens
            # Only charge for non-cached portion
            # Note: cached tokens are already separated, so media_tokens here are fresh
            if media_tokens > 0:
                media_cost = (media_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["audio_input"]
                total += media_cost
                logger.debug(f"[COST_CALC] Media tokens (audio={audio_tokens}, video={video_tokens}) = ${round(media_cost, 6)}")
        elif fresh_prompt_tokens > 0:
            # Fallback: if no modality breakdown, assume all fresh tokens are audio (Live API default)
            input_cost = (fresh_prompt_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["audio_input"]
            total += input_cost
            logger.debug(f"[COST_CALC] Fresh prompt tokens (no modality breakdown): {fresh_prompt_tokens} = ${round(input_cost, 6)}")
        
        # Cached content tokens: $0.30/1M (90% discount: 3.00 * 0.1 = 0.30)
        if cached_tokens > 0:
            cached_cost = (cached_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["cached_input"]
            total += cached_cost
            logger.debug(f"[COST_CALC] Cached tokens: {cached_tokens} = ${round(cached_cost, 6)} (90% discount applied)")
        
        # Output tokens: $12.00/1M
        if output_tokens > 0:
            output_cost = (output_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["output"]
            total += output_cost
            logger.debug(f"[COST_CALC] Output tokens: {output_tokens} = ${round(output_cost, 6)}")
        
        # Thinking tokens: $12.00/1M (billed as output)
        if thinking_tokens > 0:
            thinking_cost = (thinking_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["thinking"]
            total += thinking_cost
            logger.debug(f"[COST_CALC] Thinking tokens: {thinking_tokens} = ${round(thinking_cost, 6)}")
        
        # DASH API - Free
        total += api_calls.get("dash_api", {}).get("count", 0) * API_PRICING["dash_api"]
        
        return round(total, 4)

    def end_session(self):
        """Finalize session cost tracking"""
        # Fetch current session data
        session = mongo_db.session_costs.find_one({"session_id": self.session_id})
        
        if not session:
            logger.warning(f"[COST_TRACKER] Session {self.session_id} not found for cost calculation")
            # Still mark as ended even if not found
            mongo_db.session_costs.update_one(
                {"session_id": self.session_id},
                {
                    "$set": {
                        "ended_at": datetime.utcnow(),
                        "status": "completed"
                    }
                }
            )
            return
        
        # Get API calls data
        api_calls = session.get("api_calls", {})
        tutor_data = api_calls.get("tutor_api", {})
        
        # Ensure all required API structures exist in api_calls dict
        if "tutor_api" not in api_calls:
            api_calls["tutor_api"] = {}
        if "teaching_assistant" not in api_calls:
            api_calls["teaching_assistant"] = {"count": 0, "estimated_cost": 0.0}
        if "dash_api" not in api_calls:
            api_calls["dash_api"] = {"count": 0, "estimated_cost": 0.0}
        
        # Get all token counts (already calculated as deltas, so no need to recalculate)
        fresh_prompt_tokens = tutor_data.get("prompt_tokens", 0)
        cached_tokens = tutor_data.get("cached_content_tokens", 0)
        output_tokens = tutor_data.get("output_tokens", 0)
        thinking_tokens = tutor_data.get("thinking_tokens", 0)
        total_tokens = tutor_data.get("total_tokens", 0)
        
        # Get modality-based tokens
        text_tokens = tutor_data.get("text_input_tokens", 0)
        audio_tokens = tutor_data.get("audio_input_tokens", 0)
        video_tokens = tutor_data.get("video_input_tokens", 0)
        
        # If output_tokens is 0, calculate from historical token usage records
        # This handles cases where Gemini Live API doesn't return candidatesTokenCount
        if output_tokens == 0:
            try:
                # Get the tutor_token_usage array which has all historical deltas
                tutor_token_usage = session.get("tutor_token_usage", [])
                
                # Calculate total output tokens from the difference between total and prompt deltas
                calculated_output = 0
                for record in tutor_token_usage:
                    delta_total = record.get("delta_total_tokens", 0)
                    delta_prompt = record.get("delta_prompt_tokens", 0)
                    delta_cached = record.get("delta_cached_tokens", 0)
                    
                    # Output tokens = total - prompt - cached (for each turn)
                    turn_output = max(0, delta_total - delta_prompt - delta_cached)
                    calculated_output += turn_output
                
                if calculated_output > 0:
                    # Update output_tokens in the document
                    mongo_db.session_costs.update_one(
                        {"session_id": self.session_id},
                        {"$set": {"api_calls.tutor_api.output_tokens": calculated_output}}
                    )
                    output_tokens = calculated_output
                    # Update api_calls dict for cost calculation
                    api_calls["tutor_api"]["output_tokens"] = calculated_output
                    logger.info(f"[COST_TRACKER] Calculated output_tokens from historical records: {calculated_output}")
            except Exception as calc_error:
                logger.error(f"[COST_TRACKER] Failed to calculate output tokens from history: {calc_error}")
        
        # Calculate total cost using the updated method (handles granular tracking)
        total_cost = self._calculate_total_cost(api_calls)
        
        # Calculate individual API costs for detailed breakdown
        from services.shared.pricing_config import API_PRICING, GEMINI_TOKEN_PRICING, GEMINI_FLASH_LITE_PRICING
        
        # TeachingAssistant cost (token-based)
        ta_data = api_calls.get("teaching_assistant", {})
        ta_input_tokens = ta_data.get("input_tokens", 0)
        ta_output_tokens = ta_data.get("output_tokens", 0)
        
        ta_cost = 0.0
        if ta_input_tokens > 0:
            ta_cost += (ta_input_tokens / 1_000_000) * GEMINI_FLASH_LITE_PRICING["input"]
        if ta_output_tokens > 0:
            ta_cost += (ta_output_tokens / 1_000_000) * GEMINI_FLASH_LITE_PRICING["output"]
        
        # Tutor API cost (granular token-based)
        tutor_cost = 0.0
        
        # Text input tokens
        if text_tokens > 0:
            text_cost = (text_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["text_input"]
            tutor_cost += text_cost
        
        # Audio/Video input tokens (fresh, non-cached)
        if audio_tokens > 0 or video_tokens > 0:
            media_tokens = audio_tokens + video_tokens
            media_cost = (media_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["audio_input"]
            tutor_cost += media_cost
        elif fresh_prompt_tokens > 0:
            # Fallback: assume all fresh tokens are audio
            input_cost = (fresh_prompt_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["audio_input"]
            tutor_cost += input_cost
        
        # Cached tokens (90% discount)
        if cached_tokens > 0:
            cached_cost = (cached_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["cached_input"]
            tutor_cost += cached_cost
        
        # Output tokens
        if output_tokens > 0:
            output_cost = (output_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["output"]
            tutor_cost += output_cost
        
        # Thinking tokens (billed as output)
        if thinking_tokens > 0:
            thinking_cost = (thinking_tokens / 1_000_000) * GEMINI_TOKEN_PRICING["thinking"]
            tutor_cost += thinking_cost
        
        # DASH API is free
        dash_cost = 0.0
        
        # Update MongoDB with final costs
        mongo_db.session_costs.update_one(
            {"session_id": self.session_id},
            {
                "$set": {
                    "ended_at": datetime.utcnow(),
                    "status": "completed",
                    "total_estimated_cost": round(total_cost, 4),
                    "api_calls.tutor_api.estimated_cost": round(tutor_cost, 4),
                    "api_calls.teaching_assistant.estimated_cost": round(ta_cost, 4),
                    "api_calls.dash_api.estimated_cost": dash_cost
                }
            }
        )
        # Log detailed cost breakdown
        logger.info(
            f"[COST_TRACKER] Ended session {self.session_id[:8]}... | "
            f"Total cost: ${round(total_cost, 4)} | "
            f"Tutor API: ${round(tutor_cost, 4)} | "
            f"TA: ${round(ta_cost, 4)} (input={ta_input_tokens}, output={ta_output_tokens}) | "
            f"Tokens: fresh={fresh_prompt_tokens}, cached={cached_tokens}, "
            f"output={output_tokens}, thinking={thinking_tokens} | "
            f"Modality: text={text_tokens}, audio={audio_tokens}, video={video_tokens}"
        )
