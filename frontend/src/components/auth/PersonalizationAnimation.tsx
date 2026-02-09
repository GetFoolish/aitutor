/**
 * Personalization Animation Component
 * 
 * Neo-brutalist animated message display matching AssessmentResults style.
 * Used for "Personalizing...", "Preparing assessment...", etc.
 */
import React from 'react';

interface PersonalizationAnimationProps {
  message: string;
  subMessage: string;
}

const PersonalizationAnimation: React.FC<PersonalizationAnimationProps> = ({
  message,
  subMessage
}) => {
  // Split message by newlines if present
  const messageLines = message.split('\n').filter(line => line.trim());
  
  return (
    <div style={{
      width: '100%',
      maxWidth: '580px',
      position: 'relative',
      zIndex: 2
    }}>
      <div style={{
        border: '5px solid #000000',
        backgroundColor: '#FFD93D',
        padding: '52px 44px',
        boxShadow: '4px 4px 0px 0px #000000',
        width: '100%',
        animation: 'pulse 1.5s ease-in-out infinite'
      }}>
        <div style={{
          fontSize: '26px',
          fontWeight: 900,
          marginBottom: messageLines.length > 1 ? '24px' : '20px',
          color: '#000000',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          lineHeight: '1.3',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          textAlign: 'center'
        }}>
          {messageLines.map((line, index) => (
            <React.Fragment key={index}>
              {line}
              {index < messageLines.length - 1 && <br />}
            </React.Fragment>
          ))}
        </div>
        <div style={{
          fontSize: '15px',
          color: '#000000',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          lineHeight: '1.5',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          textAlign: 'center'
        }}>
          {subMessage}
        </div>
      </div>
      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.8;
          }
        }
      `}</style>
    </div>
  );
};

export default PersonalizationAnimation;
