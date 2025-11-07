# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License

import asyncio
import os
import base64
import websockets
import aiohttp
from PIL import Image
import io
import json
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger


from pipecat.frames.frames import LLMRunFrame, InputImageRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.runner.types import RunnerArguments, DailyRunnerArguments
from pipecat.runner.utils import (
    maybe_capture_participant_camera,
    maybe_capture_participant_screen,
)
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

load_dotenv(override=True)

# Dash API configuration
DASH_API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")

# Global set to track frontend WebSocket clients for question synchronization
frontend_clients = set()

# Global variable to track active session (only allow one concurrent session)
active_session = None
session_lock = asyncio.Lock()

# Krisp noise filtering - enable in production/cloud deployments
ENV = os.getenv("ENV", "local")
krisp_filter = None

if ENV != "local":
    try:
        from pipecat.audio.filters.krisp_filter import KrispFilter
        krisp_filter = KrispFilter()
        logger.info("Krisp noise filtering enabled for production")
    except ImportError:
        logger.warning("Krisp filter not available - install pipecat-ai[krisp]")

# We store functions so objects (e.g. SileroVADAnalyzer) don't get
# instantiated. The function will be called when the desired transport gets
# selected.
transport_params = {
    "daily": lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_in_enabled=True,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        vad_audio_passthrough=True,
        audio_in_filter=krisp_filter,
        turn_analyzer=LocalSmartTurnAnalyzerV3(),
    ),
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_in_enabled=True,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        turn_analyzer=LocalSmartTurnAnalyzerV3(),
    ),
}


async def mediamixer_video_receiver(transport, llm):
    """Connect to MediaMixer WebSocket and send video frames to Gemini"""
    mediamixer_url = os.getenv("MEDIAMIXER_VIDEO_URL", "ws://localhost:8766")
    logger.info(f"Connecting to MediaMixer at {mediamixer_url}")

    frame_count = 0
    last_sent_time = 0
    frame_interval = 1.0  # Send 1 frame every second (1 FPS) for better responsiveness

    try:
        async with websockets.connect(
            mediamixer_url,
            max_size=None,  # Allow high-resolution frames (>1 MB) from MediaMixer
            max_queue=1,    # Avoid buffering too many large frames in memory
        ) as websocket:
            logger.info("Connected to MediaMixer video stream (throttled to 1 FPS)")

            async for message in websocket:
                try:
                    # Throttle frame rate - only send every 2 seconds
                    import time
                    current_time = time.time()
                    if current_time - last_sent_time < frame_interval:
                        continue  # Skip this frame
                    last_sent_time = current_time

                    # MediaMixer sends base64 JPEG frames
                    frame_data = base64.b64decode(message)

                    # Decode JPEG to raw RGB pixels
                    image = Image.open(io.BytesIO(frame_data))
                    # Convert to RGB if needed (in case it's RGBA or other format)
                    if image.mode != 'RGB':
                        image = image.convert('RGB')

                    # Get raw pixel data
                    width, height = image.size
                    rgb_data = image.tobytes()

                    # Create InputImageRawFrame for Gemini with raw RGB data
                    image_frame = InputImageRawFrame(
                        image=rgb_data,
                        size=(width, height),
                        format="RGB"
                    )

                    # Push frame through the transport input (correct method)
                    await transport.input().push_video_frame(image_frame)

                    frame_count += 1
                    logger.debug(f"Sent MediaMixer frame #{frame_count} ({width}x{height}) to Gemini")

                except Exception as e:
                    logger.error(f"Error processing MediaMixer frame: {e}")

    except Exception as e:
        if isinstance(e, websockets.exceptions.ConnectionClosedError):
            logger.error(
                f"MediaMixer connection closed (code={e.code}, reason={e.reason})"
            )
        else:
            logger.error(f"MediaMixer connection error: {e}")


async def broadcast_question_update(question_data: dict):
    """Send question update to standalone sync server"""
    if not question_data:
        return

    message = json.dumps({
        "type": "question_update",
        "question_id": question_data.get("question_id"),
        "question_data": question_data
    })

    # Send to standalone sync server on port 8768
    try:
        async with websockets.connect('ws://localhost:8768', open_timeout=1) as ws:
            await ws.send(message)
            logger.info(f"Sent question {question_data.get('question_id')} to sync server")
    except Exception as e:
        logger.warning(f"Could not send question to sync server: {e}")


async def frontend_sync_server():
    """WebSocket server for frontend question synchronization"""
    async def handle_client(websocket, path):
        """Handle a frontend client connection"""
        frontend_clients.add(websocket)
        logger.info(f"Frontend client connected for question sync. Total clients: {len(frontend_clients)}")

        try:
            async for message in websocket:
                # Frontend might send ping/pong or other messages
                logger.debug(f"Received message from frontend: {message}")
        except Exception as e:
            logger.error(f"Frontend client error: {e}")
        finally:
            frontend_clients.remove(websocket)
            logger.info(f"Frontend client disconnected. Total clients: {len(frontend_clients)}")

    # Start WebSocket server on port 8767
    sync_port = int(os.getenv("FRONTEND_SYNC_PORT", "8767"))
    logger.info(f"Starting frontend sync WebSocket server on port {sync_port}")

    async with websockets.serve(handle_client, "localhost", sync_port):
        await asyncio.Future()  # Run forever


# Dash API integration functions
async def fetch_next_question(user_id: str) -> dict:
    """Fetch the next question from Dash API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DASH_API_URL}/next-question/{user_id}") as response:
                if response.status == 200:
                    question_data = await response.json()
                    logger.info(f"Fetched question {question_data['question_id']} for user {user_id}")
                    return question_data
                else:
                    logger.error(f"Failed to fetch question: HTTP {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching question from Dash API: {e}")
        return None


async def submit_answer_to_dash(user_id: str, question_id: str, skill_ids: list,
                                 is_correct: bool, response_time_seconds: float) -> dict:
    """Submit answer to Dash API"""
    try:
        submission = {
            "question_id": question_id,
            "skill_ids": skill_ids,
            "is_correct": is_correct,
            "response_time_seconds": response_time_seconds
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{DASH_API_URL}/submit-answer/{user_id}",
                json=submission,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Submitted answer for question {question_id}: {'✓' if is_correct else '✗'}")
                    return result
                else:
                    logger.error(f"Failed to submit answer: HTTP {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error submitting answer to Dash API: {e}")
        return None


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    global active_session

    # Get user ID from runner_args (passed from frontend) or environment or use test user
    user_id = getattr(runner_args, 'user_id', None) or os.getenv("USER_ID", "test@test.com")

    # Check if there's already an active session
    async with session_lock:
        if active_session is not None:
            logger.warning(f"Rejecting new session for {user_id} - session already active for {active_session}")
            # Wait a bit and check again (previous session might be cleaning up)
            await asyncio.sleep(2)
            if active_session is not None:
                logger.error(f"Active session {active_session} still running. Please disconnect first.")
                return

        active_session = user_id
        logger.info(f"Starting bot session for user: {user_id}")

    # AI Tutor system instruction
    system_instruction = """You are an expert AI tutor helping students learn math and problem-solving through an adaptive learning system.

Your teaching approach:
- Be patient, encouraging, and conversational
- Present questions clearly from the learning system
- Ask guiding questions instead of giving direct answers
- Wait for the student to think through problems
- Provide hints when students are stuck
- Celebrate progress and correct understanding
- Use clear, simple explanations
- Adapt to the student's pace and level

CRITICAL - You Have Live Video Feed of Student's Screen:
- You receive a CONTINUOUS live video feed showing the student's screen
- You will be given the question TEXT at the start of each problem
- ALWAYS use the video feed to:
  * See visual elements (images, diagrams, graphs, charts) that accompany the question
  * Observe the student's work and written solutions
  * Check what's currently displayed on their screen
- The math question is displayed in BLACK text on a WHITE background
- When presenting a question, use the TEXT you were given but LOOK at the VIDEO to describe any visual elements
- Do NOT make up different questions - stick to the question text you were given
- When asked "what's the question?", repeat the question you were given (not a different one)
- Use the video feed primarily to see diagrams/images and watch student work

When presenting questions:
- Use the question TEXT you were provided
- LOOK at the live video feed to see if there are visual elements (graphs, diagrams, images, equations)
- Describe any visual elements you see in the video feed
- Present the question clearly and naturally in your own words
- Wait for the complete answer before evaluating

When the student shares their screen or camera showing work:
- Observe their written work carefully in the video feed
- Point out errors gently and constructively
- Help them understand WHY something is wrong, not just WHAT is wrong
- Encourage them to explain their reasoning

After evaluating an answer:
- Provide immediate feedback
- Explain why the answer is correct or incorrect
- If incorrect, guide them to understand the mistake
- Offer to fetch the next question when ready

Remember: Your goal is to help students learn HOW to think, not just what to think."""

    # Define tools for Dash integration using FunctionSchema
    submit_answer_tool = FunctionSchema(
        name="submit_answer",
        description="Submit a student's answer to a question and get feedback on correctness. Call this after the student provides their answer.",
        properties={
            "student_answer": {
                "type": "string",
                "description": "The student's answer to the current question"
            },
            "is_correct": {
                "type": "boolean",
                "description": "Whether the student's answer is correct"
            },
            "response_time_seconds": {
                "type": "number",
                "description": "Time taken by student to answer in seconds (estimate if unknown)"
            }
        },
        required=["student_answer", "is_correct"]
    )

    get_next_question_tool = FunctionSchema(
        name="get_next_question",
        description="Fetch the next question from the adaptive learning system. Call this after providing feedback on the previous answer.",
        properties={},
        required=[]
    )

    # Convert to ToolsSchema
    tools = ToolsSchema([submit_answer_tool, get_next_question_tool])

    llm = GeminiLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        voice_id="Aoede",  # Puck, Charon, Kore, Fenrir, Aoede
        system_instruction=system_instruction,
    )

    # Initial context without question (will be added when client is ready)
    context = LLMContext([], tools=tools)
    context_aggregator = LLMContextAggregatorPair(context)

    # RTVI processor for better client-side UI feedback
    rtvi = RTVIProcessor()

    # Tool/Function handlers
    async def handle_submit_answer(function_name, tool_call_id, args, llm, context, result_callback):
        """Handle submit_answer function call"""
        student_answer = args.get("student_answer", "")
        is_correct = args.get("is_correct", False)
        response_time = args.get("response_time_seconds", 30.0)

        # Get current question from LLM state
        current_question = getattr(llm, '_current_question', None)

        if current_question:
            question_id = current_question.get("question_id", "")
            skill_ids = current_question.get("skill_ids", [])

            # Submit to Dash API
            result = await submit_answer_to_dash(
                user_id=user_id,
                question_id=question_id,
                skill_ids=skill_ids,
                is_correct=is_correct,
                response_time_seconds=response_time
            )

            if result:
                skill_details = result.get("skill_details", [])
                feedback = f"Answer recorded. "
                if skill_details:
                    feedback += f"Updated {len(skill_details)} skill(s) in your learning profile."

                await result_callback({"feedback": feedback, "success": True})
            else:
                await result_callback({"feedback": "Could not record answer.", "success": False})
        else:
            await result_callback({"feedback": "No active question.", "success": False})

    async def handle_get_next_question(function_name, tool_call_id, args, llm, context, result_callback):
        """Handle get_next_question function call"""
        question_data = await fetch_next_question(user_id)

        if question_data:
            # Store new question
            llm._current_question = question_data

            # Broadcast to frontend for synchronization
            await broadcast_question_update(question_data)

            # Format question
            content_json = question_data.get("content", {})
            question_text = content_json.get("question", {}).get("content", "")

            await result_callback({
                "question": question_text,
                "question_id": question_data.get("question_id", ""),
                "success": True
            })
        else:
            await result_callback({
                "question": "",
                "error": "Could not fetch next question",
                "success": False
            })

    # Register function handlers
    llm.register_function("submit_answer", handle_submit_answer)
    llm.register_function("get_next_question", handle_get_next_question)

    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            context_aggregator.user(),
            llm,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected: {client}")

        # MediaMixer handles all video - don't capture from Daily to avoid multiple video sources
        # await maybe_capture_participant_camera(transport, client, framerate=1)
        # await maybe_capture_participant_screen(transport, client, framerate=1)

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info(f"Client ready, starting video then conversation")

        # DON'T fetch new question - use what's already on frontend
        # Get the CURRENT question (not next) by calling the API without advancing
        question_data = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{DASH_API_URL}/next-question/{user_id}") as response:
                    if response.status == 200:
                        question_data = await response.json()
                        logger.info(f"Got current question {question_data.get('question_id')} for user {user_id}")
                    else:
                        logger.error(f"Failed to get current question: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error getting current question: {e}")

        if question_data:
            # Store current question for answer evaluation
            llm._current_question = question_data

            # Broadcast to frontend for synchronization
            await broadcast_question_update(question_data)

        # CRITICAL FIX: Enable video FIRST, before starting conversation
        logger.info("Step 1: Unpausing video input")
        llm.set_audio_input_paused(False)
        llm.set_video_input_paused(False)

        # Wait a moment for initialization
        await asyncio.sleep(0.5)

        # Start MediaMixer for live screen capture
        # This will show EXACTLY what's on the student's screen in real-time
        logger.info("Step 2: Starting MediaMixer receiver for live screen monitoring")
        asyncio.create_task(mediamixer_video_receiver(transport, llm))

        # Wait for video frames to buffer so Gemini has something to see
        logger.info("Step 3: Waiting for video frames to buffer...")
        await asyncio.sleep(3)

        screenshot_sent = False  # Not using screenshots - using live MediaMixer instead

        # Now add initial message - ONLY use video, no text hints
        if question_data:
            # Store question for later use but DON'T send to Gemini
            content_json = question_data.get("content", {})
            question_text_raw = content_json.get("question", {}).get("content", "")

            # CRITICAL: Do NOT send any question text - force Gemini to use video ONLY
            initial_message = """You are now connected to help a student with math.

CRITICAL INSTRUCTIONS - Read the Question from the Video Feed:
- You are receiving a LIVE VIDEO FEED that shows TWO sections stacked vertically
- The video frame has TWO parts:
  * TOP HALF: Scratchpad area (where student draws/writes)
  * BOTTOM HALF: The math question display (BLACK text on WHITE background)
- The MATH QUESTION YOU NEED TO READ is in the BOTTOM HALF of the video frame

Your task:
1. Greet the student warmly
2. Tell them you can see their screen through the live video
3. LOOK at the BOTTOM HALF of the video frame - that's where the question is displayed
4. READ the EXACT math question you see in the bottom half of the frame - word for word
5. Describe any images, diagrams, graphs, or visual elements you see in the question area
6. Ask if they're ready to solve it

CRITICAL REMINDERS:
- The question is in the BOTTOM HALF of the video frame, not the top
- Do NOT make up questions
- Do NOT invent problems
- ONLY present what you actually SEE in the BOTTOM HALF of the video
- The top half is just a scratchpad - ignore it when reading the question
- If you can't read the question clearly, tell the student

Start by looking at the BOTTOM HALF of the video and reading the question you see there."""

            context.messages.append({
                "role": "user",
                "content": initial_message
            })
        else:
            context.messages.append({
                "role": "user",
                "content": "Greet the student warmly and let them know you're here to help them learn math."
            })

        # NOW start the conversation - with screenshot AND video context available
        logger.info("Step 4: Starting conversation with question screenshot and video context")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    # Removed: MediaMixer handles all video, no need for separate capture
    # @rtvi.event_handler("on_client_video_capture_request")
    # async def on_client_video_capture_request(rtvi, participant_id: str):
    #     logger.info(f"Video capture requested for participant: {participant_id}")
    #     await maybe_capture_participant_camera(transport, participant_id, framerate=1)

    # Start frontend sync server in background
    sync_server_task = asyncio.create_task(frontend_sync_server())
    logger.info("Frontend sync server started in background")

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    try:
        await runner.run(task)
    finally:
        # Clear active session
        async with session_lock:
            logger.info(f"Cleaning up session for user: {active_session}")
            active_session = None

        # Cancel sync server when pipeline ends
        sync_server_task.cancel()
        try:
            await sync_server_task
        except asyncio.CancelledError:
            logger.info("Frontend sync server stopped")


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""
    # Create transport based on runner_args type
    if isinstance(runner_args, DailyRunnerArguments):
        transport = DailyTransport(
            runner_args.room_url,
            runner_args.token,
            "AI Tutor Bot",
            transport_params["daily"](),
        )
    else:
        # Try to get room URL from environment variable as fallback
        room_url = os.getenv("DAILY_ROOM_URL")
        token = None  # Token can be None for public rooms

        if not room_url:
            logger.error(f"No Daily room URL found. Set DAILY_ROOM_URL environment variable or pass via runner args")
            return

        logger.info(f"Using Daily room URL from environment: {room_url}")

        transport = DailyTransport(
            room_url,
            token,
            "AI Tutor Bot",
            transport_params["daily"](),
        )
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
