import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useAuth } from './AuthContext';

interface GameStats {
  xp: number;
  level: number;
  streak_count: number;
  last_practice_date: string | null;
  daily_goal_xp: number;
}

interface GameContextType {
  // User's persistent stats (from database)
  xp: number;
  level: number;
  streakCount: number;
  dailyGoalXp: number;

  // Session stats (ephemeral)
  sessionXp: number;
  questionsAnswered: number;
  correctAnswers: number;

  // Progress calculations
  xpToNextLevel: number;
  xpInCurrentLevel: number;
  dailyProgress: number; // 0-1 for goal progress

  // Actions
  addSessionXp: (amount: number) => void;
  recordAnswer: (isCorrect: boolean) => void;
  updateFromBackend: (stats: Partial<GameStats>) => void;
  refreshStats: () => Promise<void>;

  // Level up state
  showLevelUp: boolean;
  dismissLevelUp: () => void;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

export function GameProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  // Persistent stats from user object
  const [xp, setXp] = useState(0);
  const [level, setLevel] = useState(1);
  const [streakCount, setStreakCount] = useState(0);
  const [dailyGoalXp, setDailyGoalXp] = useState(50);

  // Session stats
  const [sessionXp, setSessionXp] = useState(0);
  const [questionsAnswered, setQuestionsAnswered] = useState(0);
  const [correctAnswers, setCorrectAnswers] = useState(0);

  // Level up UI
  const [showLevelUp, setShowLevelUp] = useState(false);
  const [previousLevel, setPreviousLevel] = useState(1);

  // Initialize from user data
  useEffect(() => {
    if (user) {
      setXp(user.xp || 0);
      setLevel(user.level || 1);
      setStreakCount(user.streak_count || 0);
      setDailyGoalXp(user.daily_goal_xp || 50);
      setPreviousLevel(user.level || 1);
    }
  }, [user]);

  // Calculate XP progress for current level
  // Duolingo-style: Level N requires N * 100 XP from previous level
  const calculateLevelProgress = (currentXp: number, currentLevel: number) => {
    // Calculate XP at start of current level
    let xpAtLevelStart = 0;
    for (let lvl = 2; lvl <= currentLevel; lvl++) {
      xpAtLevelStart += lvl * 100;
    }

    // XP needed for next level
    const xpForNext = (currentLevel + 1) * 100;

    // XP in current level
    const xpInLevel = currentXp - xpAtLevelStart;

    return {
      xpInCurrentLevel: Math.max(0, xpInLevel),
      xpToNextLevel: xpForNext,
    };
  };

  const { xpInCurrentLevel, xpToNextLevel } = calculateLevelProgress(xp, level);

  // Calculate daily goal progress
  const dailyProgress = Math.min(sessionXp / dailyGoalXp, 1);

  // Add XP from session
  const addSessionXp = (amount: number) => {
    setSessionXp((prev) => prev + amount);
  };

  // Record a question answer
  const recordAnswer = (isCorrect: boolean) => {
    setQuestionsAnswered((prev) => prev + 1);
    if (isCorrect) {
      setCorrectAnswers((prev) => prev + 1);
    }
  };

  // Update from backend response (after submit-answer)
  const updateFromBackend = (stats: Partial<GameStats>) => {
    if (stats.xp !== undefined) {
      setXp(stats.xp);
    }
    if (stats.level !== undefined) {
      // Check for level up
      if (stats.level > previousLevel) {
        setShowLevelUp(true);
        setPreviousLevel(stats.level);
      }
      setLevel(stats.level);
    }
    if (stats.streak_count !== undefined) {
      setStreakCount(stats.streak_count);
    }
    if (stats.daily_goal_xp !== undefined) {
      setDailyGoalXp(stats.daily_goal_xp);
    }
  };

  // Refresh stats from backend
  const refreshStats = async () => {
    if (!user) return;

    try {
      // Fetch fresh user data
      const response = await fetch(`http://localhost:8001/auth/me`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        updateFromBackend(userData);
      }
    } catch (error) {
      console.error('Error refreshing game stats:', error);
    }
  };

  const dismissLevelUp = () => {
    setShowLevelUp(false);
  };

  const value: GameContextType = {
    xp,
    level,
    streakCount,
    dailyGoalXp,
    sessionXp,
    questionsAnswered,
    correctAnswers,
    xpToNextLevel,
    xpInCurrentLevel,
    dailyProgress,
    addSessionXp,
    recordAnswer,
    updateFromBackend,
    refreshStats,
    showLevelUp,
    dismissLevelUp,
  };

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
}

export function useGame() {
  const context = useContext(GameContext);
  if (context === undefined) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
}
