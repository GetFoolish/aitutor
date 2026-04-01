/**
 * Auth guard component to protect routes
 * Supports demo mode bypass via ?demo=true or DEMO_MODE localStorage
 */
import React, { ReactNode } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Redirect } from 'react-router-dom';

// Demo mode bypass for testing and screenshots
const isDemoMode = () => {
  if (typeof window === 'undefined') return false;
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('demo') === 'true' || localStorage.getItem('DEMO_MODE') === 'true';
};

interface AuthGuardProps {
  children: ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  // DEMO MODE: Bypass authentication for testing/screenshots
  if (isDemoMode()) {
    console.log('🎬 AuthGuard: Demo mode active - bypassing authentication');
    return <>{children}</>;
  }

  if (isLoading) {
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
    return <Redirect to="/app/login" />;
  }

  return <>{children}</>;
};

export default AuthGuard;

