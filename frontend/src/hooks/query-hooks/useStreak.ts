import { useQuery } from "@tanstack/react-query";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface StreakData {
  current_streak: number;
  longest_streak: number;
  last_practice_date: string;
  streak_history: string[];
}

interface UseStreakOptions {
  userId: string;
  enabled?: boolean;
}

export function useStreak({
  userId,
  enabled = true,
}: UseStreakOptions) {
  return useQuery<StreakData>({
    queryKey: ["streak", userId],
    queryFn: async () => {
      // Use apiUtils.get() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no need to pass in URL
      const res = await apiUtils.get(`${DASH_API_URL}/api/streak`);
      if (!res.ok) {
        throw new Error(`Failed to fetch streak data (${res.status})`);
      }
      return res.json();
    },
    staleTime: 30_000,
    enabled,
  });
}

interface StreakCalendarData {
  practice_dates: string[];
}

interface UseStreakCalendarOptions {
  userId: string;
  enabled?: boolean;
}

export function useStreakCalendar({
  userId,
  enabled = true,
}: UseStreakCalendarOptions) {
  return useQuery<StreakCalendarData>({
    queryKey: ["streak-calendar", userId],
    queryFn: async () => {
      // Use apiUtils.get() to automatically include JWT token
      // Backend extracts user_id from JWT token, so no need to pass in URL
      const res = await apiUtils.get(`${DASH_API_URL}/api/streak/calendar`);
      if (!res.ok) {
        throw new Error(`Failed to fetch streak calendar data (${res.status})`);
      }
      return res.json();
    },
    staleTime: 30_000,
    enabled,
  });
}
