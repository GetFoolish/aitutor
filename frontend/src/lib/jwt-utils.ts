/**
 * JWT token storage and retrieval utilities
 * Wrapped in try/catch — localStorage throws in private browsing / storage disabled
 */

const TOKEN_KEY = 'jwt_token';

export const jwtUtils = {
  getToken: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },

  setToken: (token: string): void => {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      console.warn('Could not save token — storage unavailable');
    }
  },

  removeToken: (): void => {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // Already inaccessible
    }
  },

  hasToken: (): boolean => {
    try {
      return !!localStorage.getItem(TOKEN_KEY);
    } catch {
      return false;
    }
  }
};
