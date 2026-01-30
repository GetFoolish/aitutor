import React, { useState, useEffect } from 'react';
import { useHistory, useLocation } from 'react-router-dom';

interface TopicProgress {
  topic: string;
  questionsAnswered: number;
  questionsCorrect: number;
  totalNeeded: number;
  mastered: boolean;
}

interface LearningPlanProps {
  userId?: string;
  skillLevel?: string;
  focusTopics?: string[];
  strongTopics?: string[];
  grade?: string;
  subject?: string;
  onStartPractice?: (topic: string) => void;
}

interface LocationState {
  skillLevel?: string;
  focusTopics?: string[];
  strongTopics?: string[];
  grade?: string;
  subject?: string;
  fromAssessment?: boolean;
}

export const LearningPlanDashboard: React.FC<LearningPlanProps> = (props) => {
  const history = useHistory();
  const location = useLocation<LocationState>();
  const [topicProgress, setTopicProgress] = useState<TopicProgress[]>([]);
  const [loading, setLoading] = useState(true);

  // Get data from either props or location.state
  const skillLevel = props.skillLevel || location.state?.skillLevel || 'Beginner';
  const focusTopics = props.focusTopics || location.state?.focusTopics || [];
  const strongTopics = props.strongTopics || location.state?.strongTopics || [];
  const grade = props.grade || location.state?.grade || 'K-2';
  const subject = props.subject || location.state?.subject || 'math';
  const onStartPractice = props.onStartPractice;

  useEffect(() => {
    // Initialize progress for all focus topics
    const initProgress = focusTopics.map(topic => ({
      topic,
      questionsAnswered: 0,
      questionsCorrect: 0,
      totalNeeded: 10,
      mastered: false
    }));
    setTopicProgress(initProgress);
    setLoading(false);

    // Load saved progress from localStorage if available
    const savedProgress = localStorage.getItem('learning_plan_progress');
    if (savedProgress) {
      try {
        const parsed = JSON.parse(savedProgress);
        if (parsed.subject === subject && parsed.grade === grade) {
          setTopicProgress(parsed.topics);
        }
      } catch (e) {
        console.error('Failed to load progress:', e);
      }
    }
  }, [focusTopics, subject, grade]);

  const handleStartPractice = (topic: string) => {
    if (onStartPractice) {
      onStartPractice(topic);
    } else {
      // Navigate to practice with topic filter
      history.push('/app/practice', {
        focusTopic: topic,
        grade,
        subject,
        learningPlan: { skillLevel, focusTopics, strongTopics }
      });
    }
  };

  const getSkillLevelColor = (level: string) => {
    const levelLower = level.toLowerCase();
    if (levelLower.includes('begin')) return '#FF6B6B'; // Red for beginner
    if (levelLower.includes('inter')) return '#FFD93D'; // Yellow for intermediate
    if (levelLower.includes('advan')) return '#4ADE80'; // Green for advanced
    return '#A78BFA'; // Purple for unknown
  };

  const getSkillLevelEmoji = (level: string) => {
    const levelLower = level.toLowerCase();
    if (levelLower.includes('begin')) return '🌱';
    if (levelLower.includes('inter')) return '🌿';
    if (levelLower.includes('advan')) return '🌳';
    return '✨';
  };

  const calculateOverallProgress = () => {
    const masteredCount = topicProgress.filter(t => t.mastered).length;
    const totalTopics = focusTopics.length;
    return totalTopics > 0 ? Math.round((masteredCount / totalTopics) * 100) : 0;
  };

  const getProgressColor = (progress: number) => {
    if (progress >= 80) return '#4ADE80'; // Green
    if (progress >= 50) return '#FFD93D'; // Yellow
    return '#A78BFA'; // Purple
  };

  const overallProgress = calculateOverallProgress();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-2xl">loading your learning plan... ✨</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-8">

        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-black" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            your learning plan ✨
          </h1>
          <p className="text-xl text-gray-600">
            let's master {subject} together! you got this 🌟
          </p>
        </div>

        {/* Skill Level Card */}
        <div
          className="bg-white border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8 rounded-xl"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-bold text-gray-600 mb-2">your current level</div>
              <div className="flex items-center gap-3">
                <span className="text-4xl">{getSkillLevelEmoji(skillLevel)}</span>
                <span className="text-3xl font-black">{skillLevel}</span>
              </div>
            </div>
            <div
              className="w-32 h-32 rounded-full border-4 border-black flex items-center justify-center text-4xl font-black"
              style={{ backgroundColor: getSkillLevelColor(skillLevel) }}
            >
              {skillLevel.slice(0, 1)}
            </div>
          </div>
        </div>

        {/* Overall Progress */}
        <div
          className="bg-white border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-6 rounded-xl"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="text-xl font-black">overall progress</div>
            <div className="text-2xl font-black" style={{ color: getProgressColor(overallProgress) }}>
              {overallProgress}%
            </div>
          </div>
          <div className="w-full h-8 bg-gray-200 border-4 border-black rounded-lg overflow-hidden">
            <div
              className="h-full transition-all duration-500 ease-out flex items-center justify-center text-sm font-bold"
              style={{
                width: `${overallProgress}%`,
                backgroundColor: getProgressColor(overallProgress)
              }}
            >
              {overallProgress > 10 && `${overallProgress}%`}
            </div>
          </div>
          <div className="text-sm text-gray-600 mt-2">
            {topicProgress.filter(t => t.mastered).length} of {focusTopics.length} topics mastered 🎉
          </div>
        </div>

        {/* Focus Topics */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-2xl font-black">focus topics 🎯</h2>
            <span className="text-sm font-bold bg-yellow-300 px-3 py-1 rounded-full border-2 border-black">
              work on these!
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {topicProgress.map((topic, index) => {
              const progressPercent = topic.totalNeeded > 0
                ? Math.round((topic.questionsCorrect / topic.totalNeeded) * 100)
                : 0;

              return (
                <div
                  key={topic.topic}
                  className={`bg-white border-4 border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] p-6 rounded-xl transition-all hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] ${
                    topic.mastered ? 'opacity-70' : ''
                  }`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="text-xl font-black capitalize">{topic.topic}</div>
                      <div className="text-sm text-gray-600">
                        {topic.mastered ? (
                          <span className="text-green-600 font-bold">✓ mastered! 🎉</span>
                        ) : (
                          <span>
                            {topic.questionsCorrect} of {topic.totalNeeded} questions correct
                          </span>
                        )}
                      </div>
                    </div>
                    {topic.mastered && (
                      <div className="text-4xl">🏆</div>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-4">
                    <div className="w-full h-6 bg-gray-200 border-3 border-black rounded-lg overflow-hidden">
                      <div
                        className="h-full transition-all duration-500 ease-out"
                        style={{
                          width: `${progressPercent}%`,
                          backgroundColor: topic.mastered ? '#4ADE80' : '#A78BFA'
                        }}
                      />
                    </div>
                  </div>

                  {/* Action Button */}
                  {!topic.mastered && (
                    <button
                      onClick={() => handleStartPractice(topic.topic)}
                      className="w-full bg-purple-400 hover:bg-purple-500 border-4 border-black font-black py-3 px-6 rounded-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all"
                    >
                      {topic.questionsAnswered === 0 ? 'start practicing ✨' : 'continue practicing 🚀'}
                    </button>
                  )}

                  {topic.mastered && (
                    <button
                      onClick={() => handleStartPractice(topic.topic)}
                      className="w-full bg-gray-200 hover:bg-gray-300 border-4 border-black font-black py-3 px-6 rounded-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all"
                    >
                      review again 📚
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Strong Topics */}
        {strongTopics.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-2xl font-black">strong topics 💪</h2>
              <span className="text-sm font-bold bg-green-300 px-3 py-1 rounded-full border-2 border-black">
                you're great at these!
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {strongTopics.map((topic, index) => (
                <div
                  key={topic}
                  className="bg-green-100 border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-4 rounded-xl text-center"
                >
                  <div className="text-3xl mb-2">🌟</div>
                  <div className="text-sm font-bold capitalize">{topic}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Steps */}
        {focusTopics.length > 0 && (
          <div
            className="bg-gradient-to-r from-purple-400 to-pink-400 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8 rounded-xl"
          >
            <div className="text-center space-y-4">
              <div className="text-3xl">✨</div>
              <div className="text-2xl font-black text-white">
                ready to level up?
              </div>
              <div className="text-lg text-white">
                {topicProgress.filter(t => !t.mastered).length > 0 ? (
                  <>start with <span className="font-black">{topicProgress.find(t => !t.mastered)?.topic}</span> and watch your skills grow! 🚀</>
                ) : (
                  <>you've mastered all focus topics! time to challenge yourself with new material! 🎉</>
                )}
              </div>
              <button
                onClick={() => {
                  const nextTopic = topicProgress.find(t => !t.mastered);
                  if (nextTopic) {
                    handleStartPractice(nextTopic.topic);
                  }
                }}
                className="bg-white hover:bg-gray-100 border-4 border-black font-black py-4 px-8 rounded-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all text-xl"
              >
                let's go! 🎯
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default LearningPlanDashboard;
