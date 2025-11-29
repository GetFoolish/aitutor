/**
 * Google Sign-In component using Google OAuth
 */
import React, { useState, useEffect } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { authAPI } from '../../lib/auth-api';
import SignupForm from './SignupForm';
import './auth.scss';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

interface GoogleSignInContentProps {
  onAuthSuccess: (token: string, user: any) => void;
}

const GoogleSignInContent: React.FC<GoogleSignInContentProps> = ({ onAuthSuccess }) => {
  const [showSignupForm, setShowSignupForm] = useState(false);
  const [setupToken, setSetupToken] = useState<string>('');
  const [googleUser, setGoogleUser] = useState<any>(null);

  const handleGoogleLogin = async () => {
    try {
      // Get authorization URL from backend and redirect
      const authUrl = await authAPI.getGoogleAuthUrl();
      window.location.href = authUrl.authorization_url;
    } catch (error) {
      console.error('Google login error:', error);
      alert('Failed to sign in with Google. Please try again.');
    }
  };

  // Check if we're returning from OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const isNewUser = urlParams.get('is_new_user') === 'true';
    const setupTokenParam = urlParams.get('setup_token');

    if (token) {
      // Existing user - login directly
      // We need to get user info from token
      fetch(`${import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003'}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
        .then(res => res.json())
        .then(userData => {
          onAuthSuccess(token, userData);
          // Clean up URL
          window.history.replaceState({}, document.title, window.location.pathname);
        })
        .catch(error => {
          console.error('Failed to get user info:', error);
        });
    } else if (setupTokenParam) {
      // New user - show signup form
      setSetupToken(setupTokenParam);
      setShowSignupForm(true);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (showSignupForm && setupToken) {
    return (
      <SignupForm
        setupToken={setupToken}
        googleUser={googleUser}
        onComplete={(token, user) => {
          onAuthSuccess(token, user);
          setShowSignupForm(false);
        }}
        onCancel={() => setShowSignupForm(false)}
      />
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>Welcome to AI Tutor</h1>
        <p>Sign in with your Google account to get started</p>
        <button className="google-sign-in-button" onClick={handleGoogleLogin}>
          <svg width="18" height="18" viewBox="0 0 18 18">
            <path
              fill="#4285F4"
              d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"
            />
            <path
              fill="#34A853"
              d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z"
            />
            <path
              fill="#FBBC05"
              d="M3.964 10.707c-.18-.54-.282-1.117-.282-1.707s.102-1.167.282-1.707V4.961H.957C.348 6.175 0 7.55 0 9s.348 2.825.957 4.039l3.007-2.332z"
            />
            <path
              fill="#EA4335"
              d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.961L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z"
            />
          </svg>
          Sign in with Google
        </button>
      </div>
    </div>
  );
};

interface GoogleSignInProps {
  onAuthSuccess: (token: string, user: any) => void;
}

const GoogleSignIn: React.FC<GoogleSignInProps> = ({ onAuthSuccess }) => {
  if (!GOOGLE_CLIENT_ID) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <p>Error: Google Client ID not configured</p>
        </div>
      </div>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <GoogleSignInContent onAuthSuccess={onAuthSuccess} />
    </GoogleOAuthProvider>
  );
};

export default GoogleSignIn;

