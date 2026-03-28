/**
 * ClassroomPage — OpenMAIC multi-agent classroom integration (FOO-37).
 *
 * Provides three session modes:
 *   • Q&A       — user asks questions, teacher agent answers
 *   • Discussion — agents discuss a topic with proactive initiation
 *   • Debate    — agents take opposing stances on the topic
 *
 * The whiteboard is shown as an embedded iframe from OpenMAIC (port 3333)
 * when a classroom ID is available, otherwise a lightweight stub.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useParams, useHistory } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { AgentAvatarBar } from './AgentAvatarBar';
import { ClassroomChatMessage } from './ClassroomChatMessage';
import { useClassroomChat } from './useClassroomChat';
import type { SessionMode, TutoringAgent } from './types';
import {
  MessageSquare,
  Users,
  Swords,
  Send,
  StopCircle,
  Maximize2,
  Minimize2,
  ArrowLeft,
  Play,
  PenLine,
} from 'lucide-react';

const TA_API_URL =
  (import.meta as any).env?.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';
const OPENMAIC_URL =
  (import.meta as any).env?.VITE_OPENMAIC_URL || 'http://localhost:3333';

// Default tutoring agents (used if backend call fails)
const DEFAULT_TUTORING_AGENTS: TutoringAgent[] = [
  {
    id: 'tutor-teacher',
    name: 'Ms. Aria',
    role: 'teacher',
    persona:
      'You are Ms. Aria, a warm and patient math teacher. Explain step by step, use whiteboard for equations. Keep explanations clear and engaging.',
    avatar: '/avatars/teacher.png',
    color: '#3b82f6',
    allowedActions: ['wb_open', 'wb_draw_latex', 'wb_draw_text', 'spotlight'],
    priority: 10,
  },
  {
    id: 'tutor-student-1',
    name: 'Jamie',
    role: 'student',
    persona:
      'You are Jamie, a curious student. Ask clarifying questions when confused. Keep responses short (1-3 sentences).',
    avatar: '/avatars/student1.png',
    color: '#10b981',
    allowedActions: [],
    priority: 5,
  },
  {
    id: 'tutor-student-2',
    name: 'Sam',
    role: 'student',
    persona:
      'You are Sam, a diligent student who summarises what the teacher says in your own words. Keep responses short (1-3 sentences).',
    avatar: '/avatars/student2.png',
    color: '#f59e0b',
    allowedActions: [],
    priority: 4,
  },
];

export default function ClassroomPage() {
  const { classroomId } = useParams<{ classroomId?: string }>();
  const history = useHistory();

  const [agents, setAgents] = useState<TutoringAgent[]>(DEFAULT_TUTORING_AGENTS);
  const [mode, setMode] = useState<SessionMode>('qa');
  const [inputText, setInputText] = useState('');
  const [discussionTopic, setDiscussionTopic] = useState('');
  const [showWhiteboard, setShowWhiteboard] = useState(false);
  const [classroomContext, setClassroomContext] = useState<{
    topic?: string;
    scenes?: unknown[];
    stage?: unknown;
  }>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages,
    isStreaming,
    speakingAgentId,
    thinkingStage,
    isCueUser,
    whiteboardActions,
    sendMessage,
    startDiscussion,
    stop,
    clearMessages,
  } = useClassroomChat({ agents, mode, classroomContext });

  // Load tutoring agents from backend
  useEffect(() => {
    fetch(`${TA_API_URL}/api/classroom/agents/tutoring`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('auth_token') ?? ''}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.agents?.length) setAgents(data.agents);
      })
      .catch(() => {
        // use defaults
      });
  }, []);

  // Load classroom context if classroomId provided
  useEffect(() => {
    if (!classroomId) return;
    fetch(`${TA_API_URL}/api/classroom/${classroomId}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('auth_token') ?? ''}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.classroom) {
          setClassroomContext({
            topic: data.classroom.stage?.title,
            scenes: data.classroom.scenes,
            stage: data.classroom.stage,
          });
        }
      })
      .catch(() => {});
  }, [classroomId]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle whiteboard actions: auto-open whiteboard when agent uses it
  useEffect(() => {
    if (whiteboardActions.length > 0) {
      setShowWhiteboard(true);
    }
  }, [whiteboardActions]);

  const handleSend = () => {
    const text = inputText.trim();
    if (!text || isStreaming) return;
    setInputText('');
    sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStartDiscussion = () => {
    const topic = discussionTopic.trim() || classroomContext.topic || 'Today\'s lesson';
    clearMessages();
    startDiscussion(topic);
  };

  const handleModeChange = (newMode: string) => {
    setMode(newMode as SessionMode);
    clearMessages();
  };

  const whiteboardSrc = classroomId
    ? `${OPENMAIC_URL}/classroom/${classroomId}`
    : `${OPENMAIC_URL}`;

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-card shrink-0">
        <Button variant="ghost" size="sm" onClick={() => history.goBack()} className="gap-1.5 text-sm">
          <ArrowLeft className="w-4 h-4" />
          Back
        </Button>
        <div className="h-4 w-px bg-border mx-1" />
        <span className="text-sm font-semibold text-foreground">
          {classroomContext.topic ?? 'Classroom'}
        </span>
        <div className="ml-auto flex items-center gap-2">
          {/* Mode selector */}
          <Tabs value={mode} onValueChange={handleModeChange}>
            <TabsList className="h-7">
              <TabsTrigger value="qa" className="text-xs px-2 gap-1 h-6">
                <MessageSquare className="w-3 h-3" /> Q&amp;A
              </TabsTrigger>
              <TabsTrigger value="discussion" className="text-xs px-2 gap-1 h-6">
                <Users className="w-3 h-3" /> Discussion
              </TabsTrigger>
              <TabsTrigger value="debate" className="text-xs px-2 gap-1 h-6">
                <Swords className="w-3 h-3" /> Debate
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <Button
            variant={showWhiteboard ? 'secondary' : 'ghost'}
            size="sm"
            className="h-7 text-xs gap-1"
            onClick={() => setShowWhiteboard((v) => !v)}
          >
            <PenLine className="w-3 h-3" />
            Whiteboard
          </Button>
        </div>
      </div>

      {/* Agent bar */}
      <AgentAvatarBar
        agents={agents}
        speakingAgentId={speakingAgentId}
        thinkingStage={thinkingStage}
      />

      {/* Main content area */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Chat panel */}
        <div className={`flex flex-col min-h-0 transition-all duration-300 ${showWhiteboard ? 'w-[420px] shrink-0' : 'flex-1'}`}>
          {/* Mode-specific top controls */}
          {(mode === 'discussion' || mode === 'debate') && (
            <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-muted/30 shrink-0">
              <input
                type="text"
                placeholder={`${mode === 'debate' ? 'Debate topic' : 'Discussion topic'}…`}
                value={discussionTopic}
                onChange={(e) => setDiscussionTopic(e.target.value)}
                className="flex-1 text-sm bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground"
              />
              <Button
                size="sm"
                variant="default"
                className="h-7 text-xs gap-1"
                onClick={handleStartDiscussion}
                disabled={isStreaming}
              >
                <Play className="w-3 h-3" />
                {mode === 'debate' ? 'Start Debate' : 'Start Discussion'}
              </Button>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="text-4xl mb-3">
                  {mode === 'qa' ? '💬' : mode === 'discussion' ? '🗣️' : '⚔️'}
                </div>
                <p className="text-sm font-medium text-foreground mb-1">
                  {mode === 'qa'
                    ? 'Ask anything!'
                    : mode === 'discussion'
                    ? 'Start a classroom discussion'
                    : 'Start a structured debate'}
                </p>
                <p className="text-xs text-muted-foreground max-w-xs">
                  {mode === 'qa'
                    ? 'Type your question below. Ms. Aria and the class will help you understand.'
                    : mode === 'discussion'
                    ? 'Enter a topic above and click Start Discussion. The agents will have a natural classroom conversation.'
                    : 'Enter a topic above and click Start Debate. Agents will argue different perspectives.'}
                </p>
              </div>
            )}
            {messages.map((msg) => (
              <ClassroomChatMessage key={msg.id} message={msg} />
            ))}
            {thinkingStage === 'director' && messages.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="shrink-0 border-t border-border px-4 py-3 bg-card">
            {isCueUser && !isStreaming && (
              <p className="text-xs text-muted-foreground mb-2 italic">
                Your turn — ask a follow-up question or continue the conversation.
              </p>
            )}
            <div className="flex items-end gap-2">
              <Textarea
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  mode === 'qa' ? 'Ask a question…' : 'Join the discussion…'
                }
                className="flex-1 min-h-[44px] max-h-32 resize-none text-sm"
                rows={1}
                disabled={isStreaming && !isCueUser}
              />
              {isStreaming ? (
                <Button
                  size="icon"
                  variant="destructive"
                  className="h-9 w-9 shrink-0"
                  onClick={stop}
                >
                  <StopCircle className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  size="icon"
                  className="h-9 w-9 shrink-0"
                  onClick={handleSend}
                  disabled={!inputText.trim()}
                >
                  <Send className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Whiteboard panel */}
        {showWhiteboard && (
          <div className="flex-1 flex flex-col min-h-0 border-l border-border bg-white dark:bg-zinc-900">
            <div className="flex items-center justify-between px-3 py-1.5 border-b border-border bg-muted/30 shrink-0">
              <span className="text-xs font-medium text-muted-foreground">Whiteboard</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => setShowWhiteboard(false)}
              >
                <Minimize2 className="w-3 h-3" />
              </Button>
            </div>
            <iframe
              src={whiteboardSrc}
              title="OpenMAIC Whiteboard"
              className="flex-1 border-none"
              allow="microphone"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            />
          </div>
        )}
      </div>
    </div>
  );
}
