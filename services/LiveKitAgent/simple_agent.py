"""
Simple LiveKit Agent for debugging
"""
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession
from livekit.plugins import silero, deepgram, google, cartesia

# Load environment variables
load_dotenv("../../.env")

async def entrypoint(ctx: agents.JobContext):
    """Simple entry point for debugging."""
    print(f"[SimpleAgent] Starting in room: {ctx.room.name}")

    # Create the agent session with configured providers
    session = AgentSession(
        stt=deepgram.STT(model="nova-2-general", language="en"),
        llm=google.LLM(model="gemini-2.0-flash", temperature=0.7),
        tts=cartesia.TTS(voice="a0e99841-438c-4a64-b679-ae501e7d6091", language="en"),
        vad=silero.VAD.load(),
    )

    # Start the session with a simple greeting
    await session.start(room=ctx.room)

    await session.generate_reply(
        instructions="Say hello and introduce yourself as a test agent."
    )

    print("[SimpleAgent] Session started successfully")


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )
