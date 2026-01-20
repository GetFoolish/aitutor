import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

const TEACHING_ASSISTANT_API_URL = "http://localhost:8002";

export function useRecordConversationTurn() {
  return useMutation({
    mutationFn: async () => {
      console.log('[TeachingAssistant] Recording conversation turn...');
      const res = await fetch(`${TEACHING_ASSISTANT_API_URL}/conversation/turn`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      const data = await res.json().catch(() => ({}));
      console.log('[TeachingAssistant] Turn recorded:', data);
      return res;
    },
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
      console.log('[TeachingAssistant] Starting session for user:', userId);
      const res = await fetch(`${TEACHING_ASSISTANT_API_URL}/session/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_id: userId }),
      });

      if (!res.ok) {
        console.error('[TeachingAssistant] Failed to start session:', res.status);
        throw new Error(`Failed to start session (${res.status})`);
      }

      const data = await res.json();
      console.log('[TeachingAssistant] Session started:', data);
      return data as { prompt?: string; session_info?: any };
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error starting session";
      toast.error("Failed to start teaching session", {
        description: message,
      });
    },
  });
}

export function useEndTeachingSession() {
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(`${TEACHING_ASSISTANT_API_URL}/session/end`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ interrupt_audio: true }),
      });

      if (!res.ok) {
        throw new Error(`Failed to end session (${res.status})`);
      }

      return res.json() as Promise<{ prompt?: string; session_info?: any }>;
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error ending session";
      toast.error("Failed to end teaching session", {
        description: message,
      });
    },
  });
}

export function useTeachingSessionInfo() {
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(`${TEACHING_ASSISTANT_API_URL}/session/info`);
      if (!res.ok) {
        throw new Error(`Failed to fetch session info (${res.status})`);
      }
      return res.json() as Promise<{ session_active?: boolean }>;
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


