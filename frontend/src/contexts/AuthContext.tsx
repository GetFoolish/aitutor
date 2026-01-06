/**
 * Authentication context for managing user authentication state
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI, AuthResponse } from '../lib/auth-api';
import { jwtUtils } from '../lib/jwt-utils';
import { setAuthContext } from '../lib/http-client';

interface AuthUser {
  user_id: string;
  email: string;
  name: string;
  age: number;
  current_grade: string;
  user_type: string;
  learning_style?: string;
  preferred_language?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, user: AuthUser) => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const login = (token: string, userData: AuthUser) => {
    jwtUtils.setToken(token);
    setUser(userData);
  };

  const logout = async () => {
    await authAPI.logout();
    jwtUtils.removeToken();
    setUser(null);
  };

  const refreshUser = async () => {
    const token = jwtUtils.getToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const userData = await authAPI.getCurrentUser(token);
      setUser(userData);
    } catch (error) {
      console.error('Failed to refresh user:', error);
      jwtUtils.removeToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Check for existing token on mount
    const token = jwtUtils.getToken();
    if (token) {
      refreshUser();
    } else {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Register logout function with HTTP client for global 401 handling
    setAuthContext({ logout });
  }, [logout]);

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

