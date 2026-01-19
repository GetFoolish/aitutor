/**
 * Coming Soon Guard
 * Blocks access to the application unless URL contains the access prefix
 */
import React, { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import ComingSoon from './ComingSoon';

// Access prefixes - paths that bypass the coming soon page
const ACCESS_PREFIXES = ['/app', '/landing', '/pricing'];

interface ComingSoonGuardProps {
  children: ReactNode;
}

const ComingSoonGuard: React.FC<ComingSoonGuardProps> = ({ children }) => {
  const location = useLocation();

  // Check if current pathname starts with any of the access prefixes
  const hasAccess = ACCESS_PREFIXES.some(prefix =>
    location.pathname.startsWith(prefix)
  );

  if (hasAccess) {
    // User has access - render normal app
    return <>{children}</>;
  }

  // No access - show coming soon page
  return <ComingSoon />;
};

export default ComingSoonGuard;

