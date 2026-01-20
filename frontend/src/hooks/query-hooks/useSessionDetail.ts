import { useQuery } from "@tanstack/react-query";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

export interface SessionQuestion {
  question_id: string;
  skill_id: string;
  skill_name: string;
  is_correct: boolean;
  time_spent: number;
  timestamp: number;
}

export interface SessionDetailResponse {
  session_id: string;
  date: number;
  duration: number;
  questions: SessionQuestion[];
  accuracy: number;
  skills_summary: {
    skill_id: string;
    skill_name: string;
    correct: number;
    total: number;
  }[];
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
      const res = await apiUtils.get(`${DASH_API_URL}/api/practice-history/${sessionId}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch session detail (${res.status})`);
      }
      return res.json();
    },
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    refetchOnMount: true,
    enabled: enabled && !!sessionId,
  });
}
