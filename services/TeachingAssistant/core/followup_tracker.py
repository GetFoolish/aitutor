"""
Proactive Follow-up Tracker - Remembering What Matters to Students

This module tracks and surfaces things to follow up on:
- Upcoming tests and exams
- Events (sports games, recitals, trips)
- Commitments the student made ("I'll practice tonight")
- Unfinished topics from previous sessions
- Personal updates worth checking on

A great tutor remembers these things naturally. This isn't surveillance - it's caring.

Uses Gemini for intelligent extraction from conversation.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class FollowupType(str, Enum):
    """Types of things to follow up on"""
    TEST = "test"                    # Upcoming test, exam, quiz
    EVENT = "event"                  # Sports game, recital, birthday, trip
    COMMITMENT = "commitment"        # "I'll practice tonight", "I'll review this"
    UNFINISHED_TOPIC = "unfinished"  # Topic we didn't complete
    PERSONAL = "personal"            # Pet, family update, personal situation
    STRUGGLE = "struggle"            # Topic they struggled with - check progress
    ACHIEVEMENT = "achievement"      # Something they accomplished - celebrate


@dataclass
class Followup:
    """A single follow-up item"""
    type: FollowupType
    description: str
    due_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    followed_up: bool = False
    priority: int = 2  # 1=low, 2=medium, 3=high
    session_id: Optional[str] = None
    context: Optional[str] = None  # Additional context

    def is_due(self) -> bool:
        """Check if this followup should be mentioned"""
        if self.followed_up:
            return False
        if not self.due_date:
            return True  # No date = always relevant (within reason)

        now = datetime.utcnow()
        # Due within 2 days or already passed
        return now >= self.due_date - timedelta(days=2)

    def days_until(self) -> Optional[int]:
        """Get days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.utcnow()
        return delta.days

    def to_prompt_text(self) -> str:
        """Convert to text for prompt injection"""
        days = self.days_until()
        date_str = ""
        if days is not None:
            if days < 0:
                date_str = " (already passed - ask how it went)"
            elif days == 0:
                date_str = " (TODAY)"
            elif days == 1:
                date_str = " (tomorrow)"
            else:
                date_str = f" (in {days} days)"

        type_emoji = {
            FollowupType.TEST: "📝",
            FollowupType.EVENT: "📅",
            FollowupType.COMMITMENT: "🎯",
            FollowupType.UNFINISHED_TOPIC: "📚",
            FollowupType.PERSONAL: "💬",
            FollowupType.STRUGGLE: "💪",
            FollowupType.ACHIEVEMENT: "🎉"
        }

        emoji = type_emoji.get(self.type, "•")
        return f"{emoji} {self.description}{date_str}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "type": self.type.value,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "followed_up": self.followed_up,
            "priority": self.priority,
            "session_id": self.session_id,
            "context": self.context
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Followup":
        """Create from dictionary"""
        return cls(
            type=FollowupType(data["type"]),
            description=data["description"],
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            followed_up=data.get("followed_up", False),
            priority=data.get("priority", 2),
            session_id=data.get("session_id"),
            context=data.get("context")
        )


class FollowupTracker:
    """
    Extracts and manages follow-up items from conversations.

    Uses Gemini to intelligently identify:
    - Upcoming events/tests the student mentions
    - Commitments they make
    - Topics that need revisiting
    - Personal situations worth following up on
    """

    def __init__(self):
        """Initialize the Follow-up Tracker with Gemini."""
        self.enabled = False
        self.gemini_client = None
        self.gemini_model_name = None

        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
                self.gemini_model_name = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
                self.enabled = True
                logger.info(f"[FOLLOWUP_TRACKER] Initialized with Gemini ({self.gemini_model_name})")
            except Exception as e:
                logger.warning(f"[FOLLOWUP_TRACKER] Gemini initialization failed: {e}")

        if not self.enabled:
            logger.warning("[FOLLOWUP_TRACKER] Gemini not available. Follow-up extraction limited.")

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> Optional[str]:
        """Call Gemini with a prompt."""
        if not self.enabled or not self.gemini_client:
            return None

        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=prompt,
                config={
                    'temperature': temperature,
                    'max_output_tokens': 500
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"[FOLLOWUP_TRACKER] Gemini call failed: {e}")
            return None

    def extract_followups(
        self,
        conversation: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        current_topic: Optional[str] = None
    ) -> List[Followup]:
        """
        Extract follow-up items from a conversation.

        Args:
            conversation: List of conversation turns [{speaker, text}, ...]
            session_id: Current session ID
            current_topic: Topic being discussed (for unfinished tracking)

        Returns:
            List of extracted Followup items
        """
        if not conversation:
            return []

        # Extract student text
        student_texts = [
            turn.get("text", "")
            for turn in conversation
            if turn.get("speaker") == "student"
        ]

        if not student_texts:
            return []

        student_text = "\n".join(student_texts[-10:])  # Last 10 student turns

        if self.enabled:
            return self._llm_extraction(student_text, session_id, current_topic)
        else:
            return self._rule_based_extraction(student_text, session_id)

    def _llm_extraction(
        self,
        student_text: str,
        session_id: Optional[str],
        current_topic: Optional[str]
    ) -> List[Followup]:
        """Use Gemini to extract follow-up items."""
        today = datetime.utcnow().strftime("%A, %B %d, %Y")

        prompt = f"""Extract things worth following up on from what this student said.

Today's date: {today}

Student said:
"{student_text}"

{f'Current topic being studied: {current_topic}' if current_topic else ''}

Look for:
1. TEST/EXAM: Upcoming tests, quizzes, exams
2. EVENT: Games, recitals, birthdays, trips, appointments
3. COMMITMENT: Things they said they'd do ("I'll practice", "I'll review")
4. PERSONAL: Pet updates, family situations, personal news worth checking on
5. STRUGGLE: Topics they're clearly struggling with

For each item found, extract:
- type: test|event|commitment|personal|struggle
- description: Brief description
- due_date: If mentioned (format: YYYY-MM-DD), or null
- priority: 1-3 (3=high, like a test tomorrow)

Output as JSON array. If nothing found, output empty array [].

Example output:
[
  {{"type": "test", "description": "Math test on fractions", "due_date": "2024-01-25", "priority": 3}},
  {{"type": "commitment", "description": "Will practice multiplication tables", "due_date": null, "priority": 2}},
  {{"type": "personal", "description": "Dog Max is sick, going to vet", "due_date": null, "priority": 2}}
]

Extract follow-ups:"""

        result = self._call_llm(prompt)

        if not result:
            return []

        try:
            # Clean up response
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]

            items = json.loads(result.strip())

            followups = []
            for item in items:
                try:
                    due_date = None
                    if item.get("due_date"):
                        due_date = datetime.strptime(item["due_date"], "%Y-%m-%d")

                    followup = Followup(
                        type=FollowupType(item["type"]),
                        description=item["description"],
                        due_date=due_date,
                        priority=item.get("priority", 2),
                        session_id=session_id
                    )
                    followups.append(followup)
                except (ValueError, KeyError) as e:
                    logger.warning(f"[FOLLOWUP_TRACKER] Failed to parse item: {e}")

            logger.info(f"[FOLLOWUP_TRACKER] Extracted {len(followups)} follow-ups")
            return followups

        except json.JSONDecodeError as e:
            logger.warning(f"[FOLLOWUP_TRACKER] Failed to parse LLM response: {e}")
            return []

    def _rule_based_extraction(
        self,
        student_text: str,
        session_id: Optional[str]
    ) -> List[Followup]:
        """Fallback rule-based extraction."""
        followups = []
        student_lower = student_text.lower()

        # Test detection
        test_keywords = ["test", "exam", "quiz", "assessment", "midterm", "final"]
        for keyword in test_keywords:
            if keyword in student_lower:
                followups.append(Followup(
                    type=FollowupType.TEST,
                    description=f"Mentioned upcoming {keyword}",
                    priority=3,
                    session_id=session_id
                ))
                break

        # Event detection
        event_keywords = ["game", "match", "recital", "concert", "birthday", "trip"]
        for keyword in event_keywords:
            if keyword in student_lower:
                followups.append(Followup(
                    type=FollowupType.EVENT,
                    description=f"Mentioned {keyword}",
                    priority=2,
                    session_id=session_id
                ))
                break

        # Commitment detection
        commitment_patterns = ["i'll ", "i will ", "gonna ", "going to practice", "i promise"]
        for pattern in commitment_patterns:
            if pattern in student_lower:
                followups.append(Followup(
                    type=FollowupType.COMMITMENT,
                    description="Made a commitment to practice/study",
                    priority=2,
                    session_id=session_id
                ))
                break

        return followups

    def get_due_followups(
        self,
        followups: List[Followup],
        max_items: int = 3
    ) -> List[Followup]:
        """Get follow-ups that should be mentioned now."""
        due = [f for f in followups if f.is_due()]

        # Sort by priority (high first), then by due date (soonest first)
        due.sort(key=lambda f: (
            -f.priority,
            f.due_date or datetime.max
        ))

        return due[:max_items]

    def generate_opening_followups(
        self,
        followups: List[Followup],
        student_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate text for session opening with follow-ups.

        Args:
            followups: List of all followups for this student
            student_name: Student's name

        Returns:
            Formatted string for injection, or None
        """
        due = self.get_due_followups(followups)
        if not due:
            return None

        name = student_name or "the student"

        lines = [f"Things to naturally follow up on with {name}:"]
        for f in due:
            lines.append(f"- {f.to_prompt_text()}")

        lines.append("")
        lines.append("Work these into conversation naturally - don't list them all at once!")
        lines.append("Tests/events: Check how prep is going or how it went")
        lines.append("Commitments: Ask if they followed through")
        lines.append("Personal: Show genuine interest")

        return "\n".join(lines)

    def generate_mid_session_prompt(
        self,
        followups: List[Followup],
        current_emotion: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a follow-up prompt for mid-session injection.

        Only surfaces one item at natural conversation breaks.

        Args:
            followups: Available followups
            current_emotion: Student's current emotion

        Returns:
            Single follow-up prompt, or None
        """
        # Don't interrupt if student is frustrated
        if current_emotion in ["frustrated", "anxious", "tired", "confused"]:
            return None

        due = self.get_due_followups(followups, max_items=1)
        if not due:
            return None

        f = due[0]

        prompts = {
            FollowupType.TEST: f"When there's a natural pause, check in about: {f.description}",
            FollowupType.EVENT: f"When conversation allows, ask about: {f.description}",
            FollowupType.COMMITMENT: f"Follow up on their commitment: {f.description}",
            FollowupType.PERSONAL: f"Show you care - ask about: {f.description}",
            FollowupType.ACHIEVEMENT: f"Celebrate their achievement: {f.description}",
        }

        return prompts.get(f.type, f"Follow up on: {f.description}")

    def mark_followed_up(self, followup: Followup) -> None:
        """Mark a follow-up as completed."""
        followup.followed_up = True

    def create_unfinished_topic(
        self,
        topic: str,
        session_id: Optional[str] = None,
        context: Optional[str] = None
    ) -> Followup:
        """Create a follow-up for an unfinished topic."""
        return Followup(
            type=FollowupType.UNFINISHED_TOPIC,
            description=f"Didn't finish covering: {topic}",
            priority=2,
            session_id=session_id,
            context=context
        )

    def create_achievement(
        self,
        description: str,
        session_id: Optional[str] = None
    ) -> Followup:
        """Create a follow-up to celebrate an achievement."""
        return Followup(
            type=FollowupType.ACHIEVEMENT,
            description=description,
            priority=2,
            session_id=session_id
        )


# Singleton instance - lazy initialization
_followup_tracker_instance = None

def get_followup_tracker() -> FollowupTracker:
    """Get or create the singleton FollowupTracker instance."""
    global _followup_tracker_instance
    if _followup_tracker_instance is None:
        _followup_tracker_instance = FollowupTracker()
    return _followup_tracker_instance


class _FollowupTrackerProxy:
    def __getattr__(self, name):
        return getattr(get_followup_tracker(), name)

followup_tracker = _FollowupTrackerProxy()
