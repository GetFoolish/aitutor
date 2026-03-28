/**
 * Hook for multi-agent classroom chat via OpenMAIC proxy (FOO-37).
 * Streams SSE events from POST /api/classroom/chat on the TeachingAssistant service.
 */

import { useState, useCallback, useRef } from 'react';
import type {
  ClassroomMessage,
  TutoringAgent,
  DirectorState,
  StatelessEvent,
  SessionMode,
} from './types';

const TA_API_URL =
  (import.meta as any).env?.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

interface UseClassroomChatOptions {
  agents: TutoringAgent[];
  mode: SessionMode;
  classroomContext?: {
    topic?: string;
    scenes?: unknown[];
    stage?: unknown;
  };
  apiKey?: string;
  model?: string;
}

export function useClassroomChat({
  agents,
  mode,
  classroomContext,
  apiKey,
  model,
}: UseClassroomChatOptions) {
  const [messages, setMessages] = useState<ClassroomMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [speakingAgentId, setSpeakingAgentId] = useState<string | null>(null);
  const [thinkingStage, setThinkingStage] = useState<string | null>(null);
  const [isCueUser, setIsCueUser] = useState(false);
  const [whiteboardActions, setWhiteboardActions] = useState<
    Array<{ actionName: string; params: Record<string, unknown>; agentId: string }>
  >([]);

  const directorStateRef = useRef<DirectorState>({
    turnCount: 0,
    agentResponses: [],
    whiteboardLedger: [],
  });
  const abortRef = useRef<AbortController | null>(null);
  // messageId -> partial content accumulator
  const streamingContentRef = useRef<Record<string, string>>({});

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setSpeakingAgentId(null);
    setThinkingStage(null);
  }, []);

  const sendMessage = useCallback(
    async (userText: string) => {
      if (isStreaming) return;

      const userMsg: ClassroomMessage = {
        id: `user-${Date.now()}`,
        agentId: 'user',
        agentName: 'You',
        content: userText,
        isUser: true,
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setIsCueUser(false);
      setThinkingStage('director');

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      try {
        // Build messages array in the format OpenMAIC expects (UIMessage)
        const allMessages = [...messages, userMsg].map((m) => ({
          id: m.id,
          role: m.isUser ? 'user' : 'assistant',
          content: m.content,
          ...(m.isUser
            ? {}
            : {
                annotations: [
                  {
                    type: 'agent_info',
                    agentId: m.agentId,
                    agentName: m.agentName,
                    agentAvatar: m.agentAvatar,
                    agentColor: m.agentColor,
                  },
                ],
              }),
        }));

        // Build agent configs to send to the stateless API
        const agentConfigs = agents.map((a) => ({
          id: a.id,
          name: a.name,
          role: a.role,
          persona: a.persona,
          avatar: a.avatar,
          color: a.color,
          allowedActions: a.allowedActions,
          priority: a.priority,
        }));

        const sessionType = mode === 'debate' ? 'discussion' : mode;

        const requestBody = {
          messages: allMessages,
          storeState: {
            stage: classroomContext?.stage ?? null,
            scenes: classroomContext?.scenes ?? [],
            currentSceneId: null,
            mode: 'autonomous',
            whiteboardOpen: false,
          },
          config: {
            agentIds: agents.map((a) => a.id),
            sessionType,
            agentConfigs,
            ...(mode === 'discussion' && classroomContext?.topic
              ? {
                  discussionTopic: classroomContext.topic,
                  triggerAgentId: agents.find((a) => a.role === 'teacher')?.id,
                }
              : {}),
            ...(mode === 'debate'
              ? {
                  discussionTopic: classroomContext?.topic ?? userText,
                  triggerAgentId: agents[0]?.id,
                }
              : {}),
          },
          directorState: directorStateRef.current,
          apiKey: apiKey ?? '',
          model: model ?? 'google/gemini-2.0-flash-exp:free',
          providerType: 'openrouter',
          requiresApiKey: false,
        };

        const resp = await fetch(`${TA_API_URL}/api/classroom/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
          signal: ctrl.signal,
        });

        if (!resp.ok) {
          throw new Error(`Chat API error ${resp.status}`);
        }

        const reader = resp.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const raw = line.slice(6).trim();
              if (!raw || raw === '[DONE]') continue;
              try {
                const event: StatelessEvent = JSON.parse(raw);
                processEvent(event);
              } catch {
                // non-JSON SSE line (heartbeat etc.) — skip
              }
            }
          }
        }
      } catch (err: any) {
        if (err?.name !== 'AbortError') {
          console.error('[ClassroomChat] Error:', err);
          setMessages((prev) => [
            ...prev,
            {
              id: `error-${Date.now()}`,
              agentId: 'system',
              agentName: 'System',
              content: `Error: ${err?.message ?? 'Unknown error'}`,
              timestamp: Date.now(),
            },
          ]);
        }
      } finally {
        setIsStreaming(false);
        setSpeakingAgentId(null);
        setThinkingStage(null);
        streamingContentRef.current = {};
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isStreaming, messages, agents, mode, classroomContext, apiKey, model],
  );

  function processEvent(event: StatelessEvent) {
    switch (event.type) {
      case 'agent_start': {
        const { messageId, agentId, agentName, agentAvatar, agentColor } = event.data;
        setSpeakingAgentId(agentId);
        setThinkingStage(null);
        streamingContentRef.current[messageId] = '';
        setMessages((prev) => [
          ...prev,
          {
            id: messageId,
            agentId,
            agentName,
            agentAvatar,
            agentColor,
            content: '',
            isStreaming: true,
            timestamp: Date.now(),
          },
        ]);
        break;
      }
      case 'text_delta': {
        const { content, messageId } = event.data;
        if (messageId) {
          streamingContentRef.current[messageId] =
            (streamingContentRef.current[messageId] ?? '') + content;
          const accumulated = streamingContentRef.current[messageId];
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId ? { ...m, content: accumulated, isStreaming: true } : m,
            ),
          );
        }
        break;
      }
      case 'agent_end': {
        const { messageId } = event.data;
        setMessages((prev) =>
          prev.map((m) => (m.id === messageId ? { ...m, isStreaming: false } : m)),
        );
        break;
      }
      case 'action': {
        const { actionName, params, agentId } = event.data;
        setWhiteboardActions((prev) => [...prev, { actionName, params, agentId }]);
        break;
      }
      case 'thinking': {
        setThinkingStage(event.data.stage);
        break;
      }
      case 'cue_user': {
        setIsCueUser(true);
        setIsStreaming(false);
        setSpeakingAgentId(null);
        break;
      }
      case 'done': {
        if (event.data.directorState) {
          directorStateRef.current = event.data.directorState;
        }
        break;
      }
      case 'error': {
        console.error('[ClassroomChat] Server error:', event.data.message);
        break;
      }
    }
  }

  const startDiscussion = useCallback(
    async (topic: string) => {
      if (isStreaming) return;

      setIsStreaming(true);
      setThinkingStage('director');
      setIsCueUser(false);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      // Reset director state for new discussion
      directorStateRef.current = { turnCount: 0, agentResponses: [], whiteboardLedger: [] };

      const agentConfigs = agents.map((a) => ({
        id: a.id,
        name: a.name,
        role: a.role,
        persona: a.persona,
        avatar: a.avatar,
        color: a.color,
        allowedActions: a.allowedActions,
        priority: a.priority,
      }));

      const requestBody = {
        messages: [],
        storeState: {
          stage: classroomContext?.stage ?? null,
          scenes: classroomContext?.scenes ?? [],
          currentSceneId: null,
          mode: 'autonomous',
          whiteboardOpen: false,
        },
        config: {
          agentIds: agents.map((a) => a.id),
          sessionType: 'discussion',
          discussionTopic: topic,
          discussionPrompt: `Have an engaging educational discussion about: ${topic}`,
          triggerAgentId: agents.find((a) => a.role === 'teacher')?.id ?? agents[0]?.id,
          agentConfigs,
        },
        directorState: directorStateRef.current,
        apiKey: apiKey ?? '',
        model: model ?? 'google/gemini-2.0-flash-exp:free',
        providerType: 'openrouter',
        requiresApiKey: false,
      };

      try {
        const resp = await fetch(`${TA_API_URL}/api/classroom/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
          signal: ctrl.signal,
        });

        if (!resp.ok) throw new Error(`Chat API error ${resp.status}`);

        const reader = resp.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const raw = line.slice(6).trim();
              if (!raw || raw === '[DONE]') continue;
              try {
                processEvent(JSON.parse(raw) as StatelessEvent);
              } catch {}
            }
          }
        }
      } catch (err: any) {
        if (err?.name !== 'AbortError') {
          console.error('[ClassroomChat] Discussion error:', err);
        }
      } finally {
        setIsStreaming(false);
        setSpeakingAgentId(null);
        setThinkingStage(null);
        streamingContentRef.current = {};
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isStreaming, agents, mode, classroomContext, apiKey, model],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    directorStateRef.current = { turnCount: 0, agentResponses: [], whiteboardLedger: [] };
    setWhiteboardActions([]);
    setIsCueUser(false);
  }, []);

  return {
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
  };
}
