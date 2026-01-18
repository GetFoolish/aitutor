"""
AI Tutor Agent with Vision Support

This agent implements the Adam persona - a patient, empathetic AI tutor
that uses the Socratic method to guide students to discover answers themselves.

Features:
- Multimodal: Can see student's scratchpad and camera
- Vision-aware: Analyzes student work and provides guided feedback
- DASH integration: Works with adaptive learning system
"""

import asyncio
import os
from typing import Optional
import aiohttp

from livekit import rtc
from livekit.agents import Agent, RunContext
from livekit.agents.llm import ChatContext, ChatMessage, ImageContent

from prompts.system_prompt import load_system_prompt
from tools.dash_tools import DashTools


class TutorAgent(Agent):
    """AI Tutor agent that can see student's work and guide them using Socratic method."""

    def __init__(self):
        """Initialize the tutor agent with Adam persona."""
        self._latest_frame: Optional[rtc.VideoFrame] = None
        self._video_stream: Optional[rtc.VideoStream] = None
        self._tasks: list[asyncio.Task] = []
        self._current_question: Optional[dict] = None
        self._student_id: Optional[str] = None
        self._auth_token: Optional[str] = None
        self._dash_tools: Optional[DashTools] = None

        # Load the Adam tutor system prompt
        system_instructions = load_system_prompt()

        super().__init__(instructions=system_instructions)

    async def on_enter(self) -> None:
        """Called when the agent joins the room.

        Note: The new livekit-agents API calls this without arguments.
        """
        print(f"[TutorAgent] Agent entered session")
        self._student_id = "anonymous"

    async def on_exit(self) -> None:
        """Called when the agent leaves the room."""
        # Clean up video stream
        if self._video_stream is not None:
            await self._video_stream.aclose()
            self._video_stream = None

        # Cancel any pending tasks
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

        # Close DASH tools session
        if self._dash_tools:
            await self._dash_tools.close()

        print(f"[TutorAgent] Left session")

    async def _fetch_current_question(self) -> None:
        """Fetch the current/recommended question from DASH system."""
        if not self._dash_tools:
            return

        result = await self._dash_tools.get_next_question()

        if result.get("success"):
            self._current_question = result.get("question")
            metadata = result.get("metadata", {})

            # Inject question context into instructions
            question_context = f"""

=== CURRENT QUESTION ===
The student is working on the following question:
- Skills being practiced: {', '.join(metadata.get('skill_names', ['Unknown']))}
- Difficulty level: {metadata.get('difficulty', 'Unknown')}
- Question ID: {metadata.get('dash_question_id', 'Unknown')}

Focus your guidance on these specific skills. Remember to use the Socratic method -
never give the answer directly, instead ask guiding questions to help the student
discover the solution themselves.
"""
            # Update instructions with question context
            current_instructions = self.instructions or ""
            await self.update_instructions(current_instructions + question_context)

            print(f"[TutorAgent] Loaded question context: {metadata.get('skill_names', [])}")
        else:
            print(f"[TutorAgent] Could not fetch question: {result.get('error')}")

    async def _setup_video_capture(self, room: rtc.Room) -> None:
        """Set up video stream subscription for scratchpad viewing.

        Subscribes to video tracks published by the student (scratchpad,
        camera, or screen share) to enable the agent to see their work.
        Excludes Hedra avatar video tracks.
        """
        # Check for existing video tracks (exclude Hedra avatar)
        for participant in room.remote_participants.values():
            # Skip Hedra avatar participant - we want user's video, not avatar's
            if 'hedra' in participant.identity.lower():
                print(f"[TutorAgent] Skipping Hedra avatar participant: {participant.identity}")
                continue

            for pub in participant.track_publications.values():
                if pub.track and pub.track.kind == rtc.TrackKind.KIND_VIDEO:
                    await self._create_video_stream(pub.track)
                    break

        # Listen for new video tracks
        @room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant
        ):
            # Skip Hedra avatar video - we want user's scratchpad video
            if 'hedra' in participant.identity.lower():
                print(f"[TutorAgent] Skipping Hedra avatar video track from: {participant.identity}")
                return

            if track.kind == rtc.TrackKind.KIND_VIDEO:
                asyncio.create_task(self._create_video_stream(track))

    async def _create_video_stream(self, track: rtc.Track) -> None:
        """Create a video stream to capture frames from student's video.

        Args:
            track: The video track to stream from
        """
        # Close existing stream if any
        if self._video_stream is not None:
            await self._video_stream.aclose()

        self._video_stream = rtc.VideoStream(track)
        print(f"[TutorAgent] Started video stream from track: {track.name}")

        async def read_stream():
            try:
                async for event in self._video_stream:
                    self._latest_frame = event.frame
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[TutorAgent] Video stream error: {e}")

        task = asyncio.create_task(read_stream())
        self._tasks.append(task)

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage
    ) -> None:
        """Inject the latest video frame before LLM processes the turn.

        This allows the agent to see the student's scratchpad when they
        ask a question, enabling vision-aware tutoring.

        Args:
            turn_ctx: The current chat context
            new_message: The new message from the user
        """
        if self._latest_frame:
            # Add the current scratchpad frame to the message
            new_message.content.append(ImageContent(image=self._latest_frame))
            print("[TutorAgent] Injected scratchpad frame into context")

    def get_tools(self) -> list:
        """Return the tools available to this agent."""
        tools = []

        # Add DASH tools if available
        if self._dash_tools:
            tools.extend([
                self._dash_tools.record_answer_attempt,
                self._dash_tools.get_next_question,
                self._dash_tools.get_skill_scores,
            ])

        return tools
