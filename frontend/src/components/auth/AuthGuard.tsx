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
      <div className="flex justify-center items-center h-screen bg-[#FFFDF5]">
        <div className="p-6 md:p-8 border-4 border-black bg-[#FFFDF5] shadow-[8px_8px_0px_0px_#000000] text-lg font-bold uppercase tracking-wider text-black">
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

