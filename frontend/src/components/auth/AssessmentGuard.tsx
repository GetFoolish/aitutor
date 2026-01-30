/**
 * Assessment Guard Component (UPDATED)
 *
 * Enhanced to integrate with UserOnboardingFlow.
 * Only checks assessment status if onboarding is complete.
 */
import React, { useEffect, useState } from 'react';
import { Redirect } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import UserOnboardingFlow from './UserOnboardingFlow';
import LearnerOnboarding from '../onboarding/LearnerOnboarding';
import { jwtUtils } from '../../lib/jwt-utils';

interface AssessmentGuardProps {
  children: React.ReactNode;
  subject?: string;
}

const DEFAULT_SUBJECT = 'math';
const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

const AssessmentGuard: React.FC<AssessmentGuardProps> = ({
  children,
  subject = DEFAULT_SUBJECT
}) => {
  const { isAuthenticated, isLoading } = useAuth();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const [showLearnerOnboarding, setShowLearnerOnboarding] = useState(false);
  
  // Check sessionStorage for cached completion status (prevents redirect loop)
  const cachedCompleted = sessionStorage.getItem('assessment_completed_dynamic') === 'true';
  
  const [assessmentStatus, setAssessmentStatus] = useState<{
    loading: boolean;
    completed: boolean;
    checkFailed: boolean;
  }>({
    loading: !cachedCompleted, // Don't load if already completed
    completed: cachedCompleted,
    checkFailed: false
  });

  useEffect(() => {
    if (!isAuthenticated || isLoading) {
      return;
    }

    // Check if onboarding has been completed (stored in sessionStorage)
    const onboardingDone = sessionStorage.getItem('onboarding_complete');
    
    if (!onboardingDone) {
      // First time login - show onboarding flow
      setShowOnboarding(true);
    } else {
      // Onboarding done - check assessment status normally
      setOnboardingComplete(true);
      const learnerDone = sessionStorage.getItem('learner_onboarding_complete') === 'true';
      if (!learnerDone) {
        setShowLearnerOnboarding(true);
        return;
      }
      checkAssessmentStatus();
    }
  }, [isAuthenticated, isLoading, subject]);

  // Listen for onboarding completion
  useEffect(() => {
    const handleOnboardingComplete = () => {
      setShowOnboarding(false);
      setOnboardingComplete(true);
      sessionStorage.setItem('onboarding_complete', 'true');
      const learnerDone = sessionStorage.getItem('learner_onboarding_complete') === 'true';
      if (!learnerDone) {
        setShowLearnerOnboarding(true);
        return;
      }
      checkAssessmentStatus();
    };

    window.addEventListener('onboarding-complete', handleOnboardingComplete);
    return () => {
      window.removeEventListener('onboarding-complete', handleOnboardingComplete);
    };
  }, []);

  useEffect(() => {
    const handleLearnerOnboardingComplete = () => {
      setShowLearnerOnboarding(false);
    };

    window.addEventListener('learner-onboarding-complete', handleLearnerOnboardingComplete);
    return () => {
      window.removeEventListener('learner-onboarding-complete', handleLearnerOnboardingComplete);
    };
  }, []);

  const checkAssessmentStatus = async () => {
    // Skip API call if already cached as completed
    if (sessionStorage.getItem('assessment_completed_dynamic') === 'true') {
      setAssessmentStatus({
        loading: false,
        completed: true,
        checkFailed: false
      });
      return;
    }

    setAssessmentStatus({
      loading: true,
      completed: false,
      checkFailed: false
    });

    try {
      const token = jwtUtils.getToken();
      const response = await fetch(`${DASH_API_URL}/api/assessment/dynamic/status`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Status check failed: ${response.status}`);
      }

      const data = await response.json();
      const completed = data?.completed === true;

      if (completed) {
        sessionStorage.setItem('assessment_completed_dynamic', 'true');
      }

      setAssessmentStatus({
        loading: false,
        completed,
        checkFailed: false
      });
    } catch (error) {
      console.error('[AssessmentGuard] Failed to check dynamic assessment status:', error);
      setAssessmentStatus({
        loading: false,
        completed: false,
        checkFailed: true
      });
    }
  };

  // Show loading while checking authentication
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

  // If not authenticated, let AuthGuard handle redirect
  if (!isAuthenticated) {
    return <>{children}</>;
  }

  // Show onboarding flow on first login
  if (showOnboarding) {
    return <UserOnboardingFlow />;
  }

  if (showLearnerOnboarding) {
    return <LearnerOnboarding />;
  }

  // Show loading while checking assessment status
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

  // If check failed, allow access (don't block user on API error)
  if (assessmentStatus.checkFailed) {
    return <>{children}</>;
  }

  // If assessment not completed, redirect to learner onboarding
  if (!assessmentStatus.completed) {
    return <Redirect to="/app/onboarding" />;
  }

  // Assessment completed, allow access to app
  return <>{children}</>;
};

export default AssessmentGuard;
