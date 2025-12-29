/**
 * Daily Streak Tracking Utility
 * Tracks consecutive days of practice with localStorage and backend sync
 */

const STREAK_KEY = 'daily_streak_data';

export interface StreakData {
  currentStreak: number;
  longestStreak: number;
  lastPracticeDate: string | null; // ISO date string
  totalDaysPracticed: number;
  hasStreakFreeze: boolean;
  streakFreezeCount: number;
  lastStreakFreezeEarned: string | null; // ISO date string
}

const DEFAULT_STREAK_DATA: StreakData = {
  currentStreak: 0,
  longestStreak: 0,
  lastPracticeDate: null,
  totalDaysPracticed: 0,
  hasStreakFreeze: false,
  streakFreezeCount: 0,
  lastStreakFreezeEarned: null,
};

// Get today's date as YYYY-MM-DD string
export function getTodayDate(): string {
  return new Date().toISOString().split('T')[0];
}

// Get yesterday's date as YYYY-MM-DD string
export function getYesterdayDate(): string {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return yesterday.toISOString().split('T')[0];
}

// Check if two dates are the same day
export function isSameDay(date1: string, date2: string): boolean {
  return date1 === date2;
}

// Check if date1 is exactly one day before date2
export function isConsecutiveDay(lastDate: string, today: string): boolean {
  const last = new Date(lastDate);
  const current = new Date(today);
  const diffTime = current.getTime() - last.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  return diffDays === 1;
}

// Check if streak was broken (more than 1 day gap)
export function isStreakBroken(lastDate: string, today: string): boolean {
  const last = new Date(lastDate);
  const current = new Date(today);
  const diffTime = current.getTime() - last.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  return diffDays > 1;
}

export const streakUtils = {
  // Get streak data from localStorage
  getStreakData(): StreakData {
    try {
      const data = localStorage.getItem(STREAK_KEY);
      if (data) {
        return { ...DEFAULT_STREAK_DATA, ...JSON.parse(data) };
      }
    } catch (error) {
      console.error('Error reading streak data:', error);
    }
    return { ...DEFAULT_STREAK_DATA };
  },

  // Save streak data to localStorage
  saveStreakData(data: StreakData): void {
    try {
      localStorage.setItem(STREAK_KEY, JSON.stringify(data));
    } catch (error) {
      console.error('Error saving streak data:', error);
    }
  },

  // Record a practice session for today
  recordPractice(): { data: StreakData; message: string | null; isNewStreak: boolean } {
    const data = this.getStreakData();
    const today = getTodayDate();
    let message: string | null = null;
    let isNewStreak = false;

    // Already practiced today
    if (data.lastPracticeDate && isSameDay(data.lastPracticeDate, today)) {
      return { data, message: null, isNewStreak: false };
    }

    // First time practicing
    if (!data.lastPracticeDate) {
      data.currentStreak = 1;
      data.totalDaysPracticed = 1;
      message = "🔥 You started your streak! Keep it going!";
      isNewStreak = true;
    }
    // Consecutive day
    else if (isConsecutiveDay(data.lastPracticeDate, today)) {
      data.currentStreak += 1;
      data.totalDaysPracticed += 1;
      isNewStreak = true;

      // Special milestone messages
      if (data.currentStreak === 3) {
        message = "🔥 3 days in a row! You're building a habit!";
      } else if (data.currentStreak === 5) {
        message = "🔥 You're on fire! 5 days in a row!";
      } else if (data.currentStreak === 7) {
        message = "🎉 AMAZING! 7 days straight! You earned a Streak Freeze!";
        data.hasStreakFreeze = true;
        data.streakFreezeCount += 1;
        data.lastStreakFreezeEarned = today;
      } else if (data.currentStreak === 10) {
        message = "🏆 10 days! You're unstoppable!";
      } else if (data.currentStreak === 14) {
        message = "⭐ 2 weeks! You've earned another Streak Freeze!";
        data.streakFreezeCount += 1;
        data.lastStreakFreezeEarned = today;
      } else if (data.currentStreak === 21) {
        message = "👑 3 weeks! You're a learning champion!";
        data.streakFreezeCount += 1;
        data.lastStreakFreezeEarned = today;
      } else if (data.currentStreak === 30) {
        message = "🌟 30 days! A whole month of learning!";
        data.streakFreezeCount += 1;
        data.lastStreakFreezeEarned = today;
      } else if (data.currentStreak % 7 === 0 && data.currentStreak > 30) {
        message = `🎊 ${data.currentStreak} days! Incredible dedication!`;
        data.streakFreezeCount += 1;
        data.lastStreakFreezeEarned = today;
      } else {
        message = `🔥 ${data.currentStreak} days in a row! Keep going!`;
      }
    }
    // Streak broken - check for streak freeze
    else if (isStreakBroken(data.lastPracticeDate, today)) {
      if (data.hasStreakFreeze && data.streakFreezeCount > 0) {
        // Use streak freeze to save the streak
        data.streakFreezeCount -= 1;
        data.hasStreakFreeze = data.streakFreezeCount > 0;
        data.currentStreak += 1;
        data.totalDaysPracticed += 1;
        message = "❄️ Streak Freeze used! Your streak is saved!";
        isNewStreak = true;
      } else {
        // Streak is broken, reset
        const oldStreak = data.currentStreak;
        data.currentStreak = 1;
        data.totalDaysPracticed += 1;
        if (oldStreak > 0) {
          message = `Oh no! Your ${oldStreak}-day streak ended. Let's start fresh! 💪`;
        } else {
          message = "🔥 You started your streak! Keep it going!";
        }
        isNewStreak = true;
      }
    }

    // Update longest streak
    if (data.currentStreak > data.longestStreak) {
      data.longestStreak = data.currentStreak;
    }

    data.lastPracticeDate = today;
    this.saveStreakData(data);

    return { data, message, isNewStreak };
  },

  // Check if practiced today
  hasPracticedToday(): boolean {
    const data = this.getStreakData();
    return data.lastPracticeDate === getTodayDate();
  },

  // Get current streak with check for breaks
  getCurrentStreakWithCheck(): number {
    const data = this.getStreakData();
    const today = getTodayDate();

    if (!data.lastPracticeDate) return 0;

    // Already practiced today
    if (isSameDay(data.lastPracticeDate, today)) {
      return data.currentStreak;
    }

    // Practiced yesterday - streak is still valid
    if (isConsecutiveDay(data.lastPracticeDate, today)) {
      return data.currentStreak;
    }

    // More than 1 day gap - streak would be broken
    return 0;
  },

  // Reset streak data (for testing)
  resetStreak(): void {
    localStorage.removeItem(STREAK_KEY);
  },

  // Sync streak data to backend
  async syncToBackend(token: string): Promise<boolean> {
    try {
      const data = this.getStreakData();
      const response = await fetch('/api/streak/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });
      return response.ok;
    } catch (error) {
      console.error('Error syncing streak to backend:', error);
      return false;
    }
  },

  // Get motivational message based on streak
  getMotivationalMessage(streak: number): string {
    if (streak === 0) return "Start your streak today!";
    if (streak === 1) return "Great start! Come back tomorrow!";
    if (streak < 3) return "You're building momentum!";
    if (streak < 5) return "Keep the fire burning!";
    if (streak < 7) return "Almost at your first week!";
    if (streak === 7) return "One week champion!";
    if (streak < 14) return "You're on fire!";
    if (streak < 21) return "Incredible dedication!";
    if (streak < 30) return "You're unstoppable!";
    return "Learning legend!";
  }
};
