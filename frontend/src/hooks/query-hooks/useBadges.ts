import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

// Badge Types
export type BadgeType = "skill_mastery" | "streak" | "question_count" | "perfect_score";

export interface Badge {
  badge_id: string;
  name: string;
  description: string;
  badge_type: BadgeType;
  icon: string;
  requirement: number;
  tier?: string | null;
}

export interface BadgeProgress {
  current: number;
  required: number;
  percentage: number;
  earned: boolean;
}

interface BadgesResponse {
  available_badges: Badge[];
  user_progress: Record<string, BadgeProgress>;
  earned_badges: string[];
}

interface EarnedBadgesResponse {
  earned_badges: Badge[];
  total_count: number;
}

interface CheckBadgesResponse {
  newly_earned: string[];
  badge_progress: Record<string, BadgeProgress>;
}

interface UseBadgesOptions {
  userId: string;
  enabled?: boolean;
}

/**
 * Fetch all available badges with user progress
 */
export function useBadges({
  userId,
  enabled = true,
}: UseBadgesOptions) {
  return useQuery<BadgesResponse>({
    queryKey: ["badges", userId],
    queryFn: async () => {
      // Use apiUtils.get() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no need to pass in URL
      const res = await apiUtils.get(`${DASH_API_URL}/api/badges`);
      if (!res.ok) {
        throw new Error(`Failed to fetch badges (${res.status})`);
      }
      return res.json();
    },
    staleTime: 60_000, // Cache for 1 minute
    enabled,
  });
}

/**
 * Fetch user's earned badges
 */
export function useEarnedBadges({
  userId,
  enabled = true,
}: UseBadgesOptions) {
  return useQuery<EarnedBadgesResponse>({
    queryKey: ["earned-badges", userId],
    queryFn: async () => {
      // Use apiUtils.get() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no need to pass in URL
      const res = await apiUtils.get(`${DASH_API_URL}/api/badges/earned`);
      if (!res.ok) {
        throw new Error(`Failed to fetch earned badges (${res.status})`);
      }
      return res.json();
    },
    staleTime: 60_000, // Cache for 1 minute
    enabled,
  });
}

/**
 * Check and award new badges
 */
export function useCheckBadges() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      // Use apiUtils.post() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no userId in URL
      const res = await apiUtils.post(`${DASH_API_URL}/api/badges/check`, {});
      if (!res.ok) {
        throw new Error(`Failed to check badges (${res.status})`);
      }
      return res.json() as Promise<CheckBadgesResponse>;
    },
    onSuccess: () => {
      // Invalidate badge queries to refresh badge data
      queryClient.invalidateQueries({ queryKey: ["badges"] });
      queryClient.invalidateQueries({ queryKey: ["earned-badges"] });
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Unknown error checking badges";
      toast.error("Failed to check badges", { description: message });
    },
  });
}
