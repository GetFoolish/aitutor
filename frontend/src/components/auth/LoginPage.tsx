/**
 * Login page - Email/Password + Google OAuth
 */
import React, { useState, useEffect } from 'react';
import EmailPasswordForm from './EmailPasswordForm';
import SignupForm from './SignupForm';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import { useAuth } from '../../contexts/AuthContext';
import { useHistory } from 'react-router-dom';
import './auth.scss';

const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8081';

const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const history = useHistory();
  const [showSignupForm, setShowSignupForm] = useState(false);
  const [setupToken, setSetupToken] = useState<string>('');
  const [googleUser, setGoogleUser] = useState<any>(null);

  // If already authenticated, redirect to home
  useEffect(() => {
    if (isAuthenticated) {
      history.replace('/app');
    }
  }, [isAuthenticated, history]);

  // Check if we're returning from OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const setupTokenParam = urlParams.get('setup_token');
    const googleName = urlParams.get('google_name');
    const googleEmail = urlParams.get('google_email');
    const googlePicture = urlParams.get('google_picture');

    if (token) {
      // Existing user - login directly
      fetch(`${AUTH_API_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
        .then(res => res.json())
        .then(userData => {
          login(token, userData);
          history.replace('/app');
        })
        .catch(error => {
          console.error('Failed to get user info:', error);
        });
    } else if (setupTokenParam) {
      // New Google user - needs to complete signup
      setSetupToken(setupTokenParam);
      if (googleName || googleEmail) {
        setGoogleUser({
          name: googleName ? decodeURIComponent(googleName) : '',
          email: googleEmail ? decodeURIComponent(googleEmail) : '',
          picture: googlePicture ? decodeURIComponent(googlePicture) : '',
        });
      }
      setShowSignupForm(true);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handleAuthSuccess = (token: string, user: any) => {
    login(token, user);
    history.replace('/app');
  };

  const handleGoogleLogin = () => {
    window.location.href = `${AUTH_API_URL}/auth/google`;
  };

  // If showing signup wizard, render it
  if (showSignupForm && setupToken) {
    return (
      <SignupForm
        setupToken={setupToken}
        googleUser={googleUser}
        onComplete={(token, user) => {
          handleAuthSuccess(token, user);
          setShowSignupForm(false);
        }}
        onCancel={() => {
          setShowSignupForm(false);
          setGoogleUser(null);
          history.replace('/app/login');
        }}
      />
    );
  }

  return (
    <div className="auth-container">
      <BackgroundShapes />
      <div className="auth-card">
        {/* Logo Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          marginBottom: '24px'
        }}>
          <div style={{
            width: '56px',
            height: '56px',
            border: '4px solid #000000',
            background: '#FFD93D',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '4px 4px 0px 0px #000000',
            transform: 'rotate(-2deg)'
          }}>
            <span className="material-symbols-outlined" style={{
              fontSize: '32px',
              color: '#000000',
              fontWeight: 900
            }}>
              smart_toy
            </span>
          </div>
        </div>

        <h1>Welcome to AI Tutor</h1>
        <p>Sign in to continue your learning journey</p>

        {/* Email/Password Form */}
        <EmailPasswordForm onAuthSuccess={handleAuthSuccess} />

        {/* Divider */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          margin: '24px 0',
          gap: '16px'
        }}>
          <div style={{ flex: 1, height: '2px', background: '#000000' }} />
          <span style={{ 
            fontWeight: 700, 
            fontSize: '12px', 
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: '#666'
          }}>
            or
          </span>
          <div style={{ flex: 1, height: '2px', background: '#000000' }} />
        </div>

        {/* Google Login Button */}
        <button
          onClick={handleGoogleLogin}
          style={{
            width: '100%',
            padding: '14px 24px',
            border: '4px solid #000000',
            background: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            cursor: 'pointer',
            boxShadow: '4px 4px 0px 0px #000000',
            transition: 'all 150ms ease',
            fontWeight: 700,
            fontSize: '16px',
            textTransform: 'uppercase',
          }}
          onMouseDown={(e) => {
            (e.target as HTMLElement).style.boxShadow = '2px 2px 0px 0px #000000';
            (e.target as HTMLElement).style.transform = 'translate(2px, 2px)';
          }}
          onMouseUp={(e) => {
            (e.target as HTMLElement).style.boxShadow = '4px 4px 0px 0px #000000';
            (e.target as HTMLElement).style.transform = 'translate(0, 0)';
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLElement).style.boxShadow = '4px 4px 0px 0px #000000';
            (e.target as HTMLElement).style.transform = 'translate(0, 0)';
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>
      </div>
    </div>
  );
};

export default LoginPage;
