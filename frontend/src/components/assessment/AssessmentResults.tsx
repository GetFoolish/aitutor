import React, { useState, useEffect } from 'react';

interface Props {
  score: number;
  total: number;
  subject: string;
  onContinue: () => void;
}

const AssessmentResults: React.FC<Props> = ({
  score,
  total,
  subject,
  onContinue
}) => {
  const [showPersonalizing, setShowPersonalizing] = useState(false);

  const percentage = total > 0 ? Math.round((score / total) * 100) : 0;
  const passColor = percentage >= 70 ? '#4CAF50' : '#FF9800';

  const isPassed = percentage >= 70;

  // Auto-redirect after showing personalizing animation
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowPersonalizing(true);
    }, 2000); // Show results for 2 seconds, then show personalizing animation

    return () => clearTimeout(timer);
  }, []);

  // Auto-redirect after personalizing animation
  useEffect(() => {
    if (showPersonalizing) {
      const redirectTimer = setTimeout(() => {
        onContinue();
      }, 2000); // Show personalizing animation for 2 seconds

      return () => clearTimeout(redirectTimer);
    }
  }, [showPersonalizing, onContinue]);

  // Show personalizing animation
  if (showPersonalizing) {
    return (
      <div style={{
        padding: '40px 20px',
        textAlign: 'center',
        maxWidth: '600px',
        margin: '0 auto',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        backgroundColor: 'var(--neo-bg)'
      }}>
        <div style={{
          border: '5px solid var(--neo-black)',
          backgroundColor: 'var(--neo-yellow)',
          padding: '40px 32px',
          boxShadow: '3px 3px 0 var(--neo-black)',
          animation: 'pulse 1.5s ease-in-out infinite'
        }}>
          <h2 style={{
            fontSize: '24px',
            fontWeight: 700,
            marginBottom: '16px',
            color: 'var(--neo-black)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            margin: 0
          }}>
            Personalizing Your Learning Plan...
          </h2>
          <p style={{
            fontSize: '14px',
            color: 'var(--neo-black)',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginTop: '16px',
            margin: 0
          }}>
            Analyzing your assessment results
          </p>
        </div>
        <style>{`
          @keyframes pulse {
            0%, 100% {
              opacity: 1;
            }
            50% {
              opacity: 0.7;
            }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div style={{
      padding: '40px 20px',
      textAlign: 'center',
      maxWidth: '600px',
      margin: '0 auto',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      backgroundColor: 'var(--neo-bg)'
    }}>
      <div style={{
        border: '5px solid var(--neo-black)',
        backgroundColor: 'var(--neo-yellow)',
        padding: '32px',
        marginBottom: '32px',
        boxShadow: '3px 3px 0 var(--neo-black)'
      }}>
        <h1 style={{
          fontSize: '28px',
          fontWeight: 700,
          marginBottom: '24px',
          color: 'var(--neo-black)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em'
        }}>
          Assessment Complete!
        </h1>

        <div style={{
          fontSize: '64px',
          fontWeight: 900,
          margin: '24px 0',
          color: 'var(--neo-black)',
          fontFamily: 'Space Mono, monospace'
        }}>
          {score}/{total}
        </div>

        <div style={{
          fontSize: '20px',
          marginBottom: '24px',
          color: 'var(--neo-black)',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em'
        }}>
          {percentage}% on {subject}
        </div>
      </div>

      <div style={{
        border: '5px solid var(--neo-black)',
        backgroundColor: isPassed ? '#E8F5E9' : '#FFEBEE',
        padding: '24px',
        marginBottom: '32px',
        boxShadow: '2px 2px 0 var(--neo-black)'
      }}>
        {isPassed ? (
          <p style={{
            fontSize: '18px',
            color: '#2E7D32',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            margin: 0
          }}>
            Great Job! You're ready to start learning.
          </p>
        ) : (
          <p style={{
            fontSize: '18px',
            color: '#C62828',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            margin: 0
          }}>
            Keep Practicing! You'll improve over time.
          </p>
        )}
      </div>
    </div>
  );
};

export default AssessmentResults;
