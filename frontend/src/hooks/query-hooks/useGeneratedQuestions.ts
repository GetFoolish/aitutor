import { useQuery } from "@tanstack/react-query";
import type { PerseusItem } from "@khanacademy/perseus-core";

const GENERATED_API_URL = import.meta.env.VITE_GENERATED_API_URL || 'http://localhost:8001';

type GeneratedQuestionsResponse = PerseusItem[];

interface UseGeneratedQuestionsOptions {
  count: number;
  grade?: string;  // K-2, 3-5, 6-8, 9-12
  subject?: string;
  enabled?: boolean;
}

/**
 * Hook to fetch generated questions (with Innocent Drinks tone + personalization).
 * 
 * These are AI-generated questions stored locally, served via the content API.
 * Returns same Perseus format as DASH questions.
 */
export function useGeneratedQuestions({
  count,
  grade,
  subject = "math",
  enabled = true,
}: UseGeneratedQuestionsOptions) {
  return useQuery<GeneratedQuestionsResponse>({
    queryKey: ["generated-questions", count, grade, subject],
    queryFn: async () => {
      let url = `${GENERATED_API_URL}/api/generated/questions/${count}?subject=${subject}`;
      if (grade) {
        url += `&grade=${grade}`;
      }
      
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to fetch generated questions (${res.status})`);
      }
      return res.json();
    },
    staleTime: 60_000, // Cache for 1 minute
    enabled,
  });
}

/**
 * Hook to list available generated questions by grade/subject.
 */
export function useGeneratedQuestionsList() {
  return useQuery({
    queryKey: ["generated-questions-list"],
    queryFn: async () => {
      const res = await fetch(`${GENERATED_API_URL}/api/generated/list`);
      if (!res.ok) {
        throw new Error(`Failed to fetch questions list (${res.status})`);
      }
      return res.json();
    },
    staleTime: 300_000, // Cache for 5 minutes
  });
}
