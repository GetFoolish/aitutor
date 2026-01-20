"""
Engagement Processor for Vision Agents
Tracks head pose and attention for engagement signals using MediaPipe.
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


class EngagementProcessor(VideoProcessor):
    """
    Tracks head pose and gaze direction for engagement signals.
    Uses MediaPipe Face Mesh for facial landmark detection.
    """

    # Thresholds for attention detection
    LOOK_AWAY_X_MIN = 0.3  # Face center X range
    LOOK_AWAY_X_MAX = 0.7
    LOOK_AWAY_Y_MIN = 0.25
    LOOK_AWAY_Y_MAX = 0.75

    # How many frames of looking away indicates distraction
    DISTRACTION_FRAME_THRESHOLD = 15  # At 2 FPS, this is ~7.5 seconds

    def __init__(self, fps: float = 2.0, history_size: int = 30):
        """
        Initialize EngagementProcessor.

        Args:
            fps: Frame rate for engagement detection
            history_size: Number of readings to keep for averaging
        """
        self._fps = fps
        self._history_size = history_size
        self._engagement_history: deque = deque(maxlen=history_size)
        self._forwarder: Optional[VideoForwarder] = None
        self._face_mesh = None
        self._agent: Optional["Agent"] = None
        self._processing = False

        # Tracking state
        self._looking_away_frames: int = 0
        self._face_detected_frames: int = 0
        self._total_frames: int = 0

        # Latest state
        self._latest_state: Dict[str, Any] = {
            "face_detected": False,
            "looking_at_screen": True,
            "engagement_score": 1.0,
            "head_pose": {"x": 0.5, "y": 0.5},
        }

        logger.info(f"[ENGAGEMENT] Initialized with fps={fps}, history_size={history_size}")

    @property
    def name(self) -> str:
        return "engagement-processor"

    def attach_agent(self, agent: "Agent") -> None:
        """Store reference to agent for sending signals."""
        self._agent = agent
        logger.info("[ENGAGEMENT] Agent attached")

    async def _load_face_mesh(self) -> None:
        """Lazy load MediaPipe Face Mesh."""
        if self._face_mesh is None:
            try:
                import mediapipe as mp
                self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
                logger.info("[ENGAGEMENT] MediaPipe Face Mesh loaded successfully")
            except Exception as e:
                logger.error(f"[ENGAGEMENT] Failed to load Face Mesh: {e}")
                raise

    def _process_frame(self, frame: av.VideoFrame) -> None:
        """
        Process a video frame for engagement detection.
        Called by VideoForwarder at the configured FPS.
        """
        if self._face_mesh is None:
            return

        try:
            self._total_frames += 1

            # Convert av.VideoFrame to RGB numpy array (MediaPipe expects RGB)
            img = frame.to_ndarray(format="rgb24")

            # Run face mesh detection
            results = self._face_mesh.process(img)

            if results.multi_face_landmarks:
                self._face_detected_frames += 1
                landmarks = results.multi_face_landmarks[0]

                # Get nose tip landmark (index 1) for head pose estimation
                nose = landmarks.landmark[1]

                # Check if looking at screen
                is_looking_at_screen = (
                    self.LOOK_AWAY_X_MIN < nose.x < self.LOOK_AWAY_X_MAX and
                    self.LOOK_AWAY_Y_MIN < nose.y < self.LOOK_AWAY_Y_MAX
                )

                # Track looking away
                if not is_looking_at_screen:
                    self._looking_away_frames += 1
                else:
                    # Decay looking away counter when looking at screen
                    self._looking_away_frames = max(0, self._looking_away_frames - 1)

                # Calculate engagement score (1.0 = fully engaged, 0.0 = disengaged)
                engagement_score = 1.0 - min(
                    self._looking_away_frames / self.DISTRACTION_FRAME_THRESHOLD,
                    1.0
                )

                # Update history
                self._engagement_history.append({
                    "engagement_score": engagement_score,
                    "looking_at_screen": is_looking_at_screen,
                    "head_x": nose.x,
                    "head_y": nose.y,
                })

                # Update latest state
                self._latest_state = {
                    "face_detected": True,
                    "looking_at_screen": is_looking_at_screen,
                    "engagement_score": engagement_score,
                    "head_pose": {"x": nose.x, "y": nose.y},
                    "looking_away_frames": self._looking_away_frames,
                }

                logger.debug(
                    f"[ENGAGEMENT] Looking: {is_looking_at_screen}, "
                    f"Score: {engagement_score:.2f}, "
                    f"Away frames: {self._looking_away_frames}"
                )
            else:
                # No face detected - could indicate looking away or covered camera
                self._looking_away_frames += 1
                engagement_score = 1.0 - min(
                    self._looking_away_frames / self.DISTRACTION_FRAME_THRESHOLD,
                    1.0
                )

                self._latest_state = {
                    "face_detected": False,
                    "looking_at_screen": False,
                    "engagement_score": engagement_score,
                    "head_pose": None,
                    "looking_away_frames": self._looking_away_frames,
                }

        except Exception as e:
            logger.error(f"[ENGAGEMENT] Error processing frame: {e}")

    async def process_video(
        self,
        track: VideoStreamTrack,
        participant_id: Optional[str],
        shared_forwarder: Optional[VideoForwarder] = None,
    ) -> None:
        """
        Start processing video frames for engagement detection.
        Called by Agent when a new video track is published.
        """
        logger.info(f"[ENGAGEMENT] Starting video processing for participant: {participant_id}")

        # Load face mesh if not already loaded
        await self._load_face_mesh()

        self._processing = True

        # Use shared forwarder if provided, otherwise create our own
        if shared_forwarder:
            self._forwarder = shared_forwarder
        else:
            self._forwarder = VideoForwarder(
                input_track=track,
                fps=self._fps,
                name="engagement-forwarder",
            )

        # Add our frame handler at the configured FPS
        self._forwarder.add_frame_handler(
            self._process_frame,
            fps=self._fps,
            name="engagement-handler",
        )

        logger.info(f"[ENGAGEMENT] Video processing started at {self._fps} FPS")

    async def stop_processing(self) -> None:
        """Stop processing video frames."""
        logger.info("[ENGAGEMENT] Stopping video processing")
        self._processing = False

        if self._forwarder:
            await self._forwarder.remove_frame_handler(self._process_frame)
            self._forwarder = None

    async def close(self) -> None:
        """Clean up resources."""
        await self.stop_processing()
        if self._face_mesh:
            self._face_mesh.close()
            self._face_mesh = None
        self._engagement_history.clear()
        logger.info("[ENGAGEMENT] Processor closed")

    def get_latest_state(self) -> Dict[str, Any]:
        """Get the most recent engagement state."""
        return self._latest_state.copy()

    def get_average_engagement(self) -> float:
        """Get average engagement score from history."""
        if not self._engagement_history:
            return 1.0  # Default to engaged

        scores = [entry["engagement_score"] for entry in self._engagement_history]
        return sum(scores) / len(scores)

    def get_attention_percentage(self) -> float:
        """Get percentage of time looking at screen."""
        if not self._engagement_history:
            return 1.0

        looking_count = sum(
            1 for entry in self._engagement_history
            if entry.get("looking_at_screen", False)
        )

        return looking_count / len(self._engagement_history)

    def get_face_detection_rate(self) -> float:
        """Get percentage of frames where face was detected."""
        if self._total_frames == 0:
            return 0.0
        return self._face_detected_frames / self._total_frames

    def reset_tracking(self) -> None:
        """Reset tracking counters (call after intervention or break)."""
        self._looking_away_frames = 0
        self._engagement_history.clear()
        logger.info("[ENGAGEMENT] Tracking reset")

    def get_struggle_signals(self) -> Dict[str, Any]:
        """
        Get consolidated struggle signals for TeachingAssistant integration.
        """
        return {
            "engagement_score": self.get_average_engagement(),
            "attention_percentage": self.get_attention_percentage(),
            "face_detection_rate": self.get_face_detection_rate(),
            "looking_away_frames": self._looking_away_frames,
            "is_distracted": self._looking_away_frames >= self.DISTRACTION_FRAME_THRESHOLD,
            "face_detected": self._latest_state.get("face_detected", False),
        }
