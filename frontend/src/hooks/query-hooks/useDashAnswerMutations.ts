import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

const DASH_API_BASE = "http://localhost:8000/api";
const TEACHING_ASSISTANT_API_URL = "http://localhost:8002";

interface SubmitDashAnswerPayload {
  userId: string;
  questionId: string;
  skillIds: string[];
  isCorrect: boolean;
  responseTimeSeconds: number;
}

interface LogQuestionDisplayedPayload {
  userId: string;
  index: number;
  metadata: any;
}

interface TeachingAssistantQuestionAnsweredPayload {
  questionId: string;
  isCorrect: boolean;
}

export function useDashAnswerMutations() {
  const queryClient = useQueryClient();

  const submitDashAnswer = useMutation({
    mutationFn: async ({
      userId,
      questionId,
      skillIds,
      isCorrect,
      responseTimeSeconds,
    }: SubmitDashAnswerPayload) => {
      const res = await fetch(`${DASH_API_BASE}/submit-answer/${userId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question_id: questionId,
          skill_ids: skillIds,
          is_correct: isCorrect,
          response_time_seconds: responseTimeSeconds,
        }),
      });

      if (!res.ok) {
        throw new Error(`Failed to submit answer (${res.status})`);
      }

      return res.json();
    },
    onSuccess: () => {
      // Invalidate related questions, so next fetch can reflect updated state if needed
      queryClient.invalidateQueries({ queryKey: ["dash-questions"] });
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error submitting answer";
      toast.error("Failed to submit answer", { description: message });
    },
  });

  const logQuestionDisplayed = useMutation({
    mutationFn: async ({
      userId,
      index,
      metadata,
    }: LogQuestionDisplayedPayload) =>
      fetch(`${DASH_API_BASE}/question-displayed/${userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question_index: index,
          metadata,
        }),
      }),
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error logging question";
      toast.error("Failed to log question display", { description: message });
    },
  });

  return {
    submitDashAnswer,
    logQuestionDisplayed,
  };
}

export function useTeachingAssistantQuestionAnswered() {
  return useMutation({
    mutationFn: async ({
      questionId,
      isCorrect,
    }: TeachingAssistantQuestionAnsweredPayload) =>
      fetch(`${TEACHING_ASSISTANT_API_URL}/question/answered`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question_id: questionId,
          is_correct: isCorrect,
        }),
      }),
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error recording answer";
      toast.error("Failed to record answer with Teaching Assistant", {
        description: message,
      });
    },
  });
}

