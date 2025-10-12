#!/usr/bin/env python3
"""
Teaching Assistant WebSocket Server

This server bridges the React frontend with the Teaching Assistant backend.
It receives Gemini responses, runs TA analysis, and sends prompt injections back.
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Set, Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from teaching_assistant.ta_core import TeachingAssistant, SessionState
from teaching_assistant.emotional_intelligence import EmotionalIntelligence, EmotionState
from teaching_assistant.context_provider import ContextProvider
from teaching_assistant.performance_tracker import PerformanceTracker
from memory.vector_store import VectorStore
from memory.knowledge_graph import KnowledgeGraph

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Connected WebSocket clients
connected_clients: Set[websockets.WebSocketServerProtocol] = set()

# TA Components
ta_core: TeachingAssistant = None
emotional_intelligence: EmotionalIntelligence = None
context_provider: ContextProvider = None
performance_tracker: PerformanceTracker = None

# Session data
current_session_id: str = None
student_name: str = "Student"
messages_in_session: int = 0
session_start_time: float = None
questions_answered: int = 0
questions_correct: int = 0
hints_used: int = 0
session_emotions: list = []

# Conversation buffer for real-time analysis
conversation_history: list = []  # List of {"speaker": "student"|"adam", "text": str, "timestamp": float}
last_student_message: str = ""


async def send_to_frontend(message: Dict[str, Any]):
    """Send a message to all connected frontend clients"""
    if not connected_clients:
        logger.warning("No clients connected to send message")
        return

    message_json = json.dumps(message)
    disconnected_clients = set()

    for client in connected_clients:
        try:
            await client.send(message_json)
            logger.debug(f"Sent message to frontend: {message.get('type')}")
        except websockets.exceptions.ConnectionClosed:
            disconnected_clients.add(client)
            logger.warning("Client connection closed during send")

    # Clean up disconnected clients
    for client in disconnected_clients:
        connected_clients.discard(client)


async def analyze_teaching_quality(adam_response: str, student_message: str) -> bool:
    """
    Real-time analysis of Adam's teaching quality

    Returns True if coaching was provided to Adam
    """
    coaching_prompts = []

    # Check 1: Is Adam giving direct answers instead of guiding?
    # Simple heuristic: responses starting with "The answer is" or containing "=" followed by number
    if ("the answer is" in adam_response.lower() or
        "it equals" in adam_response.lower() or
        "the solution is" in adam_response.lower()):
        coaching_prompts.append(
            "[TA Coaching]: You just gave a direct answer. Instead, try asking guiding questions "
            "that help the student discover the answer themselves. Use Socratic method - "
            "ask 'What do you think?', 'How would you approach this?', or 'What's the first step?'"
        )

    # Check 2: Did Adam miss an opportunity to probe deeper?
    # If student's message was very short (< 10 words) and Adam didn't ask follow-up
    if student_message and len(student_message.split()) < 10:
        if "?" not in adam_response:  # Adam didn't ask a question
            coaching_prompts.append(
                "[TA Coaching]: The student gave a brief response. Consider asking a follow-up question "
                "to understand their thinking better. Try: 'Can you explain your reasoning?' or "
                "'What made you think of that approach?'"
            )

    # Check 3: Is Adam being too verbose?
    if len(adam_response) > 500:  # Very long response
        coaching_prompts.append(
            "[TA Coaching]: Your response is quite long. Try to be more concise and focus on "
            "one guiding question at a time. Students learn better with shorter, focused interactions."
        )

    # Send coaching to Adam if needed
    for prompt in coaching_prompts:
        logger.info(f"🎯 TA COACHING ADAM: {prompt[:100]}...")
        await inject_prompt_callback(prompt)

        # Send visible log to frontend
        await send_to_frontend({
            "type": "ta_log",
            "level": "warning",
            "message": f"🎯 TA COACHING ADAM: {prompt[:120]}...",
            "timestamp": datetime.now().timestamp()
        })

    return len(coaching_prompts) > 0


async def inject_prompt_callback(prompt: str):
    """Callback function for TA to inject prompts to Gemini"""
    logger.info(f"🤖 TA → Adam: {prompt[:100]}...")

    await send_to_frontend({
        "type": "ta_inject_prompt",
        "prompt": prompt,
        "timestamp": datetime.now().timestamp()
    })

    # Also log to console
    await send_to_frontend({
        "type": "ta_log",
        "level": "info",
        "message": f"TA → Adam: {prompt[:80]}...",
        "timestamp": datetime.now().timestamp()
    })


async def handle_gemini_response(data: Dict[str, Any]):
    """Handle incoming Gemini response from frontend - Real-time TA analysis of Adam's teaching"""
    global messages_in_session

    try:
        text = data.get("text", "")
        student_last_message = data.get("student_context", "")  # Get student's previous message if available

        if not text or len(text.strip()) == 0:
            return

        messages_in_session += 1
        logger.info(f"📨 Adam responded ({len(text)} chars) - TA analyzing teaching quality...")

        # Reset activity timer
        ta_core.reset_activity()

        # Store in vector DB for future context
        if context_provider and current_session_id:
            context_provider.vector_store.store(
                text=text,
                metadata={
                    "session_id": current_session_id,
                    "student_id": student_name,
                    "speaker": "adam",
                    "timestamp": datetime.now().timestamp()
                }
            )
            logger.debug("Stored Adam's response in vector DB")

        # Add Adam's response to conversation history
        conversation_history.append({
            "speaker": "adam",
            "text": text,
            "timestamp": datetime.now().timestamp()
        })

        # REAL-TIME TEACHING QUALITY ANALYSIS
        # Analyze Adam's response to see if coaching is needed
        coaching_needed = await analyze_teaching_quality(text, last_student_message)

        # Analyze student emotion (check if Adam detected confusion/frustration in student's messages)
        if emotional_intelligence:
            logger.info("Running emotional intelligence analysis...")
            emotion_result = await emotional_intelligence.detect_emotion(
                transcript=text
            )

            if emotion_result.emotion != EmotionState.NEUTRAL:
                logger.info(f"😔 Detected emotion: {emotion_result.emotion.value}")

                # Track emotion for performance tracking
                session_emotions.append(emotion_result.emotion.value)

                # Inform Adam of the emotion with teaching suggestions
                success = await emotional_intelligence.inform_adam_of_emotion(emotion_result)

                if success:
                    await send_to_frontend({
                        "type": "ta_log",
                        "level": "info",
                        "message": f"TA detected {emotion_result.emotion.value} emotion and informed Adam",
                        "timestamp": datetime.now().timestamp()
                    })

        # Check for historical context every 10 messages
        if messages_in_session % 10 == 0 and context_provider and current_session_id:
            logger.info("Fetching historical context...")
            context_results = await context_provider.get_past_struggles(
                topic=text[:100],  # Use recent text as topic
                student_id=student_name
            )

            if context_results and len(context_results) > 0:
                # Build context prompt from results
                context_lines = ["[Historical Context]"]
                for ctx in context_results[:2]:  # Limit to top 2
                    context_lines.append(f"- {ctx.content}")

                context_prompt = "\n".join(context_lines)
                context_prompt += "\nConsider this history when responding."

                await send_to_frontend({
                    "type": "ta_log",
                    "level": "info",
                    "message": f"TA providing historical context to Adam ({len(context_results)} items)",
                    "timestamp": datetime.now().timestamp()
                })

                await ta_core.inject_prompt(context_prompt)

    except Exception as e:
        logger.error(f"Error handling Gemini response: {e}", exc_info=True)


async def handle_student_message(data: Dict[str, Any]):
    """Handle student message from frontend - Track for TA analysis"""
    global last_student_message, conversation_history

    try:
        text = data.get("text", "")
        if not text:
            return

        logger.info(f"👤 Student: {text[:50]}...")

        # Store student message for next TA analysis
        last_student_message = text
        conversation_history.append({
            "speaker": "student",
            "text": text,
            "timestamp": datetime.now().timestamp()
        })

        # Keep conversation history manageable (last 20 messages)
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]

        # Reset activity
        ta_core.reset_activity()

        # Store in vector DB
        if context_provider and current_session_id:
            context_provider.vector_store.store(
                text=text,
                metadata={
                    "session_id": current_session_id,
                    "student_id": student_name,
                    "speaker": "student",
                    "timestamp": datetime.now().timestamp()
                }
            )

    except Exception as e:
        logger.error(f"Error handling student message: {e}", exc_info=True)


async def handle_session_start(data: Dict[str, Any]):
    """Handle session start"""
    global current_session_id, student_name, messages_in_session
    global session_start_time, questions_answered, questions_correct, hints_used, session_emotions

    try:
        current_session_id = data.get("session_id", f"session_{datetime.now().timestamp()}")
        student_name = data.get("student_name", "Student")
        messages_in_session = 0
        session_start_time = datetime.now().timestamp()
        questions_answered = 0
        questions_correct = 0
        hints_used = 0
        session_emotions = []

        logger.info(f"🎬 Session started: {current_session_id} (Student: {student_name})")

        # DO NOT start activity monitoring or send greetings
        # The TA only coaches Adam when he responds, not proactively

        await send_to_frontend({
            "type": "ta_log",
            "level": "success",
            "message": f"✅ TA monitoring session for {student_name} - Ready to coach Adam in real-time",
            "timestamp": datetime.now().timestamp()
        })

    except Exception as e:
        logger.error(f"Error handling session start: {e}", exc_info=True)


async def handle_session_end(data: Dict[str, Any]):
    """Handle session end"""
    try:
        logger.info(f"🛑 Session ending: {current_session_id}")

        # Calculate session duration
        session_duration = datetime.now().timestamp() - session_start_time if session_start_time else 0

        # Track session metrics
        if performance_tracker:
            session_data = {
                "session_id": current_session_id,
                "student_id": student_name,
                "questions_answered": questions_answered,
                "questions_correct": questions_correct,
                "total_time": session_duration,
                "hints_used": hints_used,
                "emotions": session_emotions,
                "timestamp": session_start_time
            }

            metrics = performance_tracker.track_metrics(session_data)
            accuracy = performance_tracker.calculate_accuracy(metrics)

            # Generate performance suggestions
            await performance_tracker.generate_suggestions(metrics)

            # Get dashboard data
            dashboard = performance_tracker.get_dashboard_data()

            logger.info(f"Session metrics tracked: {questions_answered} questions, {accuracy:.1%} accuracy")

        # Get session summary
        session_summary = {
            "questions_answered": questions_answered,
            "accuracy": accuracy if performance_tracker else 0.0,
            "topics_covered": ["general"]  # Could be extracted from context
        }

        # Send closure
        await ta_core.greet_on_close(session_summary)

        await send_to_frontend({
            "type": "ta_log",
            "level": "info",
            "message": f"TA session closed. {messages_in_session} messages, {questions_answered} questions.",
            "timestamp": datetime.now().timestamp()
        })

    except Exception as e:
        logger.error(f"Error handling session end: {e}", exc_info=True)


async def handle_answer_result(data: Dict[str, Any]):
    """Handle student answer result for performance tracking"""
    global questions_answered, questions_correct

    try:
        is_correct = data.get("is_correct", False)
        questions_answered += 1
        if is_correct:
            questions_correct += 1

        logger.info(f"Answer tracked: {'correct' if is_correct else 'incorrect'} ({questions_correct}/{questions_answered})")

    except Exception as e:
        logger.error(f"Error handling answer result: {e}", exc_info=True)


async def handle_hint_used(data: Dict[str, Any]):
    """Handle hint usage tracking"""
    global hints_used

    try:
        hints_used += 1
        logger.info(f"Hint used (total: {hints_used})")

    except Exception as e:
        logger.error(f"Error handling hint usage: {e}", exc_info=True)


async def handle_client_message(websocket, message: str):
    """Handle incoming message from frontend client"""
    try:
        data = json.loads(message)
        message_type = data.get("type")

        if message_type == "gemini_response":
            await handle_gemini_response(data)
        elif message_type == "student_message":
            await handle_student_message(data)
        elif message_type == "session_start":
            await handle_session_start(data)
        elif message_type == "session_end":
            await handle_session_end(data)
        elif message_type == "answer_result":
            await handle_answer_result(data)
        elif message_type == "hint_used":
            await handle_hint_used(data)
        elif message_type == "gemini_turn_complete":
            # Gemini has completed its turn - this is informational only
            logger.debug("Gemini turn completed")
        elif message_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
        else:
            logger.warning(f"Unknown message type: {message_type}")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON received: {e}")
    except Exception as e:
        logger.error(f"Error handling client message: {e}", exc_info=True)


async def handle_websocket_connection(websocket):
    """Handle new WebSocket connection from frontend"""
    logger.info(f"🔌 Frontend connected from {websocket.remote_address}")
    connected_clients.add(websocket)

    # Send welcome message
    await websocket.send(json.dumps({
        "type": "ta_connected",
        "message": "Teaching Assistant connected",
        "timestamp": datetime.now().timestamp()
    }))

    try:
        async for message in websocket:
            await handle_client_message(websocket, message)
    except websockets.exceptions.ConnectionClosed:
        logger.info("Frontend connection closed")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Frontend disconnected. Active clients: {len(connected_clients)}")


async def initialize_ta_components():
    """Initialize all Teaching Assistant components"""
    global ta_core, emotional_intelligence, context_provider, performance_tracker

    logger.info("Initializing Teaching Assistant components...")

    # Initialize vector store and knowledge graph
    vector_store = VectorStore(persist_directory="./backend/data/chroma_db")
    knowledge_graph = KnowledgeGraph()

    # Initialize TA components
    ta_core = TeachingAssistant(inactivity_threshold=60)
    ta_core.set_prompt_injection_callback(inject_prompt_callback)

    emotional_intelligence = EmotionalIntelligence(prompt_injection_callback=inject_prompt_callback)
    context_provider = ContextProvider(vector_store, knowledge_graph, prompt_injection_callback=inject_prompt_callback)
    performance_tracker = PerformanceTracker(suggestion_callback=inject_prompt_callback)

    logger.info("✅ All TA components initialized")


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Teaching Assistant Server Starting...")
    logger.info("=" * 60)

    # Initialize components
    await initialize_ta_components()

    # Start WebSocket server
    host = "localhost"
    port = 9000

    logger.info(f"Starting WebSocket server on {host}:{port}")

    async with websockets.serve(handle_websocket_connection, host, port):
        logger.info(f"✅ Teaching Assistant listening on ws://{host}:{port}")
        logger.info("Waiting for frontend connections...")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Teaching Assistant server...")
