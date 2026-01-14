import { useQuery } from "@tanstack/react-query";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

export interface SessionQuestion {
  question_id: string;
  skill_ids: string[];
  skill_names: string[];
  is_correct: boolean;
  response_time_seconds: number;
  timestamp: number;
  question_text: string;
}

export interface SessionMetadata {
  date: number;
  duration: number;
  question_count: number;
  accuracy: number;
  skills_practiced: string[];
}

export interface SessionDetailResponse {
  session_id: string;
  questions: SessionQuestion[];
  metadata: SessionMetadata;
}

interface UseSessionDetailOptions {
  sessionId: string;
  enabled?: boolean;
}

export function useSessionDetail({
  sessionId,
  enabled = true,
}: UseSessionDetailOptions) {
  return useQuery<SessionDetailResponse>({
    queryKey: ["session-detail", sessionId],
    queryFn: async () => {
      // Use apiUtils.get() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no need to pass in URL
      const res = await apiUtils.get(`${DASH_API_URL}/api/practice-history/${sessionId}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch session detail (${res.status})`);
      }
      return res.json();
    },
    staleTime: 60_000, // Consider data fresh for 60 seconds
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
    refetchOnMount: true, // Only refetch when component mounts
    enabled: enabled && !!sessionId, // Only fetch if enabled and sessionId is provided
  });
}
