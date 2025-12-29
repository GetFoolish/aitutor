/**
 * Streak Message Component
 * Displays motivational messages when streak updates
 */

import { useStreak } from '@/contexts/StreakContext';
import { X } from 'lucide-react';
import './StreakMessage.scss';

export default function StreakMessage() {
  const { showMessage, currentMessage, dismissMessage } = useStreak();

  if (!showMessage || !currentMessage) {
    return null;
  }

  return (
    <div className="streak-message">
      <div className="message-content">
        <span className="message-text">{currentMessage}</span>
        <button
          className="dismiss-button"
          onClick={dismissMessage}
          aria-label="Dismiss message"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}
