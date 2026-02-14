/**
 * Dev Quick Login — pick a subject + age, create test user, go straight to assessment.
 * Access at /app/dev-login
 */
import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import BackgroundShapes from '../background-shapes/BackgroundShapes';
import { useTheme } from '../theme/theme-provier';

const AUTH_API_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';
const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

const AGES = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18];

const SUBJECTS = [
  { id: 'Math', label: 'Math', color: '#FF6B6B', icon: '\u{1D70B}' },
  { id: 'Science', label: 'Science', color: '#4ECDC4', icon: '\u{1F52C}' },
  { id: 'English', label: 'English', color: '#FFD93D', icon: '\u{1F4DA}' },
  { id: 'History', label: 'History', color: '#95E1D3', icon: '\u{1F3DB}' },
];

const gradeForAge = (age: number) => {
  if (age <= 5) return 'K';
  if (age >= 18) return 'Grade 12+';
  return `Grade ${age - 5}`;
};

const DevLogin: React.FC = () => {
  const history = useHistory();
  const { theme, setTheme } = useTheme();
  const [selectedSubject, setSelectedSubject] = useState<string>('Math');
  const [presetSubject, setPresetSubject] = useState<string>('Math'); // last clicked preset
  const [customSubject, setCustomSubject] = useState('');
  const [selectedAge, setSelectedAge] = useState<number | null>(null);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Clear stale session on mount so each test starts fresh
  React.useEffect(() => {
    sessionStorage.removeItem('selected_subject');
    sessionStorage.removeItem('onboarding_complete');
  }, []);

  const handleLogin = async (age: number) => {
    setSelectedAge(age);
    setLoading(true);
    setError('');

    try {
      // 1. Create dev user
      const res = await fetch(`${AUTH_API_URL}/auth/dev-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ age, name: name.trim() || 'Test Student' })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = data.detail || `HTTP ${res.status}`;
        throw new Error(
          res.status === 404
            ? 'Auth service unavailable. Please ensure the auth server is running on port 8003.'
            : res.status === 500
            ? 'Server error. Please check the backend logs and try again.'
            : `Login failed: ${detail}`
        );
      }

      const data = await res.json();
      localStorage.setItem('jwt_token', data.token);

      // 2. Fire-and-forget subject switch (don't await — assessment flow retries)
      fetch(`${DASH_API_URL}/api/start-subject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${data.token}`
        },
        body: JSON.stringify({ subject: selectedSubject, region: 'US' })
      }).catch(() => {});

      // 3. Navigate via React Router — avoids full page reload blank screen (Bug #1)
      sessionStorage.setItem('onboarding_complete', 'true');
      sessionStorage.setItem('selected_subject', selectedSubject);
      history.push(`/app/assessment/${selectedSubject}`);
    } catch (err: any) {
      setError(err.message || 'Login failed');
      setLoading(false);
    }
  };

  const isDark = theme === 'dark';
  const activeColor = SUBJECTS.find(s => s.id === selectedSubject)?.color || (customSubject ? '#C3ACD0' : '#FFD93D');
  const borderColor = isDark ? '#fff' : '#000';
  const textColor = isDark ? '#fff' : '#000';
  const bgColor = isDark ? '#000' : '#FFFDF5';
  const inputBg = isDark ? '#1a1a1a' : '#fff';
  const shadowColor = isDark ? 'rgba(255,255,255,0.3)' : '#000';

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      background: bgColor,
      fontFamily: 'system-ui, -apple-system, sans-serif',
      overflow: 'auto',
      color: textColor,
      transition: 'background 200ms ease-out, color 200ms ease-out'
    }}>
      <BackgroundShapes />

      {/* Theme toggle — top-right corner */}
      <button
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        style={{
          position: 'fixed',
          top: '16px',
          right: '16px',
          zIndex: 10,
          width: '36px',
          height: '36px',
          border: '3px solid currentColor',
          borderRadius: '0',
          background: 'transparent',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
          boxShadow: '2px 2px 0 currentColor'
        }}
        title="Toggle dark mode"
      >
        {theme === 'dark' ? '\u2600' : '\u263D'}
      </button>

      <div style={{
        position: 'relative',
        zIndex: 1,
        textAlign: 'center',
        maxWidth: '640px',
        width: '90%',
        padding: '20px 0'
      }}>
        <div style={{
          display: 'inline-block',
          padding: '6px 16px',
          border: `3px solid ${borderColor}`,
          background: '#FF6B6B',
          color: '#fff',
          fontWeight: 900,
          fontSize: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '16px'
        }}>
          Dev Mode
        </div>

        <h1 style={{
          fontSize: '26px',
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '8px',
          color: textColor
        }}>
          Quick Test Login
        </h1>
        <p style={{
          fontSize: '13px',
          fontWeight: 600,
          color: isDark ? '#aaa' : '#666',
          marginBottom: '20px'
        }}>
          Select a subject, then choose your age to begin.
        </p>

        {/* Name field */}
        <div style={{ marginBottom: '20px' }}>
          <input
            type="text"
            className="dev-login-input"
            value={name}
            maxLength={40}
            onChange={(e) => setName(e.target.value.replace(/[^\p{L}\p{N} .\-']/gu, ''))}
            onBlur={() => setName(n => n.trim())}
            placeholder="Student name (optional)"
            disabled={loading}
            onFocus={(e) => e.target.select()}
            style={{
              padding: '10px 16px',
              border: `3px solid ${borderColor}`,
              background: loading ? (isDark ? '#333' : '#eee') : inputBg,
              color: textColor,
              boxShadow: `3px 3px 0 ${shadowColor}`,
              fontSize: '14px',
              fontWeight: 700,
              width: '240px',
              textAlign: 'center',
              outline: 'none',
              opacity: loading ? 0.6 : 1,
              cursor: loading ? 'not-allowed' : 'text'
            }}
          />
        </div>

        {/* Subject picker */}
        <p style={{
          fontSize: '11px',
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: textColor,
          marginBottom: '10px'
        }}>
          1. Subject
        </p>
        <div style={{
          display: 'flex',
          gap: '10px',
          justifyContent: 'center',
          marginBottom: '24px',
          flexWrap: 'wrap'
        }}>
          {SUBJECTS.map((subj) => {
            const isActive = selectedSubject === subj.id && !customSubject;
            return (
              <button
                key={subj.id}
                onClick={() => {
                  if (loading) return;
                  setSelectedSubject(subj.id);
                  setPresetSubject(subj.id);
                  setCustomSubject('');
                }}
                disabled={loading}
                style={{
                  padding: '12px 20px',
                  border: isActive ? `4px solid ${borderColor}` : `3px solid ${borderColor}`,
                  background: isActive ? subj.color : inputBg,
                  boxShadow: isActive ? `4px 4px 0 ${shadowColor}` : `2px 2px 0 ${shadowColor}`,
                  cursor: loading ? 'wait' : 'pointer',
                  transition: 'all 100ms ease-out',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  transform: isActive ? 'translate(-1px, -1px)' : 'none',
                }}
              >
                <span style={{ fontSize: '20px' }}>{subj.icon}</span>
                <span style={{
                  fontSize: '14px',
                  fontWeight: 900,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: isActive ? '#000' : textColor
                }}>
                  {subj.label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Custom subject input */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginBottom: '12px',
          justifyContent: 'center'
        }}>
          <div style={{ flex: '0 0 auto', height: '3px', width: '40px', background: borderColor }} />
          <span style={{
            fontSize: '11px',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: textColor
          }}>
            or type any subject
          </span>
          <div style={{ flex: '0 0 auto', height: '3px', width: '40px', background: borderColor }} />
        </div>
        <div style={{
          display: 'flex',
          gap: '10px',
          justifyContent: 'center',
          marginBottom: '24px'
        }}>
          <input
            type="text"
            className="dev-login-input"
            value={customSubject}
            maxLength={50}
            onChange={(e) => {
              const cleaned = e.target.value.replace(/[^\p{L}\p{N} ,.\-'&]/gu, '');
              setCustomSubject(cleaned);
              if (cleaned.trim()) {
                setSelectedSubject(cleaned.trim());
              } else {
                // Restore last clicked preset instead of hardcoding 'Math' (Bug #26)
                setSelectedSubject(presetSubject);
              }
            }}
            placeholder="e.g. Geography, Music Theory, Python..."
            disabled={loading}
            style={{
              padding: '10px 16px',
              border: customSubject ? `4px solid ${borderColor}` : `3px solid ${borderColor}`,
              background: customSubject ? '#C3ACD0' : inputBg,
              color: customSubject ? '#000' : textColor,
              boxShadow: customSubject ? `4px 4px 0 ${shadowColor}` : `2px 2px 0 ${shadowColor}`,
              fontSize: '14px',
              fontWeight: 700,
              width: '320px',
              maxWidth: '90%',
              outline: 'none',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              transition: 'all 100ms ease-out'
            }}
          />
        </div>

        {/* Active subject indicator */}
        <div style={{
          marginBottom: '16px',
          padding: '8px 16px',
          background: activeColor,
          border: `2px solid ${borderColor}`,
          display: 'inline-block',
          fontSize: '12px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: '#000', // Always dark text on colored background
          maxWidth: '90%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap'
        }}>
          Testing: {selectedSubject}
        </div>

        {/* Age grid */}
        <p style={{
          fontSize: '11px',
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: textColor,
          marginBottom: '10px'
        }}>
          2. Select your age
        </p>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          gap: '10px',
          marginBottom: '20px'
        }}>
          {AGES.map((age) => {
            const isSelected = selectedAge === age && loading;
            return (
              <button
                key={age}
                onClick={() => !loading && handleLogin(age)}
                disabled={loading}
                style={{
                  padding: '18px 8px',
                  minHeight: '44px',
                  minWidth: '44px',
                  border: `3px solid ${borderColor}`,
                  background: isSelected ? (isDark ? '#333' : '#ddd') : activeColor,
                  boxShadow: loading ? `1px 1px 0 ${shadowColor}` : `3px 3px 0 ${shadowColor}`,
                  cursor: loading ? 'wait' : 'pointer',
                  transition: 'all 100ms ease-out',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '4px'
                }}
                onMouseDown={(e) => {
                  if (!loading) {
                    (e.currentTarget).style.transform = 'translate(2px, 2px)';
                    (e.currentTarget).style.boxShadow = `1px 1px 0 ${shadowColor}`;
                  }
                }}
                onMouseUp={(e) => {
                  (e.currentTarget).style.transform = 'none';
                  (e.currentTarget).style.boxShadow = `3px 3px 0 ${shadowColor}`;
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget).style.transform = 'none';
                  (e.currentTarget).style.boxShadow = `3px 3px 0 ${shadowColor}`;
                }}
              >
                <span style={{
                  fontSize: '22px',
                  fontWeight: 900,
                  color: '#fff',
                  textShadow: '1px 1px 0 rgba(0,0,0,0.3)'
                }}>
                  {age}
                </span>
                <span style={{
                  fontSize: '10px',
                  fontWeight: 800,
                  color: 'rgba(255,255,255,0.85)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  textShadow: '1px 1px 0 rgba(0,0,0,0.2)'
                }}>
                  {gradeForAge(age)}
                </span>
              </button>
            );
          })}
        </div>

        {loading && (
          <div style={{
            padding: '16px 24px',
            border: `4px solid ${borderColor}`,
            background: activeColor,
            boxShadow: `4px 4px 0 ${shadowColor}`,
            fontWeight: 900,
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            color: '#000'
          }}>
            <span style={{
              display: 'inline-block',
              width: '18px',
              height: '18px',
              border: '3px solid #000',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }} />
            Creating assessment for {selectedSubject}, age {selectedAge}...
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {error && (
          <div style={{
            padding: '10px 16px',
            border: `3px solid ${borderColor}`,
            background: '#FF6B6B',
            color: '#fff',
            fontWeight: 700,
            fontSize: '13px',
            textTransform: 'uppercase',
            marginBottom: '12px'
          }}>
            {error}
          </div>
        )}

        <p style={{
          fontSize: '11px',
          color: '#999',
          marginTop: '8px'
        }}>
          Each click creates a new user and goes straight to assessment.
          Come back here anytime to switch subject or age.
        </p>
      </div>

      {/* Ensure input placeholder is visible in both themes (Bug #2/#5/#7) */}
      <style>{`
        .dev-login-input::placeholder {
          color: ${isDark ? 'rgba(255, 255, 255, 0.5)' : 'rgba(0, 0, 0, 0.45)'} !important;
          opacity: 1 !important;
        }
      `}</style>
    </div>
  );
};

export default DevLogin;
