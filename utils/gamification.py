"""
Gamification utilities - XP calculation, leveling, streaks
"""
from datetime import datetime, date
from typing import Dict, Any, Tuple
from db.auth_repository import get_user_by_id, update_user


# XP Constants (Duolingo-inspired)
XP_CORRECT_ANSWER = 10  # Base XP for correct answer
XP_FIRST_TRY_BONUS = 5  # Bonus for getting it right first try
XP_STREAK_BONUS = 2  # Bonus per day of streak (max +10)
XP_PER_LEVEL = 100  # XP needed per level (increases slightly each level)


def calculate_xp_earned(is_correct: bool, is_first_try: bool = True, streak_count: int = 0) -> int:
    """
    Calculate XP earned for a question attempt.

    Args:
        is_correct: Whether the answer was correct
        is_first_try: Whether this was the first attempt
        streak_count: Current streak count for bonus calculation

    Returns:
        XP earned (0 if incorrect)
    """
    if not is_correct:
        return 0

    xp = XP_CORRECT_ANSWER

    # First try bonus
    if is_first_try:
        xp += XP_FIRST_TRY_BONUS

    # Streak bonus (capped at 5 days = +10 XP)
    streak_bonus = min(streak_count, 5) * XP_STREAK_BONUS
    xp += streak_bonus

    return xp


def calculate_level_from_xp(xp: int) -> int:
    """
    Calculate level based on total XP.
    Uses a slightly increasing curve: Level N requires N * 100 XP from previous level.

    Level 1: 0 XP
    Level 2: 100 XP
    Level 3: 300 XP (100 + 200)
    Level 4: 600 XP (100 + 200 + 300)
    """
    if xp == 0:
        return 1

    level = 1
    xp_required = 0

    while xp >= xp_required:
        level += 1
        xp_required += level * XP_PER_LEVEL

    return level - 1  # Back off by one since we went over


def xp_for_next_level(current_xp: int) -> Tuple[int, int]:
    """
    Calculate XP progress toward next level.

    Returns:
        (xp_in_current_level, xp_needed_for_next_level)
    """
    current_level = calculate_level_from_xp(current_xp)

    # Calculate XP at start of current level
    xp_at_level_start = 0
    for lvl in range(2, current_level + 1):
        xp_at_level_start += lvl * XP_PER_LEVEL

    # XP needed for next level
    xp_for_next = (current_level + 1) * XP_PER_LEVEL

    # XP in current level
    xp_in_level = current_xp - xp_at_level_start

    return (xp_in_level, xp_for_next)


def update_streak(last_practice_date: str | None) -> Tuple[int, str]:
    """
    Update streak count based on last practice date.

    Args:
        last_practice_date: ISO date string (YYYY-MM-DD) of last practice, or None

    Returns:
        (new_streak_count, today_date_string)
    """
    today = date.today()
    today_str = today.isoformat()

    # First time practicing
    if not last_practice_date:
        return (1, today_str)

    # Already practiced today
    if last_practice_date == today_str:
        # Parse existing streak from user data (will be passed separately)
        # Return unchanged - this is handled by caller
        return (None, today_str)  # None signals no change needed

    # Convert last practice to date
    try:
        last_date = date.fromisoformat(last_practice_date)
    except ValueError:
        # Invalid date format, reset streak
        return (1, today_str)

    # Calculate days since last practice
    days_diff = (today - last_date).days

    if days_diff == 1:
        # Consecutive day - increment streak (caller will add 1)
        return (-1, today_str)  # -1 signals increment
    else:
        # Streak broken - reset to 1
        return (1, today_str)


def award_xp_and_update_gamification(user_id: str, xp_earned: int) -> Dict[str, Any]:
    """
    Award XP to a user and update their gamification stats.

    Args:
        user_id: User's ID
        xp_earned: XP to award

    Returns:
        Dict with updated stats: {
            'xp': new_xp,
            'level': new_level,
            'level_up': bool,
            'streak_count': current_streak,
            'streak_updated': bool
        }
    """
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Get current stats (with defaults for backward compatibility)
    current_xp = user.get('xp', 0)
    current_level = user.get('level', 1)
    current_streak = user.get('streak_count', 0)
    last_practice = user.get('last_practice_date')

    # Update XP
    new_xp = current_xp + xp_earned
    new_level = calculate_level_from_xp(new_xp)
    level_up = new_level > current_level

    # Update streak
    streak_result, today_str = update_streak(last_practice)

    if streak_result is None:
        # Already practiced today, no streak change
        new_streak = current_streak
        streak_updated = False
    elif streak_result == -1:
        # Consecutive day, increment
        new_streak = current_streak + 1
        streak_updated = True
    else:
        # Reset or first time
        new_streak = streak_result
        streak_updated = True

    # Update database
    update_data = {
        'xp': new_xp,
        'level': new_level,
        'streak_count': new_streak,
        'last_practice_date': today_str
    }

    update_user(user_id, update_data)

    return {
        'xp': new_xp,
        'level': new_level,
        'level_up': level_up,
        'streak_count': new_streak,
        'streak_updated': streak_updated,
        'xp_earned': xp_earned
    }
