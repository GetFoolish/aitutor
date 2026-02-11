/**
 * API utilities for authenticated requests
 */
import { httpClient } from './http-client';
import { jwtUtils } from './jwt-utils';

export const apiUtils = {
  /**
   * Make an authenticated API request with automatic token attachment
   */
  async authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const token = jwtUtils.getToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return httpClient.fetch(url, {
      ...options,
      headers,
    });
  },

  /**
   * Make an authenticated GET request
   */
  async get(url: string, options: RequestInit = {}): Promise<Response> {
    return this.authenticatedFetch(url, { ...options, method: 'GET' });
  },

  /**
   * Make an authenticated POST request
   */
  async post(url: string, body?: any, options: RequestInit = {}): Promise<Response> {
    return this.authenticatedFetch(url, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  /**
   * Make an authenticated PUT request
   */
  async put(url: string, body?: any, options: RequestInit = {}): Promise<Response> {
    return this.authenticatedFetch(url, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  },
};

const DASH_API_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_DASH_API_URL) || 'http://localhost:8000';

/**
 * Fire-and-forget analytics reporting for question attempts.
 * Does not block the UI -- failures are silently ignored.
 */
export function reportQuestionAnalytics(data: {
  question_id: string;
  correct: boolean;
  hints_used: number;
  time_seconds: number;
  skipped: boolean;
  skill_id?: string;
}) {
  const token = jwtUtils.getToken();
  fetch(`${DASH_API_URL}/api/question-analytics`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
  }).catch(() => {}); // Silent fail -- analytics should never block UX
}
