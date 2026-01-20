import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiUtils } from "../../lib/api-utils";

const TA_API_URL = import.meta.env.VITE_TA_API_URL || 'http://localhost:8002';

// Types
export interface StruggleSignals {
  interaction: {
    long_pause: boolean;
    repeated_errors: boolean;
    inactivity: boolean;
    high_hint_usage: boolean;
  };
  audio?: {
    hesitation: boolean;
    long_pauses: boolean;
    decreasing_volume: boolean;
    is_speaking: boolean;
  };
  visual?: {
    frustrated_or_confused: boolean;
    disengaged: boolean;
    looking_away: boolean;
    face_detected: boolean;
    emotion: string;
  };
}

export interface Intervention {
  type: "hint" | "encouragement" | "simplification" | "break_suggestion";
  message: string;
  urgency: "low" | "medium" | "high";
}

export interface StruggleStatus {
  session_id: string;
  struggle_score: number;
  needs_intervention: boolean;
  intervention_urgency: "low" | "medium" | "high";
  signal_mode: "multi_signal" | "interaction_only";
  signals: StruggleSignals;
  intervention: Intervention | null;
}

interface UseStruggleStatusOptions {
  enabled?: boolean;
  pollingInterval?: number; // ms between polls
}

/**
 * Hook to poll struggle status from the backend.
 * Used to display struggle indicators and interventions in the UI.
 */
export function useStruggleStatus({
  enabled = true,
  pollingInterval = 10000, // Poll every 10 seconds
}: UseStruggleStatusOptions = {}) {
  return useQuery<StruggleStatus>({
    queryKey: ["struggle-status"],
    queryFn: async () => {
      const res = await apiUtils.get(`${TA_API_URL}/struggle/status`);
      if (!res.ok) {
        if (res.status === 404) {
          // No active session - return default state
          return {
            session_id: "",
            struggle_score: 0,
            needs_intervention: false,
            intervention_urgency: "low",
            signal_mode: "interaction_only",
            signals: {
              interaction: {
                long_pause: false,
                repeated_errors: false,
                inactivity: false,
                high_hint_usage: false,
              },
            },
            intervention: null,
          } as StruggleStatus;
        }
        throw new Error(`Failed to fetch struggle status (${res.status})`);
      }
      return res.json();
    },
    staleTime: 5000,
    refetchInterval: enabled ? pollingInterval : false,
    enabled,
  });
}

/**
 * Hook to record an error (incorrect answer) for struggle detection.
 */
export function useRecordError() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await apiUtils.post(`${TA_API_URL}/struggle/record-error`, {});
      if (!res.ok) {
        throw new Error(`Failed to record error (${res.status})`);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["struggle-status"] });
    },
  });
}

/**
 * Hook to record a success (correct answer) for struggle detection.
 */
export function useRecordSuccess() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await apiUtils.post(`${TA_API_URL}/struggle/record-success`, {});
      if (!res.ok) {
        throw new Error(`Failed to record success (${res.status})`);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["struggle-status"] });
    },
  });
}

/**
 * Hook to record a hint request for struggle detection.
 */
export function useRecordHintRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await apiUtils.post(`${TA_API_URL}/struggle/request-hint`, {});
      if (!res.ok) {
        throw new Error(`Failed to record hint request (${res.status})`);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["struggle-status"] });
    },
  });
}

/**
 * Hook to send audio/visual signals for multi-signal struggle detection.
 */
export function useSendSignals() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (signals: {
      audio_signals?: {
        hesitation_score?: number;
        long_pauses?: number;
        volume_trend?: "increasing" | "stable" | "decreasing";
        is_speaking?: boolean;
      };
      visual_signals?: {
        emotion?: string;
        emotion_struggle_score?: number;
        engagement_score?: number;
        is_distracted?: boolean;
        face_detected?: boolean;
      };
    }) => {
      const res = await apiUtils.post(`${TA_API_URL}/signals/update`, signals);
      if (!res.ok) {
        throw new Error(`Failed to send signals (${res.status})`);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["struggle-status"] });
    },
  });
}
