"""
Teaching Assistant Core

Proactive tutor engagement features:
- Session greetings (warm welcome)
- Session closure (positive wrap-up)
- Inactivity monitoring (60s silence nudge)
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Dict
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states for Teaching Assistant"""
    IDLE = "idle"
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class ActivityMonitor:
    """Monitors student activity and detects inactivity"""
    last_activity_time: float
    inactivity_threshold: float

    def is_inactive(self) -> bool:
        """Check if student has been inactive beyond threshold"""
        current_time = datetime.now().timestamp()
        elapsed = current_time - self.last_activity_time
        return elapsed >= self.inactivity_threshold

    def reset(self):
        """Reset activity timer"""
        self.last_activity_time = datetime.now().timestamp()


class TeachingAssistant:
    """
    Teaching Assistant Core

    Proactive engagement system that works alongside Adam (Gemini) to:
    - Greet students warmly at session start
    - Provide positive closure at session end
    - Nudge students after periods of inactivity
    """

    def __init__(self, inactivity_threshold: float = 60):
        """
        Initialize Teaching Assistant

        Args:
            inactivity_threshold: Seconds of inactivity before nudging (default: 60s)
        """
        self.session_state = SessionState.IDLE
        self.inactivity_threshold = inactivity_threshold
        self.is_monitoring = False
        self.prompt_injection_callback: Optional[Callable] = None

        # Activity monitor
        self.activity_monitor = ActivityMonitor(
            last_activity_time=datetime.now().timestamp(),
            inactivity_threshold=inactivity_threshold
        )

        logger.info(f"Teaching Assistant initialized (inactivity threshold: {inactivity_threshold}s)")

    def set_prompt_injection_callback(self, callback: Callable):
        """
        Set callback function for injecting prompts to Gemini

        Args:
            callback: Async function that takes prompt string and sends to Gemini
        """
        self.prompt_injection_callback = callback
        logger.info("Prompt injection callback set")

    async def greet_on_startup(self, student_name: str) -> str:
        """
        Generate warm greeting for session startup

        Args:
            student_name: Name of the student

        Returns:
            Greeting prompt to inject to Gemini
        """
        # Generate guidance prompt FOR ADAM about how to greet the student
        if student_name and len(student_name.strip()) > 0:
            greeting_prompt = (
                f"[Teaching Assistant Note to Adam]: A new session is starting with {student_name}. "
                f"Please greet them warmly and ask what they'd like to explore today. "
                f"Remember to emphasize your role as a guide who helps them think through problems, "
                f"not someone who just gives answers. Set a collaborative, encouraging tone."
            )
        else:
            greeting_prompt = (
                "[Teaching Assistant Note to Adam]: A new session is starting with a student. "
                "Please greet them warmly and ask what they'd like to explore today. "
                "Remember to emphasize your role as a guide who helps them think through problems, "
                "not someone who just gives answers. Set a collaborative, encouraging tone."
            )

        # Update session state
        self.session_state = SessionState.ACTIVE
        self.activity_monitor.reset()

        # Inject prompt if callback is set
        if self.prompt_injection_callback:
            await self.prompt_injection_callback(greeting_prompt)

        logger.info(f"Session started with greeting for: {student_name or 'student'}")
        return greeting_prompt

    async def greet_on_close(self, session_summary: Dict) -> str:
        """
        Generate positive closure for session end

        Args:
            session_summary: Dictionary with session metrics (questions_answered, accuracy, etc.)

        Returns:
            Closure prompt to inject to Gemini
        """
        # Extract metrics from summary
        questions_answered = session_summary.get("questions_answered", 0)
        accuracy = session_summary.get("accuracy", 0)
        topics_covered = session_summary.get("topics_covered", [])

        # Generate personalized closure
        closure_parts = ["Great work today!"]

        if questions_answered > 0:
            closure_parts.append(f"You tackled {questions_answered} question{'s' if questions_answered > 1 else ''}.")

        if accuracy > 0:
            accuracy_pct = int(accuracy * 100)
            if accuracy_pct >= 80:
                closure_parts.append(f"Your {accuracy_pct}% accuracy shows strong understanding!")
            elif accuracy_pct >= 60:
                closure_parts.append(f"You're making good progress with {accuracy_pct}% accuracy.")
            else:
                closure_parts.append("Remember, every mistake is a learning opportunity!")

        if topics_covered and len(topics_covered) > 0:
            topics_str = ", ".join(topics_covered)
            closure_parts.append(f"You explored: {topics_str}.")

        closure_parts.append(
            "Keep up the curiosity and I'll see you next time. "
            "Remember: the journey of learning is just as important as the destination!"
        )

        closure_prompt = " ".join(closure_parts)

        # Update session state and stop monitoring
        self.session_state = SessionState.CLOSED
        self.is_monitoring = False

        # Inject prompt if callback is set
        if self.prompt_injection_callback:
            await self.prompt_injection_callback(closure_prompt)

        logger.info(f"Session closed with summary: {session_summary}")
        return closure_prompt

    async def monitor_activity(self):
        """
        Monitor student activity and nudge after inactivity threshold

        This runs as a background task during active sessions.
        Sends nudge prompts to Gemini when student is inactive for too long.
        """
        self.is_monitoring = True
        logger.info("Activity monitoring started")

        try:
            while self.session_state == SessionState.ACTIVE and self.is_monitoring:
                # Check if student is inactive
                if self.activity_monitor.is_inactive():
                    # Generate nudge guidance FOR ADAM
                    nudge_prompt = (
                        "[Teaching Assistant Note to Adam]: The student has been inactive for 60 seconds. "
                        "Please check in with them gently. Ask if they're still there or if they need help. "
                        "Remind them that it's okay to take time thinking, and encourage them to ask questions if stuck. "
                        "Keep the tone patient and supportive."
                    )

                    # Inject nudge
                    if self.prompt_injection_callback:
                        await self.prompt_injection_callback(nudge_prompt)
                        logger.info("Inactivity nudge sent")

                    # Reset activity timer after nudging
                    self.activity_monitor.reset()

                # Check every 100ms for responsive shutdown
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Activity monitoring cancelled")
            raise
        finally:
            self.is_monitoring = False
            logger.info("Activity monitoring stopped")

    def reset_activity(self):
        """
        Reset activity timer (called when student interacts)

        Should be called whenever:
        - Student sends a message
        - Student submits an answer
        - Student interacts with the interface
        """
        self.activity_monitor.reset()
        logger.debug("Activity timer reset")

    async def inject_prompt(self, prompt: str):
        """
        Inject a prompt to Gemini (generic method)

        Args:
            prompt: Prompt text to send to Gemini
        """
        if self.prompt_injection_callback:
            await self.prompt_injection_callback(prompt)
            logger.info(f"Prompt injected: {prompt[:50]}...")
        else:
            logger.warning("Prompt injection attempted but no callback set")
