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

    // Handle 401 Unauthorized globally, but only for auth-related endpoints
    // Don't auto-logout for other endpoints (might be temporary/permission issues)
    if (response.status === 401) {
      const urlPath = new URL(url, window.location.origin).pathname;
      const isAuthEndpoint = urlPath.includes('/auth/') || urlPath.includes('/account/');
      
      if (isAuthEndpoint) {
        // Only auto-logout for auth endpoints (token is definitely invalid)
        console.warn('Received 401 Unauthorized on auth endpoint - token expired, logging out');
        if (authContext) {
          try {
            await authContext.logout();
          } catch (error) {
            console.error('Error during automatic logout:', error);
          }
        }
        // Remove token immediately
        jwtUtils.removeToken();
      } else {
        // For non-auth endpoints, just log a warning but don't logout
        // The calling code can handle the 401 appropriately
        console.debug('Received 401 Unauthorized (non-auth endpoint):', urlPath);
      }
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

