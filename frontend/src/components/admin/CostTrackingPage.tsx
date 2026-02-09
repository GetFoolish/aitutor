import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import cn from 'classnames';
import { DollarSign, TrendingUp, Activity, Clock, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { apiUtils } from '../../lib/api-utils';

const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

interface Analytics {
  total_sessions: number;
  avg_cost: number;
  total_cost: number;
}

interface SessionCost {
  session_id: string;
  user_id: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  total_estimated_cost: number;
  api_calls: {
    tutor_api: {
      count: number;
      prompt_tokens: number;  // Fresh (non-cached) tokens
      cached_content_tokens?: number;  // Cached tokens (90% discount)
      output_tokens: number;
      thinking_tokens?: number;  // Thinking tokens
      total_tokens: number;
      text_input_tokens?: number;  // Modality breakdown
      audio_input_tokens?: number;
      video_input_tokens?: number;
    };
    teaching_assistant: {
      count: number;
      input_tokens?: number;
      output_tokens?: number;
      total_tokens?: number;
    };
    dash_api: {
      count: number;
    };
  };
}

const CostTrackingPage: React.FC = () => {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [sessions, setSessions] = useState<SessionCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch analytics
      const analyticsResponse = await apiUtils.get(`${TEACHING_ASSISTANT_API_URL}/cost/analytics`);
      if (analyticsResponse.ok) {
        const analyticsData = await analyticsResponse.json();
        setAnalytics(analyticsData);
      }

      // Fetch user sessions
      const sessionsResponse = await apiUtils.get(`${TEACHING_ASSISTANT_API_URL}/cost/user?limit=50`);
      if (sessionsResponse.ok) {
        const sessionsData = await sessionsResponse.json();
        setSessions(sessionsData.sessions || []);
      }
    } catch (err: any) {
      console.error('Error fetching cost tracking data:', err);
      setError(err?.message || 'Failed to load cost tracking data');
    } finally {
      setLoading(false);
    }
  };

  const toggleSession = (sessionId: string) => {
    const newExpanded = new Set(expandedSessions);
    if (newExpanded.has(sessionId)) {
      newExpanded.delete(sessionId);
    } else {
      newExpanded.add(sessionId);
    }
    setExpandedSessions(newExpanded);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4,
      maximumFractionDigits: 4,
    }).format(amount);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Active';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  const formatDuration = (startedAt: string, endedAt: string | null) => {
    if (!endedAt) return 'Ongoing';
    try {
      const start = new Date(startedAt);
      const end = new Date(endedAt);
      const diffMs = end.getTime() - start.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const mins = diffMins % 60;
      if (diffHours > 0) {
        return `${diffHours}h ${mins}m`;
      }
      return `${diffMins}m`;
    } catch {
      return 'N/A';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
            {[1, 2, 3].map((i) => (
              <Card
                key={i}
                className={cn(
                  "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
                  "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
                )}
              >
                <CardHeader>
                  <Skeleton className="h-6 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-24" />
                </CardContent>
              </Card>
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8 flex items-center justify-center">
        <Card
          className={cn(
            "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
            "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] max-w-md"
          )}
        >
          <CardContent className="pt-6">
            <p className="text-center text-red-600 dark:text-red-400 font-bold">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <h1
          className={cn(
            "text-3xl md:text-4xl font-black mb-6 md:mb-8 text-black dark:text-white uppercase tracking-wide",
            "border-b-[3px] border-black dark:border-white pb-4"
          )}
        >
          Cost Tracking
        </h1>

        {/* Analytics Cards */}
        {analytics && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
            <Card
              className={cn(
                "border-[3px] border-black dark:border-white bg-[#FFD93D]",
                "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
              )}
            >
              <CardHeader className={cn("border-b-[2px] border-black dark:border-white")}>
                <CardTitle className={cn("text-lg font-black text-black uppercase flex items-center gap-2")}>
                  <Activity className="w-5 h-5" />
                  Total Sessions
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <p className={cn("text-3xl font-black text-black")}>
                  {analytics.total_sessions}
                </p>
              </CardContent>
            </Card>

            <Card
              className={cn(
                "border-[3px] border-black dark:border-white bg-[#C4B5FD]",
                "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
              )}
            >
              <CardHeader className={cn("border-b-[2px] border-black dark:border-white")}>
                <CardTitle className={cn("text-lg font-black text-black uppercase flex items-center gap-2")}>
                  <TrendingUp className="w-5 h-5" />
                  Average Cost
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <p className={cn("text-3xl font-black text-black")}>
                  {formatCurrency(analytics.avg_cost)}
                </p>
              </CardContent>
            </Card>

            <Card
              className={cn(
                "border-[3px] border-black dark:border-white bg-[#FFD93D]",
                "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
              )}
            >
              <CardHeader className={cn("border-b-[2px] border-black dark:border-white")}>
                <CardTitle className={cn("text-lg font-black text-black uppercase flex items-center gap-2")}>
                  <DollarSign className="w-5 h-5" />
                  Total Cost
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <p className={cn("text-3xl font-black text-black")}>
                  {formatCurrency(analytics.total_cost)}
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Sessions List */}
        <Card
          className={cn(
            "border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
            "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
          )}
        >
          <CardHeader className={cn("border-b-[2px] border-black dark:border-white bg-[#C4B5FD]")}>
            <CardTitle className={cn("text-xl font-black text-black uppercase")}>
              Session History
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {sessions.length === 0 ? (
              <div className="text-center py-8">
                <p className={cn("text-base font-bold text-black dark:text-white")}>
                  No sessions found
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {sessions.map((session) => {
                  const isExpanded = expandedSessions.has(session.session_id);
                  return (
                    <div
                      key={session.session_id}
                      className={cn(
                        "border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
                        "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
                      )}
                    >
                      <button
                        onClick={() => toggleSession(session.session_id)}
                        className={cn(
                          "w-full p-4 text-left flex items-center justify-between gap-4",
                          "bg-[#FFD93D] hover:bg-[#FFD93D] transition-all",
                          "border-b-[2px] border-black dark:border-white"
                        )}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <Clock className="w-4 h-4 text-black" />
                            <p className={cn("text-sm font-black text-black uppercase truncate")}>
                              {formatDate(session.started_at)}
                            </p>
                            <span
                              className={cn(
                                "px-2 py-0.5 text-xs font-black uppercase",
                                session.status === 'active'
                                  ? "bg-[#C4B5FD] text-black"
                                  : "bg-[#E8F5E9] text-black"
                              )}
                            >
                              {session.status}
                            </span>
                          </div>
                          <div className="flex items-center gap-4">
                            <p className={cn("text-lg font-black text-black")}>
                              {formatCurrency(session.total_estimated_cost)}
                            </p>
                            <p className={cn("text-xs font-bold text-black")}>
                              Duration: {formatDuration(session.started_at, session.ended_at)}
                            </p>
                          </div>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5 text-black flex-shrink-0" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-black flex-shrink-0" />
                        )}
                      </button>

                      {isExpanded && (
                        <div className="p-4 space-y-3">
                          <div>
                            <label className={cn("text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block")}>
                              Session ID
                            </label>
                            <p className={cn("text-sm font-bold text-black dark:text-white p-2 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]")}>
                              {session.session_id}
                            </p>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                              <label className={cn("text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block")}>
                                Tutor API
                              </label>
                              <div className={cn("p-2 border-[2px] border-black dark:border-white bg-[#FFD93D]")}>
                                <p className={cn("text-xs font-bold text-black mb-1")}>
                                  Calls: {session.api_calls.tutor_api.count}
                                </p>
                                <p className={cn("text-xs font-bold text-black mb-1")}>
                                  Total: {session.api_calls.tutor_api.total_tokens.toLocaleString()}
                                </p>
                                <p className={cn("text-xs font-bold text-black mb-1")}>
                                  Fresh Input: {session.api_calls.tutor_api.prompt_tokens.toLocaleString()}
                                </p>
                                {session.api_calls.tutor_api.cached_content_tokens !== undefined && session.api_calls.tutor_api.cached_content_tokens > 0 && (
                                  <p className={cn("text-xs font-bold text-green-700 mb-1")}>
                                    Cached: {session.api_calls.tutor_api.cached_content_tokens.toLocaleString()} (90% off)
                                  </p>
                                )}
                                <p className={cn("text-xs font-bold text-black mb-1")}>
                                  Output: {session.api_calls.tutor_api.output_tokens.toLocaleString()}
                                </p>
                                {session.api_calls.tutor_api.thinking_tokens !== undefined && session.api_calls.tutor_api.thinking_tokens > 0 && (
                                  <p className={cn("text-xs font-bold text-purple-700 mb-1")}>
                                    Thinking: {session.api_calls.tutor_api.thinking_tokens.toLocaleString()}
                                  </p>
                                )}
                                {(session.api_calls.tutor_api.text_input_tokens !== undefined || 
                                  session.api_calls.tutor_api.audio_input_tokens !== undefined || 
                                  session.api_calls.tutor_api.video_input_tokens !== undefined) && (
                                  <div className={cn("mt-1 pt-1 border-t border-black dark:border-white")}>
                                    <p className={cn("text-xs font-black text-black mb-0.5")}>Modality:</p>
                                    {session.api_calls.tutor_api.text_input_tokens !== undefined && session.api_calls.tutor_api.text_input_tokens > 0 && (
                                      <p className={cn("text-xs font-bold text-black")}>
                                        Text: {session.api_calls.tutor_api.text_input_tokens.toLocaleString()}
                                      </p>
                                    )}
                                    {session.api_calls.tutor_api.audio_input_tokens !== undefined && session.api_calls.tutor_api.audio_input_tokens > 0 && (
                                      <p className={cn("text-xs font-bold text-black")}>
                                        Audio: {session.api_calls.tutor_api.audio_input_tokens.toLocaleString()}
                                      </p>
                                    )}
                                    {session.api_calls.tutor_api.video_input_tokens !== undefined && session.api_calls.tutor_api.video_input_tokens > 0 && (
                                      <p className={cn("text-xs font-bold text-black")}>
                                        Video: {session.api_calls.tutor_api.video_input_tokens.toLocaleString()}
                                      </p>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>

                            <div>
                              <label className={cn("text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block")}>
                                Teaching Assistant
                              </label>
                              <div className={cn("p-2 border-[2px] border-black dark:border-white bg-[#C4B5FD]")}>
                                <p className={cn("text-xs font-bold text-black mb-1")}>
                                  Calls: {session.api_calls.teaching_assistant.count}
                                </p>
                                {session.api_calls.teaching_assistant.total_tokens !== undefined && session.api_calls.teaching_assistant.total_tokens > 0 && (
                                  <>
                                    <p className={cn("text-xs font-bold text-black mb-1")}>
                                      Total: {session.api_calls.teaching_assistant.total_tokens.toLocaleString()}
                                    </p>
                                    <p className={cn("text-xs font-bold text-black mb-1")}>
                                      Input: {(session.api_calls.teaching_assistant.input_tokens || 0).toLocaleString()}
                                    </p>
                                    <p className={cn("text-xs font-bold text-black")}>
                                      Output: {(session.api_calls.teaching_assistant.output_tokens || 0).toLocaleString()}
                                    </p>
                                  </>
                                )}
                              </div>
                            </div>

                            <div>
                              <label className={cn("text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block")}>
                                DASH API
                              </label>
                              <div className={cn("p-2 border-[2px] border-black dark:border-white bg-[#E8F5E9]")}>
                                <p className={cn("text-xs font-bold text-black")}>
                                  Calls: {session.api_calls.dash_api.count}
                                </p>
                              </div>
                            </div>
                          </div>

                          <div>
                              <label className={cn("text-xs font-black uppercase tracking-wide text-black dark:text-white mb-1 block")}>
                                Timeline
                              </label>
                              <div className={cn("p-2 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]")}>
                                <p className={cn("text-xs font-bold text-black dark:text-white mb-1")}>
                                  Started: {formatDate(session.started_at)}
                                </p>
                                <p className={cn("text-xs font-bold text-black dark:text-white")}>
                                  Ended: {formatDate(session.ended_at)}
                                </p>
                              </div>
                            </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CostTrackingPage;


