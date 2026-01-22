"""
LiveKit Agent Entry Point for AI Tutor

This is the main entry point for the LiveKit AI Tutor agent.
Uses Deepgram STT, Gemini LLM, and Cartesia TTS.

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
from livekit.plugins import silero, deepgram, google, cartesia, hedra
from PIL import Image

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
from tools.scratchpad_tools import set_room as set_scratchpad_room, get_scratchpad_tools

# Load environment variables - check aitutor/.env first, then project root
load_dotenv(os.path.join(AITUTOR_ROOT, ".env.local"))
load_dotenv(os.path.join(AITUTOR_ROOT, ".env"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env.local"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Configuration
DEEPGRAM_MODEL = "nova-2-general"
GEMINI_MODEL = "gemini-2.0-flash"
USE_HEDRA_AVATAR = os.getenv("USE_HEDRA_AVATAR", "true").lower() == "true"
# Avatar image path - same image used for intro videos to ensure consistent appearance
AVATAR_IMAGE_FILENAME = "avatar-ms-davis-clean.png"


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the AI Tutor LiveKit agent."""
    # Reload env vars in worker subprocess
    load_dotenv(os.path.join(AITUTOR_ROOT, ".env.local"))
    load_dotenv(os.path.join(AITUTOR_ROOT, ".env"))

    # Get Hedra config fresh
    use_hedra = os.getenv("USE_HEDRA_AVATAR", "true").lower() == "true"
    # Use consistent avatar image for both intro videos and live sessions
    avatar_image_path = os.path.join(AITUTOR_ROOT, "frontend", "public", "avatar-ms-davis-clean.png")

    print(f"[Agent] Starting tutoring session in room: {ctx.room.name}")
    print(f"[Agent] Hedra config: USE_HEDRA={use_hedra}, AVATAR_IMAGE={avatar_image_path}")

    # Set up scratchpad drawing tools with room access
    set_scratchpad_room(ctx.room)
    scratchpad_tools = get_scratchpad_tools()
    print(f"[Agent] Initialized {len(scratchpad_tools)} scratchpad drawing tools")

    # Create the agent session with traditional STT + LLM + TTS pipeline
    # Include scratchpad tools as function tools for the LLM
    session = AgentSession(
        # Speech-to-Text: Deepgram Nova 2
        stt=deepgram.STT(
            model=DEEPGRAM_MODEL,
            language="en",
        ),
        # LLM: Google Gemini with function calling for scratchpad tools
        llm=google.LLM(
            model=GEMINI_MODEL,
            temperature=0.7,
        ),
        # Text-to-Speech: Cartesia Sonic
        # IMPORTANT: Use 16000 Hz sample rate to match Hedra avatar requirements
        tts=cartesia.TTS(
            model="sonic-2",
            voice="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
            sample_rate=16000,  # Must match Hedra's expected sample rate for lip sync
        ),
        # Voice Activity Detection: Silero
        vad=_preloaded_vad,
        # Register scratchpad drawing tools for AI to use
        tools=scratchpad_tools,
    )

    # Create the tutor agent
    tutor = TutorAgent()

    # Start Hedra video avatar BEFORE session.start() for proper audio routing
    # The avatar worker intercepts audio so lips sync with speech
    avatar = None
    use_avatar = use_hedra and os.path.exists(avatar_image_path)

    if use_avatar:
        try:
            print(f"[Agent] Loading avatar image from: {avatar_image_path}")
            avatar_img = Image.open(avatar_image_path)
            # Convert RGBA to RGB (Hedra requires JPEG format which doesn't support alpha)
            if avatar_img.mode == 'RGBA':
                avatar_img = avatar_img.convert('RGB')
            print(f"[Agent] Starting Hedra video avatar with image ({avatar_img.size}, mode={avatar_img.mode})")
            avatar = hedra.AvatarSession(
                avatar_image=avatar_img,
            )
            # Start avatar first - this sets up audio routing before session starts
            await avatar.start(session, room=ctx.room)
            print("[Agent] Hedra avatar started successfully - audio will route through avatar")
        except Exception as e:
            print(f"[Agent] Failed to start Hedra avatar: {e}")
            import traceback
            traceback.print_exc()
            print("[Agent] Continuing without video avatar")
            use_avatar = False  # Fall back to direct audio
    elif use_hedra:
        print(f"[Agent] Hedra enabled but avatar image not found at {avatar_image_path}")

    # Configure room options
    # Note: When using avatar, the avatar.start() call already sets up audio routing
    # We don't need to explicitly disable audio_output
    room_options = room_io.RoomOptions(
        audio_input=True,
        video_input=True,
    )

    print(f"[Agent] Room options: audio_input=True, video_input=True, use_avatar={use_avatar}")

    # Start the session AFTER avatar is set up
    await session.start(
        room=ctx.room,
        agent=tutor,
        room_options=room_options,
    )

    # Set up video capture for scratchpad viewing
    await tutor._setup_video_capture(ctx.room)

    print("[Agent] Tutoring session started successfully")

    # Send initial greeting in background (non-blocking for faster startup)
    import asyncio
    asyncio.create_task(session.generate_reply(
        instructions="""Greet the student warmly as Ms Davis, their AI math tutor.
        You have a friendly British accent. Let them know you can see their
        scratchpad and are ready to help them work through the problem.
        Keep the greeting very brief (1-2 sentences max), warm and encouraging."""
    ))


def main():
    """Main function to run the agent server."""
    # Validate required environment variables
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "DEEPGRAM_API_KEY",
        "GOOGLE_API_KEY",
        "CARTESIA_API_KEY",
        "HEDRA_API_KEY",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"[Agent] Warning: Missing environment variables: {', '.join(missing)}")
        print("[Agent] Please copy .env.example to .env.local and fill in your API keys")

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
