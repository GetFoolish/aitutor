/**
 * Types for the OpenMAIC multi-agent classroom integration (FOO-37).
 */

export type SessionMode = 'qa' | 'discussion' | 'debate';

export interface TutoringAgent {
  id: string;
  name: string;
  role: 'teacher' | 'student' | 'assistant';
  persona: string;
  avatar: string;
  color: string;
  allowedActions: string[];
  priority: number;
}

export interface ClassroomMessage {
  id: string;
  agentId: string;
  agentName: string;
  agentAvatar?: string;
  agentColor?: string;
  content: string;
  isUser?: boolean;
  timestamp: number;
  isStreaming?: boolean;
}

export interface DirectorState {
  turnCount: number;
  agentResponses: AgentTurnSummary[];
  whiteboardLedger: WhiteboardActionRecord[];
}

export interface AgentTurnSummary {
  agentId: string;
  agentName: string;
  summary: string;
}

export interface WhiteboardActionRecord {
  agentId: string;
  actionName: string;
  params: Record<string, unknown>;
}

export interface WhiteboardAction {
  actionId: string;
  actionName: string;
  params: Record<string, unknown>;
  agentId: string;
}

/** SSE events from OpenMAIC /api/chat */
export type StatelessEvent =
  | {
      type: 'agent_start';
      data: {
        messageId: string;
        agentId: string;
        agentName: string;
        agentAvatar?: string;
        agentColor?: string;
      };
    }
  | { type: 'agent_end'; data: { messageId: string; agentId: string } }
  | { type: 'text_delta'; data: { content: string; messageId?: string } }
  | {
      type: 'action';
      data: WhiteboardAction;
    }
  | { type: 'thinking'; data: { stage: string; agentId?: string } }
  | { type: 'cue_user'; data: { fromAgentId?: string; prompt?: string } }
  | {
      type: 'done';
      data: {
        totalActions: number;
        totalAgents: number;
        directorState?: DirectorState;
      };
    }
  | { type: 'error'; data: { message: string } };
