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
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
};

export default AuthGuard;

