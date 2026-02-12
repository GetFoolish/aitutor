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
  const [assessmentStatus, setAssessmentStatus] = useState<{
    loading: boolean;
    completed: boolean;
    checkFailed: boolean;
  }>({
    loading: true,
    completed: false,
    checkFailed: false
  });

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
        try {
          await apiUtils.post(`${DASH_API_URL}/api/start-subject`, {
            subject: urlSubject,
            region: 'US'
          });
          subjectAlreadySwitched = true;
        } catch (err) {
          console.warn('Failed to switch subject after assessment:', err);
        }
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
          : apiUtils.post(`${DASH_API_URL}/api/start-subject`, {
              subject: effectiveSubject,
              region: 'US'
            }).catch((err: any) => console.warn('Failed to ensure subject:', err));

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

  if (!onboardingComplete || assessmentStatus.loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: '#FFFDF5'
      }}>
        <div>Checking assessment status...</div>
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
