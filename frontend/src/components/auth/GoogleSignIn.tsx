/**
 * Google Sign-In component using Google OAuth
 */
import React, { useState, useEffect } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { authAPI } from '../../lib/auth-api';
import { App, URLOpenListenerEvent } from '@capacitor/app';
import { Browser } from '@capacitor/browser';
import { PluginListenerHandle } from '@capacitor/core';
import SignupForm from './SignupForm';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
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
    console.log('Google Sign-In button clicked');
    try {
      // Get authorization URL from backend
      const authUrl = await authAPI.getGoogleAuthUrl();

      // Use Capacitor Browser to open the auth URL
      await Browser.open({ url: authUrl.authorization_url });

    } catch (error: any) {
      console.error('Google login error:', error);
      // Show specific error to help debugging
      alert(`Failed to sign in: ${error.message || JSON.stringify(error, null, 2)}. check your network connection.`);
    }
  };

  // Check if we're returning from OAuth callback
  useEffect(() => {
    const handleAuthParams = (params: URLSearchParams) => {
      const token = params.get('token');
      const isNewUser = params.get('is_new_user') === 'true';
      const setupTokenParam = params.get('setup_token');

      if (token) {
        // Existing user - login directly
        // We need to get user info from token
        authAPI.getCurrentUser(token)
          .then(userData => {
            onAuthSuccess(token, userData);
            // Clean up URL if possible (web only)
            if (window.history && window.history.replaceState) {
              window.history.replaceState({}, document.title, window.location.pathname);
            }
          })
          .catch(error => {
            console.error('Failed to get user info:', error);
            alert('Failed to get user info. Please try again.');
          });
      } else if (setupTokenParam) {
        // New user - show signup form
        setSetupToken(setupTokenParam);
        setShowSignupForm(true);
        // Clean up URL if possible (web only)
        if (window.history && window.history.replaceState) {
          window.history.replaceState({}, document.title, window.location.pathname);
        }
      }
    };

    // Check initial URL (Web & Mobile Cold Start)
    handleAuthParams(new URLSearchParams(window.location.search));

    // Listen for Deep Links (Mobile Resume)
    const listener = App.addListener('appUrlOpen', (data: URLOpenListenerEvent) => {
      try {
        const url = new URL(data.url);
        if (url.search) {
          handleAuthParams(new URLSearchParams(url.search));
        }
      } catch (e) {
        console.error('Error parsing deep link:', e);
      }
    });

    return () => {
      listener.then((handle: PluginListenerHandle) => handle.remove());
    };
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

  const handleDevSignupTest = () => {
    setSetupToken('dev-test-token');
    setGoogleUser({
      name: "Test User",
      email: "test@example.com",
      picture: ""
    });
    setShowSignupForm(true);
  };

  return (
    <div className="auth-container">
      {/* <BackgroundShapes /> */}
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
        <p>Sign in with your Google account to get started</p>

        <button
          onClick={() => {
            console.log('Debug Button Clicked');
            alert('Debug Button Works!');
          }}
          style={{
            marginBottom: '20px',
            padding: '10px',
            background: 'red',
            color: 'white',
            zIndex: 9999,
            position: 'relative'
          }}
        >
          DEBUG CLICK TEST
        </button>

        <button
          className="google-sign-in-button"
          onClick={handleGoogleLogin}
          onTouchEnd={(e) => {
            // Ensure touch events trigger the login if click fails
            // (though React usually handles this, some fast-click libs or mobile behaviors interfere)
            console.log('Touch end on Google button');
            // preventDefault to avoid double-firing if onClick also fires?
            // Better to just log for now to see if it even receives touch.
          }}
          style={{ position: 'relative', zIndex: 100 }}
        >
          <svg width="20" height="20" viewBox="0 0 18 18" style={{ flexShrink: 0, pointerEvents: 'none' }}>
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

        {/* Dev Mode Verification Button - Always enabled for mobile testing */}
        {(
          <div style={{ marginTop: '20px', borderTop: '2px dashed #ccc', paddingTop: '20px' }}>
            <p style={{ fontSize: '12px', marginBottom: '10px', color: '#666' }}>Test Mode:</p>
            <button
              onClick={handleDevSignupTest}
              style={{
                padding: '10px 15px',
                background: '#333',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 'bold'
              }}
            >
              Test Signup / Bypass Login
            </button>
          </div>
        )}
      </div>
      <div className="background-shapes-container" style={{ pointerEvents: 'none' }}>
        <BackgroundShapes />
      </div>
    </div>
  );
};

interface GoogleSignInProps {
  onAuthSuccess: (token: string, user: any) => void;
}

const GoogleSignIn: React.FC<GoogleSignInProps> = ({ onAuthSuccess }) => {
  // If no client ID, we still render the content but the Google button will fail/not render correctly.
  // We wrap in Provider if ID exists, otherwise just render content for Dev access.

  if (GOOGLE_CLIENT_ID) {
    return (
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <GoogleSignInContent onAuthSuccess={onAuthSuccess} />
      </GoogleOAuthProvider>
    );
  }

  // Fallback for dev mode without Client ID
  return <GoogleSignInContent onAuthSuccess={onAuthSuccess} />;
};

export default GoogleSignIn;
