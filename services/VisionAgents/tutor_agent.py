"""
AI Tutor Vision Agent
Main agent that combines audio/visual processing with Gemini for tutoring.
Sends struggle signals to TeachingAssistant for intervention decisions.
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from vision_agents.core import Agent, User
from vision_agents.core.runner import Runner
from vision_agents.plugins import getstream, gemini

from processors import EmotionProcessor, VADProcessor, EngagementProcessor
from teaching_assistant_bridge import TeachingAssistantBridge

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Tutor system prompt
TUTOR_SYSTEM_PROMPT = """You are a friendly and patient AI tutor helping students learn math.

Your role is to:
1. Explain concepts clearly and concisely
2. Encourage students when they're struggling
3. Break down complex problems into smaller steps
4. Celebrate correct answers enthusiastically
5. Never give away answers directly - guide students to discover them

When you detect signs of struggle (through my signals):
- Frustrated: Offer encouragement and suggest a simpler approach
- Confused: Re-explain the concept in different words
- Disengaged: Ask an engaging question to bring focus back

Keep responses SHORT and conversational - you're speaking, not writing.
Use simple language appropriate for the student's level.
"""


class TutorAgent:
    """
    Main Vision Agent for AI tutoring with struggle detection.
    """

    def __init__(
        self,
        ta_url: str = "http://localhost:8002",
        video_fps: float = 2.0,
    ):
        """
        Initialize TutorAgent.

        Args:
            ta_url: TeachingAssistant service URL
            video_fps: Frame rate for video processing
        """
        self.ta_url = ta_url
        self.video_fps = video_fps

        # Initialize processors
        self.emotion_processor = EmotionProcessor(fps=video_fps)
        self.vad_processor = VADProcessor()
        self.engagement_processor = EngagementProcessor(fps=video_fps)

        # Initialize bridge to TeachingAssistant
        self.ta_bridge = TeachingAssistantBridge(ta_url=ta_url)

        # Session tracking
        self.session_id: Optional[str] = None

        logger.info(f"[TUTOR_AGENT] Initialized with TA URL: {ta_url}")

    async def create_agent(self, **kwargs) -> Agent:
        """
        Create and configure the Vision Agent.

        Args:
            **kwargs: Additional arguments passed by runner
        """
        # Get session ID from call metadata if available
        self.session_id = kwargs.get("call_id", "unknown")

        logger.info(f"[TUTOR_AGENT] Creating agent for session: {self.session_id}")

        # Create the agent with all components
        agent = Agent(
            edge=getstream.Edge(),
            agent_user=User(name="AI Tutor", id="ai-tutor"),
            instructions=TUTOR_SYSTEM_PROMPT,
            llm=gemini.Realtime(fps=self.video_fps),
            processors=[
                self.emotion_processor,
                self.vad_processor,
                self.engagement_processor,
            ],
        )

        # Start signal forwarding loop
        asyncio.create_task(self._signal_forwarding_loop())

        return agent

    async def _signal_forwarding_loop(self) -> None:
        """
        Periodically collect signals from processors and send to TeachingAssistant.
        """
        logger.info("[TUTOR_AGENT] Starting signal forwarding loop")

        while True:
            try:
                await asyncio.sleep(2.0)  # Send signals every 2 seconds

                if not self.session_id:
                    continue

                # Collect signals from all processors
                signals = self._collect_signals()

                # Send to TeachingAssistant
                result = await self.ta_bridge.send_signals(
                    session_id=self.session_id,
                    signals=signals,
                )

                # Check for intervention
                if result and result.get("intervention"):
                    intervention = result["intervention"]
                    logger.info(
                        f"[TUTOR_AGENT] Intervention triggered: {intervention.get('type')}"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[TUTOR_AGENT] Signal forwarding error: {e}")

    def _collect_signals(self) -> Dict[str, Any]:
        """
        Collect all signals from processors into a single dict.
        """
        # Get emotion signals
        emotion = self.emotion_processor.get_latest_emotion()
        emotion_struggle = self.emotion_processor.get_average_struggle_score()

        # Get VAD signals
        vad = self.vad_processor.get_struggle_signals()

        # Get engagement signals
        engagement = self.engagement_processor.get_struggle_signals()

        return {
            "visual": {
                "emotion": emotion.get("emotion", "unknown"),
                "emotion_confidence": emotion.get("confidence", 0.0),
                "emotion_struggle_score": emotion_struggle,
                "engagement_score": engagement.get("engagement_score", 1.0),
                "attention_percentage": engagement.get("attention_percentage", 1.0),
                "face_detected": engagement.get("face_detected", False),
                "is_distracted": engagement.get("is_distracted", False),
            },
            "audio": {
                "hesitation_score": vad.get("hesitation_score", 0.0),
                "short_pauses": vad.get("short_pauses", 0),
                "long_pauses": vad.get("long_pauses", 0),
                "speaking_rate": vad.get("speaking_rate", 0.0),
                "volume_trend": vad.get("volume_trend", "stable"),
                "is_speaking": vad.get("is_speaking", False),
            },
        }


def create_agent(**kwargs) -> Agent:
    """
    Factory function called by vision-agents runner.
    """
    tutor = TutorAgent(
        ta_url=os.getenv("TEACHING_ASSISTANT_URL", "http://localhost:8002"),
        video_fps=float(os.getenv("VIDEO_FPS", "2")),
    )
    return asyncio.get_event_loop().run_until_complete(tutor.create_agent(**kwargs))


def main():
    """
    Main entry point - starts the Vision Agent runner.
    """
    logger.info("[TUTOR_AGENT] Starting AI Tutor Vision Agent")

    # Create runner with our agent factory
    runner = Runner(create_agent)

    # Run CLI (handles join, serve commands)
    runner.cli()


if __name__ == "__main__":
    main()
