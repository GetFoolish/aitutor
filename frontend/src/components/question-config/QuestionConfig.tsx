import React, { useState } from 'react';

const SUBJECTS = [
  { id: 'math', label: '🔢 Math', color: '#FFD93D' },
  { id: 'english', label: '📚 English', color: '#A8E6CF' },
  { id: 'science', label: '🔬 Science', color: '#88D8F7' },
  { id: 'history', label: '🏛️ History', color: '#FFB366' },
  { id: 'art', label: '🎨 Art', color: '#DDA0DD' },
];

const GRADES = [
  { id: 'K-2', label: 'K-2', desc: 'ages 5-7' },
  { id: '3-5', label: '3-5', desc: 'ages 8-10' },
  { id: '6-8', label: '6-8', desc: 'ages 11-13' },
  { id: '9-12', label: '9-12', desc: 'ages 14-18' },
];

const LANGUAGES = [
  { id: 'en', label: '🇬🇧 English' },
  { id: 'es', label: '🇪🇸 Español' },
  { id: 'fr', label: '🇫🇷 Français' },
  { id: 'de', label: '🇩🇪 Deutsch' },
  { id: 'zh', label: '🇨🇳 中文' },
  { id: 'hi', label: '🇮🇳 हिन्दी' },
  { id: 'ar', label: '🇸🇦 العربية' },
  { id: 'pt', label: '🇧🇷 Português' },
  { id: 'ja', label: '🇯🇵 日本語' },
  { id: 'ko', label: '🇰🇷 한국어' },
];

interface QuestionConfigProps {
  onStart: (config: { subject: string; grade: string; language: string; count: number; topic: string }) => void;
  isLoading?: boolean;
}

const QuestionConfig: React.FC<QuestionConfigProps> = ({ onStart, isLoading }) => {
  const [subject, setSubject] = useState('math');
  const [grade, setGrade] = useState('3-5');
  const [language, setLanguage] = useState('en');
  const [count, setCount] = useState(10);
  const [topic, setTopic] = useState('');

  const handleStart = () => {
    onStart({ subject, grade, language, count, topic: topic.trim() || subject });
  };

  return (
    <div style={{
      maxWidth: '600px',
      margin: '0 auto',
      padding: '24px',
      fontFamily: 'Space Grotesk, sans-serif',
    }}>
      <h2 style={{
        fontSize: '24px',
        fontWeight: 800,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: '24px',
        color: 'var(--neo-black)',
      }}>
        📝 Question Setup
      </h2>

      {/* Topic Input (free text) */}
      <div style={{ marginBottom: '24px' }}>
        <label style={{
          display: 'block',
          fontSize: '14px',
          fontWeight: 700,
          textTransform: 'uppercase',
          marginBottom: '12px',
          color: 'var(--neo-black)',
        }}>
          What do you want to learn? 🎯
        </label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. fractions, dinosaurs, world war 2, spanish verbs..."
          style={{
            width: '100%',
            padding: '14px 16px',
            border: '3px solid var(--neo-black)',
            backgroundColor: '#fff',
            fontWeight: 600,
            fontSize: '16px',
            boxShadow: '3px 3px 0 var(--neo-black)',
            outline: 'none',
          }}
        />
        <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.7 }}>
          Type anything! We'll generate questions about it.
        </div>
      </div>

      {/* Subject Selection */}
      <div style={{ marginBottom: '24px' }}>
        <label style={{
          display: 'block',
          fontSize: '14px',
          fontWeight: 700,
          textTransform: 'uppercase',
          marginBottom: '12px',
          color: 'var(--neo-black)',
        }}>
          Subject Area {topic && '(optional)'}
        </label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {SUBJECTS.map((s) => (
            <button
              key={s.id}
              onClick={() => setSubject(s.id)}
              style={{
                padding: '12px 16px',
                border: '3px solid var(--neo-black)',
                backgroundColor: subject === s.id ? s.color : '#fff',
                fontWeight: 700,
                fontSize: '14px',
                cursor: 'pointer',
                boxShadow: subject === s.id 
                  ? '0 0 0 var(--neo-black)' 
                  : '3px 3px 0 var(--neo-black)',
                transform: subject === s.id ? 'translate(3px, 3px)' : 'none',
                transition: 'all 0.1s',
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grade Selection */}
      <div style={{ marginBottom: '24px' }}>
        <label style={{
          display: 'block',
          fontSize: '14px',
          fontWeight: 700,
          textTransform: 'uppercase',
          marginBottom: '12px',
          color: 'var(--neo-black)',
        }}>
          Grade Level
        </label>
        <div style={{ display: 'flex', gap: '8px' }}>
          {GRADES.map((g) => (
            <button
              key={g.id}
              onClick={() => setGrade(g.id)}
              style={{
                padding: '12px 20px',
                border: '3px solid var(--neo-black)',
                backgroundColor: grade === g.id ? '#FFD93D' : '#fff',
                fontWeight: 700,
                fontSize: '16px',
                cursor: 'pointer',
                boxShadow: grade === g.id 
                  ? '0 0 0 var(--neo-black)' 
                  : '3px 3px 0 var(--neo-black)',
                transform: grade === g.id ? 'translate(3px, 3px)' : 'none',
                transition: 'all 0.1s',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              <span>{g.label}</span>
              <span style={{ fontSize: '10px', opacity: 0.7 }}>{g.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Language Selection */}
      <div style={{ marginBottom: '24px' }}>
        <label style={{
          display: 'block',
          fontSize: '14px',
          fontWeight: 700,
          textTransform: 'uppercase',
          marginBottom: '12px',
          color: 'var(--neo-black)',
        }}>
          Language
        </label>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          style={{
            padding: '12px 16px',
            border: '3px solid var(--neo-black)',
            backgroundColor: '#fff',
            fontWeight: 600,
            fontSize: '16px',
            cursor: 'pointer',
            boxShadow: '3px 3px 0 var(--neo-black)',
            minWidth: '200px',
          }}
        >
          {LANGUAGES.map((l) => (
            <option key={l.id} value={l.id}>{l.label}</option>
          ))}
        </select>
      </div>

      {/* Question Count */}
      <div style={{ marginBottom: '32px' }}>
        <label style={{
          display: 'block',
          fontSize: '14px',
          fontWeight: 700,
          textTransform: 'uppercase',
          marginBottom: '12px',
          color: 'var(--neo-black)',
        }}>
          Number of Questions: {count}
        </label>
        <input
          type="range"
          min="5"
          max="20"
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
          style={{
            width: '100%',
            cursor: 'pointer',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', opacity: 0.7 }}>
          <span>5</span>
          <span>20</span>
        </div>
      </div>

      {/* Start Button */}
      <button
        onClick={handleStart}
        disabled={isLoading}
        style={{
          width: '100%',
          padding: '16px 24px',
          border: '4px solid var(--neo-black)',
          backgroundColor: '#4ADE80',
          fontWeight: 800,
          fontSize: '18px',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          cursor: isLoading ? 'wait' : 'pointer',
          boxShadow: '4px 4px 0 var(--neo-black)',
          transition: 'all 0.1s',
          opacity: isLoading ? 0.7 : 1,
        }}
        onMouseDown={(e) => {
          if (!isLoading) {
            e.currentTarget.style.transform = 'translate(4px, 4px)';
            e.currentTarget.style.boxShadow = '0 0 0 var(--neo-black)';
          }
        }}
        onMouseUp={(e) => {
          e.currentTarget.style.transform = 'none';
          e.currentTarget.style.boxShadow = '4px 4px 0 var(--neo-black)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'none';
          e.currentTarget.style.boxShadow = '4px 4px 0 var(--neo-black)';
        }}
      >
        {isLoading ? '⏳ Loading...' : '🚀 Start Learning'}
      </button>

      {/* Preview */}
      <div style={{
        marginTop: '24px',
        padding: '16px',
        border: '2px dashed var(--neo-black)',
        backgroundColor: '#f5f5f5',
        fontSize: '14px',
      }}>
        <strong>Preview:</strong> {count} questions about {topic ? `"${topic}"` : SUBJECTS.find(s => s.id === subject)?.label} 
        {' '}for grades {grade} in {LANGUAGES.find(l => l.id === language)?.label}
      </div>
    </div>
  );
};

export default QuestionConfig;
