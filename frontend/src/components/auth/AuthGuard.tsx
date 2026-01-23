/**
 * Auth guard component to protect routes
 */
import React, { ReactNode } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Redirect } from 'react-router-dom';

interface AuthGuardProps {
  children: ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

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
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
};

export default AuthGuard;

