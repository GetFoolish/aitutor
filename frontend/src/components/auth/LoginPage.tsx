/**
 * Login page wrapper
 */
import React from 'react';
import GoogleSignIn from './GoogleSignIn';
import { useAuth } from '../../contexts/AuthContext';
import { useHistory } from 'react-router-dom';

const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const history = useHistory();

  // If already authenticated, redirect to home
  React.useEffect(() => {
    if (isAuthenticated) {
      history.replace('/');
    }
  }, [isAuthenticated, history]);

  const handleAuthSuccess = (token: string, user: any) => {
    login(token, user);
    history.replace('/');
  };

  return <GoogleSignIn onAuthSuccess={handleAuthSuccess} />;
};

export default LoginPage;

