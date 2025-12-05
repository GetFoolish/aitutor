import { useQuery } from "@tanstack/react-query";
import type { PerseusItem } from "@khanacademy/perseus-core";

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
      const res = await fetch(
        `http://localhost:8000/api/questions/${count}?user_id=${userId}`,
      );
      if (!res.ok) {
        throw new Error(`Failed to fetch questions (${res.status})`);
      }
      return res.json();
    },
    staleTime: 30_000,
    enabled,
  });
}


