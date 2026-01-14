import { useQuery } from "@tanstack/react-query";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

export interface PracticeSession {
  session_id: string;
  date: number;
  duration: number;
  question_count: number;
  accuracy: number;
  skills_practiced: string[];
}

export interface PracticeHistoryResponse {
  sessions: PracticeSession[];
  total_count: number;
  page: number;
  limit: number;
}

interface UsePracticeHistoryOptions {
  page?: number;
  limit?: number;
  enabled?: boolean;
}

export function usePracticeHistory({
  page = 1,
  limit = 10,
  enabled = true,
}: UsePracticeHistoryOptions = {}) {
  return useQuery<PracticeHistoryResponse>({
    queryKey: ["practice-history", page, limit],
    queryFn: async () => {
      // Use apiUtils.get() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no need to pass in URL
      const res = await apiUtils.get(`${DASH_API_URL}/api/practice-history?page=${page}&limit=${limit}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch practice history (${res.status})`);
      }
      return res.json();
    },
    staleTime: 60_000, // Consider data fresh for 60 seconds
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
    refetchOnMount: true, // Only refetch when component mounts
    enabled,
  });
}
