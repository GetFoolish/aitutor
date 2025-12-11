/**
 * Auth guard component to protect routes
 */
import React, { ReactNode, useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Redirect } from 'react-router-dom';
import { apiUtils } from '../../lib/api-utils';

const ONBOARDING_API_URL = import.meta.env.VITE_ONBOARDING_API_URL || 'http://localhost:8004';

interface AuthGuardProps {
  children: ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const [onboardingStatus, setOnboardingStatus] = useState<{ completed: boolean; checking: boolean }>({
    completed: false,
    checking: true
  });

  useEffect(() => {
    const checkOnboarding = async () => {
      if (!isAuthenticated) {
        setOnboardingStatus({ completed: false, checking: false });
        return;
      }

      try {
        const response = await apiUtils.get(`${ONBOARDING_API_URL}/api/onboarding/status`);
        if (response.ok) {
          const data = await response.json();
          setOnboardingStatus({ completed: data.completed, checking: false });
        } else {
          // If API fails, assume onboarding is not required (for backward compatibility)
          setOnboardingStatus({ completed: true, checking: false });
        }
      } catch (error) {
        console.error('Error checking onboarding status:', error);
        // On error, assume onboarding is not required
        setOnboardingStatus({ completed: true, checking: false });
      }
    };

    if (!isLoading && isAuthenticated) {
      checkOnboarding();
    }
  }, [isAuthenticated, isLoading]);

  if (isLoading || onboardingStatus.checking) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: '#FFFDF5'
      }}>
        <div style={{
          padding: '24px 32px',
          border: '4px solid #000000',
          background: '#FFFDF5',
          boxShadow: '8px 8px 0px 0px #000000',
          fontSize: '18px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: '#000000'
        }}>
          Loading...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Redirect to="/login" />;
  }

  // Redirect to onboarding if not completed
  if (!onboardingStatus.completed) {
    return <Redirect to="/onboarding" />;
  }

  return <>{children}</>;
};

export default AuthGuard;

