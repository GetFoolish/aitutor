/**
 * IP Geolocation utility using backend endpoint
 */

export interface LocationData {
  country: string | null;
  country_code: string | null;
  error?: string;
}

export async function detectLocationFromIP(): Promise<LocationData> {
  try {
    const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/detect-location`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error('Failed to detect location');
    }

    const data = await response.json();
    return {
      country: data.country || null,
      country_code: data.country_code || null,
      error: data.error || undefined,
    };
  } catch (error) {
    console.error('Error detecting location:', error);
    return {
      country: null,
      country_code: null,
      error: 'Could not detect location',
    };
  }
}

