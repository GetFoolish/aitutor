import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  user_id: string;
  email: string;
  name: string;
  account_type: 'self-learner' | 'parent';
  age?: number;
  language: string;
  region: string;
  credits: number;
  parent_id?: string;
  children: string[];
  profile_picture?: string;
  created_at: string;
  last_login: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string, age?: number) => Promise<void>;
  googleLogin: (oauth_id: string, email: string, name: string, profile_picture?: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  error: string | null;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = 'http://localhost:8001';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  console.log('[AuthProvider] Render - user:', user?.email, 'isLoading:', isLoading);

  // Load user from localStorage on mount
  useEffect(() => {
    console.log('[AuthProvider] Initial load effect running...');
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('user');

    console.log('[AuthProvider] localStorage - token exists:', !!storedToken, 'user exists:', !!storedUser);

    if (storedToken && storedUser) {
      console.log('[AuthProvider] Restoring user from localStorage:', JSON.parse(storedUser).email);
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    } else {
      console.log('[AuthProvider] No stored credentials found');
    }
    setIsLoading(false);
    console.log('[AuthProvider] Initial load complete, isLoading set to false');
  }, []);

  const login = async (email: string, password: string) => {
    try {
      console.log('[AuthProvider] Login attempt for:', email);
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      console.log('[AuthProvider] Login response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      console.log('[AuthProvider] Login response data:', { hasToken: !!data.access_token, hasUser: !!data.user, userEmail: data.user?.email });

      setToken(data.access_token);
      setUser(data.user);

      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      console.log('[AuthProvider] Login complete, user set to:', data.user?.email);
    } catch (err: any) {
      console.error('[AuthProvider] Login error:', err.message);
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
      console.log('[AuthProvider] Login finally block, isLoading set to false');
    }
  };

  const signup = async (email: string, password: string, name: string, age?: number) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          name,
          age,
          account_type: 'self-learner',
          language: 'en',
          region: 'US',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Signup failed');
      }

      const data = await response.json();
      setToken(data.access_token);
      setUser(data.user);

      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const googleLogin = async (oauth_id: string, email: string, name: string, profile_picture?: string) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/auth/oauth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          oauth_id,
          email,
          name,
          profile_picture,
          auth_provider: 'google',
          account_type: 'self-learner',
          language: 'en',
          region: 'US',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Google login failed');
      }

      const data = await response.json();
      setToken(data.access_token);
      setUser(data.user);

      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  };

  const refreshUser = async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
      } else {
        logout();
      }
    } catch (err) {
      console.error('Failed to refresh user:', err);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        signup,
        googleLogin,
        logout,
        isLoading,
        error,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
