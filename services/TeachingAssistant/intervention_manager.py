"""
Intervention Manager for TeachingAssistant
Selects and generates appropriate intervention prompts based on struggle signals.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from shared.logging_config import get_logger

logger = get_logger(__name__)


class InterventionManager:
    """
    Selects appropriate intervention type based on struggle analysis
    and generates system prompts for the AI tutor to deliver interventions naturally.
    """

    SYSTEM_PROMPT_PREFIX = "[SYSTEM PROMPT FOR ADAM]"

    # Intervention type selection thresholds
    BREAK_SUGGESTION_SCORE = 0.7  # High struggle - suggest break
    SIMPLIFICATION_ERROR_THRESHOLD = 3  # Multiple errors - simplify
    HINT_PAUSE_THRESHOLD = 30  # Long pause - offer hint

    def __init__(self):
        """Initialize InterventionManager"""
        logger.info("[INTERVENTION_MANAGER] Initialized")

    def select_intervention_type(
        self,
        analysis: Dict[str, Any],
        session: Dict[str, Any]
    ) -> str:
        """
        Select the most appropriate intervention type based on struggle analysis.

        Args:
            analysis: Struggle analysis from StruggleDetector.analyze_session()
            session: Session document from MongoDB

        Returns:
            Intervention type: 'hint', 'encouragement', 'simplification', 'break_suggestion'
        """
        struggle_score = analysis.get("struggle_score", 0.0)
        signals = analysis.get("signals", {})
        urgency = analysis.get("intervention_urgency", "low")

        consecutive_errors = session.get("consecutive_errors", 0)
        hint_requests = session.get("hint_requests", 0)

        # Priority order: break > simplification > hint > encouragement

        # High struggle or inactivity - suggest break
        if struggle_score >= self.BREAK_SUGGESTION_SCORE or signals.get("inactivity"):
            intervention_type = "break_suggestion"

        # Repeated errors - offer simplification
        elif signals.get("repeated_errors") or consecutive_errors >= self.SIMPLIFICATION_ERROR_THRESHOLD:
            intervention_type = "simplification"

        # Long pause - offer hint
        elif signals.get("long_pause"):
            intervention_type = "hint"

        # High hint usage or medium struggle - provide encouragement
        elif signals.get("high_hint_usage") or urgency == "medium":
            intervention_type = "encouragement"

        # Default to encouragement for any other low-level struggles
        else:
            intervention_type = "encouragement"

        logger.info(
            f"[INTERVENTION_MANAGER] Selected intervention type: {intervention_type} "
            f"(score={struggle_score:.2f}, urgency={urgency}, signals={signals})"
        )

        return intervention_type

    def get_hint_intervention(self, session: Dict[str, Any]) -> str:
        """
        Generate hint intervention prompt.
        Use when student is pausing for a long time on a question.

        Args:
            session: Session document from MongoDB

        Returns:
            System prompt for AI tutor to offer a hint
        """
        return f"""{self.SYSTEM_PROMPT_PREFIX}
The student has been thinking about this problem for a while and might be stuck.
Gently offer to provide a hint to help them move forward.
Be encouraging and let them know it's okay to ask for help.
Don't give away the answer - just offer to provide a helpful hint if they'd like one."""

    def get_encouragement_intervention(
        self,
        session: Dict[str, Any],
        struggle_score: float
    ) -> str:
        """
        Generate encouragement intervention prompt.
        Use when student is showing early signs of struggle.

        Args:
            session: Session document from MongoDB
            struggle_score: Current struggle score (0.0 to 1.0)

        Returns:
            System prompt for AI tutor to provide encouragement
        """
        questions_attempted = session.get("questions_answered_this_session", 0)

        return f"""{self.SYSTEM_PROMPT_PREFIX}
The student is working hard but might be feeling challenged.
Provide warm, genuine encouragement to boost their confidence.
Acknowledge their effort and persistence.
Remind them that making mistakes is part of learning.
Keep it brief and natural - don't interrupt their flow too much."""

    def get_simplification_intervention(self, session: Dict[str, Any]) -> str:
        """
        Generate simplification intervention prompt.
        Use when student is making repeated errors on the current problem.

        Args:
            session: Session document from MongoDB

        Returns:
            System prompt for AI tutor to suggest problem simplification
        """
        consecutive_errors = session.get("consecutive_errors", 0)

        return f"""{self.SYSTEM_PROMPT_PREFIX}
The student has made {consecutive_errors} attempts at this problem without success.
They may need a different approach or a simpler problem to build confidence.
Gently suggest that you can:
1. Break down the current problem into smaller steps
2. Try a similar but slightly easier problem first
3. Walk through a related example together
Let them choose what feels most helpful.
Be supportive and normalize that some problems need more scaffolding."""

    def get_break_suggestion_intervention(self, session: Dict[str, Any]) -> str:
        """
        Generate break suggestion intervention prompt.
        Use when student shows signs of high struggle or prolonged inactivity.

        Args:
            session: Session document from MongoDB

        Returns:
            System prompt for AI tutor to suggest taking a break
        """
        session_duration = session.get("session_duration_minutes", 0)

        return f"""{self.SYSTEM_PROMPT_PREFIX}
The student is showing signs of fatigue or frustration.
Gently suggest taking a short break.
Normalize that everyone needs breaks when learning challenging material.
Offer options:
- Take a 5-minute break and come back refreshed
- End the session for today and return tomorrow
- Try a quick fun math game before continuing
Be warm and supportive - avoid making them feel like they failed.
Emphasize that taking breaks is smart learning strategy."""

    def generate_intervention_prompt(
        self,
        intervention_type: str,
        session: Dict[str, Any],
        analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate intervention prompt for the specified type.

        Args:
            intervention_type: Type of intervention to generate
            session: Session document from MongoDB
            analysis: Optional struggle analysis data

        Returns:
            System prompt for AI tutor to deliver the intervention
        """
        logger.info(
            f"[INTERVENTION_MANAGER] Generating {intervention_type} intervention "
            f"for session {session.get('session_id')}"
        )

        if intervention_type == "hint":
            return self.get_hint_intervention(session)

        elif intervention_type == "encouragement":
            struggle_score = analysis.get("struggle_score", 0.5) if analysis else 0.5
            return self.get_encouragement_intervention(session, struggle_score)

        elif intervention_type == "simplification":
            return self.get_simplification_intervention(session)

        elif intervention_type == "break_suggestion":
            return self.get_break_suggestion_intervention(session)

        else:
            logger.warning(
                f"[INTERVENTION_MANAGER] Unknown intervention type: {intervention_type}, "
                f"defaulting to encouragement"
            )
            return self.get_encouragement_intervention(session, 0.5)

    def should_intervene(
        self,
        analysis: Dict[str, Any],
        session: Dict[str, Any]
    ) -> bool:
        """
        Determine if intervention should be triggered based on analysis and cooldown.

        Args:
            analysis: Struggle analysis from StruggleDetector.analyze_session()
            session: Session document from MongoDB

        Returns:
            True if intervention should be triggered now
        """
        # Check if intervention is needed based on struggle score
        if not analysis.get("needs_intervention", False):
            return False

        # Check cooldown period (minimum 2 minutes between interventions)
        last_intervention = session.get("last_intervention_time")
        if last_intervention:
            minutes_since_last = (datetime.utcnow() - last_intervention).total_seconds() / 60
            if minutes_since_last < 2.0:
                logger.info(
                    f"[INTERVENTION_MANAGER] Intervention blocked by cooldown: "
                    f"{minutes_since_last:.1f} minutes since last intervention "
                    f"(minimum 2.0 minutes)"
                )
                return False

        logger.info(
            f"[INTERVENTION_MANAGER] Intervention approved: "
            f"score={analysis.get('struggle_score', 0):.2f}, "
            f"urgency={analysis.get('intervention_urgency', 'unknown')}"
        )
        return True

    def get_user_friendly_message(self, intervention_type: str, session: Dict[str, Any]) -> str:
        """
        Generate user-friendly message for frontend display.

        Args:
            intervention_type: Type of intervention
            session: Session document from MongoDB

        Returns:
            User-friendly message string for display in InterventionOverlay
        """
        if intervention_type == "hint":
            return "You've been thinking hard about this problem. Would you like a hint to help you move forward?"

        elif intervention_type == "encouragement":
            return "You're doing great! Remember, making mistakes is part of learning. Keep up the excellent effort!"

        elif intervention_type == "simplification":
            return "This problem seems tricky. Would you like to try breaking it down into smaller steps, or work on a similar but simpler problem first?"

        elif intervention_type == "break_suggestion":
            return "You've been working hard! Sometimes a short break helps our brains process what we've learned. Would you like to take a 5-minute break?"

        else:
            return "I'm here to help if you need anything!"

    def create_intervention(
        self,
        analysis: Dict[str, Any],
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create complete intervention with type, prompt, and metadata.

        Args:
            analysis: Struggle analysis from StruggleDetector.analyze_session()
            session: Session document from MongoDB

        Returns:
            Dictionary with intervention details:
            - type: intervention type
            - prompt: system prompt for AI tutor
            - message: user-friendly message for frontend display
            - struggle_score: score that triggered intervention
            - signals: signals that were detected
            - timestamp: when intervention was created
        """
        intervention_type = self.select_intervention_type(analysis, session)
        prompt = self.generate_intervention_prompt(intervention_type, session, analysis)
        message = self.get_user_friendly_message(intervention_type, session)

        intervention = {
            "type": intervention_type,
            "prompt": prompt,
            "message": message,
            "struggle_score": analysis.get("struggle_score", 0.0),
            "signals": analysis.get("signals", {}),
            "urgency": analysis.get("intervention_urgency", "unknown"),
            "timestamp": datetime.utcnow(),
            "session_id": session.get("session_id"),
        }

        logger.info(
            f"[INTERVENTION_MANAGER] Created {intervention_type} intervention "
            f"for session {session.get('session_id')} "
            f"(score={intervention['struggle_score']:.2f})"
        )

        return intervention
