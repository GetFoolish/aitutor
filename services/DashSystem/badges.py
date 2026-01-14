import math
import time
import logging
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from shared.logging_config import get_logger

logger = get_logger(__name__)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Helper function for backward compatibility
def log_print(message: str):
    """Wrapper for logger.info for easier migration"""
    logger.info(message)


class BadgeType(Enum):
    """Types of badges that can be earned"""
    SKILL_MASTERY = "skill_mastery"
    STREAK = "streak"
    QUESTION_COUNT = "question_count"
    PERFECT_SCORE = "perfect_score"


@dataclass
class Badge:
    """Represents a badge that can be earned"""
    badge_id: str
    name: str
    description: str
    badge_type: BadgeType
    icon: str  # Icon identifier (e.g., "trophy", "star", "fire")
    requirement: float  # Numeric requirement (e.g., 50 for 50%, 10 for 10 questions)
    tier: Optional[str] = None  # "bronze", "silver", "gold" for mastery badges

    def to_dict(self):
        return {
            'badge_id': self.badge_id,
            'name': self.name,
            'description': self.description,
            'badge_type': self.badge_type.value,
            'icon': self.icon,
            'requirement': self.requirement,
            'tier': self.tier
        }


class BadgeSystem:
    """System for managing badges and tracking user progress"""

    def __init__(self):
        self.badges: Dict[str, Badge] = {}
        self._initialize_badges()
        log_print(f"[BADGES] Initialized badge system with {len(self.badges)} badges")

    def _initialize_badges(self):
        """Initialize all available badges"""

        # Skill Mastery Badges (Bronze/Silver/Gold for 50%/75%/90% mastery)
        mastery_badges = [
            Badge(
                badge_id="mastery_bronze",
                name="Bronze Master",
                description="Achieve 50% mastery in any skill",
                badge_type=BadgeType.SKILL_MASTERY,
                icon="medal",
                requirement=50.0,
                tier="bronze"
            ),
            Badge(
                badge_id="mastery_silver",
                name="Silver Master",
                description="Achieve 75% mastery in any skill",
                badge_type=BadgeType.SKILL_MASTERY,
                icon="medal",
                requirement=75.0,
                tier="silver"
            ),
            Badge(
                badge_id="mastery_gold",
                name="Gold Master",
                description="Achieve 90% mastery in any skill",
                badge_type=BadgeType.SKILL_MASTERY,
                icon="medal",
                requirement=90.0,
                tier="gold"
            ),
        ]

        # Streak Badges (3-day, 7-day, 30-day streaks)
        streak_badges = [
            Badge(
                badge_id="streak_3day",
                name="3-Day Streak",
                description="Practice for 3 consecutive days",
                badge_type=BadgeType.STREAK,
                icon="flame",
                requirement=3.0
            ),
            Badge(
                badge_id="streak_7day",
                name="Week Warrior",
                description="Practice for 7 consecutive days",
                badge_type=BadgeType.STREAK,
                icon="flame",
                requirement=7.0
            ),
            Badge(
                badge_id="streak_30day",
                name="Monthly Master",
                description="Practice for 30 consecutive days",
                badge_type=BadgeType.STREAK,
                icon="flame",
                requirement=30.0
            ),
        ]

        # Question Count Badges (10, 50, 100, 500 questions answered)
        question_count_badges = [
            Badge(
                badge_id="questions_10",
                name="Getting Started",
                description="Answer 10 questions",
                badge_type=BadgeType.QUESTION_COUNT,
                icon="check-circle",
                requirement=10.0
            ),
            Badge(
                badge_id="questions_50",
                name="Dedicated Learner",
                description="Answer 50 questions",
                badge_type=BadgeType.QUESTION_COUNT,
                icon="check-circle",
                requirement=50.0
            ),
            Badge(
                badge_id="questions_100",
                name="Century Club",
                description="Answer 100 questions",
                badge_type=BadgeType.QUESTION_COUNT,
                icon="check-circle",
                requirement=100.0
            ),
            Badge(
                badge_id="questions_500",
                name="Knowledge Seeker",
                description="Answer 500 questions",
                badge_type=BadgeType.QUESTION_COUNT,
                icon="check-circle",
                requirement=500.0
            ),
        ]

        # Perfect Score Badges (5, 10, 25 perfect answers in a row)
        perfect_score_badges = [
            Badge(
                badge_id="perfect_5",
                name="Perfect Start",
                description="Get 5 correct answers in a row",
                badge_type=BadgeType.PERFECT_SCORE,
                icon="star",
                requirement=5.0
            ),
            Badge(
                badge_id="perfect_10",
                name="Perfect Ten",
                description="Get 10 correct answers in a row",
                badge_type=BadgeType.PERFECT_SCORE,
                icon="star",
                requirement=10.0
            ),
            Badge(
                badge_id="perfect_25",
                name="Perfection Master",
                description="Get 25 correct answers in a row",
                badge_type=BadgeType.PERFECT_SCORE,
                icon="star",
                requirement=25.0
            ),
        ]

        # Add all badges to the badges dictionary
        all_badges = mastery_badges + streak_badges + question_count_badges + perfect_score_badges
        for badge in all_badges:
            self.badges[badge.badge_id] = badge

    def get_all_badges(self) -> List[Badge]:
        """Get all available badges"""
        return list(self.badges.values())

    def get_badge_by_id(self, badge_id: str) -> Optional[Badge]:
        """Get a specific badge by ID"""
        return self.badges.get(badge_id)

    def _calculate_mastery_progress(self, user_profile) -> Dict[str, float]:
        """Calculate mastery progress for all skills (memory_strength as percentage)"""
        mastery_progress = {}
        for skill_id, skill_state in user_profile.skill_states.items():
            # Memory strength is typically 0-1, convert to percentage
            mastery_percent = skill_state.memory_strength * 100.0
            mastery_progress[skill_id] = mastery_percent
        return mastery_progress

    def _calculate_streak(self, user_profile) -> int:
        """Calculate current consecutive day streak"""
        if not user_profile.question_history:
            return 0

        # Sort attempts by timestamp (most recent first)
        sorted_attempts = sorted(
            user_profile.question_history,
            key=lambda x: x.timestamp,
            reverse=True
        )

        # Get unique days when user practiced
        practice_days = set()
        for attempt in sorted_attempts:
            day = datetime.fromtimestamp(attempt.timestamp).date()
            practice_days.add(day)

        # Sort days in reverse chronological order
        sorted_days = sorted(practice_days, reverse=True)

        if not sorted_days:
            return 0

        # Check for consecutive days starting from most recent
        today = datetime.now().date()
        streak = 0
        expected_day = today

        for day in sorted_days:
            if day == expected_day:
                streak += 1
                expected_day = expected_day - timedelta(days=1)
            elif day < expected_day - timedelta(days=1):
                # Gap in streak
                break

        return streak

    def _calculate_question_count(self, user_profile) -> int:
        """Calculate total number of questions answered"""
        return len(user_profile.question_history)

    def _calculate_current_perfect_streak(self, user_profile) -> int:
        """Calculate current perfect answer streak (consecutive correct)"""
        if not user_profile.question_history:
            return 0

        # Sort attempts by timestamp (most recent first)
        sorted_attempts = sorted(
            user_profile.question_history,
            key=lambda x: x.timestamp,
            reverse=True
        )

        # Count consecutive correct answers from most recent
        streak = 0
        for attempt in sorted_attempts:
            if attempt.is_correct:
                streak += 1
            else:
                break

        return streak

    def _calculate_max_perfect_streak(self, user_profile) -> int:
        """Calculate maximum perfect answer streak ever achieved"""
        if not user_profile.question_history:
            return 0

        # Sort attempts by timestamp (oldest first)
        sorted_attempts = sorted(
            user_profile.question_history,
            key=lambda x: x.timestamp
        )

        max_streak = 0
        current_streak = 0

        for attempt in sorted_attempts:
            if attempt.is_correct:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def get_badge_progress(self, user_profile) -> Dict[str, Dict]:
        """
        Calculate progress toward each badge for the user.

        Returns:
            Dict mapping badge_id to progress info:
            {
                'badge_id': {
                    'current': current_progress,
                    'required': requirement,
                    'percentage': percentage_complete,
                    'earned': is_earned
                }
            }
        """
        progress = {}

        # Get current earned badges from user profile
        earned_badges = getattr(user_profile, 'earned_badges', [])

        # Calculate metrics
        mastery_progress = self._calculate_mastery_progress(user_profile)
        max_mastery = max(mastery_progress.values()) if mastery_progress else 0.0
        current_streak = self._calculate_streak(user_profile)
        question_count = self._calculate_question_count(user_profile)
        max_perfect_streak = self._calculate_max_perfect_streak(user_profile)

        for badge_id, badge in self.badges.items():
            current_value = 0.0

            if badge.badge_type == BadgeType.SKILL_MASTERY:
                current_value = max_mastery
            elif badge.badge_type == BadgeType.STREAK:
                current_value = float(current_streak)
            elif badge.badge_type == BadgeType.QUESTION_COUNT:
                current_value = float(question_count)
            elif badge.badge_type == BadgeType.PERFECT_SCORE:
                current_value = float(max_perfect_streak)

            is_earned = badge_id in earned_badges
            percentage = min(100.0, (current_value / badge.requirement * 100.0) if badge.requirement > 0 else 0.0)

            progress[badge_id] = {
                'current': current_value,
                'required': badge.requirement,
                'percentage': percentage,
                'earned': is_earned
            }

        return progress

    def check_badges_earned(self, user_profile) -> Tuple[List[str], Dict[str, Dict]]:
        """
        Check which new badges the user has earned.

        Args:
            user_profile: UserProfile object with earned_badges field

        Returns:
            Tuple of (newly_earned_badge_ids, badge_progress)
        """
        # Get current earned badges
        earned_badges = getattr(user_profile, 'earned_badges', [])

        # Calculate badge progress
        badge_progress = self.get_badge_progress(user_profile)

        # Find newly earned badges
        newly_earned = []
        for badge_id, progress in badge_progress.items():
            # Check if badge is earned but not yet in user's earned list
            if progress['current'] >= progress['required'] and badge_id not in earned_badges:
                newly_earned.append(badge_id)
                log_print(f"[BADGES] User {user_profile.user_id} earned new badge: {badge_id}")

        return newly_earned, badge_progress
