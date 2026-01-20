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
  useMockData?: boolean;
}

// Mock data for demo purposes
const MOCK_STREAK_DATA: StreakData = {
  current_streak: 5,
  longest_streak: 12,
  last_practice_date: new Date().toISOString(),
  streak_history: [
    new Date(Date.now() - 86400000 * 4).toISOString().split('T')[0],
    new Date(Date.now() - 86400000 * 3).toISOString().split('T')[0],
    new Date(Date.now() - 86400000 * 2).toISOString().split('T')[0],
    new Date(Date.now() - 86400000 * 1).toISOString().split('T')[0],
    new Date().toISOString().split('T')[0],
  ]
};

export function useStreak({
  userId,
  enabled = true,
  useMockData = true, // Default to true for demo
}: UseStreakOptions) {
  return useQuery<StreakData>({
    queryKey: ["streak", userId, useMockData],
    queryFn: async () => {
      if (useMockData) {
        return MOCK_STREAK_DATA;
      }

      try {
        const res = await apiUtils.get(`${DASH_API_URL}/api/streak`);
        if (!res.ok) {
          console.warn(`Streak API returned ${res.status}, using mock data`);
          return MOCK_STREAK_DATA;
        }
        return res.json();
      } catch (error) {
        console.warn('Streak API error, using mock data:', error);
        return MOCK_STREAK_DATA;
      }
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
  useMockData?: boolean;
}

// Mock calendar data
const MOCK_CALENDAR_DATA: StreakCalendarData = {
  practice_dates: [
    new Date(Date.now() - 86400000 * 4).toISOString().split('T')[0],
    new Date(Date.now() - 86400000 * 3).toISOString().split('T')[0],
    new Date(Date.now() - 86400000 * 2).toISOString().split('T')[0],
    new Date(Date.now() - 86400000 * 1).toISOString().split('T')[0],
    new Date().toISOString().split('T')[0],
  ]
};

export function useStreakCalendar({
  userId,
  enabled = true,
  useMockData = true,
}: UseStreakCalendarOptions) {
  return useQuery<StreakCalendarData>({
    queryKey: ["streak-calendar", userId, useMockData],
    queryFn: async () => {
      if (useMockData) {
        return MOCK_CALENDAR_DATA;
      }

      try {
        const res = await apiUtils.get(`${DASH_API_URL}/api/streak/calendar`);
        if (!res.ok) {
          console.warn(`Streak calendar API returned ${res.status}, using mock data`);
          return MOCK_CALENDAR_DATA;
        }
        return res.json();
      } catch (error) {
        console.warn('Streak calendar API error, using mock data:', error);
        return MOCK_CALENDAR_DATA;
      }
    },
    staleTime: 30_000,
    enabled,
  });
}
