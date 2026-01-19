import React, { useState, useEffect } from 'react';
import { ChevronDown, Check, X } from 'lucide-react';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface Video {
  video_id: string;
  title: string;
  language: string;
  channel: string;
  score: number;
  views: number;
  suggested_at: string;
}

interface QuestionWithVideos {
  question_id: string;
  question_text: string;
  suggested_videos_count: number;
  videos: Video[];
}

interface Stats {
  questions_with_suggested: number;
  total_suggested_videos: number;
  questions_with_approved: number;
  total_approved_videos: number;
}

const AdminVideoPanel: React.FC = () => {
  const [questions, setQuestions] = useState<QuestionWithVideos[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<string>>(new Set());
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('jwt_token');

      // Fetch suggested videos
      const videosResponse = await fetch(
        `${DASH_API_URL}/api/admin/videos/suggested?limit=50&offset=0`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!videosResponse.ok) {
        throw new Error('Failed to fetch suggested videos');
      }

      const videosData = await videosResponse.json();
      setQuestions(videosData);

      // Fetch statistics
      const statsResponse = await fetch(
        `${DASH_API_URL}/api/admin/videos/stats`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
    } catch (error) {
      console.error('Error fetching admin panel data:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleQuestion = (questionId: string) => {
    const newExpanded = new Set(expandedQuestions);
    if (newExpanded.has(questionId)) {
      newExpanded.delete(questionId);
    } else {
      newExpanded.add(questionId);
    }
    setExpandedQuestions(newExpanded);
  };

  const handleApprove = async (questionId: string, videoId: string) => {
    try {
      setActionInProgress(`${questionId}-${videoId}-approve`);
      const token = localStorage.getItem('jwt_token');

      const response = await fetch(
        `${DASH_API_URL}/api/videos/approve?question_id=${questionId}&video_id=${videoId}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to approve video');
      }

      // Refresh data
      await fetchData();
    } catch (error) {
      console.error('Error approving video:', error);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReject = async (questionId: string, videoId: string) => {
    try {
      setActionInProgress(`${questionId}-${videoId}-reject`);
      const token = localStorage.getItem('jwt_token');

      const response = await fetch(
        `${DASH_API_URL}/api/videos/reject?question_id=${questionId}&video_id=${videoId}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to reject video');
      }

      // Refresh data
      await fetchData();
    } catch (error) {
      console.error('Error rejecting video:', error);
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1
        style={{
          fontSize: '28px',
          fontWeight: 700,
          marginBottom: '24px',
          color: 'var(--neo-black)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        Video Approval Admin Panel
      </h1>

      {/* Statistics */}
      {stats && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginBottom: '32px',
          }}
        >
          <div
            style={{
              border: '5px solid var(--neo-black)',
              backgroundColor: 'var(--neo-yellow)',
              padding: '16px',
              boxShadow: '2px 2px 0 var(--neo-black)',
            }}
          >
            <p
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: 'var(--neo-black)',
                textTransform: 'uppercase',
                margin: '0 0 8px 0',
              }}
            >
              Suggested Videos
            </p>
            <p
              style={{
                fontSize: '24px',
                fontWeight: 900,
                color: 'var(--neo-black)',
                margin: 0,
              }}
            >
              {stats.total_suggested_videos}
            </p>
          </div>

          <div
            style={{
              border: '5px solid var(--neo-black)',
              backgroundColor: '#E8F5E9',
              padding: '16px',
              boxShadow: '2px 2px 0 var(--neo-black)',
            }}
          >
            <p
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: '#2E7D32',
                textTransform: 'uppercase',
                margin: '0 0 8px 0',
              }}
            >
              Approved Videos
            </p>
            <p
              style={{
                fontSize: '24px',
                fontWeight: 900,
                color: '#2E7D32',
                margin: 0,
              }}
            >
              {stats.total_approved_videos}
            </p>
          </div>

          <div
            style={{
              border: '5px solid var(--neo-black)',
              backgroundColor: '#F3E5F5',
              padding: '16px',
              boxShadow: '2px 2px 0 var(--neo-black)',
            }}
          >
            <p
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: '#6A1B9A',
                textTransform: 'uppercase',
                margin: '0 0 8px 0',
              }}
            >
              Questions Needing Videos
            </p>
            <p
              style={{
                fontSize: '24px',
                fontWeight: 900,
                color: '#6A1B9A',
                margin: 0,
              }}
            >
              {stats.questions_with_suggested}
            </p>
          </div>
        </div>
      )}

      {/* Questions List */}
      {loading ? (
        <div
          style={{
            textAlign: 'center',
            padding: '32px',
            border: '5px solid var(--neo-black)',
            backgroundColor: 'var(--neo-yellow)',
            boxShadow: '2px 2px 0 var(--neo-black)',
          }}
        >
          <p style={{ fontSize: '16px', fontWeight: 700, margin: 0 }}>
            Loading...
          </p>
        </div>
      ) : questions.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '32px',
            border: '5px solid var(--neo-black)',
            backgroundColor: '#E8F5E9',
            boxShadow: '2px 2px 0 var(--neo-black)',
          }}
        >
          <p style={{ fontSize: '16px', fontWeight: 700, color: '#2E7D32', margin: 0 }}>
            No videos waiting for approval
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {questions.map((question) => (
            <div
              key={question.question_id}
              style={{
                border: '5px solid var(--neo-black)',
                backgroundColor: 'var(--neo-bg)',
                boxShadow: '2px 2px 0 var(--neo-black)',
              }}
            >
              {/* Question Header */}
              <button
                onClick={() => toggleQuestion(question.question_id)}
                style={{
                  width: '100%',
                  padding: '16px',
                  backgroundColor: 'var(--neo-yellow)',
                  border: 'none',
                  borderBottom: '3px solid var(--neo-black)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  transition: 'all 0.2s ease',
                }}
                onMouseDown={(e) => {
                  (e.target as HTMLElement).style.boxShadow = 'inset 2px 2px 0 rgba(0,0,0,0.1)';
                }}
                onMouseUp={(e) => {
                  (e.target as HTMLElement).style.boxShadow = 'none';
                }}
              >
                <div style={{ flex: 1, textAlign: 'left' }}>
                  <p
                    style={{
                      fontSize: '14px',
                      fontWeight: 700,
                      color: 'var(--neo-black)',
                      textTransform: 'uppercase',
                      margin: '0 0 4px 0',
                      letterSpacing: '0.05em',
                    }}
                  >
                    {question.question_text || 'Question (no text available)'}
                  </p>
                  <p
                    style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: 'rgba(0,0,0,0.6)',
                      margin: 0,
                    }}
                  >
                    ID: {question.question_id}
                  </p>
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    flexShrink: 0,
                  }}
                >
                  <div
                    style={{
                      backgroundColor: 'var(--neo-black)',
                      color: 'var(--neo-yellow)',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 700,
                    }}
                  >
                    {question.suggested_videos_count}
                  </div>
                  <ChevronDown
                    size={20}
                    style={{
                      transform: expandedQuestions.has(question.question_id)
                        ? 'rotate(180deg)'
                        : 'rotate(0deg)',
                      transition: 'transform 0.2s ease',
                    }}
                  />
                </div>
              </button>

              {/* Videos List */}
              {expandedQuestions.has(question.question_id) && (
                <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {question.videos.map((video) => (
                    <div
                      key={video.video_id}
                      style={{
                        border: '3px solid var(--neo-black)',
                        backgroundColor: '#F9F9F9',
                        padding: '12px',
                        boxShadow: '1px 1px 0 var(--neo-black)',
                      }}
                    >
                      <div style={{ marginBottom: '8px' }}>
                        <p
                          style={{
                            fontSize: '12px',
                            fontWeight: 700,
                            color: 'var(--neo-black)',
                            textTransform: 'uppercase',
                            margin: '0 0 4px 0',
                            letterSpacing: '0.05em',
                          }}
                        >
                          {video.title}
                        </p>
                        <p
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            color: 'rgba(0,0,0,0.6)',
                            margin: '0 0 2px 0',
                          }}
                        >
                          Channel: {video.channel}
                        </p>
                        <p
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            color: 'rgba(0,0,0,0.6)',
                            margin: 0,
                          }}
                        >
                          Language: {video.language} | ID: {video.video_id}
                        </p>
                      </div>

                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => handleApprove(question.question_id, video.video_id)}
                          disabled={actionInProgress === `${question.question_id}-${video.video_id}-approve`}
                          style={{
                            flex: 1,
                            padding: '8px 12px',
                            backgroundColor:
                              actionInProgress === `${question.question_id}-${video.video_id}-approve`
                                ? 'rgba(46, 125, 50, 0.5)'
                                : '#E8F5E9',
                            color: '#2E7D32',
                            border: '2px solid #2E7D32',
                            fontWeight: 700,
                            fontSize: '11px',
                            textTransform: 'uppercase',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '4px',
                            transition: 'all 0.2s ease',
                          }}
                          onMouseDown={(e) => {
                            if (
                              actionInProgress !== `${question.question_id}-${video.video_id}-approve`
                            ) {
                              (e.target as HTMLElement).style.boxShadow = 'inset 1px 1px 0 #2E7D32';
                            }
                          }}
                          onMouseUp={(e) => {
                            (e.target as HTMLElement).style.boxShadow = 'none';
                          }}
                        >
                          <Check size={14} />
                          Approve
                        </button>

                        <button
                          onClick={() => handleReject(question.question_id, video.video_id)}
                          disabled={actionInProgress === `${question.question_id}-${video.video_id}-reject`}
                          style={{
                            flex: 1,
                            padding: '8px 12px',
                            backgroundColor:
                              actionInProgress === `${question.question_id}-${video.video_id}-reject`
                                ? 'rgba(198, 40, 40, 0.5)'
                                : '#FFEBEE',
                            color: '#C62828',
                            border: '2px solid #C62828',
                            fontWeight: 700,
                            fontSize: '11px',
                            textTransform: 'uppercase',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '4px',
                            transition: 'all 0.2s ease',
                          }}
                          onMouseDown={(e) => {
                            if (actionInProgress !== `${question.question_id}-${video.video_id}-reject`) {
                              (e.target as HTMLElement).style.boxShadow = 'inset 1px 1px 0 #C62828';
                            }
                          }}
                          onMouseUp={(e) => {
                            (e.target as HTMLElement).style.boxShadow = 'none';
                          }}
                        >
                          <X size={14} />
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AdminVideoPanel;
