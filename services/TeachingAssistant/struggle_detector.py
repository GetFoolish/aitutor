"""
Struggle Detector for TeachingAssistant
Detects when students are struggling based on multi-signal analysis.
Combines interaction, audio, and visual signals for comprehensive detection.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from shared.logging_config import get_logger

logger = get_logger(__name__)


class StruggleDetector:
    """
    Detects struggle signals from student behavior and calculates struggle score.
    Analyzes three signal categories:
    - Interaction signals (40%): errors, pauses, inactivity, hints
    - Audio signals (30%): voice hesitation, pauses, volume
    - Visual signals (30%): facial emotion, engagement, attention
    """

    # Thresholds for struggle detection
    LONG_PAUSE_THRESHOLD_SECONDS = 30
    INACTIVITY_THRESHOLD_SECONDS = 60
    REPEATED_ERRORS_THRESHOLD = 3
    HIGH_HINT_USAGE_THRESHOLD = 2

    # Multi-signal weights (sum to 1.0)
    # Interaction signals (40%)
    WEIGHT_ERRORS = 0.20
    WEIGHT_PAUSES = 0.10
    WEIGHT_HINTS = 0.10

    # Audio signals from Vision Agents (30%)
    WEIGHT_VOICE_HESITATION = 0.15
    WEIGHT_LONG_SILENCE = 0.10
    WEIGHT_LOW_VOLUME = 0.05

    # Visual signals from Vision Agents (30%)
    WEIGHT_FACIAL_EMOTION = 0.15
    WEIGHT_ENGAGEMENT = 0.10
    WEIGHT_LOOKING_AWAY = 0.05

    # Legacy weights for backward compatibility (when no audio/visual signals)
    LEGACY_WEIGHT_ERRORS = 0.4
    LEGACY_WEIGHT_PAUSES = 0.3
    LEGACY_WEIGHT_INACTIVITY = 0.2
    LEGACY_WEIGHT_HINTS = 0.1

    def __init__(self):
        """Initialize StruggleDetector"""
        logger.info("[STRUGGLE_DETECTOR] Initialized")

    def detect_long_pause(self, session: Dict[str, Any]) -> bool:
        """
        Detect if student is pausing for too long on current question.

        Args:
            session: Session document from MongoDB

        Returns:
            True if student has been paused longer than threshold
        """
        pause_start = session.get("pause_start_time")
        if not pause_start:
            return False

        now = datetime.utcnow()
        pause_duration = (now - pause_start).total_seconds()

        is_long_pause = pause_duration > self.LONG_PAUSE_THRESHOLD_SECONDS

        if is_long_pause:
            logger.info(
                f"[STRUGGLE_DETECTOR] Long pause detected: {pause_duration:.1f}s "
                f"for session {session.get('session_id')}"
            )

        return is_long_pause

    def detect_repeated_errors(self, session: Dict[str, Any]) -> bool:
        """
        Detect if student is making repeated errors.

        Args:
            session: Session document from MongoDB

        Returns:
            True if consecutive errors exceed threshold
        """
        consecutive_errors = session.get("consecutive_errors", 0)
        has_repeated_errors = consecutive_errors >= self.REPEATED_ERRORS_THRESHOLD

        if has_repeated_errors:
            logger.info(
                f"[STRUGGLE_DETECTOR] Repeated errors detected: {consecutive_errors} "
                f"consecutive errors for session {session.get('session_id')}"
            )

        return has_repeated_errors

    def detect_inactivity(self, session: Dict[str, Any]) -> bool:
        """
        Detect if student has been inactive for too long.

        Args:
            session: Session document from MongoDB

        Returns:
            True if student has been inactive longer than threshold
        """
        last_activity = session.get("last_activity")
        if not last_activity:
            return False

        now = datetime.utcnow()
        inactivity_duration = (now - last_activity).total_seconds()

        is_inactive = inactivity_duration > self.INACTIVITY_THRESHOLD_SECONDS

        if is_inactive:
            logger.info(
                f"[STRUGGLE_DETECTOR] Inactivity detected: {inactivity_duration:.1f}s "
                f"for session {session.get('session_id')}"
            )

        return is_inactive

    def detect_high_hint_usage(self, session: Dict[str, Any]) -> bool:
        """
        Detect if student is requesting hints frequently.

        Args:
            session: Session document from MongoDB

        Returns:
            True if hint requests exceed threshold
        """
        hint_requests = session.get("hint_requests", 0)
        questions_answered = session.get("questions_answered_this_session", 0)

        # High hint usage if more hints than questions (or threshold in short sessions)
        has_high_hint_usage = hint_requests >= self.HIGH_HINT_USAGE_THRESHOLD

        if has_high_hint_usage and questions_answered > 0:
            hint_ratio = hint_requests / questions_answered
            logger.info(
                f"[STRUGGLE_DETECTOR] High hint usage detected: {hint_requests} hints, "
                f"{questions_answered} questions (ratio: {hint_ratio:.2f}) "
                f"for session {session.get('session_id')}"
            )

        return has_high_hint_usage

    def calculate_struggle_score(self, session: Dict[str, Any]) -> float:
        """
        Calculate overall struggle score based on multiple signals.
        Uses multi-signal weights if audio/visual signals are present,
        otherwise falls back to legacy interaction-only weights.

        Args:
            session: Session document from MongoDB

        Returns:
            Struggle score between 0.0 (no struggle) and 1.0 (high struggle)
        """
        # Get individual interaction signals
        has_long_pause = self.detect_long_pause(session)
        has_repeated_errors = self.detect_repeated_errors(session)
        is_inactive = self.detect_inactivity(session)
        has_high_hint_usage = self.detect_high_hint_usage(session)

        # Calculate interaction component scores (0.0 to 1.0)
        error_score = min(session.get("consecutive_errors", 0) / 5.0, 1.0)
        pause_score = 1.0 if has_long_pause else 0.0
        inactivity_score = 1.0 if is_inactive else 0.0
        hint_score = min(session.get("hint_requests", 0) / 5.0, 1.0)

        # Check if we have audio/visual signals from Vision Agents
        audio_signals = session.get("audio_signals", {})
        visual_signals = session.get("visual_signals", {})
        has_multi_signal = bool(audio_signals) or bool(visual_signals)

        if has_multi_signal:
            # Multi-signal calculation with audio and visual
            struggle_score = self._calculate_multi_signal_score(
                session, error_score, pause_score, hint_score,
                audio_signals, visual_signals
            )
        else:
            # Legacy calculation using only interaction signals
            struggle_score = (
                error_score * self.LEGACY_WEIGHT_ERRORS +
                pause_score * self.LEGACY_WEIGHT_PAUSES +
                inactivity_score * self.LEGACY_WEIGHT_INACTIVITY +
                hint_score * self.LEGACY_WEIGHT_HINTS
            )

            logger.info(
                f"[STRUGGLE_DETECTOR] Calculated struggle score (legacy): {struggle_score:.2f} "
                f"(errors={error_score:.2f}, pauses={pause_score:.2f}, "
                f"inactivity={inactivity_score:.2f}, hints={hint_score:.2f}) "
                f"for session {session.get('session_id')}"
            )

        return struggle_score

    def _calculate_multi_signal_score(
        self,
        session: Dict[str, Any],
        error_score: float,
        pause_score: float,
        hint_score: float,
        audio_signals: Dict[str, Any],
        visual_signals: Dict[str, Any],
    ) -> float:
        """
        Calculate struggle score using multi-signal fusion.

        Args:
            session: Session document
            error_score: Interaction error score (0-1)
            pause_score: Interaction pause score (0-1)
            hint_score: Interaction hint score (0-1)
            audio_signals: Audio signals from Vision Agents
            visual_signals: Visual signals from Vision Agents

        Returns:
            Multi-signal struggle score (0.0 to 1.0)
        """
        # Audio signal scores
        hesitation_score = audio_signals.get("hesitation_score", 0.0)
        long_silence_score = 1.0 if audio_signals.get("long_pauses", 0) >= 2 else 0.0
        volume_trend = audio_signals.get("volume_trend", "stable")
        low_volume_score = 1.0 if volume_trend == "decreasing" else 0.0

        # Visual signal scores
        emotion = visual_signals.get("emotion", "neutral")
        emotion_struggle_score = visual_signals.get("emotion_struggle_score", 0.0)

        # Map emotion to score
        if emotion in ("frustrated", "confused"):
            facial_emotion_score = max(emotion_struggle_score, 0.5)
        elif emotion == "engaged":
            facial_emotion_score = 0.0  # Engaged = not struggling
        else:
            facial_emotion_score = emotion_struggle_score

        engagement_score = visual_signals.get("engagement_score", 1.0)
        # Invert engagement (1.0 = engaged = no struggle, 0.0 = disengaged = high struggle)
        disengagement_score = 1.0 - engagement_score

        is_distracted = visual_signals.get("is_distracted", False)
        looking_away_score = 1.0 if is_distracted else 0.0

        # Calculate weighted sum
        struggle_score = (
            # Interaction (40%)
            error_score * self.WEIGHT_ERRORS +
            pause_score * self.WEIGHT_PAUSES +
            hint_score * self.WEIGHT_HINTS +
            # Audio (30%)
            hesitation_score * self.WEIGHT_VOICE_HESITATION +
            long_silence_score * self.WEIGHT_LONG_SILENCE +
            low_volume_score * self.WEIGHT_LOW_VOLUME +
            # Visual (30%)
            facial_emotion_score * self.WEIGHT_FACIAL_EMOTION +
            disengagement_score * self.WEIGHT_ENGAGEMENT +
            looking_away_score * self.WEIGHT_LOOKING_AWAY
        )

        logger.info(
            f"[STRUGGLE_DETECTOR] Multi-signal struggle score: {struggle_score:.2f}"
        )
        logger.info(
            f"[STRUGGLE_DETECTOR]   Interaction: errors={error_score:.2f}, "
            f"pauses={pause_score:.2f}, hints={hint_score:.2f}"
        )
        logger.info(
            f"[STRUGGLE_DETECTOR]   Audio: hesitation={hesitation_score:.2f}, "
            f"silence={long_silence_score:.2f}, volume={low_volume_score:.2f}"
        )
        logger.info(
            f"[STRUGGLE_DETECTOR]   Visual: emotion={facial_emotion_score:.2f} ({emotion}), "
            f"disengage={disengagement_score:.2f}, away={looking_away_score:.2f}"
        )

        return struggle_score

    def analyze_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive struggle analysis on a session.
        Includes interaction, audio, and visual signals when available.

        Args:
            session: Session document from MongoDB

        Returns:
            Dictionary with analysis results:
            - struggle_score: float (0.0 to 1.0)
            - signals: dict of detected signals (interaction, audio, visual)
            - needs_intervention: bool
            - intervention_urgency: str ('low', 'medium', 'high')
            - signal_mode: str ('multi_signal' or 'interaction_only')
        """
        session_id = session.get('session_id', 'unknown')
        consecutive_errors = session.get('consecutive_errors', 0)
        audio_signals = session.get("audio_signals", {})
        visual_signals = session.get("visual_signals", {})
        has_multi_signal = bool(audio_signals) or bool(visual_signals)

        logger.info(f"")
        logger.info(f"[STRUGGLE_DETECTOR] {'─'*50}")
        logger.info(f"[STRUGGLE_DETECTOR] 🔬 ANALYZING SESSION: {session_id}")
        logger.info(f"[STRUGGLE_DETECTOR]    Mode: {'multi_signal' if has_multi_signal else 'interaction_only'}")
        logger.info(f"[STRUGGLE_DETECTOR]    Consecutive errors: {consecutive_errors}")
        logger.info(f"[STRUGGLE_DETECTOR]    Hint requests: {session.get('hint_requests', 0)}")

        if has_multi_signal:
            logger.info(f"[STRUGGLE_DETECTOR]    Audio signals: {audio_signals}")
            logger.info(f"[STRUGGLE_DETECTOR]    Visual signals: {visual_signals}")

        struggle_score = self.calculate_struggle_score(session)

        # Interaction signals
        interaction_signals = {
            "long_pause": self.detect_long_pause(session),
            "repeated_errors": self.detect_repeated_errors(session),
            "inactivity": self.detect_inactivity(session),
            "high_hint_usage": self.detect_high_hint_usage(session),
        }

        # Build comprehensive signals dict
        signals = {
            "interaction": interaction_signals,
        }

        if audio_signals:
            signals["audio"] = {
                "hesitation": audio_signals.get("hesitation_score", 0.0) > 0.3,
                "long_pauses": audio_signals.get("long_pauses", 0) >= 2,
                "decreasing_volume": audio_signals.get("volume_trend") == "decreasing",
                "is_speaking": audio_signals.get("is_speaking", False),
            }

        if visual_signals:
            signals["visual"] = {
                "frustrated_or_confused": visual_signals.get("emotion") in ("frustrated", "confused"),
                "disengaged": visual_signals.get("engagement_score", 1.0) < 0.5,
                "looking_away": visual_signals.get("is_distracted", False),
                "face_detected": visual_signals.get("face_detected", True),
                "emotion": visual_signals.get("emotion", "unknown"),
            }

        # Determine if intervention is needed
        needs_intervention = struggle_score >= 0.2  # Lowered from 0.4 for testing

        # Determine urgency level
        if struggle_score >= 0.7:
            urgency = "high"
        elif struggle_score >= 0.4:
            urgency = "medium"
        else:
            urgency = "low"

        logger.info(f"[STRUGGLE_DETECTOR] 📊 ANALYSIS RESULT:")
        logger.info(f"[STRUGGLE_DETECTOR]    Score: {struggle_score:.2f} (threshold: 0.2)")
        logger.info(f"[STRUGGLE_DETECTOR]    Needs intervention: {needs_intervention}")
        logger.info(f"[STRUGGLE_DETECTOR]    Urgency: {urgency}")
        logger.info(f"[STRUGGLE_DETECTOR]    Signals: {signals}")
        logger.info(f"[STRUGGLE_DETECTOR] {'─'*50}")

        return {
            "struggle_score": struggle_score,
            "signals": signals,
            "needs_intervention": needs_intervention,
            "intervention_urgency": urgency,
            "signal_mode": "multi_signal" if has_multi_signal else "interaction_only",
            "analyzed_at": datetime.utcnow(),
        }
