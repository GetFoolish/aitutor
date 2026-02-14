/**
 * Assessment Guard Component
 *
 * Flow: Auth -> Onboarding -> Subject Selector -> Assessment -> App
 * Shows subject selector after onboarding so student can pick their subject.
 */
import React, { useEffect, useState } from 'react';
import { Redirect } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiUtils } from '../../lib/api-utils';
import UserOnboardingFlow from './UserOnboardingFlow';
import SubjectSelector from './SubjectSelector';

interface AssessmentGuardProps {
  children: React.ReactNode;
  subject?: string;
  onStartAssessment?: (subject: string) => void;
}

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
const DEFAULT_SUBJECT = 'math';

const AssessmentGuard: React.FC<AssessmentGuardProps> = ({
  children,
  subject: defaultSubject = DEFAULT_SUBJECT,
  onStartAssessment
}) => {
  const { isAuthenticated, isLoading } = useAuth();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const [showSubjectSelector, setShowSubjectSelector] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<string>(defaultSubject);
  const [curriculumGenerating, setCurriculumGenerating] = useState(false);
  const [assessmentStatus, setAssessmentStatus] = useState<{
    loading: boolean;
    completed: boolean;
    checkFailed: boolean;
  }>({
    loading: true,
    completed: false,
    checkFailed: false
  });

  // Call /api/start-subject and poll until curriculum is ready if generating
  const ensureSubjectReady = async (subject: string): Promise<void> => {
    try {
      const resp = await apiUtils.post(`${DASH_API_URL}/api/start-subject`, {
        subject,
        region: 'US'
      });
      if (!resp.ok) {
        console.warn('start-subject returned non-OK:', resp.status);
        return;
      }
      const data = await resp.json();
      if (data.status === 'generating' && data.poll_url) {
        // Curriculum is being generated — poll until ready
        setCurriculumGenerating(true);
        const pollUrl = `${DASH_API_URL}${data.poll_url}`;
        const maxPollTime = 120_000; // 2 minutes max
        const pollInterval = 3_000;
        const start = Date.now();
        while (Date.now() - start < maxPollTime) {
          await new Promise(r => setTimeout(r, pollInterval));
          try {
            const pollResp = await apiUtils.get(pollUrl);
            if (pollResp.ok) {
              const pollData = await pollResp.json();
              if (pollData.status === 'complete') {
                // Reload DASH with the newly generated curriculum
                await apiUtils.post(`${DASH_API_URL}/api/start-subject`, {
                  subject,
                  region: 'US'
                });
                break;
              }
            }
          } catch (err) {
            console.warn('Curriculum poll failed:', err);
          }
        }
        setCurriculumGenerating(false);
      }
    } catch (err) {
      console.warn('Failed to ensure subject ready:', err);
    }
  };

  useEffect(() => {
    if (!isAuthenticated || isLoading) {
      return;
    }

    const init = async () => {
      // Check if returning from assessment with a subject in the URL
      const urlParams = new URLSearchParams(window.location.search);
      const urlSubject = urlParams.get('subject');

      const onboardingDone = sessionStorage.getItem('onboarding_complete');
      const savedSubject = sessionStorage.getItem('selected_subject');

      // If URL has a subject param (e.g. after assessment), update sessionStorage
      // and WAIT for backend to switch before proceeding
      let subjectAlreadySwitched = false;
      if (urlSubject && urlSubject !== savedSubject) {
        sessionStorage.setItem('selected_subject', urlSubject);
        await ensureSubjectReady(urlSubject);
        subjectAlreadySwitched = true;
      }

      const effectiveSubject = urlSubject || savedSubject;

      if (!onboardingDone) {
        setShowOnboarding(true);
      } else if (!effectiveSubject) {
        // Onboarding done but no subject selected yet — show selector
        setOnboardingComplete(true);
        setShowSubjectSelector(true);
      } else {
        // Both done — start subject + check assessment IN PARALLEL
        setOnboardingComplete(true);
        setSelectedSubject(effectiveSubject);
        const subjectPromise = subjectAlreadySwitched
          ? Promise.resolve()
          : ensureSubjectReady(effectiveSubject);

        const statusPromise = checkAssessmentStatus(effectiveSubject);
        await Promise.all([subjectPromise, statusPromise]);
      }
    };

    init();
  }, [isAuthenticated, isLoading]);

  // Listen for onboarding completion
  useEffect(() => {
    const handleOnboardingComplete = () => {
      setShowOnboarding(false);
      setOnboardingComplete(true);
      sessionStorage.setItem('onboarding_complete', 'true');
      // Show subject selector after onboarding
      setShowSubjectSelector(true);
    };

    window.addEventListener('onboarding-complete', handleOnboardingComplete);
    return () => {
      window.removeEventListener('onboarding-complete', handleOnboardingComplete);
    };
  }, []);

  const handleSubjectReady = (subject: string) => {
    setSelectedSubject(subject);
    sessionStorage.setItem('selected_subject', subject);
    setShowSubjectSelector(false);
    checkAssessmentStatus(subject);
  };

  const checkAssessmentStatus = async (subject: string) => {
    try {
      const response = await apiUtils.get(
        `${DASH_API_URL}/assessment/status/${subject}`
      );

      if (!response.ok) {
        console.warn(`Failed to check assessment status: ${response.status}`);
        setAssessmentStatus({
          loading: false,
          completed: false,
          checkFailed: true
        });
        return;
      }

      const data = await response.json();

      setAssessmentStatus({
        loading: false,
        completed: data.completed || false,
        checkFailed: false
      });
    } catch (error) {
      console.error('Error checking assessment status:', error);
      setAssessmentStatus({
        loading: false,
        completed: false,
        checkFailed: true
      });
    }
  };

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: '#FFFDF5'
      }}>
        <div>Initializing...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <>{children}</>;
  }

  if (showOnboarding) {
    return <UserOnboardingFlow />;
  }

  // Show subject selector
  if (showSubjectSelector) {
    return <SubjectSelector onSubjectReady={handleSubjectReady} />;
  }

  if (!onboardingComplete || assessmentStatus.loading || curriculumGenerating) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        gap: '16px',
        background: '#FFFDF5',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}>
        <div style={{
          width: '200px',
          height: '8px',
          border: '3px solid #000',
          backgroundColor: '#fff',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: '40%',
            backgroundColor: '#C4B5FD',
            animation: 'guard-loading-bar 1.5s ease-in-out infinite',
          }} />
        </div>
        <div style={{
          fontWeight: 900,
          fontSize: '14px',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#000',
        }}>
          {curriculumGenerating ? 'Preparing your curriculum...' : 'Checking assessment status...'}
        </div>
        <style>{`
          @keyframes guard-loading-bar {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(350%); }
          }
        `}</style>
      </div>
    );
  }

  if (assessmentStatus.checkFailed) {
    return <>{children}</>;
  }

  // If assessment not completed, redirect to assessment
  if (!assessmentStatus.completed) {
    if (onStartAssessment) {
      // Trigger assessment inline
      onStartAssessment(selectedSubject);
    }
    return <Redirect to={`/app/assessment/${selectedSubject}`} />;
  }

  return <>{children}</>;
};

export default AssessmentGuard;
