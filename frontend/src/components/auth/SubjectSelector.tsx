/**
 * Subject Selector Component
 *
 * Lets students pick which subject to study — popular presets + custom input.
 * Calls /api/start-subject to ensure curriculum is ready.
 * Shows generation progress for new subjects.
 */
import React, { useState, useEffect, useRef } from 'react';
import { apiUtils } from '../../lib/api-utils';
import BackgroundShapes from '../background-shapes/BackgroundShapes';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface SubjectOption {
  id: string;
  label: string;
  color: string;
  icon: string;
}

const POPULAR_SUBJECTS: SubjectOption[] = [
  { id: 'Math', label: 'Math', color: '#FF6B6B', icon: '\u{1D70B}' },
  { id: 'Science', label: 'Science', color: '#4ECDC4', icon: '\u{1F52C}' },
  { id: 'English', label: 'English', color: '#FFD93D', icon: '\u{1F4DA}' },
  { id: 'History', label: 'History', color: '#95E1D3', icon: '\u{1F3DB}' },
];

const RANDOM_COLORS = ['#C3ACD0', '#F7C8E0', '#B5DEFF', '#DFFFD8', '#FFB4B4', '#B6E2D3'];

interface SubjectSelectorProps {
  onSubjectReady: (subject: string) => void;
  region?: string;
}

const SubjectSelector: React.FC<SubjectSelectorProps> = ({
  onSubjectReady,
  region = 'US'
}) => {
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);
  const [customSubject, setCustomSubject] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'generating' | 'error'>('idle');
  const [pollUrl, setPollUrl] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState('');
  const pollFailCountRef = useRef(0);

  // Stable ref for callback to avoid effect re-runs on parent re-render (Bug H1)
  const onSubjectReadyRef = useRef(onSubjectReady);
  onSubjectReadyRef.current = onSubjectReady;

  // AbortController ref to cancel stale polls on rapid subject changes (Bug H2)
  const pollAbortRef = useRef<AbortController | null>(null);

  // Poll for curriculum generation status
  useEffect(() => {
    if (status !== 'generating' || !pollUrl) return;

    // Abort previous polling cycle
    pollAbortRef.current?.abort();
    pollFailCountRef.current = 0;
    const abortController = new AbortController();
    pollAbortRef.current = abortController;

    const interval = setInterval(async () => {
      if (abortController.signal.aborted) {
        clearInterval(interval);
        return;
      }
      try {
        const response = await apiUtils.get(`${DASH_API_URL}${pollUrl}`);
        if (!response.ok) return;

        const data = await response.json();
        if (data.status === 'complete') {
          clearInterval(interval);
          if (selectedSubject) {
            const r = await apiUtils.post(`${DASH_API_URL}/api/start-subject`, {
              subject: selectedSubject,
              region
            });
            if (r.ok) {
              const d = await r.json();
              if (d.status === 'ready') {
                onSubjectReadyRef.current(selectedSubject);
                return;
              }
            }
          }
          setStatus('error');
        } else {
          setGenerationProgress(data.message || 'Building curriculum...');
        }
      } catch {
        pollFailCountRef.current += 1;
        if (pollFailCountRef.current >= 10) {
          clearInterval(interval);
          setStatus('error');
          return;
        }
      }
    }, 3000);

    return () => {
      clearInterval(interval);
      abortController.abort();
    };
  }, [status, pollUrl, selectedSubject, region]);

  const handleSelect = async (subject: string) => {
    const trimmed = subject.trim();
    if (!trimmed) return;

    setSelectedSubject(trimmed);
    setStatus('loading');

    try {
      const response = await apiUtils.post(`${DASH_API_URL}/api/start-subject`, {
        subject: trimmed,
        region
      });

      if (!response.ok) {
        setStatus('error');
        return;
      }

      const data = await response.json();

      if (data.status === 'ready') {
        onSubjectReady(trimmed);
      } else if (data.status === 'generating') {
        setStatus('generating');
        setPollUrl(data.poll_url);
        setGenerationProgress('Starting curriculum generation...');
      } else {
        setStatus('error');
      }
    } catch (err) {
      console.error('Failed to start subject:', err);
      setStatus('error');
    }
  };

  const subjectColor = POPULAR_SUBJECTS.find(s => s.id === selectedSubject)?.color
    || RANDOM_COLORS[Math.abs((selectedSubject || '').length) % RANDOM_COLORS.length];

  // Generating state — full-screen progress
  if (status === 'generating') {
    return (
      <div style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        background: '#FFFDF5',
        zIndex: 50,
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        <BackgroundShapes />
        <div style={{
          position: 'relative',
          zIndex: 1,
          textAlign: 'center',
          padding: '48px',
          border: '4px solid #000',
          background: '#fff',
          boxShadow: '6px 6px 0 #000',
          maxWidth: '420px'
        }}>
          <h2 style={{
            fontSize: '22px',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            margin: '0 0 16px 0'
          }}>
            Building Your {selectedSubject} Curriculum
          </h2>
          <div style={{
            width: '100%',
            height: '12px',
            border: '3px solid #000',
            background: '#eee',
            overflow: 'hidden',
            marginBottom: '16px'
          }}>
            <div style={{
              height: '100%',
              background: subjectColor,
              animation: 'progress-pulse 2s ease-in-out infinite',
              width: '60%'
            }} />
          </div>
          <p style={{
            fontSize: '14px',
            fontWeight: 700,
            color: '#555',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            margin: 0
          }}>
            {generationProgress}
          </p>
          <p style={{
            fontSize: '12px',
            color: '#888',
            marginTop: '8px'
          }}>
            This takes about 30 seconds. Hang tight!
          </p>
        </div>
        <style>{`
          @keyframes progress-pulse {
            0% { width: 20%; }
            50% { width: 80%; }
            100% { width: 20%; }
          }
        `}</style>
      </div>
    );
  }

  const isDisabled = status === 'loading';

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      background: '#FFFDF5',
      zIndex: 50,
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <BackgroundShapes />
      <div style={{
        position: 'relative',
        zIndex: 1,
        textAlign: 'center',
        maxWidth: '600px',
        width: '90%'
      }}>
        <h1 style={{
          fontSize: '28px',
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '8px',
          color: '#000'
        }}>
          What do you want to learn?
        </h1>
        <p style={{
          fontSize: '14px',
          fontWeight: 600,
          color: '#666',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: '32px'
        }}>
          Pick a subject or type your own
        </p>

        {/* Popular subjects grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '16px',
          marginBottom: '24px'
        }}>
          {POPULAR_SUBJECTS.map((subj) => {
            const isLoading = isDisabled && selectedSubject === subj.id;

            return (
              <button
                key={subj.id}
                onClick={() => !isDisabled && handleSelect(subj.id)}
                disabled={isDisabled}
                style={{
                  padding: '28px 16px',
                  border: '4px solid #000',
                  background: isLoading ? '#ddd' : subj.color,
                  boxShadow: isDisabled ? '2px 2px 0 #000' : '5px 5px 0 #000',
                  cursor: isDisabled ? 'wait' : 'pointer',
                  transform: isDisabled ? 'translate(2px, 2px)' : 'none',
                  transition: 'all 100ms ease-out',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '8px'
                }}
                onMouseEnter={(e) => {
                  if (!isDisabled) {
                    (e.currentTarget as HTMLElement).style.transform = 'translate(1px, 1px) scale(1.02)';
                    (e.currentTarget as HTMLElement).style.boxShadow = '4px 4px 0 #000';
                  }
                }}
                onMouseDown={(e) => {
                  if (!isDisabled) {
                    (e.currentTarget as HTMLElement).style.transform = 'translate(3px, 3px)';
                    (e.currentTarget as HTMLElement).style.boxShadow = '2px 2px 0 #000';
                  }
                }}
                onMouseUp={(e) => {
                  if (!isDisabled) {
                    (e.currentTarget as HTMLElement).style.transform = 'translate(1px, 1px) scale(1.02)';
                    (e.currentTarget as HTMLElement).style.boxShadow = '4px 4px 0 #000';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isDisabled) {
                    (e.currentTarget as HTMLElement).style.transform = 'none';
                    (e.currentTarget as HTMLElement).style.boxShadow = '5px 5px 0 #000';
                  }
                }}
              >
                <span style={{ fontSize: '36px' }}>{subj.icon}</span>
                <span style={{
                  fontSize: '18px',
                  fontWeight: 900,
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: '#000'
                }}>
                  {isLoading ? 'Loading...' : subj.label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Divider */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginBottom: '20px'
        }}>
          <div style={{ flex: 1, height: '3px', background: '#000' }} />
          <span style={{
            fontSize: '13px',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: '#000'
          }}>
            or type anything
          </span>
          <div style={{ flex: 1, height: '3px', background: '#000' }} />
        </div>

        {/* Custom subject input */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (customSubject.trim() && !isDisabled) {
              handleSelect(customSubject.trim());
            }
          }}
          style={{
            display: 'flex',
            gap: '12px'
          }}
        >
          <input
            type="text"
            value={customSubject}
            maxLength={50}
            onChange={(e) => setCustomSubject(e.target.value.replace(/[^a-zA-Z0-9 ,.\-']/g, ''))}
            placeholder="e.g. Geography, Music Theory, Python..."
            disabled={isDisabled}
            style={{
              flex: 1,
              padding: '14px 16px',
              border: '4px solid #000',
              background: '#fff',
              boxShadow: '3px 3px 0 #000',
              fontSize: '16px',
              fontWeight: 700,
              outline: 'none',
              fontFamily: 'system-ui, -apple-system, sans-serif'
            }}
          />
          <button
            type="submit"
            disabled={isDisabled || !customSubject.trim()}
            style={{
              padding: '14px 24px',
              border: '4px solid #000',
              background: isDisabled ? '#ddd' : '#FF6B6B',
              color: '#fff',
              boxShadow: isDisabled ? '2px 2px 0 #000' : '4px 4px 0 #000',
              cursor: isDisabled || !customSubject.trim() ? 'not-allowed' : 'pointer',
              fontSize: '16px',
              fontWeight: 900,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              transition: 'all 100ms ease-out',
              fontFamily: 'system-ui, -apple-system, sans-serif'
            }}
            onMouseDown={(e) => {
              if (!isDisabled && customSubject.trim()) {
                (e.currentTarget as HTMLElement).style.transform = 'translate(2px, 2px)';
                (e.currentTarget as HTMLElement).style.boxShadow = '2px 2px 0 #000';
              }
            }}
            onMouseUp={(e) => {
              (e.currentTarget as HTMLElement).style.transform = 'none';
              (e.currentTarget as HTMLElement).style.boxShadow = '4px 4px 0 #000';
            }}
          >
            {isDisabled && selectedSubject === customSubject.trim() ? 'Loading...' : 'Go'}
          </button>
        </form>

        {status === 'error' && (
          <div style={{
            marginTop: '16px',
            padding: '12px 16px',
            border: '3px solid #000',
            background: '#FF6B6B',
            color: '#fff',
            fontWeight: 700,
            fontSize: '14px',
            textTransform: 'uppercase'
          }}>
            Something went wrong. Try again.
          </div>
        )}
      </div>
    </div>
  );
};

export default SubjectSelector;
