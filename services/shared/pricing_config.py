"""
API Pricing Configuration for Cost Tracking
"""

# Pricing per API call (in USD) - Legacy, kept for backward compatibility
API_PRICING = {
    "gemini": 0.0001,      # Legacy - not used for token-based tracking
    "openrouter": 0.0002,  # Legacy - not used anymore
    "dash_api": 0.0        # DASH API - Free
}

# gemini-2.5-flash-native-audio-preview-09-2025 Token Pricing (per 1M tokens in USD)
# Used by Tutor API (Live API)
GEMINI_TOKEN_PRICING = {
    "text_input": 0.50,      # Text input
    "audio_input": 3.00,     # Audio/Video input (Live API uses audio)
    "output": 12.00,         # Output tokens (candidates)
    "cached_input": 0.30,    # Cached content tokens (90% discount: 3.00 * 0.1 = 0.30)
    "thinking": 12.00        # Thinking tokens (billed as output tokens)
}

# gemini-2.0-flash-lite Token Pricing (per 1M tokens in USD)
# Used by TeachingAssistant internal API calls (memory, retrieval, consolidation)
GEMINI_FLASH_LITE_PRICING = {
    "input": 0.075,   # Input tokens (text only)
    "output": 0.30    # Output tokens
}

# Session interval progression (in seconds)
COST_TRACKING_INTERVALS = {
    0: 30,      # First 5 minutes: every 30 seconds
    300: 60,    # After 5 minutes: every 1 minute
    900: 300    # After 15 minutes: every 5 minutes
}
