/**
 * AnswerFeedback - Animated feedback for correct/incorrect answers
 * 
 * Uses canvas-confetti for correct answers and encouraging animations for incorrect.
 * Part of making learning feel rewarding and fun.
 */
import React, { useEffect, useState } from 'react';
import confetti from 'canvas-confetti';

interface AnswerFeedbackProps {
  isCorrect: boolean | null;
  show: boolean;
  onComplete?: () => void;
}

const ENCOURAGEMENTS_CORRECT = [
  "nailed it! 🎯",
  "you got it! ⭐",
  "brilliant! 🌟",
  "spot on! ✨",
  "yes! perfect! 🎉",
  "amazing work! 💪",
  "you're on fire! 🔥",
];

const ENCOURAGEMENTS_INCORRECT = [
  "not quite, but you're learning! 💡",
  "good try! let's see the next one 🌱",
  "almost there! keep going 💪",
  "mistakes help us grow! 🌟",
  "no worries, you've got this! ✨",
];

// Fire confetti bursts
const fireConfetti = () => {
  const duration = 2000;
  const end = Date.now() + duration;

  const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#FF69B4', '#00FF7F'];

  // Initial burst
  confetti({
    particleCount: 100,
    spread: 70,
    origin: { y: 0.6 },
    colors,
  });

  // Continuous smaller bursts from sides
  const interval = setInterval(() => {
    if (Date.now() > end) {
      clearInterval(interval);
      return;
    }

    confetti({
      particleCount: 50,
      angle: 60,
      spread: 55,
      origin: { x: 0 },
      colors,
    });
    confetti({
      particleCount: 50,
      angle: 120,
      spread: 55,
      origin: { x: 1 },
      colors,
    });
  }, 250);
};

const AnswerFeedback: React.FC<AnswerFeedbackProps> = ({ isCorrect, show, onComplete }) => {
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (show && isCorrect !== null) {
      const messages = isCorrect ? ENCOURAGEMENTS_CORRECT : ENCOURAGEMENTS_INCORRECT;
      setMessage(messages[Math.floor(Math.random() * messages.length)]);
      
      // Fire confetti for correct answers
      if (isCorrect) {
        fireConfetti();
      }

      // Callback after feedback shown
      if (onComplete) {
        setTimeout(onComplete, isCorrect ? 2000 : 1500);
      }
    }
  }, [show, isCorrect, onComplete]);

  if (!show || isCorrect === null) return null;

  return (
    <>
      {/* Feedback popup */}
      <div style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 100000,
        padding: '2rem 3rem',
        borderRadius: '20px',
        background: isCorrect 
          ? 'linear-gradient(135deg, #22C55E, #86EFAC)' 
          : 'linear-gradient(135deg, #F97316, #FDBA74)',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.4)',
        display: 'flex',
        flexDirection: 'column' as const,
        alignItems: 'center',
        gap: '1rem',
        animation: 'popup 0.3s ease-out',
        border: '5px solid #000',
      }}>
        <div style={{
          fontSize: '5rem',
          fontWeight: 'bold',
          background: 'rgba(255, 255, 255, 0.3)',
          borderRadius: '50%',
          width: '100px',
          height: '100px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          animation: isCorrect ? 'bounce 0.6s ease-in-out' : 'shake 0.5s ease-in-out',
        }}>
          {isCorrect ? '✓' : '✗'}
        </div>
        <div style={{
          fontSize: '1.8rem',
          fontWeight: 700,
          textAlign: 'center',
          color: '#000',
          maxWidth: '300px',
          fontFamily: 'Space Mono, monospace',
        }}>
          {message}
        </div>
      </div>

      <style>{`
        @keyframes popup {
          0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
          50% { transform: translate(-50%, -50%) scale(1.1); }
          100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
        @keyframes bounce {
          0%, 100% { transform: scale(1); }
          25% { transform: scale(1.2); }
          50% { transform: scale(0.95); }
          75% { transform: scale(1.1); }
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-10px); }
          40% { transform: translateX(10px); }
          60% { transform: translateX(-10px); }
          80% { transform: translateX(10px); }
        }
      `}</style>
    </>
  );
};

export default AnswerFeedback;
