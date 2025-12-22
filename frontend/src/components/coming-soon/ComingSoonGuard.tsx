/**
 * Coming Soon Guard
 * Blocks access to the application unless URL contains the access prefix
 */
import React, { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import ComingSoon from './ComingSoon';

// Access key - change this to enable/disable coming soon mode
const ACCESS_PREFIX = '/app';

interface ComingSoonGuardProps {
  children: ReactNode;
}

const ComingSoonGuard: React.FC<ComingSoonGuardProps> = ({ children }) => {
  const location = useLocation();
  
  // Bypass guard for mobile app
  return <>{children}</>;
  
  /* 
  // Check if current pathname starts with the access prefix
  const hasAccess = location.pathname.startsWith(ACCESS_PREFIX);
  
  if (hasAccess) {
    // User has access - render normal app
    return <>{children}</>;
  }
  
  // No access - show coming soon page
  return <ComingSoon />; 
  */
};

export default ComingSoonGuard;

