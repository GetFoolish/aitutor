"""
LiveKit Agent Entry Point for AI Tutor

This is the main entry point for the LiveKit AI Tutor agent.
Service Rationalization:
- Google Gemini: LLM (intelligence), STT (speech-to-text), TTS (text-to-speech)
- Hedra: Video avatar only

Usage:
    python agent.py dev      # Development mode with auto-reload
    python agent.py start    # Production mode
"""

import os
import sys
import json

from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import AgentSession, room_io
from livekit.plugins import silero, google, hedra
# Note: deepgram and cartesia imports removed - using Gemini for STT/TTS

# Preload VAD model at import time to avoid timeout during worker init
print("[Agent] Preloading Silero VAD model...")
_preloaded_vad = silero.VAD.load()
print("[Agent] VAD model loaded successfully")

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AITUTOR_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # aitutor directory
PROJECT_ROOT = os.path.dirname(AITUTOR_ROOT)  # livekit directory

# Add parent directory to path for imports
sys.path.insert(0, SCRIPT_DIR)

from tutor_agent import TutorAgent

# Load environment variables - check aitutor/.env first, then project root
load_dotenv(os.path.join(AITUTOR_ROOT, ".env.local"))
load_dotenv(os.path.join(AITUTOR_ROOT, ".env"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env.local"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def _sanitize_env_var(name: str) -> str:
    """Strip whitespace and CR/LF from env vars (common on Windows copy/paste)."""
    raw = os.getenv(name)
    if not raw:
        return ""
    cleaned = raw.strip().strip('"').strip("'").replace("\r", "").replace("\n", "")
    if cleaned != raw:
        os.environ[name] = cleaned
    return cleaned


# Normalize common secrets/URLs early so downstream libs see clean values
for _var in (
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "HEDRA_API_KEY",
    "HEDRA_AVATAR_ID",
):
    _sanitize_env_var(_var)

# Configuration - Service Rationalization
# Using Gemini for LLM/STT/TTS (native audio capabilities)
# Using Hedra for video avatar only
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# HEDRA_AVATAR_ID: Must point to an avatar created in Hedra Studio that has a face configured
# To use your own image as the avatar face:
# 1. Go to https://hedra.pro/studio (or https://app.hedra.pro/index.php)
# 2. Upload your image (headshot photo works best - clear face, front-facing)
# 3. Once uploaded, go to your Library
# 4. Hover over your uploaded image, click the three dots (⋯), select "Copy Asset ID"
# 5. Set HEDRA_AVATAR_ID environment variable to that Asset ID in your .env file
# 
# Example: If you uploaded a teacher headshot image, use its Asset ID here
# NOTE: No default value - you must provide your own avatar_id with a face
HEDRA_AVATAR_ID = os.getenv("HEDRA_AVATAR_ID", "")
USE_HEDRA_AVATAR = os.getenv("USE_HEDRA_AVATAR", "true").lower() == "true"


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the AI Tutor LiveKit agent."""
    print(f"[Agent] ========================================")
    print(f"[Agent] Entrypoint called for room: {ctx.room.name}")
    print(f"[Agent] ========================================")
    
    # Reload env vars in worker subprocess
    load_dotenv(os.path.join(AITUTOR_ROOT, ".env.local"))
    load_dotenv(os.path.join(AITUTOR_ROOT, ".env"))

    # Ensure Google API key is available - plugins read from GOOGLE_API_KEY env var
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if google_api_key:
        # Set both GOOGLE_API_KEY and GEMINI_API_KEY for compatibility
        os.environ["GOOGLE_API_KEY"] = google_api_key
        os.environ["GEMINI_API_KEY"] = google_api_key
        print(f"[Agent] ✅ Google API key loaded (length: {len(google_api_key)})")
    else:
        print(f"[Agent] ❌ ERROR: Google API key NOT SET - STT/TTS/LLM will fail!")
        print(f"[Agent] Please set GOOGLE_API_KEY or GEMINI_API_KEY in .env file")
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be set")

    # Get Hedra config fresh
    hedra_avatar_id = os.getenv("HEDRA_AVATAR_ID", "")
    hedra_api_key = os.getenv("HEDRA_API_KEY", "")
    use_hedra = os.getenv("USE_HEDRA_AVATAR", "true").lower() == "true"

    print(f"[Agent] Starting tutoring session in room: {ctx.room.name}")
    print(f"[Agent] Hedra config: USE_HEDRA={use_hedra}, AVATAR_ID={'✅ Set' if hedra_avatar_id else '❌ NOT SET'}, API_KEY={'✅ Set' if hedra_api_key else '❌ NOT SET'}")

    # Create the agent session with rationalized services
    # Service Rationalization: Gemini for LLM/STT/TTS, Hedra for video avatar
    # Note: Gemini Flash 2.5/3 Live has native audio capabilities (STT/TTS)
    # For now, using separate plugins but can migrate to Gemini native audio later
    print(f"[Agent] Creating AgentSession with Google services...")
    print(f"[Agent] Using API key (length: {len(google_api_key)}) for Google services")
    try:
        # Prepare credentials_info dict for STT/TTS (they need credentials_info)
        # For API key-based auth, we pass it in credentials_info
        credentials_dict = {"api_key": google_api_key}
        
        session = AgentSession(
            # Speech-to-Text: Google STT
            # Pass API key via credentials_info parameter
            stt=google.STT(
                credentials_info=credentials_dict,
            ),
            # LLM: Google Gemini Flash - provides super intelligence
            # LLM accepts api_key parameter directly
            llm=google.LLM(
                model=GEMINI_MODEL,
                temperature=0.7,
                api_key=google_api_key,
            ),
            # Text-to-Speech: Google TTS
            # Pass API key via credentials_info parameter
            # Note: Hedra requires 24000 Hz sample rate for proper lip sync
            tts=google.TTS(
                voice_name="Aoede",  # Default Gemini voice
                sample_rate=24000,  # Hedra requires 24kHz for proper lip sync
                credentials_info=credentials_dict,
            ),
            # Voice Activity Detection: Silero
            # VAD ensures avatar is silent when student is talking
            # When student speaks, VAD detects it and avatar won't generate speech
            vad=_preloaded_vad,
        )
        print(f"[Agent] ✅ AgentSession created successfully")
    except Exception as e:
        print(f"[Agent] ❌ ERROR: Failed to create AgentSession: {e}")
        import traceback
        traceback.print_exc()
        raise

    # Create the tutor agent
    tutor = TutorAgent()

    # Start Hedra video avatar BEFORE session.start() for proper audio routing
    # The avatar worker intercepts audio so lips sync with speech
    avatar = None
    use_avatar = use_hedra and hedra_avatar_id

    if use_avatar:
        try:
            print(f"[Agent] ========================================")
            print(f"[Agent] Starting Hedra video avatar")
            print(f"[Agent] Avatar ID: {hedra_avatar_id}")
            print(f"[Agent] Room: {ctx.room.name}")
            print(f"[Agent] ========================================")
            
            # Create Hedra avatar session with teacher face
            # The avatar_id must point to an avatar created in Hedra Studio that has a teacher face
            # Hedra automatically uses the face associated with the avatar_id
            # The avatar will:
            # - Show natural expressions based on speech (lip sync, facial movements)
            # - Be silent when student is talking (VAD handles this automatically)
            # - Display teacher-like appearance and behavior
            avatar = hedra.AvatarSession(
                avatar_id=hedra_avatar_id,
            )
            
            print("[Agent] AvatarSession created, starting avatar...")
            # Start avatar first - this sets up audio routing before session starts
            # IMPORTANT: avatar.start() automatically intercepts TTS audio from the session
            # The avatar will ONLY receive TTS audio, NOT user microphone audio
            # Expressions and lip sync happen automatically based on TTS audio only
            # VAD ensures TTS stops when user speaks, so avatar won't react to user audio
            await avatar.start(session, room=ctx.room)
            print("[Agent] Avatar started - configured to receive TTS audio only (not user microphone)")
            
            print("[Agent] ========================================")
            print("[Agent] ✅ Hedra teacher avatar started successfully!")
            print("[Agent] - Face: Using image from Hedra Studio")
            print("[Agent] - Expressions: Automatic (lip sync, facial movements)")
            print("[Agent] - Silent when student talks: Enabled via VAD")
            print("[Agent] - Video track: Published to LiveKit room")
            print(f"[Agent] - Room name: {ctx.room.name}")
            print("[Agent] ========================================")
            print("[Agent] NOTE: Frontend must connect to LiveKit room to see avatar")
            print("[Agent] The avatar video is published to the LiveKit room")
            print("[Agent] ========================================")
        except Exception as e:
            print(f"[Agent] ========================================")
            print(f"[Agent] ❌ ERROR: Failed to start Hedra avatar!")
            print(f"[Agent] Error: {e}")
            print(f"[Agent] ========================================")
            print("[Agent] Troubleshooting:")
            print(f"[Agent] 1. Check HEDRA_API_KEY is set: {'✅' if os.getenv('HEDRA_API_KEY') else '❌ NOT SET'}")
            print(f"[Agent] 2. Check HEDRA_AVATAR_ID is set: {'✅' if hedra_avatar_id else '❌ NOT SET'}")
            print(f"[Agent] 3. Verify avatar_id exists in Hedra Studio")
            print(f"[Agent] 4. Check Hedra API key is valid")
            print(f"[Agent] ========================================")
            import traceback
            traceback.print_exc()
            print("[Agent] Continuing without video avatar")
            use_avatar = False  # Fall back to direct audio
    elif use_hedra:
        print("[Agent] ERROR: Hedra enabled but HEDRA_AVATAR_ID is not set!")
        print("[Agent] To use your image as the avatar:")
        print("[Agent] 1. Go to https://hedra.pro/studio")
        print("[Agent] 2. Upload your image (headshot photo with clear face)")
        print("[Agent] 3. In Library, hover over image → three dots → 'Copy Asset ID'")
        print("[Agent] 4. Set HEDRA_AVATAR_ID in .env file to that Asset ID")
        print("[Agent] See upload_avatar_image.md for detailed instructions")
        print("[Agent] Continuing without video avatar")

    # Configure room options
    # Note: When using avatar, the avatar.start() call already sets up audio routing
    # audio_output=False ensures user microphone audio doesn't go to avatar
    # The avatar only receives TTS audio from the session, not user input
    room_options = room_io.RoomOptions(
        audio_input=True,  # We need to hear the user
        audio_output=False if use_avatar else True,  # Disable audio output to room when using avatar (avatar handles it)
        video_input=True,
    )

    print(f"[Agent] Room options: audio_input=True, video_input=True, use_avatar={use_avatar}")

    # Start the session AFTER avatar is set up
    print(f"[Agent] Starting session in room: {ctx.room.name}...")
    try:
        await session.start(
            room=ctx.room,
            agent=tutor,
            room_options=room_options,
        )
        print(f"[Agent] ✅ Session started successfully in room: {ctx.room.name}")
        local_participant = ctx.room.local_participant
        print(f"[Agent] Room participants: {len(ctx.room.remote_participants)} remote, local_participant={'✅' if local_participant else '❌'}")
    except Exception as e:
        print(f"[Agent] ❌ ERROR: Failed to start session: {e}")
        import traceback
        traceback.print_exc()
        raise

    # Set up video capture for scratchpad viewing
    print(f"[Agent] Setting up video capture for scratchpad...")
    await tutor._setup_video_capture(ctx.room)

    print(f"[Agent] ✅ Tutoring session fully initialized in room: {ctx.room.name}")
    print(f"[Agent] Agent is now a participant in the room and ready to interact")

    # Send initial greeting in background (non-blocking for faster startup)
    # The avatar will speak this greeting with natural expressions
    # When student talks, VAD will detect it and avatar will be silent
    import asyncio
    asyncio.create_task(session.generate_reply(
        instructions="""Greet the student warmly as Professor Nova, their expert private teacher.
        Address them as "my student" or by their name if provided.
        Let them know you can see their scratchpad and are ready to help them work through the problem.
        Keep the greeting very brief (1-2 sentences max), warm and encouraging.
        Your tone should be professional yet warm, like a caring teacher.
        
        IMPORTANT: When the student is speaking, remain silent and listen.
        Only speak when the student has finished talking or asks a question.
        Use natural expressions and be engaging like a real teacher."""
    ))


def main():
    """Main function to run the agent server."""
    # Validate required environment variables
    # Service Rationalization: Only need Gemini and Hedra keys
    # Note: GOOGLE_API_KEY or GEMINI_API_KEY can be used for Google services
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    required_vars = {
        "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
        "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"),
        "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
        "GOOGLE_API_KEY or GEMINI_API_KEY": google_key,
        "HEDRA_API_KEY": os.getenv("HEDRA_API_KEY"),
        "HEDRA_AVATAR_ID": os.getenv("HEDRA_AVATAR_ID"),
    }
    
    # Optional (for future migration to Gemini native audio)
    optional_vars = [
        "DEEPGRAM_API_KEY",  # Can be removed after full Gemini migration
        "CARTESIA_API_KEY",  # Can be removed after full Gemini migration
    ]

    missing = [var for var, value in required_vars.items() if not value]
    if missing:
        print(f"[Agent] Warning: Missing environment variables: {', '.join(missing)}")
        print("[Agent] Please copy .env.example to .env.local and fill in your API keys")

    # Fail fast if LiveKit credentials are rejected (prevents endless 401 retry spam)
    livekit_url = _sanitize_env_var("LIVEKIT_URL")
    livekit_api_key = _sanitize_env_var("LIVEKIT_API_KEY")
    livekit_api_secret = _sanitize_env_var("LIVEKIT_API_SECRET")

    if livekit_url and livekit_api_key and livekit_api_secret:
        import asyncio

        async def _preflight_livekit() -> None:
            from livekit import api as lk_api
            from livekit.protocol import room as room_proto

            # LiveKit API uses HTTP(S); convert WS(S) URLs if provided
            http_url = livekit_url
            if http_url.startswith("wss://"):
                http_url = "https://" + http_url[len("wss://"):]
            elif http_url.startswith("ws://"):
                http_url = "http://" + http_url[len("ws://"):]

            lk = lk_api.LiveKitAPI(url=http_url, api_key=livekit_api_key, api_secret=livekit_api_secret)
            try:
                await lk.room.list_rooms(room_proto.ListRoomsRequest())
                print("[Agent] ✅ LiveKit credentials validated (list_rooms ok)")
            finally:
                await lk.aclose()

        try:
            asyncio.run(_preflight_livekit())
        except Exception as e:
            safe_url = (livekit_url or "").split("?")[0]
            key_suffix = livekit_api_key[-4:] if livekit_api_key else "????"
            print("[Agent] ❌ ERROR: LiveKit credential preflight failed")
            print(f"[Agent] - LIVEKIT_URL: {safe_url}")
            print(f"[Agent] - LIVEKIT_API_KEY: ****{key_suffix} (len={len(livekit_api_key)})")
            print("[Agent] This usually means LIVEKIT_API_KEY / LIVEKIT_API_SECRET do not match the LiveKit project for LIVEKIT_URL.")
            print(f"[Agent] Underlying error: {type(e).__name__}: {e}")
            raise

    # Run the agent with a unique name to avoid stale worker conflicts
    import time
    unique_agent_name = f"ai-tutor-{int(time.time())}"
    print(f"[Agent] Registering with unique name: {unique_agent_name}")

    # Write agent name to file for DASH API to read
    agent_name_file = os.path.join(AITUTOR_ROOT, ".current_agent_name")
    with open(agent_name_file, "w") as f:
        f.write(unique_agent_name)
    print(f"[Agent] Wrote agent name to {agent_name_file}")

    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=unique_agent_name,
        ),
    )


if __name__ == "__main__":
    main()
