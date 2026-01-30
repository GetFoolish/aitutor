import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { jwtUtils } from "../../lib/jwt-utils";

const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || "http://localhost:8002";

// Console logging styles for memory pipeline events
const logStyles = {
  session: 'background: #3498db; color: white; padding: 2px 6px; border-radius: 2px; font-weight: bold;',
  memory: 'background: #9b59b6; color: white; padding: 2px 6px; border-radius: 2px;',
  error: 'background: #e74c3c; color: white; padding: 2px 6px; border-radius: 2px;',
  success: 'background: #2ecc71; color: white; padding: 2px 6px; border-radius: 2px;',
};

function getAuthHeaders(): Record<string, string> {
  const token = jwtUtils.getToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
  };
}

export function useRecordConversationTurn() {
  return useMutation({
    mutationFn: async () =>
      fetch(`${TEACHING_ASSISTANT_API_URL}/conversation/turn`, {
        method: "POST",
        headers: getAuthHeaders(),
      }),
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error recording turn";
      toast.error("Failed to record conversation turn", { description: message });
    },
  });
}

export function useStartTeachingSession(userId: string) {
  return useMutation({
    mutationFn: async () => {
      console.log('%c[SESSION START]', logStyles.session, 'Starting teaching session...');
      console.log('User ID:', userId);

      const res = await fetch(`${TEACHING_ASSISTANT_API_URL}/session/start`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ user_id: userId }),
      });

      if (!res.ok) {
        throw new Error(`Failed to start session (${res.status})`);
      }

      const data = await res.json() as { prompt?: string; session_info?: any };

      // Log session info to console for debugging
      console.log('%c[SESSION STARTED]', logStyles.success, 'Session created successfully');
      if (data.session_info) {
        console.log('Session Info:', data.session_info);
        if (data.session_info.session_id) {
          console.log('Session ID:', data.session_info.session_id);
        }
        if (data.session_info.total_sessions !== undefined) {
          console.log('Total Sessions:', data.session_info.total_sessions);
        }
      }
      if (data.prompt) {
        console.log('%c[OPENING PROMPT]', logStyles.memory);
        console.log(data.prompt.substring(0, 500) + (data.prompt.length > 500 ? '...' : ''));
      }

      return data;
    },
    onSuccess: (data) => {
      console.log('%c[MEMORY PIPELINE]', logStyles.memory, 'Biography loaded into session context');
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error starting session";
      console.log('%c[SESSION ERROR]', logStyles.error, message);
      toast.error("Failed to start teaching session", {
        description: message,
      });
    },
  });
}

export function useEndTeachingSession() {
  return useMutation({
    mutationFn: async () => {
      console.log('%c[SESSION END]', logStyles.session, 'Ending teaching session...');

      const res = await fetch(`${TEACHING_ASSISTANT_API_URL}/session/end`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ interrupt_audio: true }),
      });

      if (!res.ok) {
        throw new Error(`Failed to end session (${res.status})`);
      }

      const data = await res.json() as { prompt?: string; session_info?: any };

      // Log session end info
      console.log('%c[SESSION ENDED]', logStyles.success, 'Session closed');
      if (data.session_info) {
        console.log('Final Session Info:', data.session_info);
        if (data.session_info.topics_covered) {
          console.log('Topics Covered:', data.session_info.topics_covered);
        }
        if (data.session_info.emotional_arc) {
          console.log('Emotional Arc:', data.session_info.emotional_arc);
        }
        if (data.session_info.key_moments) {
          console.log('Key Moments:', data.session_info.key_moments);
        }
      }
      console.log('%c[MEMORY PIPELINE]', logStyles.memory, 'Biographer will update student biography with session data');

      return data;
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error ending session";
      console.log('%c[SESSION ERROR]', logStyles.error, message);
      toast.error("Failed to end teaching session", {
        description: message,
      });
    },
  });
}

export function useTeachingSessionInfo() {
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(`${TEACHING_ASSISTANT_API_URL}/session/info`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        throw new Error(`Failed to fetch session info (${res.status})`);
      }
      const data = await res.json() as { session_active?: boolean; [key: string]: any };

      console.log('%c[SESSION INFO]', logStyles.session, data);

      return data;
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error getting session info";
      toast.error("Failed to fetch teaching session info", {
        description: message,
      });
    },
  });
}

export function useTeachingInactivityCheck() {
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(
        `${TEACHING_ASSISTANT_API_URL}/inactivity/check`,
        { headers: getAuthHeaders() }
      );
      if (!res.ok) {
        throw new Error(`Failed to check inactivity (${res.status})`);
      }
      return res.json() as Promise<{ prompt?: string }>;
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error checking inactivity";
      toast.error("Failed to check teaching inactivity", {
        description: message,
      });
    },
  });
}


