/**
 * Enterprise-level User Onboarding Flow
 * 
 * Orchestrates the complete post-authentication flow:
 * 1. Personalization animation
 * 2. Completeness check
 * 3. Missing info collection (if needed)
 * 4. Assessment preparation animation
 * 5. Redirect to assessment or main app
 * 
 * Design: Neo-brutalist with BackgroundShapes, matching AssessmentResults style
 */
import React, { useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiUtils } from '../../lib/api-utils';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import MissingInfoForm from './MissingInfoForm';
import PersonalizationAnimation from './PersonalizationAnimation';
import './auth.scss';

const AUTH_API_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';
const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

type OnboardingStep = 
  | 'initializing'
  | 'checking' 
  | 'personalizing' 
  | 'collecting_info' 
  | 'preparing_assessment' 
  | 'ready';

interface CompletenessCheck {
  is_complete: boolean;
  missing_fields: string[];
  assessment_completed: boolean;
  assessment_subject: string;
  readiness_status: 'ready' | 'needs_info' | 'needs_assessment' | 'complete';
  user_data: {
    date_of_birth?: string;
    gender?: string;
    preferred_language?: string;
    location?: string;
    age?: number;
    current_grade?: string;
  };
}

const UserOnboardingFlow: React.FC = () => {
  const history = useHistory();
  const { isAuthenticated, isLoading } = useAuth();
  const [step, setStep] = useState<OnboardingStep>('initializing');
  const [completeness, setCompleteness] = useState<CompletenessCheck | null>(null);
  const [message, setMessage] = useState('Personalizing everything for you...');
  const [subMessage, setSubMessage] = useState('Checking your profile...');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      history.replace('/app/login');
      return;
    }

    if (isAuthenticated && !isLoading) {
      startOnboardingFlow();
    }
  }, [isAuthenticated, isLoading, history]);

  const startOnboardingFlow = async () => {
    try {
      // Step 1: Initial personalization animation
      setStep('personalizing');
      setMessage('Personalizing everything for\nyou...');
      setSubMessage('Setting up your learning experience');
      
      // Show animation for 1.5 seconds
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Step 2: Check completeness
      setStep('checking');
      setSubMessage('Checking your profile and assessment status...');

      const response = await apiUtils.get(`${AUTH_API_URL}/auth/check-completeness`);
      
      if (!response.ok) {
        throw new Error('Failed to check completeness');
      }

      const data: CompletenessCheck = await response.json();
      setCompleteness(data);

      // Brief pause before next step
      await new Promise(resolve => setTimeout(resolve, 800));

      // Step 3: Route based on readiness
      if (data.readiness_status === 'needs_info') {
        // Missing information - show form
        setStep('collecting_info');
        setMessage('Before starting, I need some more information from you');
        setSubMessage('This will help us personalize your learning experience');
      } else if (data.readiness_status === 'needs_assessment') {
        // All info complete, but no assessment - prepare for assessment
        setStep('preparing_assessment');
        setMessage('Preparing your assessment...');
        setSubMessage('Setting up your personalized learning plan');
        
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Emit completion event for AssessmentGuard
        window.dispatchEvent(new CustomEvent('onboarding-complete'));
        sessionStorage.setItem('onboarding_complete', 'true');
        
        // Redirect to assessment
        history.replace(`/app/assessment/${data.assessment_subject}`);
      } else if (data.readiness_status === 'complete') {
        // Everything complete - go to main app
        setStep('ready');
        setMessage('Welcome back!');
        setSubMessage('Loading your personalized dashboard...');
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Emit completion event for AssessmentGuard
        window.dispatchEvent(new CustomEvent('onboarding-complete'));
        sessionStorage.setItem('onboarding_complete', 'true');
        
        history.replace('/app');
      }
    } catch (error) {
      console.error('Error in onboarding flow:', error);
      // On error, allow access (don't block user)
      setMessage('Loading your dashboard...');
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Emit completion event
      window.dispatchEvent(new CustomEvent('onboarding-complete'));
      sessionStorage.setItem('onboarding_complete', 'true');
      
      history.replace('/app');
    }
  };

  const handleInfoSubmitted = async (formData: any) => {
    try {
      setStep('preparing_assessment');
      setMessage('Preparing your assessment...');
      setSubMessage('Setting up your personalized learning plan');

      // Update missing information
      const response = await apiUtils.post(
        `${AUTH_API_URL}/auth/update-missing-info`,
        formData
      );

      if (!response.ok) {
        throw new Error('Failed to update information');
      }

      const result = await response.json();
      
      // Wait for animation
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Emit completion event
      window.dispatchEvent(new CustomEvent('onboarding-complete'));
      sessionStorage.setItem('onboarding_complete', 'true');

      // Check if assessment is needed (should be, since we just collected info)
      if (completeness && !completeness.assessment_completed) {
        history.replace(`/app/assessment/${completeness.assessment_subject}`);
      } else {
        history.replace('/app');
      }
    } catch (error) {
      console.error('Error updating information:', error);
      setMessage('Error updating information');
      setSubMessage('Please try again');
      // Allow retry by going back to collecting_info
      setStep('collecting_info');
    }
  };

  // Render based on current step
  if (step === 'initializing' || step === 'checking' || step === 'personalizing' || step === 'preparing_assessment' || step === 'ready') {
    return (
      <div className="auth-container">
        <BackgroundShapes />
        <PersonalizationAnimation 
          message={message} 
          subMessage={subMessage}
        />
      </div>
    );
  }

  if (step === 'collecting_info' && completeness) {
    return (
      <MissingInfoForm
        missingFields={completeness.missing_fields}
        existingData={completeness.user_data}
        onSubmit={handleInfoSubmitted}
      />
    );
  }

  return null;
};

export default UserOnboardingFlow;
