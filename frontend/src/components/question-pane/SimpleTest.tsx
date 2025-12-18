/**
 * Simple Test Page - Minimal Athena Test
 *
 * A very simple test to verify basic rendering works.
 */

import React, { useState, useEffect } from 'react';
import { fetchQuestions, fetchQuestionById, checkHealth } from '../../services/athenaAPI';
import type { AthenaItem } from '../../services/athenaAPI';

export const SimpleTest: React.FC = () => {
  const [questions, setQuestions] = useState<AthenaItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [objectId, setObjectId] = useState('');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  // Check backend status
  useEffect(() => {
    checkHealth().then(healthy => {
      setBackendStatus(healthy ? 'online' : 'offline');
    });
  }, []);

  // Load questions
  useEffect(() => {
    if (backendStatus === 'online') {
      loadQuestions();
    }
  }, [backendStatus]);

  const loadQuestions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchQuestions(5);
      if (data.length > 0) {
        setQuestions(data);
      } else {
        setError('No questions returned');
      }
    } catch (err) {
      setError('Failed to fetch questions');
    } finally {
      setIsLoading(false);
    }
  };

  const loadById = async () => {
    if (!objectId.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchQuestionById(objectId.trim());
      if (data) {
        setQuestions([data]);
        setCurrentIndex(0);
      } else {
        setError('Question not found');
      }
    } catch (err) {
      setError('Failed to fetch question');
    } finally {
      setIsLoading(false);
    }
  };

  const currentQuestion = questions[currentIndex];

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      padding: '20px',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <div style={{ maxWidth: '900px', margin: '0 auto' }}>
        {/* Header */}
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '20px' }}>
          Athena Question Renderer Test
        </h1>

        {/* Backend Status */}
        <div style={{
          padding: '10px 15px',
          marginBottom: '20px',
          borderRadius: '8px',
          backgroundColor: backendStatus === 'online' ? '#d4edda' : backendStatus === 'offline' ? '#f8d7da' : '#fff3cd',
          border: `1px solid ${backendStatus === 'online' ? '#c3e6cb' : backendStatus === 'offline' ? '#f5c6cb' : '#ffeaa7'}`
        }}>
          <strong>Backend Status:</strong>{' '}
          {backendStatus === 'checking' && '⏳ Checking...'}
          {backendStatus === 'online' && '✅ Online (localhost:8010)'}
          {backendStatus === 'offline' && '❌ Offline - Start backend with: cd services/athenaAPI && python run_backend.py'}
        </div>

        {/* ObjectID Input */}
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input
            type="text"
            placeholder="Enter MongoDB ObjectID..."
            value={objectId}
            onChange={(e) => setObjectId(e.target.value)}
            style={{
              flex: 1,
              padding: '10px 15px',
              fontSize: '16px',
              border: '2px solid #333',
              borderRadius: '8px'
            }}
          />
          <button
            onClick={loadById}
            style={{
              padding: '10px 20px',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            Load
          </button>
          <button
            onClick={loadQuestions}
            style={{
              padding: '10px 20px',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            Random
          </button>
        </div>

        {/* Main Content */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          border: '3px solid #333',
          padding: '20px',
          boxShadow: '4px 4px 0 #333'
        }}>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳</div>
              <p>Loading questions...</p>
            </div>
          ) : error ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#c00' }}>
              <div style={{ fontSize: '24px', marginBottom: '10px' }}>❌</div>
              <p>{error}</p>
            </div>
          ) : currentQuestion ? (
            <div>
              {/* Question Info */}
              <div style={{
                backgroundColor: '#f0f0f0',
                padding: '10px 15px',
                borderRadius: '8px',
                marginBottom: '20px',
                fontSize: '14px'
              }}>
                <strong>ID:</strong> {currentQuestion._id} |{' '}
                <strong>Slug:</strong> {currentQuestion.slug || 'N/A'} |{' '}
                <strong>Widgets:</strong> {currentQuestion.widgetTypes?.join(', ') || 'none'}
              </div>

              {/* Question Content */}
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>
                  Question Content:
                </h3>
                <div style={{
                  padding: '15px',
                  backgroundColor: '#fafafa',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'monospace',
                  fontSize: '14px'
                }}>
                  {currentQuestion.question.content}
                </div>
              </div>

              {/* Widgets */}
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>
                  Widgets ({Object.keys(currentQuestion.question.widgets).length}):
                </h3>
                {Object.entries(currentQuestion.question.widgets).map(([id, widget]) => (
                  <div key={id} style={{
                    padding: '10px 15px',
                    backgroundColor: '#e8f4fd',
                    borderRadius: '8px',
                    marginBottom: '10px',
                    border: '1px solid #b3d9f7'
                  }}>
                    <strong>{id}</strong> - Type: <code>{widget.type}</code>
                  </div>
                ))}
              </div>

              {/* Hints */}
              {currentQuestion.hints.length > 0 && (
                <div style={{ marginBottom: '20px' }}>
                  <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>
                    Hints ({currentQuestion.hints.length}):
                  </h3>
                  {currentQuestion.hints.map((hint, i) => (
                    <div key={i} style={{
                      padding: '10px 15px',
                      backgroundColor: '#fff8e1',
                      borderRadius: '8px',
                      marginBottom: '10px',
                      border: '1px solid #ffcc80'
                    }}>
                      <strong>Hint {i + 1}:</strong> {hint.content.substring(0, 100)}...
                    </div>
                  ))}
                </div>
              )}

              {/* Answer Area */}
              <div style={{
                padding: '10px 15px',
                backgroundColor: '#f3e5f5',
                borderRadius: '8px',
                border: '1px solid #ce93d8'
              }}>
                <strong>Answer Area:</strong>{' '}
                Calculator: {currentQuestion.answerArea.calculator ? '✅' : '❌'} |{' '}
                Periodic Table: {currentQuestion.answerArea.periodicTable ? '✅' : '❌'}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <p>No question loaded</p>
            </div>
          )}
        </div>

        {/* Navigation */}
        {questions.length > 1 && (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '10px',
            marginTop: '20px'
          }}>
            <button
              onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
              disabled={currentIndex === 0}
              style={{
                padding: '10px 20px',
                backgroundColor: currentIndex === 0 ? '#ccc' : '#333',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontWeight: 'bold',
                cursor: currentIndex === 0 ? 'not-allowed' : 'pointer'
              }}
            >
              ← Previous
            </button>
            <span style={{ padding: '10px 20px' }}>
              {currentIndex + 1} / {questions.length}
            </span>
            <button
              onClick={() => setCurrentIndex(Math.min(questions.length - 1, currentIndex + 1))}
              disabled={currentIndex === questions.length - 1}
              style={{
                padding: '10px 20px',
                backgroundColor: currentIndex === questions.length - 1 ? '#ccc' : '#333',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontWeight: 'bold',
                cursor: currentIndex === questions.length - 1 ? 'not-allowed' : 'pointer'
              }}
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimpleTest;
