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
  useMockData?: boolean; // For demo/testing purposes
}

// Mock data for demo purposes
const MOCK_SESSIONS: PracticeSession[] = [
  {
    session_id: "session_0",
    date: Date.now() / 1000 - 3600, // 1 hour ago
    duration: 1800, // 30 minutes
    question_count: 15,
    accuracy: 0.87,
    skills_practiced: ["addition_within_20", "subtraction_within_20", "place_value"]
  },
  {
    session_id: "session_1",
    date: Date.now() / 1000 - 86400, // Yesterday
    duration: 2400, // 40 minutes
    question_count: 22,
    accuracy: 0.73,
    skills_practiced: ["multiplication_facts", "division_facts", "word_problems"]
  },
  {
    session_id: "session_2",
    date: Date.now() / 1000 - 172800, // 2 days ago
    duration: 1200, // 20 minutes
    question_count: 10,
    accuracy: 0.90,
    skills_practiced: ["fractions_basics", "comparing_fractions"]
  },
  {
    session_id: "session_3",
    date: Date.now() / 1000 - 259200, // 3 days ago
    duration: 3000, // 50 minutes
    question_count: 28,
    accuracy: 0.64,
    skills_practiced: ["geometry_shapes", "area_perimeter", "angles"]
  },
  {
    session_id: "session_4",
    date: Date.now() / 1000 - 432000, // 5 days ago
    duration: 900, // 15 minutes
    question_count: 8,
    accuracy: 1.0,
    skills_practiced: ["counting", "number_recognition"]
  }
];

export function usePracticeHistory({
  page = 1,
  limit = 10,
  enabled = true,
  useMockData = false, // Default to false to use real backend (mock data is fallback)
}: UsePracticeHistoryOptions = {}) {
  return useQuery<PracticeHistoryResponse>({
    queryKey: ["practice-history", page, limit, useMockData],
    queryFn: async () => {
      // Helper to return mock data
      const getMockData = () => {
        const startIdx = (page - 1) * limit;
        const endIdx = startIdx + limit;
        return {
          sessions: MOCK_SESSIONS.slice(startIdx, endIdx),
          total_count: MOCK_SESSIONS.length,
          page,
          limit
        };
      };

      // Return mock data for demo/testing
      if (useMockData) {
        return getMockData();
      }

      try {
        // Use apiUtils.get() to automatically include JWT token
        const res = await apiUtils.get(`${DASH_API_URL}/api/practice-history?page=${page}&limit=${limit}`);
        if (!res.ok) {
          console.warn(`Practice history API returned ${res.status}, using mock data`);
          return getMockData();
        }
        const data = await res.json();

        // If no real data, return mock data for demo
        if (!data.sessions || data.sessions.length === 0) {
          return getMockData();
        }

        return data;
      } catch (error) {
        console.warn('Practice history API error, using mock data:', error);
        return getMockData();
      }
    },
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    refetchOnMount: true,
    enabled,
  });
}
