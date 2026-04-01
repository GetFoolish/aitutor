/**
 * Dev Quick Login — pick a subject + age, create test user, go straight to assessment.
 * Access at /app/dev-login
 */
import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import Header from '../header/Header';
import { useTheme } from '../theme/theme-provier';
import { jwtUtils } from '../../lib/jwt-utils';

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
  const [forceMC, setForceMC] = useState(false);

  // Clear stale session on mount so each test starts fresh
  React.useEffect(() => {
    sessionStorage.removeItem('selected_subject');
    sessionStorage.removeItem('onboarding_complete');
  }, []);

  // Update selectedSubject when customSubject changes (for automation compatibility)
  React.useEffect(() => {
    const trimmed = customSubject.trim();
    const hasLetter = /[a-zA-Z]/.test(trimmed);

    if (trimmed.length >= 2 && hasLetter) {
      console.log('[DevLogin] useEffect: Setting selectedSubject to custom:', trimmed);
      setSelectedSubject(trimmed);
    } else if (trimmed.length === 0 && selectedSubject !== presetSubject) {
      console.log('[DevLogin] useEffect: Restoring preset:', presetSubject);
      setSelectedSubject(presetSubject);
    }
  }, [customSubject, presetSubject, selectedSubject]);

  // Expose setter for automation/testing
  React.useEffect(() => {
    (window as any).__setCustomSubject = (subject: string) => {
      console.log('[DevLogin] Automation: Setting custom subject to:', subject);
      setCustomSubject(subject);
    };
    return () => {
      delete (window as any).__setCustomSubject;
    };
  }, []);

  const handleLogin = async (age: number) => {
    setSelectedAge(age);
    setLoading(true);
    setError('');

    // CRITICAL FIX: Read custom subject directly from DOM to support automation
    // React state might not update in time when automated, so check DOM value
    const customInput = document.querySelector('#custom-subject-input') as HTMLInputElement;
    const customValue = customInput?.value?.trim() || '';

    // Use DOM value if it's valid, otherwise use React state
    const finalSubject = (customValue.length >= 2 && /[a-zA-Z]/.test(customValue))
      ? customValue
      : selectedSubject;

    console.log('[DevLogin] handleLogin called with:', {
      age,
      selectedSubject,
      customSubject,
      customInputDOMValue: customValue,
      finalSubjectUsed: finalSubject,
      presetSubject
    });

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
      jwtUtils.setToken(data.token);

      // Verify token was saved before proceeding
      if (!jwtUtils.hasToken()) {
        throw new Error('Failed to save authentication token. Please check if localStorage is enabled.');
      }

      // 2. Fire-and-forget subject switch (don't await — assessment flow retries)
      fetch(`${DASH_API_URL}/api/start-subject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${data.token}`
        },
        body: JSON.stringify({ subject: finalSubject, region: 'US' })
      }).catch((err) => {
        console.warn('[DevLogin] Subject switch failed (will retry in assessment):', err);
        // Don't block login - assessment flow will retry
      });

      // 3. Navigate via React Router — avoids full page reload blank screen (Bug #1)
      sessionStorage.setItem('onboarding_complete', 'true');
      sessionStorage.setItem('selected_subject', finalSubject);
      sessionStorage.setItem('dev_force_mc', forceMC ? '1' : '0');

      // Small delay to ensure localStorage writes complete before navigation
      await new Promise(resolve => setTimeout(resolve, 100));

      history.push(`/app/assessment/${finalSubject}`);
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
      justifyContent: 'flex-start',
      alignItems: 'center',
      background: bgColor,
      fontFamily: "'Space Grotesk', -apple-system, sans-serif",
      overflow: 'auto',
      paddingTop: '80px',
      paddingBottom: '80px',
      color: textColor,
      transition: 'background 200ms ease-out, color 200ms ease-out'
    }}>
      <Header
        sidebarOpen={false}
        onToggleSidebar={() => {}}
        assessmentMode={true}
      />

      {/* Theme toggle — top-right corner */}
      <button
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        style={{
          position: 'fixed',
          top: '16px',
          right: '16px',
          zIndex: 9,
          width: '48px',
          height: '48px',
          border: '4px solid currentColor',
          borderRadius: '0',
          background: 'transparent',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '20px',
          fontWeight: 900,
          boxShadow: '4px 4px 0 currentColor',
          overflow: 'hidden'
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
        <span style={{
          display: 'inline-block',
          background: '#FF4B4B',
          color: 'white',
          padding: '4px 12px',
          fontSize: '11px',
          fontWeight: 'bold' as const,
          letterSpacing: '0.1em',
          border: '2px solid #000',
          cursor: 'default',
          userSelect: 'none' as const,
          marginBottom: '16px',
        }}>
          DEMO
        </span>

        <h1 style={{
          fontSize: '32px',
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '8px',
          color: textColor
        }}>
          Quick Test Login
        </h1>
        <p style={{
          fontSize: '16px',
          fontWeight: 400,
          color: '#666',
          marginBottom: '24px'
        }}>
          Select a subject, then choose your age to begin.
        </p>

        {/* Name field */}
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="student-name-input" style={{ position: 'absolute', left: '-10000px' }}>
            Student name (optional)
          </label>
          <input
            id="student-name-input"
            type="text"
            className="dev-login-input"
            value={name}
            maxLength={40}
            onChange={(e) => setName(e.target.value.replace(/[^\p{L}\p{N} .\-']/gu, ''))}
            onBlur={() => setName(n => n.trim())}
            placeholder="Student name (optional)"
            aria-label="Student name (optional)"
            disabled={loading}
            onFocus={(e) => e.target.select()}
            style={{
              padding: '14px 20px',
              border: `4px solid ${borderColor}`,
              background: loading ? (isDark ? '#333' : '#eee') : inputBg,
              color: textColor,
              boxShadow: `4px 4px 0 ${shadowColor}`,
              fontSize: '16px',
              fontWeight: 700,
              width: '300px',
              textAlign: 'center',
              outline: 'none',
              opacity: loading ? 0.6 : 1,
              cursor: loading ? 'not-allowed' : 'text'
            }}
          />
        </div>

        {/* Subject picker */}
        <p style={{
          fontSize: '12px',
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: '0.15em',
          color: '#666',
          marginBottom: '8px'
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
                  width: 'calc(50% - 6px)',
                  minWidth: 0,
                  maxWidth: '140px',
                  padding: '10px 8px',
                  border: '2px solid #000',
                  background: isActive ? '#FF4B4B' : '#fff',
                  color: isActive ? '#fff' : '#000',
                  boxShadow: '4px 4px 0 #000',
                  cursor: loading ? 'wait' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  overflow: 'hidden',
                }}
              >
                <span style={{ fontSize: '24px' }}>{subj.icon}</span>
                <span style={{
                  fontSize: '13px',
                  fontWeight: 900,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  minWidth: 0,
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
          <div style={{ flex: '0 0 auto', height: '4px', width: '50px', background: borderColor }} />
          <span style={{
            fontSize: '14px',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.15em',
            color: textColor
          }}>
            or type any subject
          </span>
          <div style={{ flex: '0 0 auto', height: '4px', width: '50px', background: borderColor }} />
        </div>
        <div style={{
          display: 'flex',
          gap: '10px',
          justifyContent: 'center',
          marginBottom: '24px'
        }}>
          <label htmlFor="custom-subject-input" style={{ position: 'absolute', left: '-10000px' }}>
            Enter a custom subject
          </label>
          <input
            id="custom-subject-input"
            type="text"
            className="dev-login-input"
            value={customSubject}
            maxLength={50}
            onChange={(e) => {
              const cleaned = e.target.value.replace(/[^\p{L}\p{N} ,.\-'&]/gu, '');
              setCustomSubject(cleaned);
              // Validate: minimum 2 chars and at least one letter
              const trimmed = cleaned.trim();
              const hasLetter = /[a-zA-Z]/.test(trimmed);

              console.log('[DevLogin] Custom subject onChange:', {
                input: e.target.value,
                cleaned,
                trimmed,
                hasLetter,
                willUpdate: trimmed.length >= 2 && hasLetter
              });

              if (trimmed.length >= 2 && hasLetter) {
                console.log('[DevLogin] Setting selectedSubject to:', trimmed);
                setSelectedSubject(trimmed);
              } else if (trimmed.length === 0) {
                // Restore last clicked preset when field is cleared
                console.log('[DevLogin] Clearing custom, restoring preset:', presetSubject);
                setSelectedSubject(presetSubject);
              }
              // If 1 char or no letters, don't update selectedSubject (keep previous)
            }}
            placeholder="e.g. Geography, Music Theory, Python..."
            aria-label="Enter a custom subject (e.g. Geography, Music Theory, Python)"
            disabled={loading}
            style={{
              padding: '14px 20px',
              border: `4px solid ${borderColor}`,
              background: customSubject ? '#C3ACD0' : inputBg,
              color: customSubject ? '#000' : textColor,
              boxShadow: customSubject ? `6px 6px 0 ${shadowColor}` : `4px 4px 0 ${shadowColor}`,
              fontSize: '16px',
              fontWeight: 700,
              width: '360px',
              maxWidth: '90%',
              outline: 'none',
              fontFamily: "'Space Grotesk', -apple-system, sans-serif",
              transition: 'all 100ms ease-out'
            }}
          />
        </div>

        {/* Active subject indicator */}
        <div style={{
          display: 'inline-block',
          background: 'white',
          border: '2px solid #FF4B4B',
          color: '#FF4B4B',
          padding: '4px 12px',
          fontSize: '12px',
          fontWeight: 700,
          marginBottom: '16px',
          letterSpacing: '0.05em',
          textTransform: 'uppercase' as const,
        }}>
          {selectedSubject}
        </div>

        {/* Dev toggle: Force MC */}
        <div style={{ width: '100%', marginBottom: '20px', display: 'flex', justifyContent: 'center' }}>
          <label
            htmlFor="force-mc-toggle"
            data-testid="force-mc-label"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              cursor: 'pointer',
              userSelect: 'none' as const,
              padding: '12px 24px',
              border: `2px solid ${forceMC ? '#4f46e5' : '#a5b4fc'}`,
              background: forceMC ? '#4f46e5' : '#eef2ff',
              color: forceMC ? '#fff' : '#4338ca',
              fontWeight: 800,
              fontSize: '13px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase' as const,
              transition: 'all 100ms',
              minWidth: '260px',
              boxShadow: forceMC ? '3px 3px 0 #312e81' : '2px 2px 0 #a5b4fc',
            }}
          >
            <input
              id="force-mc-toggle"
              type="checkbox"
              checked={forceMC}
              onChange={e => setForceMC(e.target.checked)}
              disabled={loading}
              style={{ width: '18px', height: '18px', accentColor: '#4f46e5', cursor: 'pointer', flexShrink: 0 }}
            />
            Force Multiple Choice (QA)
          </label>
        </div>

        {/* Age grid */}
        <p style={{
          fontSize: '12px',
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: '0.15em',
          color: '#666',
          marginBottom: '8px'
        }}>
          2. Select your age
        </p>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(60px, 1fr))',
          gap: '6px',
          marginBottom: '20px',
          justifyContent: 'center'
        }}>
          {AGES.map((age) => {
            const isSelected = selectedAge === age;
            return (
              <button
                key={age}
                onClick={() => !loading && setSelectedAge(age)}
                disabled={loading}
                style={{
                  width: '100%',
                  height: '60px',
                  minWidth: 'unset',
                  minHeight: 'unset',
                  padding: '0',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '2px',
                  border: isSelected ? '3px solid #FF4B4B' : '2px solid #000',
                  background: isSelected ? '#FF4B4B' : '#FFFFFF',
                  boxShadow: isSelected ? '3px 3px 0 #FF4B4B' : '2px 2px 0 #000',
                  cursor: loading ? 'wait' : 'pointer',
                  transform: isSelected ? 'translateY(-2px)' : 'none',
                  transition: 'all 80ms ease-out',
                }}
              >
                <span style={{
                  fontSize: age >= 10 ? '22px' : '28px',
                  fontWeight: 900,
                  color: isSelected ? '#fff' : '#000',
                  textShadow: 'none'
                }}>
                  {age}
                </span>
                <span style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  color: isSelected ? 'rgba(255,255,255,0.9)' : 'rgba(0,0,0,0.6)',
                  textTransform: 'uppercase',
                  whiteSpace: 'nowrap',
                  letterSpacing: '0.05em'
                }}>
                  {gradeForAge(age)}
                </span>
              </button>
            );
          })}
        </div>

        {/* Start Assessment sticky button */}
        <button
          onClick={() => selectedSubject && selectedAge !== null && handleLogin(selectedAge)}
          disabled={!selectedSubject || selectedAge === null || loading}
          style={{
            position: 'sticky',
            bottom: 0,
            width: '100%',
            padding: '16px',
            background: selectedSubject && selectedAge !== null && !loading ? '#FF4B4B' : '#E5E5E5',
            border: selectedSubject && selectedAge !== null && !loading ? '2px solid #000' : '2px solid #999',
            boxShadow: selectedSubject && selectedAge !== null && !loading ? '4px 4px 0 #000' : 'none',
            fontWeight: 700,
            fontSize: '14px',
            textTransform: 'uppercase' as const,
            letterSpacing: '0.05em',
            cursor: selectedSubject && selectedAge !== null && !loading ? 'pointer' : 'not-allowed',
            color: selectedSubject && selectedAge !== null && !loading ? 'white' : '#999',
            marginBottom: '20px',
            fontFamily: "'Space Grotesk', -apple-system, sans-serif"
          }}
        >
          {loading ? 'Starting...' : 'Start Assessment →'}
        </button>

        {loading && (
          <div style={{
            padding: '16px 24px',
            border: `4px solid ${borderColor}`,
            background: activeColor,
            boxShadow: `4px 4px 0 ${shadowColor}`,
            fontWeight: 900,
            fontSize: '16px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            color: '#000'
          }}>
            <span style={{
              display: 'inline-block',
              width: '20px',
              height: '20px',
              border: '4px solid #000',
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
            padding: '12px 20px',
            border: `4px solid ${borderColor}`,
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
