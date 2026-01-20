"""
VAD (Voice Activity Detection) Processor for Vision Agents
Detects voice activity and hesitation patterns as struggle signals.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any, Dict, Optional, TYPE_CHECKING

import numpy as np
from getstream.video.rtc import PcmData
from vision_agents.core.processors import AudioProcessor

if TYPE_CHECKING:
    from vision_agents.core import Agent

logger = logging.getLogger(__name__)


class VADProcessor(AudioProcessor):
    """
    Detects voice activity and hesitation patterns.
    Tracks pauses, speech rate, and volume levels for struggle detection.
    """

    # Thresholds
    SILENCE_THRESHOLD = 0.02  # RMS below this = silence
    PAUSE_THRESHOLD_SECONDS = 0.5  # Pause longer than this = hesitation
    LONG_PAUSE_THRESHOLD_SECONDS = 2.0  # Very long pause
    SPEAKING_RATE_WINDOW = 10  # Seconds to track speaking rate

    def __init__(self, history_size: int = 100):
        """
        Initialize VADProcessor.

        Args:
            history_size: Number of audio samples to keep for analysis
        """
        self._history_size = history_size
        self._agent: Optional["Agent"] = None

        # State tracking
        self._silence_start: Optional[float] = None
        self._last_speech_time: Optional[float] = None
        self._pause_count: int = 0
        self._long_pause_count: int = 0
        self._speech_segments: deque = deque(maxlen=history_size)
        self._volume_history: deque = deque(maxlen=history_size)

        # Speaking rate tracking (speech segments per window)
        self._speaking_rate_samples: deque = deque(maxlen=50)

        # Latest state
        self._latest_state: Dict[str, Any] = {
            "is_speaking": False,
            "volume": 0.0,
            "pause_count": 0,
            "long_pause_count": 0,
            "hesitation_score": 0.0,
            "speaking_rate": 0.0,
        }

        logger.info(f"[VAD] Initialized with history_size={history_size}")

    @property
    def name(self) -> str:
        return "vad-processor"

    def attach_agent(self, agent: "Agent") -> None:
        """Store reference to agent for sending signals."""
        self._agent = agent
        logger.info("[VAD] Agent attached")

    async def process_audio(self, audio_data: PcmData) -> None:
        """
        Process audio data for voice activity and hesitation detection.

        Args:
            audio_data: PcmData containing audio samples and metadata
        """
        try:
            # Get audio samples as float32 numpy array
            samples = audio_data.to_float32()

            if samples is None or len(samples) == 0:
                return

            # Calculate RMS (volume level)
            rms = np.sqrt(np.mean(samples ** 2))
            self._volume_history.append(rms)

            # Determine if speaking
            is_speaking = rms > self.SILENCE_THRESHOLD
            current_time = time.time()

            # Track silence/pause periods
            if not is_speaking:
                if self._silence_start is None:
                    # Start of silence
                    self._silence_start = current_time
            else:
                # Speaking - check if we had a pause
                if self._silence_start is not None:
                    pause_duration = current_time - self._silence_start

                    if pause_duration > self.LONG_PAUSE_THRESHOLD_SECONDS:
                        self._long_pause_count += 1
                        logger.debug(f"[VAD] Long pause detected: {pause_duration:.2f}s")
                    elif pause_duration > self.PAUSE_THRESHOLD_SECONDS:
                        self._pause_count += 1
                        logger.debug(f"[VAD] Hesitation pause: {pause_duration:.2f}s")

                    self._silence_start = None

                # Track speech segment
                self._last_speech_time = current_time
                self._speech_segments.append(current_time)

            # Calculate hesitation score
            hesitation_score = self._calculate_hesitation_score()

            # Calculate speaking rate (speech segments in last window)
            speaking_rate = self._calculate_speaking_rate()

            # Update latest state
            self._latest_state = {
                "is_speaking": is_speaking,
                "volume": float(rms),
                "pause_count": self._pause_count,
                "long_pause_count": self._long_pause_count,
                "hesitation_score": hesitation_score,
                "speaking_rate": speaking_rate,
                "participant": str(audio_data.participant) if audio_data.participant else None,
            }

        except Exception as e:
            logger.error(f"[VAD] Error processing audio: {e}")

    def _calculate_hesitation_score(self) -> float:
        """
        Calculate hesitation score (0.0 to 1.0) based on pause patterns.
        Higher score = more hesitation/struggle.
        """
        # Weight short pauses less than long pauses
        short_pause_weight = 0.1
        long_pause_weight = 0.25

        # Calculate weighted score
        raw_score = (
            self._pause_count * short_pause_weight +
            self._long_pause_count * long_pause_weight
        )

        # Normalize to 0.0 - 1.0 (cap at 5 pauses for max score)
        normalized = min(raw_score, 1.0)

        return normalized

    def _calculate_speaking_rate(self) -> float:
        """
        Calculate speaking rate as speech segments per second.
        Low speaking rate can indicate confusion or hesitation.
        """
        if not self._speech_segments:
            return 0.0

        current_time = time.time()
        window_start = current_time - self.SPEAKING_RATE_WINDOW

        # Count segments in the window
        segments_in_window = sum(
            1 for t in self._speech_segments
            if t >= window_start
        )

        # Rate is segments per second
        rate = segments_in_window / self.SPEAKING_RATE_WINDOW

        return rate

    async def close(self) -> None:
        """Clean up resources."""
        self._speech_segments.clear()
        self._volume_history.clear()
        self._speaking_rate_samples.clear()
        logger.info("[VAD] Processor closed")

    def get_latest_state(self) -> Dict[str, Any]:
        """Get the most recent VAD state."""
        return self._latest_state.copy()

    def get_average_volume(self) -> float:
        """Get average volume from history."""
        if not self._volume_history:
            return 0.0
        return sum(self._volume_history) / len(self._volume_history)

    def get_volume_trend(self) -> str:
        """
        Detect volume trend (decreasing volume may indicate losing confidence).
        Returns: 'increasing', 'decreasing', 'stable', or 'unknown'
        """
        if len(self._volume_history) < 10:
            return "unknown"

        # Compare first half to second half
        history_list = list(self._volume_history)
        mid = len(history_list) // 2

        first_half_avg = sum(history_list[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(history_list[mid:]) / (len(history_list) - mid)

        difference = second_half_avg - first_half_avg
        threshold = 0.01  # 1% change threshold

        if difference > threshold:
            return "increasing"
        elif difference < -threshold:
            return "decreasing"
        else:
            return "stable"

    def reset_pause_counts(self) -> None:
        """Reset pause counters (call after intervention or new question)."""
        self._pause_count = 0
        self._long_pause_count = 0
        logger.info("[VAD] Pause counts reset")

    def get_struggle_signals(self) -> Dict[str, Any]:
        """
        Get consolidated struggle signals for TeachingAssistant integration.
        """
        return {
            "hesitation_score": self._calculate_hesitation_score(),
            "short_pauses": self._pause_count,
            "long_pauses": self._long_pause_count,
            "speaking_rate": self._calculate_speaking_rate(),
            "volume_trend": self.get_volume_trend(),
            "average_volume": self.get_average_volume(),
            "is_speaking": self._latest_state.get("is_speaking", False),
        }
