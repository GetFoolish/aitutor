import React, { useEffect, useState } from 'react';

interface MasteryCelebrationProps {
  show: boolean;
  topic: string;
  onClose: () => void;
}

export const MasteryCelebration: React.FC<MasteryCelebrationProps> = ({ show, topic, onClose }) => {
  const [confetti, setConfetti] = useState<Array<{id: number; left: number; delay: number; duration: number}>>([]);

  useEffect(() => {
    if (show) {
      // Generate confetti pieces
      const pieces = Array.from({ length: 50 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        delay: Math.random() * 0.5,
        duration: 2 + Math.random() * 2
      }));
      setConfetti(pieces);

      // Play celebration sound (optional)
      try {
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLUiDwHHGS57+OcTgwOUKjj8LdjHAY8j9ryy3kgBSh+yPLYiDYIGWa57+eXSAsOTqPm8LdkHAU2jdnyxnkgBSh+yfLUiDYGG2S77+aaSgwOTqPm8LZkGwU2jdj')
        audio.volume = 0.3;
        audio.play().catch(() => {}); // Ignore if autoplay blocked
      } catch (e) {
        // Sound optional
      }
    }
  }, [show]);

  if (!show) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        animation: 'fadeIn 0.3s ease-out'
      }}
      onClick={onClose}
    >
      {/* Confetti */}
      {confetti.map((piece) => (
        <div
          key={piece.id}
          style={{
            position: 'absolute',
            top: '-10px',
            left: `${piece.left}%`,
            width: '10px',
            height: '10px',
            backgroundColor: ['#FFD93D', '#6C63FF', '#4ADE80', '#FF6B6B', '#A78BFA'][piece.id % 5],
            animation: `confettiFall ${piece.duration}s linear ${piece.delay}s`,
            opacity: 0
          }}
        />
      ))}

      {/* Celebration Modal */}
      <div
        style={{
          backgroundColor: 'white',
          border: '4px solid black',
          borderRadius: '16px',
          padding: '48px',
          maxWidth: '500px',
          boxShadow: '12px 12px 0px 0px rgba(0,0,0,1)',
          textAlign: 'center',
          animation: 'scaleIn 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Trophy */}
        <div
          style={{
            fontSize: '80px',
            marginBottom: '24px',
            animation: 'bounce 0.6s ease-in-out 0.3s'
          }}
        >
          🏆
        </div>

        {/* Title */}
        <h2
          style={{
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: '36px',
            fontWeight: 900,
            marginBottom: '16px',
            color: '#000'
          }}
        >
          you've mastered {topic}!
        </h2>

        {/* Message */}
        <p
          style={{
            fontSize: '18px',
            color: '#666',
            marginBottom: '32px',
            lineHeight: 1.6
          }}
        >
          amazing work! 🎉 you answered 8 out of 10 questions correctly.
          keep up the great progress! ✨
        </p>

        {/* Achievement Badge */}
        <div
          style={{
            display: 'inline-block',
            backgroundColor: '#4ADE80',
            border: '3px solid black',
            borderRadius: '12px',
            padding: '12px 24px',
            fontWeight: 700,
            marginBottom: '32px',
            boxShadow: '4px 4px 0px 0px rgba(0,0,0,1)'
          }}
        >
          🌟 topic mastered badge earned!
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            width: '100%',
            backgroundColor: '#6C63FF',
            color: 'white',
            border: '4px solid black',
            borderRadius: '12px',
            padding: '16px',
            fontSize: '18px',
            fontWeight: 700,
            cursor: 'pointer',
            boxShadow: '4px 4px 0px 0px rgba(0,0,0,1)',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translate(2px, 2px)';
            e.currentTarget.style.boxShadow = '2px 2px 0px 0px rgba(0,0,0,1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translate(0, 0)';
            e.currentTarget.style.boxShadow = '4px 4px 0px 0px rgba(0,0,0,1)';
          }}
        >
          continue to next topic! 🚀
        </button>
      </div>

      {/* CSS Animations */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes scaleIn {
          from {
            transform: scale(0.5);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }

        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-20px); }
        }

        @keyframes confettiFall {
          0% {
            transform: translateY(0) rotate(0deg);
            opacity: 1;
          }
          100% {
            transform: translateY(100vh) rotate(360deg);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
};

export default MasteryCelebration;
