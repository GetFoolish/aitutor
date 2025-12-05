import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

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
      // Use apiUtils.post() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no userId in URL
      const res = await apiUtils.post(`${DASH_API_URL}/api/submit-answer`, {
        question_id: questionId,
        skill_ids: skillIds,
        is_correct: isCorrect,
        response_time_seconds: responseTimeSeconds,
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
    }: LogQuestionDisplayedPayload) => {
      // Use apiUtils.post() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no userId in URL
      const res = await apiUtils.post(`${DASH_API_URL}/api/question-displayed`, {
        question_index: index,
        metadata,
      });
      if (!res.ok) {
        throw new Error(`Failed to log question display (${res.status})`);
      }
      return res.json();
    },
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
    }: TeachingAssistantQuestionAnsweredPayload) => {
      // Use apiUtils.post() to automatically include JWT token
      const res = await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/question/answered`, {
        question_id: questionId,
        is_correct: isCorrect,
      });
      if (!res.ok) {
        throw new Error(`Failed to record answer (${res.status})`);
      }
      return res.json();
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error recording answer";
      toast.error("Failed to record answer with Teaching Assistant", {
        description: message,
      });
    },
  });
}

