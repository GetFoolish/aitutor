/**
 * Login page wrapper - Google OAuth + Email/Password
 */
import React, { useState, useEffect } from 'react';
import GoogleSignIn from './GoogleSignIn';
import EmailPasswordForm from './EmailPasswordForm';
import SignupForm from './SignupForm';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import { useAuth } from '../../contexts/AuthContext';
import { useHistory } from 'react-router-dom';
import { authAPI } from '../../lib/auth-api';
import './auth.scss';

const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const history = useHistory();
  const [showSignupForm, setShowSignupForm] = useState(false);
  const [setupToken, setSetupToken] = useState<string>('');

  // If already authenticated, show option to continue or switch to dev mode
  const [showAuthRedirect, setShowAuthRedirect] = useState(false);
  React.useEffect(() => {
    if (isAuthenticated) {
      setShowAuthRedirect(true);
    }
  }, [isAuthenticated]);

  // Check if we're returning from OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const authCode = urlParams.get('auth_code');

    if (!authCode) return;

    authAPI.exchangeAuthCode(authCode)
      .then(async exchange => {
        window.history.replaceState({}, document.title, window.location.pathname);

        if (exchange.token) {
          const response = await fetch(`${import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003'}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${exchange.token}`,
            },
          });
          if (!response.ok) {
            throw new Error(`Failed to load user profile (${response.status})`);
          }
          const userData = await response.json();
          login(exchange.token, userData);
          history.replace('/app');
          return;
        }

        if (exchange.setup_token) {
          setSetupToken(exchange.setup_token);
          setShowSignupForm(true);
          return;
        }

        throw new Error('Invalid auth exchange payload');
      })
      .catch(error => {
        console.error('OAuth callback handling failed:', error);
        alert('Sign-in failed. Please try again.');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAuthSuccess = (token: string, user: any) => {
    login(token, user);
    history.replace('/app');
  };

  const handleGoogleLogin = async () => {
    try {
      const authUrl = await authAPI.getGoogleAuthUrl();
      window.location.href = authUrl.authorization_url;
    } catch (error) {
      console.error('Google login error:', error);
      alert('Failed to sign in with Google. Please try again.');
    }
  };

  // If showing signup wizard, render it
  if (showSignupForm && setupToken) {
    return (
      <SignupForm
        setupToken={setupToken}
        googleUser={null}
        onComplete={(token, user) => {
          handleAuthSuccess(token, user);
          setShowSignupForm(false);
        }}
        onCancel={() => {
          setShowSignupForm(false);
          history.replace('/app/login');
        }}
      />
    );
  }

  if (showAuthRedirect) {
    return (
      <div className="auth-container">
        <BackgroundShapes />
        <div className="auth-card">
          <h1>You're signed in</h1>
          <p style={{ marginBottom: '24px' }}>Where do you want to go?</p>

          <button
            onClick={() => history.replace('/app')}
            style={{
              width: '100%',
              padding: '14px 20px',
              border: '3px solid #000',
              background: '#FFD93D',
              fontWeight: 900,
              fontSize: '14px',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              cursor: 'pointer',
              boxShadow: '3px 3px 0 #000',
              marginBottom: '12px',
            }}
          >
            Continue Learning
          </button>

          <button
            onClick={() => history.push('/app/dev-login')}
            style={{
              width: '100%',
              padding: '14px 20px',
              border: '3px solid #000',
              background: '#FF6B6B',
              color: '#fff',
              fontWeight: 900,
              fontSize: '14px',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              cursor: 'pointer',
              boxShadow: '3px 3px 0 #000',
              marginBottom: '12px',
            }}
          >
            Dev Mode — Test Any Subject + Age
          </button>

          <button
            onClick={() => {
              localStorage.removeItem('jwt_token');
              localStorage.removeItem('active_assessment');
              // Targeted session cleanup instead of sessionStorage.clear()
              sessionStorage.removeItem('selected_subject');
              sessionStorage.removeItem('onboarding_complete');
              sessionStorage.removeItem('assessmentSubject');
              sessionStorage.removeItem('assessment_completed_subject');
              sessionStorage.removeItem('content_v1_mode');
              sessionStorage.removeItem('content_v1_started');
              window.location.reload();
            }}
            style={{
              width: '100%',
              padding: '10px 20px',
              border: '3px solid #000',
              background: '#fff',
              fontWeight: 700,
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              cursor: 'pointer',
              boxShadow: '2px 2px 0 #000',
            }}
          >
            Sign Out
          </button>
        </div>
      </div>
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

        {/* Google Sign In Button */}
        <button className="google-sign-in-button" onClick={handleGoogleLogin}>
          <svg width="20" height="20" viewBox="0 0 18 18" style={{ flexShrink: 0 }}>
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
          Continue with Google
        </button>

        {/* OR Divider */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          margin: '28px 0',
        }}>
          <div style={{ flex: 1, height: '3px', background: '#000000' }}></div>
          <span style={{
            fontWeight: 900,
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em'
          }}>OR</span>
          <div style={{ flex: 1, height: '3px', background: '#000000' }}></div>
        </div>

        {/* Email/Password Form */}
        <EmailPasswordForm onAuthSuccess={handleAuthSuccess} />

        {/* Dev Quick-Test Link */}
        <button
          onClick={() => history.push('/app/dev-login')}
          style={{
            marginTop: '24px',
            padding: '10px 20px',
            border: '3px solid #000',
            background: '#FF6B6B',
            color: '#fff',
            fontWeight: 900,
            fontSize: '12px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            cursor: 'pointer',
            boxShadow: '3px 3px 0 #000',
            width: '100%',
          }}
        >
          Dev Mode — Test Any Subject + Age
        </button>
      </div>
    </div>
  );
};

export default LoginPage;
