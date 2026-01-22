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
  const [isFading, setIsFading] = useState(false);
  const [gradingData, setGradingData] = useState<GradingData | null>(null);
  const [skillCards, setSkillCards] = useState<SkillCard[]>([]);
  const tutor = useOptionalTutorContext();
  const client = tutor?.client;
  const connected = tutor?.connected;
  const disconnect = tutor?.disconnect;

  const percentage = total > 0 ? Math.round((score / total) * 100) : 0;
  const passColor = percentage >= 70 ? '#4CAF50' : '#FF9800';

  const isPassed = percentage >= 70;

  // Prefetch grading data when results are shown (no loading state needed)
  useEffect(() => {
    const fetchGradingData = async () => {
      try {
        const response = await apiUtils.get(`${DASH_API_URL}/api/grading-panel`);
        if (response.ok) {
          const data: GradingData = await response.json();
          setGradingData(data);
          
          // Extract all units from grading data and create skill cards
          const allUnits: SkillCard[] = [];
          if (data.subjects) {
            Object.values(data.subjects).forEach((subjectData) => {
              Object.entries(subjectData.grade_levels || {}).forEach(([gradeLevel, gradeData]) => {
                (gradeData.units || []).forEach((unit) => {
                  allUnits.push({
                    id: unit.id,
                    name: unit.name,
                    grade_level: gradeLevel,
                  });
                });
              });
            });
          }
          
          // Randomly select 16-18 units (or all if fewer) for fuller grid
          const shuffled = allUnits.sort(() => Math.random() - 0.5);
          const selected = shuffled.slice(0, Math.min(18, shuffled.length));
          setSkillCards(selected);
        }
      } catch (error) {
        console.warn('Failed to fetch grading data:', error);
        // Fallback: create placeholder cards if API fails
        setSkillCards([
          { id: '1', name: 'Basic Math', grade_level: 'GRADE_1' },
          { id: '2', name: 'Addition', grade_level: 'GRADE_2' },
          { id: '3', name: 'Subtraction', grade_level: 'GRADE_2' },
          { id: '4', name: 'Multiplication', grade_level: 'GRADE_3' },
          { id: '5', name: 'Division', grade_level: 'GRADE_3' },
          { id: '6', name: 'Fractions', grade_level: 'GRADE_4' },
          { id: '7', name: 'Decimals', grade_level: 'GRADE_5' },
          { id: '8', name: 'Algebra', grade_level: 'GRADE_7' },
        ]);
      }
    };

    fetchGradingData();
  }, []);

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

  // Auto-redirect after showing personalizing animation with fade
  // Wait for skills to load before starting transition
  useEffect(() => {
    if (skillCards.length === 0) return; // Don't start timers until skills are loaded

    const fadeTimer = setTimeout(() => {
      setIsFading(true); // Start fade out at 1.7s
    }, 1700);

    const showTimer = setTimeout(() => {
      setShowPersonalizing(true); // Show cards at 2s
    }, 2000);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(showTimer);
    };
  }, [skillCards.length]);

  // Handle personalization cards animation complete
  const handlePersonalizationComplete = () => {
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
      padding: '40px 20px',
      textAlign: 'center',
      maxWidth: '600px',
      margin: '0 auto',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      backgroundColor: 'var(--neo-bg)',
      opacity: isFading ? 0 : 1,
      transition: 'opacity 300ms ease-out'
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
