/**
 * Payment API client for Stripe integration
 */
import { httpClient } from './http-client';

const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';

export interface CheckoutSessionResponse {
  checkout_url: string;
  session_id: string;
}

class PaymentAPI {
  async createCheckoutSession(plan: 'starter' | 'pro' | 'premium'): Promise<CheckoutSessionResponse> {
    const token = localStorage.getItem('jwt_token');
    if (!token) {
      throw new Error('Not authenticated');
    }

    const response = await httpClient.fetch(`${AUTH_SERVICE_URL}/payment/create-checkout-session`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ plan }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create checkout session');
    }

    return response.json();
  }
}

export const paymentAPI = new PaymentAPI();
