"""
Emotion Processor for Vision Agents
Detects facial expressions as struggle signals using FER (Facial Expression Recognition).
"""

import asyncio
import logging
from collections import deque
from typing import Any, Dict, Optional, TYPE_CHECKING

import av
import numpy as np
from aiortc import VideoStreamTrack
from vision_agents.core.processors import VideoProcessor
from vision_agents.core.utils.video_forwarder import VideoForwarder

if TYPE_CHECKING:
    from vision_agents.core import Agent

logger = logging.getLogger(__name__)


class EmotionProcessor(VideoProcessor):
    """
    Detects facial expressions for struggle signals.
    Maps emotions to struggle categories: frustrated, confused, engaged, neutral.
    """

    def __init__(self, fps: float = 2.0, history_size: int = 10):
        """
        Initialize EmotionProcessor.

        Args:
            fps: Frame rate for emotion detection (default 2 FPS to balance CPU usage)
            history_size: Number of emotion readings to keep for averaging
        """
        self._fps = fps
        self._history_size = history_size
        self._emotion_history: deque = deque(maxlen=history_size)
        self._forwarder: Optional[VideoForwarder] = None
        self._detector = None
        self._agent: Optional["Agent"] = None
        self._processing = False

        # Latest emotion state
        self._latest_emotion: Dict[str, Any] = {
            "emotion": "unknown",
            "confidence": 0.0,
            "struggle_score": 0.0,
            "raw_emotions": {},
        }

        logger.info(f"[EMOTION] Initialized with fps={fps}, history_size={history_size}")

    @property
    def name(self) -> str:
        return "emotion-processor"

    def attach_agent(self, agent: "Agent") -> None:
        """Store reference to agent for sending signals."""
        self._agent = agent
        logger.info("[EMOTION] Agent attached")

    async def _load_detector(self) -> None:
        """Lazy load the FER detector to avoid import issues."""
        if self._detector is None:
            try:
                from fer import FER
                self._detector = FER(mtcnn=True)
                logger.info("[EMOTION] FER detector loaded successfully")
            except Exception as e:
                logger.error(f"[EMOTION] Failed to load FER detector: {e}")
                raise

    def _process_frame(self, frame: av.VideoFrame) -> None:
        """
        Process a video frame for emotion detection.
        Called by VideoForwarder at the configured FPS.
        """
        if self._detector is None:
            return

        try:
            # Convert av.VideoFrame to numpy array (BGR format for OpenCV)
            img = frame.to_ndarray(format="bgr24")

            # Run emotion detection
            results = self._detector.detect_emotions(img)

            if results and len(results) > 0:
                # Get emotions from first detected face
                emotions = results[0].get('emotions', {})

                # Calculate struggle emotion category
                struggle_emotion = self._calculate_struggle_emotion(emotions)
                confidence = max(emotions.values()) if emotions else 0.0

                # Update history
                self._emotion_history.append({
                    "emotion": struggle_emotion,
                    "confidence": confidence,
                    "raw": emotions,
                })

                # Calculate struggle score from emotion
                struggle_score = self._calculate_struggle_score(emotions)

                # Update latest state
                self._latest_emotion = {
                    "emotion": struggle_emotion,
                    "confidence": confidence,
                    "struggle_score": struggle_score,
                    "raw_emotions": emotions,
                }

                logger.debug(
                    f"[EMOTION] Detected: {struggle_emotion} "
                    f"(confidence: {confidence:.2f}, struggle: {struggle_score:.2f})"
                )
            else:
                # No face detected
                self._latest_emotion = {
                    "emotion": "no_face",
                    "confidence": 0.0,
                    "struggle_score": 0.0,
                    "raw_emotions": {},
                }

        except Exception as e:
            logger.error(f"[EMOTION] Error processing frame: {e}")

    def _calculate_struggle_emotion(self, emotions: Dict[str, float]) -> str:
        """
        Map FER emotions to struggle categories.

        Categories:
        - frustrated: angry or sad emotions (indicates difficulty)
        - confused: fear or surprise (indicates uncertainty)
        - engaged: happy (indicates positive learning state)
        - neutral: default state
        """
        if not emotions:
            return "unknown"

        angry = emotions.get('angry', 0)
        sad = emotions.get('sad', 0)
        fear = emotions.get('fear', 0)
        surprise = emotions.get('surprise', 0)
        happy = emotions.get('happy', 0)
        neutral = emotions.get('neutral', 0)

        # Frustration check (anger or sadness)
        if angry > 0.3 or sad > 0.3:
            return "frustrated"

        # Confusion check (fear or surprise)
        if fear > 0.3 or surprise > 0.3:
            return "confused"

        # Engagement check (happiness)
        if happy > 0.3:
            return "engaged"

        # Default to neutral
        return "neutral"

    def _calculate_struggle_score(self, emotions: Dict[str, float]) -> float:
        """
        Calculate a struggle score (0.0 to 1.0) based on emotions.
        Higher score = more struggle indicators.
        """
        if not emotions:
            return 0.0

        # Negative emotion weights (contribute to struggle)
        angry = emotions.get('angry', 0) * 1.0
        sad = emotions.get('sad', 0) * 0.8
        fear = emotions.get('fear', 0) * 0.7
        disgust = emotions.get('disgust', 0) * 0.5

        # Positive emotions (reduce struggle score)
        happy = emotions.get('happy', 0) * -0.5

        # Calculate weighted score
        raw_score = angry + sad + fear + disgust + happy

        # Normalize to 0.0 - 1.0 range
        return max(0.0, min(1.0, raw_score))

    async def process_video(
        self,
        track: VideoStreamTrack,
        participant_id: Optional[str],
        shared_forwarder: Optional[VideoForwarder] = None,
    ) -> None:
        """
        Start processing video frames for emotion detection.
        Called by Agent when a new video track is published.
        """
        logger.info(f"[EMOTION] Starting video processing for participant: {participant_id}")

        # Load detector if not already loaded
        await self._load_detector()

        self._processing = True

        # Use shared forwarder if provided, otherwise create our own
        if shared_forwarder:
            self._forwarder = shared_forwarder
        else:
            self._forwarder = VideoForwarder(
                input_track=track,
                fps=self._fps,
                name="emotion-forwarder",
            )

        # Add our frame handler at the configured FPS
        self._forwarder.add_frame_handler(
            self._process_frame,
            fps=self._fps,
            name="emotion-handler",
        )

        logger.info(f"[EMOTION] Video processing started at {self._fps} FPS")

    async def stop_processing(self) -> None:
        """Stop processing video frames."""
        logger.info("[EMOTION] Stopping video processing")
        self._processing = False

        if self._forwarder:
            await self._forwarder.remove_frame_handler(self._process_frame)
            self._forwarder = None

    async def close(self) -> None:
        """Clean up resources."""
        await self.stop_processing()
        self._detector = None
        self._emotion_history.clear()
        logger.info("[EMOTION] Processor closed")

    def get_latest_emotion(self) -> Dict[str, Any]:
        """Get the most recent emotion detection result."""
        return self._latest_emotion.copy()

    def get_average_struggle_score(self) -> float:
        """Get average struggle score from emotion history."""
        if not self._emotion_history:
            return 0.0

        scores = []
        for entry in self._emotion_history:
            if entry.get("raw"):
                score = self._calculate_struggle_score(entry["raw"])
                scores.append(score)

        return sum(scores) / len(scores) if scores else 0.0

    def get_dominant_emotion(self) -> str:
        """Get the most common emotion from history."""
        if not self._emotion_history:
            return "unknown"

        emotion_counts: Dict[str, int] = {}
        for entry in self._emotion_history:
            emotion = entry.get("emotion", "unknown")
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        return max(emotion_counts, key=emotion_counts.get)
