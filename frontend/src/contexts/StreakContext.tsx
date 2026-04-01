/**
 * Streak Context Provider
 * Manages daily streak state across the application
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { streakUtils, StreakData } from '@/lib/streak-utils';

interface StreakContextType {
  streakData: StreakData;
  isAnimating: boolean;
  showMessage: boolean;
  currentMessage: string | null;
  recordPractice: () => void;
  dismissMessage: () => void;
  triggerAnimation: () => void;
}

const StreakContext = createContext<StreakContextType | undefined>(undefined);

export function StreakProvider({ children }: { children: ReactNode }) {
  const [streakData, setStreakData] = useState<StreakData>(() => streakUtils.getStreakData());
  const [isAnimating, setIsAnimating] = useState(false);
  const [showMessage, setShowMessage] = useState(false);
  const [currentMessage, setCurrentMessage] = useState<string | null>(null);

  // Load initial streak data
  useEffect(() => {
    const data = streakUtils.getStreakData();
    setStreakData(data);
  }, []);

  // Record a practice session
  const recordPractice = useCallback(() => {
    const { data, message, isNewStreak } = streakUtils.recordPractice();
    setStreakData(data);

    if (isNewStreak) {
      setIsAnimating(true);
      setTimeout(() => setIsAnimating(false), 1500);
    }

    if (message) {
      setCurrentMessage(message);
      setShowMessage(true);
      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        setShowMessage(false);
      }, 5000);
    }
  }, []);

  // Dismiss the message manually
  const dismissMessage = useCallback(() => {
    setShowMessage(false);
    setCurrentMessage(null);
  }, []);

  // Trigger animation manually (for testing or special events)
  const triggerAnimation = useCallback(() => {
    setIsAnimating(true);
    setTimeout(() => setIsAnimating(false), 1500);
  }, []);

  // Auto-record practice when the app loads (simulating user activity)
  // In a real app, this would be triggered by completing a lesson/question
  useEffect(() => {
    // Check if we haven't practiced today yet
    if (!streakUtils.hasPracticedToday()) {
      // We'll trigger this when the user interacts with learning content
      // For demo purposes, we can trigger it after a short delay
    }
  }, []);

  const value = {
    streakData,
    isAnimating,
    showMessage,
    currentMessage,
    recordPractice,
    dismissMessage,
    triggerAnimation,
  };

  return (
    <StreakContext.Provider value={value}>
      {children}
    </StreakContext.Provider>
  );
}

export function useStreak() {
  const context = useContext(StreakContext);
  if (context === undefined) {
    throw new Error('useStreak must be used within a StreakProvider');
  }
  return context;
}
