/**
 * Authentication API client
 */
import { httpClient } from './http-client';

const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';

export interface GoogleUser {
  id: string;
  email: string;
  name: string;
  picture?: string;
  verified_email: boolean;
}

export interface AuthResponse {
  token: string;
  user: {
    user_id: string;
    email: string;
    name: string;
    age: number;
    current_grade: string;
    user_type: string;
    preferred_language?: string;
  };
  is_new_user: boolean;
}

export interface SetupResponse {
  google_user: GoogleUser;
  requires_setup: boolean;
  setup_token: string;
}

export interface AccountInfo {
  user_id: string;
  email: string;
  name: string;
  date_of_birth: string;
  location: string;
  credits: {
    balance: number;
    currency: string;
  };
}

class AuthAPI {
  async getGoogleAuthUrl(): Promise<{ authorization_url: string; state: string }> {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/google`);
    if (!response.ok) {
      throw new Error('Failed to get Google auth URL');
    }
    return response.json();
  }

  async completeSetup(
    setupToken: string,
    userType: string,
    dateOfBirth: string,
    gender: string,
    preferredLanguage: string,
    profileData: {
      subjects: string[];
      learningGoals: string[];
      interests: string[];
      learningStyle: string;
    }
  ): Promise<AuthResponse> {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/complete-setup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        setup_token: setupToken,
        user_type: userType,
        date_of_birth: dateOfBirth,
        gender: gender,
        preferred_language: preferredLanguage,
        subjects: profileData.subjects,
        learning_goals: profileData.learningGoals,
        interests: profileData.interests,
        learning_style: profileData.learningStyle
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Setup failed');
    }

    return response.json();
  }

  async emailSignup(
    email: string,
    password: string,
    name: string,
    dateOfBirth: string,
    gender: string,
    preferredLanguage: string,
    userType: string = "student"
  ): Promise<AuthResponse> {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        name,
        date_of_birth: dateOfBirth,
        gender,
        preferred_language: preferredLanguage,
        user_type: userType
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Signup failed');
    }

    return response.json();
  }

  async emailLogin(email: string, password: string): Promise<AuthResponse> {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    return response.json();
  }

  async getCurrentUser(token: string): Promise<AuthResponse['user']> {
    const response = await httpClient.fetch(`${AUTH_SERVICE_URL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get current user');
    }

    return response.json();
  }

  async getAccountInfo(): Promise<AccountInfo> {
    const token = localStorage.getItem('jwt_token');
    if (!token) {
      throw new Error('Not authenticated');
    }

    const response = await httpClient.fetch(`${AUTH_SERVICE_URL}/account/info`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get account info');
    }

    return response.json();
  }

  async logout(): Promise<void> {
    const token = localStorage.getItem('jwt_token');
    if (token) {
      try {
        await httpClient.fetch(`${AUTH_SERVICE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      } catch (error) {
        console.error('Logout error:', error);
      }
    }
  }
}

export const authAPI = new AuthAPI();

