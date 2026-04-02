/**
 * Streak Counter Component
 * Displays fire emoji with streak count and animation
 */

import { useStreak } from '@/contexts/StreakContext';
import { useEffect, useState } from 'react';
import './StreakCounter.scss';

interface StreakCounterProps {
  compact?: boolean;
  onClick?: () => void;
}

export default function StreakCounter({ compact = false, onClick }: StreakCounterProps) {
  const { streakData, isAnimating, recordPractice } = useStreak();
  const [showTooltip, setShowTooltip] = useState(false);

  const handleClick = () => {
    if (onClick) {
      onClick();
    }
    // For demo: record practice on click
    recordPractice();
  };

  // Determine fire intensity based on streak
  const getFireIntensity = () => {
    if (streakData.currentStreak === 0) return 'dormant';
    if (streakData.currentStreak < 3) return 'low';
    if (streakData.currentStreak < 7) return 'medium';
    if (streakData.currentStreak < 14) return 'high';
    return 'blazing';
  };

  const intensity = getFireIntensity();

  return (
    <div
      className="streak-counter-wrapper"
      data-streak={streakData.currentStreak}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <button
        onClick={handleClick}
        className={`streak-counter ${intensity} ${isAnimating ? 'animating' : ''} ${compact ? 'compact' : ''}`}
        aria-label={`Current streak: ${streakData.currentStreak} days`}
        title="Learning streak"
      >
        <span className="fire-container">
          <span className="fire-emoji" role="img" aria-hidden="true">
            🔥
          </span>
          {isAnimating && (
            <>
              <span className="fire-particle fire-particle-1">✨</span>
              <span className="fire-particle fire-particle-2">⭐</span>
              <span className="fire-particle fire-particle-3">✨</span>
            </>
          )}
        </span>
        <span className="streak-count">{streakData.currentStreak}</span>
        {streakData.hasStreakFreeze && streakData.streakFreezeCount > 0 && (
          <span className="freeze-indicator" title="Streak Freeze available">
            ❄️
          </span>
        )}
      </button>

      {showTooltip && !compact && (
        <div className="streak-tooltip">
          <div className="tooltip-header">
            <span className="tooltip-fire">🔥</span>
            <span className="tooltip-title">Daily Streak</span>
          </div>
          <div className="tooltip-stats">
            <div className="stat">
              <span className="stat-value">{streakData.currentStreak}</span>
              <span className="stat-label">Current</span>
            </div>
            <div className="stat">
              <span className="stat-value">{streakData.longestStreak}</span>
              <span className="stat-label">Best</span>
            </div>
            <div className="stat">
              <span className="stat-value">{streakData.totalDaysPracticed}</span>
              <span className="stat-label">Total Days</span>
            </div>
          </div>
          {streakData.streakFreezeCount > 0 && (
            <div className="freeze-info">
              ❄️ {streakData.streakFreezeCount} Streak Freeze{streakData.streakFreezeCount > 1 ? 's' : ''} available
            </div>
          )}
          <div className="tooltip-footer">
            Practice daily to keep your streak! 🎯
          </div>
        </div>
      )}
    </div>
  );
}
