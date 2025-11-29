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
  };
  is_new_user: boolean;
}

export interface SetupResponse {
  google_user: GoogleUser;
  requires_setup: boolean;
  setup_token: string;
}

class AuthAPI {
  async getGoogleAuthUrl(): Promise<{ authorization_url: string; state: string }> {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/google`);
    if (!response.ok) {
      throw new Error('Failed to get Google auth URL');
    }
    return response.json();
  }

  async completeSetup(setupToken: string, userType: string, age: number): Promise<AuthResponse> {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/complete-setup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        setup_token: setupToken,
        user_type: userType,
        age: age,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Setup failed');
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

