/**
 * Dev Quick Login — pick a subject + age, create test user, go straight to assessment.
 * Access at /app/dev-login
 */
import React, { useState } from 'react';
import BackgroundShapes from '../background-shapes/BackgroundShapes';

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
  if (age >= 18) return 'Grade 12';
  return `Grade ${age - 5}`;
};

const DevLogin: React.FC = () => {
  const [selectedSubject, setSelectedSubject] = useState<string>('Math');
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
        body: JSON.stringify({ age, name: name || 'Test Student' })
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

      // 3. Redirect immediately — assessment flow handles subject init + loading
      sessionStorage.setItem('onboarding_complete', 'true');
      sessionStorage.setItem('selected_subject', selectedSubject);
      window.location.href = `/app/assessment/${selectedSubject}`;
    } catch (err: any) {
      setError(err.message || 'Login failed');
      setLoading(false);
    }
  };

  const activeColor = SUBJECTS.find(s => s.id === selectedSubject)?.color || (customSubject ? '#C3ACD0' : '#FFD93D');

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      background: '#FFFDF5',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      overflow: 'auto'
    }}>
      <BackgroundShapes />
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
          border: '3px solid #000',
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
          color: '#000'
        }}>
          Quick Test Login
        </h1>
        <p style={{
          fontSize: '13px',
          fontWeight: 600,
          color: '#666',
          marginBottom: '20px'
        }}>
          Pick a subject, then click an age to jump straight into assessment.
        </p>

        {/* Name field */}
        <div style={{ marginBottom: '20px' }}>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Student name (optional)"
            disabled={loading}
            onFocus={(e) => e.target.select()}
            style={{
              padding: '10px 16px',
              border: '3px solid #000',
              background: loading ? '#eee' : '#fff',
              boxShadow: '3px 3px 0 #000',
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
          color: '#000',
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
                  setCustomSubject('');
                }}
                disabled={loading}
                style={{
                  padding: '12px 20px',
                  border: isActive ? '4px solid #000' : '3px solid #000',
                  background: isActive ? subj.color : '#fff',
                  boxShadow: isActive ? '4px 4px 0 #000' : '2px 2px 0 #000',
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
                  color: '#000'
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
          <div style={{ flex: '0 0 auto', height: '3px', width: '40px', background: '#000' }} />
          <span style={{
            fontSize: '11px',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: '#000'
          }}>
            or type any subject
          </span>
          <div style={{ flex: '0 0 auto', height: '3px', width: '40px', background: '#000' }} />
        </div>
        <div style={{
          display: 'flex',
          gap: '10px',
          justifyContent: 'center',
          marginBottom: '24px'
        }}>
          <input
            type="text"
            value={customSubject}
            onChange={(e) => {
              setCustomSubject(e.target.value);
              if (e.target.value.trim()) {
                setSelectedSubject(e.target.value.trim());
              }
            }}
            placeholder="e.g. Geography, Music Theory, Python..."
            disabled={loading}
            style={{
              padding: '10px 16px',
              border: customSubject ? '4px solid #000' : '3px solid #000',
              background: customSubject ? '#C3ACD0' : '#fff',
              boxShadow: customSubject ? '4px 4px 0 #000' : '2px 2px 0 #000',
              fontSize: '14px',
              fontWeight: 700,
              width: '320px',
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
          background: '#f5f5f5',
          border: '2px solid #000',
          display: 'inline-block',
          fontSize: '12px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em'
        }}>
          Testing: {selectedSubject}
        </div>

        {/* Age grid */}
        <p style={{
          fontSize: '11px',
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#000',
          marginBottom: '10px'
        }}>
          2. Age (click to start)
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
                  padding: '16px 8px',
                  border: '3px solid #000',
                  background: isSelected ? '#ddd' : activeColor,
                  boxShadow: loading ? '1px 1px 0 #000' : '3px 3px 0 #000',
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
                    (e.currentTarget).style.boxShadow = '1px 1px 0 #000';
                  }
                }}
                onMouseUp={(e) => {
                  (e.currentTarget).style.transform = 'none';
                  (e.currentTarget).style.boxShadow = '3px 3px 0 #000';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget).style.transform = 'none';
                  (e.currentTarget).style.boxShadow = '3px 3px 0 #000';
                }}
              >
                <span style={{
                  fontSize: '22px',
                  fontWeight: 900,
                  color: '#000'
                }}>
                  {age}
                </span>
                <span style={{
                  fontSize: '9px',
                  fontWeight: 700,
                  color: '#555',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
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
            border: '4px solid #000',
            background: activeColor,
            boxShadow: '4px 4px 0 #000',
            fontWeight: 900,
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px'
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
            border: '3px solid #000',
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
    </div>
  );
};

export default DevLogin;
