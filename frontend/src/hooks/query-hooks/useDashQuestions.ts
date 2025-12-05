import { useQuery } from "@tanstack/react-query";
import type { PerseusItem } from "@khanacademy/perseus-core";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

type DashQuestionsResponse = PerseusItem[];

interface UseDashQuestionsOptions {
  userId: string;
  count: number;
  enabled?: boolean;
}

export function useDashQuestions({
  userId,
  count,
  enabled = true,
}: UseDashQuestionsOptions) {
  return useQuery<DashQuestionsResponse>({
    queryKey: ["dash-questions", userId, count],
    queryFn: async () => {
      // Use apiUtils.get() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no need to pass in URL
      const res = await apiUtils.get(`${DASH_API_URL}/api/questions/${count}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch questions (${res.status})`);
      }
      return res.json();
    },
    staleTime: 30_000,
    enabled,
  });
}


