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

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
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
