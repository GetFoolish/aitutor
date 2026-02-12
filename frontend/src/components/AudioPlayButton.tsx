import React, { useEffect, useCallback, useState } from 'react';
import { Volume2 } from 'lucide-react';

/**
 * Detect if question text references listening/audio, extract the target word(s).
 * Returns null if no audio keyword found.
 */
export function extractAudioWord(questionContent: string): string | null {
  if (!questionContent) return null;
  // Match: "listen ... 'word'" or "hear ... 'word'" or "say ... 'word'"
  // Handles both straight quotes and curly quotes
  const match = questionContent.match(
    /(?:listen|hear|say)\b[\s\S]*?[''']([^''']+)[''']/i
  );
  return match ? match[1].trim() : null;
}

interface AudioPlayButtonProps {
  word: string;
  autoPlay?: boolean;
}

const AudioPlayButton: React.FC<AudioPlayButtonProps> = ({ word, autoPlay = true }) => {
  const [speaking, setSpeaking] = useState(false);

  const speak = useCallback(() => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.rate = 0.75;
    utterance.pitch = 1.0;
    utterance.lang = 'en-US';
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }, [word]);

  useEffect(() => {
    if (autoPlay && word) {
      // Small delay to let the question render first
      const timer = setTimeout(speak, 500);
      return () => {
        clearTimeout(timer);
        // Cancel any in-progress speech on unmount or word change
        window.speechSynthesis?.cancel();
      };
    }
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, [word, autoPlay, speak]);

  return (
    <button
      onClick={speak}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '10px',
        padding: '12px 20px',
        backgroundColor: speaking ? '#4CAF50' : '#6C63FF',
        color: '#FFFFFF',
        border: '4px solid #000000',
        fontWeight: 800,
        fontSize: '16px',
        cursor: 'pointer',
        boxShadow: '3px 3px 0px 0px #000000',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        transition: 'all 0.1s ease-out',
      }}
      onMouseDown={(e) => {
        (e.target as HTMLElement).style.boxShadow = '1px 1px 0px 0px #000000';
        (e.target as HTMLElement).style.transform = 'translate(2px, 2px)';
      }}
      onMouseUp={(e) => {
        (e.target as HTMLElement).style.boxShadow = '3px 3px 0px 0px #000000';
        (e.target as HTMLElement).style.transform = 'translate(0, 0)';
      }}
      onMouseLeave={(e) => {
        (e.target as HTMLElement).style.boxShadow = '3px 3px 0px 0px #000000';
        (e.target as HTMLElement).style.transform = 'translate(0, 0)';
      }}
      title={`Click to hear "${word}"`}
    >
      <Volume2 size={22} style={{ animation: speaking ? 'pulse-speaker 0.6s ease-in-out infinite' : 'none' }} />
      {speaking ? 'Playing...' : `Listen: "${word}"`}
      <style>{`
        @keyframes pulse-speaker {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </button>
  );
};

export default AudioPlayButton;
