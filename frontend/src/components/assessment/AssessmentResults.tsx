import React, { useState, useEffect } from 'react';
import { useOptionalTutorContext } from '../../features/tutor/TutorContext';
import { apiUtils } from '../../lib/api-utils';
import PersonalizationCards from './PersonalizationCards';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface Props {
  score: number;
  total: number;
  subject: string;
  onContinue: () => void;
}

interface GradingData {
  subjects: {
    [subject: string]: {
      grade_levels: {
        [grade: string]: {
          units: Array<{
            id: string;
            name: string;
            grade_level?: string;
          }>;
        };
      };
    };
  };
}

interface SkillCard {
  id: string;
  name: string;
  grade_level: string;
}

const AssessmentResults: React.FC<Props> = ({
  score,
  total,
  subject,
  onContinue
}) => {
  const [showPersonalizing, setShowPersonalizing] = useState(false);
  const [gradingData, setGradingData] = useState<GradingData | null>(null);
  const [skillCards, setSkillCards] = useState<SkillCard[]>([]);
  const tutor = useOptionalTutorContext();
  const client = tutor?.client;
  const connected = tutor?.connected;
  const disconnect = tutor?.disconnect;

  const percentage = total > 0 ? Math.round((score / total) * 100) : 0;
  const isPassed = percentage >= 70;

  // Prefetch grading data when results are shown (no loading state needed)
  useEffect(() => {
    const fetchGradingData = async () => {
      try {
        const response = await apiUtils.get(`${DASH_API_URL}/api/grading-panel`);
        if (response.ok) {
          const data: GradingData = await response.json();
          setGradingData(data);
          
          // Extract units for the CURRENT subject only
          const allUnits: SkillCard[] = [];
          if (data.subjects) {
            const subjectKey = Object.keys(data.subjects).find(
              k => k.toLowerCase() === subject.toLowerCase()
            );
            const currentSubjectData = subjectKey ? data.subjects[subjectKey] : null;
            if (currentSubjectData) {
              Object.entries(currentSubjectData.grade_levels || {}).forEach(([gradeLevel, gradeData]) => {
                (gradeData.units || []).forEach((unit) => {
                  allUnits.push({
                    id: unit.id,
                    name: unit.name,
                    grade_level: gradeLevel,
                  });
                });
              });
            }
          }
          
          // Randomly select 16-18 units (or all if fewer) for fuller grid
          const shuffled = allUnits.sort(() => Math.random() - 0.5);
          const selected = shuffled.slice(0, Math.min(18, shuffled.length));
          setSkillCards(selected);
        }
      } catch (error) {
        console.warn('Failed to fetch grading data:', error);
        // Skip personalization cards when API fails — don't show fake data
        setSkillCards([]);
      }
    };

    fetchGradingData();
  }, [subject]);

  // Send transition message and disconnect tutor when results are shown
  useEffect(() => {
    if (connected && client && disconnect) {
      try {
        // Send explicit transition message to AI
        client.send({ 
          text: "SYSTEM: Assessment complete. Transitioning to regular tutoring mode." 
        });
        
        // Wait a moment for the message to be sent, then disconnect
        const disconnectTimer = setTimeout(() => {
          disconnect();
        }, 500);
        
        return () => clearTimeout(disconnectTimer);
      } catch (error) {
        console.warn('Failed to send transition message to tutor:', error);
        // Still disconnect even if message fails
        disconnect?.();
      }
    }
  }, [connected, client, disconnect]);

  // Handle personalization cards animation complete
  const handlePersonalizationComplete = () => {
    onContinue();
  };

  const handleContinueClick = () => {
    if (skillCards.length > 0) {
      setShowPersonalizing(true);
      return;
    }
    onContinue();
  };

  // Show personalizing animation with cards
  if (showPersonalizing && skillCards.length > 0) {
    return (
      <PersonalizationCards
        skills={skillCards}
        onComplete={handlePersonalizationComplete}
      />
    );
  }

  return (
    <div style={{
      marginTop: '56px',
      padding: '14px 14px 20px',
      maxWidth: '860px',
      width: '100%',
      marginLeft: 'auto',
      marginRight: 'auto',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'stretch',
      gap: '12px',
      backgroundColor: 'transparent',
    }}>
      <div style={{
        border: '5px solid var(--neo-black)',
        backgroundColor: 'var(--neo-yellow)',
        padding: '18px 20px',
        boxShadow: '3px 3px 0 var(--neo-black)',
        textAlign: 'center',
      }}>
        <h1 style={{
          fontSize: 'clamp(20px, 2.6vw, 30px)',
          fontWeight: 900,
          margin: '0 0 10px 0',
          color: 'var(--neo-black)',
          textTransform: 'uppercase',
          letterSpacing: '0.06em'
        }}>
          Assessment Complete!
        </h1>

        <div style={{
          fontSize: 'clamp(44px, 8vw, 72px)',
          fontWeight: 900,
          lineHeight: 1,
          margin: '8px 0 4px 0',
          color: 'var(--neo-black)',
          fontFamily: 'Space Mono, monospace'
        }}>
          {score}/{total}
        </div>

        <div style={{
          fontSize: 'clamp(14px, 2vw, 20px)',
          marginBottom: '0',
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
        padding: '16px 18px',
        boxShadow: '2px 2px 0 var(--neo-black)',
        textAlign: 'center',
      }}>
        {isPassed ? (
          <p style={{
            fontSize: 'clamp(16px, 2vw, 20px)',
            color: '#2E7D32',
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            margin: 0
          }}>
            Great Job! You're ready to start learning.
          </p>
        ) : (
          <p style={{
            fontSize: 'clamp(16px, 2vw, 20px)',
            color: '#C62828',
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            margin: 0
          }}>
            Keep Practicing! You'll improve over time.
          </p>
        )}
      </div>

      <button
        onClick={handleContinueClick}
        style={{
          width: '100%',
          maxWidth: '420px',
          margin: '0 auto',
          padding: '14px 24px',
          border: '4px solid var(--neo-black)',
          background: '#4FC3F7',
          color: 'var(--neo-black)',
          fontWeight: 900,
          fontSize: '16px',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          boxShadow: '3px 3px 0 var(--neo-black)',
          cursor: 'pointer',
          alignSelf: 'center'
        }}
      >
        Continue to Learning
      </button>

    </div>
  );
};

export default AssessmentResults;
