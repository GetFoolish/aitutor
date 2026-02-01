/**
 * AnswerFeedback - Animated feedback for correct/incorrect answers
 * 
 * Uses confetti for correct answers and encouraging animations for incorrect.
 * Part of making learning feel rewarding and fun.
 */
import React, { useEffect, useState } from 'react';
import Confetti from 'react-confetti';
import './AnswerFeedback.scss';

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

const AnswerFeedback: React.FC<AnswerFeedbackProps> = ({ isCorrect, show, onComplete }) => {
  const [message, setMessage] = useState('');
  const [showConfetti, setShowConfetti] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (show && isCorrect !== null) {
      const messages = isCorrect ? ENCOURAGEMENTS_CORRECT : ENCOURAGEMENTS_INCORRECT;
      setMessage(messages[Math.floor(Math.random() * messages.length)]);
      
      if (isCorrect) {
        setShowConfetti(true);
        setDimensions({ width: window.innerWidth, height: window.innerHeight });
        
        // Stop confetti after 3 seconds
        setTimeout(() => {
          setShowConfetti(false);
        }, 3000);
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
      {showConfetti && (
        <Confetti
          width={dimensions.width}
          height={dimensions.height}
          recycle={false}
          numberOfPieces={300}
          gravity={0.2}
          colors={['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#FF69B4', '#00FF7F']}
        />
      )}
      
      {/* Inline styles for guaranteed visibility */}
      <div style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 10000,
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
