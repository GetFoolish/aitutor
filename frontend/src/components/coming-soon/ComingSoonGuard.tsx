/**
 * Coming Soon Guard
 * Blocks access to the application unless URL contains the access prefix
 */
import React, { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import ComingSoon from './ComingSoon';

interface ComingSoonGuardProps {
  children: ReactNode;
}

const ComingSoonGuard: React.FC<ComingSoonGuardProps> = ({ children }) => {
  const location = useLocation();

  // Show coming-soon page only for the explicit /comingsoon path
  // All other paths pass through to the router (Switch handles 404 via NotFound)
  if (location.pathname === '/comingsoon') {
    return <ComingSoon />;
  }

  return <>{children}</>;
};

export default ComingSoonGuard;

