import React, { useState, useEffect } from 'react';
import { useOptionalTutorContext } from '../../features/tutor/TutorContext';
import { apiUtils } from '../../lib/api-utils';
import PersonalizationCards from './PersonalizationCards';
import {
  Trophy,
  CheckCircle2,
  AlertCircle,
  ArrowRight
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

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

  useEffect(() => {
    const fetchGradingData = async () => {
      try {
        const response = await apiUtils.get(`${DASH_API_URL}/api/grading-panel`);
        if (response.ok) {
          const data: GradingData = await response.json();
          setGradingData(data);

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

          const shuffled = allUnits.sort(() => Math.random() - 0.5);
          const selected = shuffled.slice(0, Math.min(18, shuffled.length));
          setSkillCards(selected);
        }
      } catch (error) {
        console.warn('Failed to fetch grading data:', error);
        setSkillCards([]);
      }
    };

    fetchGradingData();
  }, [subject]);

  useEffect(() => {
    if (connected && client && disconnect) {
      try {
        client.send({
          text: "SYSTEM: Assessment complete. Transitioning to regular tutoring mode."
        });

        const disconnectTimer = setTimeout(() => {
          disconnect();
        }, 500);

        return () => clearTimeout(disconnectTimer);
      } catch (error) {
        console.warn('Failed to send transition message to tutor:', error);
        disconnect?.();
      }
    }
  }, [connected, client, disconnect]);

  const handlePersonalizationComplete = () => {
    onContinue();
  };

  const [isContinuing, setIsContinuing] = useState(false);

  const handleContinueClick = () => {
    if (isContinuing) return;
    setIsContinuing(true);
    if (skillCards.length > 0) {
      setShowPersonalizing(true);
      return;
    }
    onContinue();
  };

  if (showPersonalizing && skillCards.length > 0) {
    return (
      <PersonalizationCards
        skills={skillCards}
        onComplete={handlePersonalizationComplete}
      />
    );
  }

  return (
    <div className="mx-auto w-full max-w-[700px] px-4 py-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card className="relative flex flex-col border-[5px] border-black dark:border-white shadow-[12px_12px_0_0_rgba(0,0,0,1)] dark:shadow-[12px_12px_0_0_rgba(255,255,255,0.3)] bg-[#FFFDF5] dark:bg-[#000000] overflow-hidden">

        {/* Header with Icon and Result Banner */}
        <CardHeader className="p-0 border-b-[5px] border-black dark:border-white">
          <div
            className={`py-8 px-6 flex flex-col items-center justify-center gap-4 ${isPassed ? 'bg-[#ADFF2F]' : 'bg-[#FF6B6B]'
              }`}
          >
            <div className="p-4 bg-white border-[4px] border-black shadow-[4px_4px_0_0_#000]">
              {isPassed ? (
                <Trophy className="w-12 h-12 text-black" strokeWidth={3} />
              ) : (
                <AlertCircle className="w-12 h-12 text-black" strokeWidth={3} />
              )}
            </div>

            <div className="text-center space-y-1">
              <h1 className="text-3xl sm:text-4xl font-black uppercase tracking-tighter text-black">
                {isPassed ? 'Assessment Mastered!' : 'Keep Pushing!'}
              </h1>
              <p className="text-sm font-black uppercase tracking-widest text-black/70">
                Course: {subject}
              </p>
            </div>
          </div>
        </CardHeader>

        {/* Score and Stats */}
        <CardContent className="p-8 sm:p-12 flex flex-col items-center text-center gap-10">
          <div className="relative">
            <div className="absolute inset-0 bg-black dark:bg-white translate-x-3 translate-y-3"></div>
            <div className="relative border-4 border-black dark:border-white bg-[#C4B5FD] p-10 px-16">
              <div className="text-sm font-black uppercase tracking-[0.2em] text-black mb-1">Total Score</div>
              <div className="text-7xl sm:text-8xl font-black text-black leading-none font-mono">
                {score}<span className="text-4xl sm:text-5xl opacity-40">/{total}</span>
              </div>
            </div>
          </div>

          <div className="w-full space-y-6">
            <div className="flex items-center gap-4">
              <div className="h-[4px] flex-1 bg-black/10 dark:bg-white/10"></div>
              <div className="px-4 py-2 border-2 border-black dark:border-white bg-white dark:bg-black text-xs font-black uppercase tracking-widest">
                Accuracy: {percentage}%
              </div>
              <div className="h-[4px] flex-1 bg-black/10 dark:bg-white/10"></div>
            </div>

            <div className="p-6 bg-[#FFD93D] border-[4px] border-black shadow-[6px_6px_0_0_#000] text-black text-left flex items-start gap-4">
              <div className="mt-1">
                {isPassed ? (
                  <CheckCircle2 className="w-6 h-6 shrink-0" strokeWidth={3} />
                ) : (
                  <AlertCircle className="w-6 h-6 shrink-0" strokeWidth={3} />
                )}
              </div>
              <div className="space-y-1">
                <div className="font-black uppercase text-sm">Tutor's Evaluation</div>
                <p className="font-bold text-sm leading-relaxed">
                  {isPassed
                    ? "Fantastic work! You've shown strong foundational knowledge. We're personalizing your learning path to focus on advanced mastery."
                    : "Good effort! You've identified some key concepts, but we need more practice here. I'm building a custom plan to help you level up."
                  }
                </p>
              </div>
            </div>
          </div>
        </CardContent>

        {/* Footer with Action */}
        <CardFooter className="p-8 pt-0 flex flex-col gap-4">
          <Button
            onClick={handleContinueClick}
            disabled={isContinuing}
            className="w-full h-16 border-[4px] border-black bg-white hover:bg-white text-black font-black uppercase tracking-[0.1em] text-lg shadow-[8px_8px_0_0_#000] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[6px_6px_0_0_#000] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none transition-all duration-100 flex items-center justify-center gap-3"
          >
            {isContinuing ? (
              <>
                <div className="w-5 h-5 border-[3px] border-black border-t-transparent rounded-full animate-spin"></div>
                Initializing...
              </>
            ) : (
              <>
                Continue to Learning
                <ArrowRight className="w-6 h-6" strokeWidth={3} />
              </>
            )}
          </Button>

          <p className="text-[10px] font-black uppercase tracking-widest text-center opacity-40">
            Powered by Sacred Guide AI • Assessment Ver. 2.4
          </p>
        </CardFooter>
      </Card>
    </div>
  );
};

export default AssessmentResults;
