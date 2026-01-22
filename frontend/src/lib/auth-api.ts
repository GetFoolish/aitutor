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
  gender?: string;
  preferred_language?: string;
  user_type?: string;
  credits: {
    balance: number;
    currency: string;
  };
  free_minutes?: {
    balance: number;
    last_reset_date: string | null;
    next_reset_in_hours?: number | null;
    next_reset_in_minutes?: number | null;
  };
  subscription_plan?: string | null;
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
    location: string,
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
        location: location,
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
    location: string,
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
        location: location,
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

  async updateAccountInfo(updates: {
    name?: string;
    dateOfBirth?: string;
    location?: string;
    gender?: string;
    preferredLanguage?: string;
  }): Promise<AccountInfo> {
    const token = localStorage.getItem('jwt_token');
    if (!token) {
      throw new Error('Not authenticated');
    }

    const response = await httpClient.fetch(`${AUTH_SERVICE_URL}/account/update`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: updates.name,
        date_of_birth: updates.dateOfBirth,
        location: updates.location,
        gender: updates.gender,
        preferred_language: updates.preferredLanguage,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update account info');
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

