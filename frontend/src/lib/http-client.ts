/**
 * HTTP client with global error handling for authentication
 */
import { jwtUtils } from './jwt-utils';

interface AuthContext {
  logout: () => Promise<void>;
}

let authContext: AuthContext | null = null;

export const setAuthContext = (context: AuthContext) => {
  authContext = context;
};

export const httpClient = {
  async fetch(url: string, options: RequestInit = {}): Promise<Response> {
    const response = await fetch(url, options);

    // Handle 401 Unauthorized globally
    if (response.status === 401) {
      console.warn('Received 401 Unauthorized - token expired, logging out');
      if (authContext) {
        try {
          await authContext.logout();
        } catch (error) {
          console.error('Error during automatic logout:', error);
        }
      }
      // Remove token immediately
      jwtUtils.removeToken();
    }

    return response;
  },

  async get(url: string, options: RequestInit = {}): Promise<Response> {
    return this.fetch(url, { ...options, method: 'GET' });
  },

  async post(url: string, body?: any, options: RequestInit = {}): Promise<Response> {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    return this.fetch(url, {
      ...options,
      method: 'POST',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  async put(url: string, body?: any, options: RequestInit = {}): Promise<Response> {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    return this.fetch(url, {
      ...options,
      method: 'PUT',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  async delete(url: string, options: RequestInit = {}): Promise<Response> {
    return this.fetch(url, { ...options, method: 'DELETE' });
  },
};
