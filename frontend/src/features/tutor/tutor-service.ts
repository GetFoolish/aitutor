/**
 * Tutor Service - Direct Gemini Live API Integration
 *
 * This service manages direct connection to Google Gemini Live API
 * from the frontend, eliminating the need for a backend proxy.
 *
 * This is a separate service component that handles:
 * - Direct WebSocket connection to Gemini Live API
 * - System prompt loading and injection
 * - Message processing and forwarding
 * - Error handling and reconnection logic
 */

import { GoogleGenAI } from '@google/genai';
import { LiveConnectConfig, LiveServerMessage } from '@google/genai';
import { apiUtils } from '../../lib/api-utils';

const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';

// Token cache - only caches model, token is always fresh (single-use)
interface GeminiTokenResponse {
  token: string;
  model: string;
}

let cachedModel: string | null = null;

/**
 * Fetch ephemeral token from AuthService
 * Uses JWT authentication to ensure only authenticated users can access
 * Token is single-use - always fetches fresh token for each connection
 */
async function fetchGeminiToken(): Promise<{ token: string; model: string }> {
  try {
    const response = await apiUtils.get(`${AUTH_SERVICE_URL}/auth/gemini-token`);

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Authentication required. Please log in.');
      }
      throw new Error(`Failed to fetch token: ${response.status} ${response.statusText}`);
    }

    const data: GeminiTokenResponse = await response.json();

    if (!data.token) {
      throw new Error('Token not found in response');
    }

    if (!data.model) {
      throw new Error('Model not found in response');
    }

    // Cache only the model (doesn't change), token is always fresh
    cachedModel = data.model;

    console.log('Fetched fresh ephemeral token:', data.token.substring(0, 30) + '...');
    console.log('Model:', cachedModel);

    return { token: data.token, model: cachedModel };
  } catch (error) {
    console.error('Error fetching Gemini token:', error);
    throw error;
  }
}

/**
 * Clear cached model (useful for logout)
 */
export function clearTokenCache(): void {
  cachedModel = null;
}

// System prompt cache
let systemPromptCache: string | null = null;
let systemPromptLoading: Promise<string> | null = null;

/**
 * Load system prompt from public directory
 */
async function loadSystemPrompt(): Promise<string> {
  // Return cached prompt if available
  if (systemPromptCache) {
    return systemPromptCache;
  }

  // If already loading, wait for it
  if (systemPromptLoading) {
    return systemPromptLoading;
  }

  // Start loading
  systemPromptLoading = (async () => {
    try {
      const response = await fetch('/ai_tutor_system_prompt.md');
      if (!response.ok) {
        console.warn('Could not load system prompt file, using empty prompt');
        return '';
      }
      const prompt = await response.text();
      systemPromptCache = prompt;
      console.log(`System prompt loaded (${prompt.length} characters)`);
      return prompt;
    } catch (error) {
      console.error('Error loading system prompt:', error);
      return '';
    } finally {
      systemPromptLoading = null;
    }
  })();

  return systemPromptLoading;
}

/**
 * Tutor Service Class
 * Manages direct connection to Gemini Live API
 */
export class TutorService {
  private geminiClient: GoogleGenAI | null = null;
  private geminiSession: any = null;
  private model: string = '';
  private systemPrompt: string = '';

  /**
   * Initialize the service
   * Fetches ephemeral token and loads system prompt
   */
  async initialize(): Promise<void> {
    try {
      // Fetch ephemeral token from backend
      const { token, model } = await fetchGeminiToken();
      this.model = model;

      // Load system prompt
      this.systemPrompt = await loadSystemPrompt();

      // Initialize Gemini client with ephemeral token
      // IMPORTANT: Ephemeral tokens require v1alpha API version
      console.log('Initializing GoogleGenAI with ephemeral token:', token.substring(0, 30) + '...');
      this.geminiClient = new GoogleGenAI({
        apiKey: token,
        apiVersion: 'v1alpha'
      });
      console.log('GoogleGenAI client initialized');
    } catch (error) {
      console.error('Failed to initialize Tutor Service:', error);
      throw error;
    }
  }

  /**
   * Connect to Gemini Live API
   */
  async connect(
    config: LiveConnectConfig,
    callbacks: {
      onopen?: () => void;
      onmessage?: (message: LiveServerMessage) => void;
      onerror?: (error: Error) => void;
      onclose?: (event: { reason?: string }) => void;
    }
  ): Promise<void> {
    if (!this.geminiClient) {
      throw new Error('Tutor Service not initialized. Call initialize() first.');
    }

    // Inject system prompt into config
    const fullConfig: LiveConnectConfig = {
      ...config,
      systemInstruction: config.systemInstruction || this.systemPrompt,
    };

    console.log(`Connecting to Gemini model: ${this.model}`);
    console.log(`Voice: ${fullConfig.speechConfig?.voiceConfig?.prebuiltVoiceConfig?.voiceName || 'default'}`);

    try {
      this.geminiSession = await this.geminiClient.live.connect({
        model: this.model,
        config: fullConfig,
        callbacks: {
          onopen: () => {
            console.log('Gemini Live API connected');
            callbacks.onopen?.();
          },
          onmessage: (message: LiveServerMessage) => {
            callbacks.onmessage?.(message);
          },
          onerror: (error: ErrorEvent | Error) => {
            const message = 'message' in error ? error.message : String(error);
            console.error('Gemini error:', message);
            if (error instanceof Error) {
              callbacks.onerror?.(error);
            } else {
              callbacks.onerror?.(new Error(message));
            }
          },
          onclose: (event: { reason?: string }) => {
            console.log(`Gemini connection closed: ${event.reason || 'Unknown reason'}`);
            callbacks.onclose?.(event);
          },
        },
      });

      console.log('Gemini session established');
    } catch (error) {
      console.error('Failed to connect to Gemini:', error);
      throw error;
    }
  }

  /**
   * Disconnect from Gemini Live API
   */
  disconnect(): void {
    if (this.geminiSession) {
      this.geminiSession.close();
      this.geminiSession = null;
      console.log('Gemini session closed');
    }
  }

  /**
   * Send realtime input (audio/video) to Gemini
   */
  sendRealtimeInput(media: { mimeType: string; data: string }): void {
    if (!this.geminiSession) {
      console.warn('Cannot send realtime input: session not connected');
      return;
    }

    try {
      this.geminiSession.sendRealtimeInput({ media });
    } catch (error) {
      console.error('Error sending realtime input:', error);
    }
  }

  /**
   * Send tool response to Gemini
   */
  sendToolResponse(toolResponse: any): void {
    if (!this.geminiSession) {
      console.warn('Cannot send tool response: session not connected');
      return;
    }

    try {
      this.geminiSession.sendToolResponse(toolResponse);
    } catch (error) {
      console.error('Error sending tool response:', error);
    }
  }

  /**
   * Send client content (text messages) to Gemini
   */
  sendClientContent(parts: any[], turnComplete: boolean = true): void {
    if (!this.geminiSession) {
      console.warn('Cannot send client content: session not connected');
      return;
    }

    try {
      this.geminiSession.sendClientContent({
        turns: parts,
        turnComplete,
      });
    } catch (error) {
      console.error('Error sending client content:', error);
    }
  }

  /**
   * Clear token cache (useful for logout)
   */
  clearCache(): void {
    clearTokenCache();
    this.geminiClient = null;
    this.geminiSession = null;
  }

  /**
   * Get current session status
   */
  isConnected(): boolean {
    return this.geminiSession !== null;
  }

  /**
   * Inject homework content into the active session
   * This tells the tutor about uploaded homework so it can help
   */
  injectHomeworkContext(homeworkContent: string, filename: string): void {
    if (!this.geminiSession) {
      console.warn('Cannot inject homework: session not connected');
      return;
    }

    const contextMessage = `[HOMEWORK UPLOADED]
The student has uploaded homework that they need help with.

Filename: ${filename}

--- HOMEWORK CONTENT ---
${homeworkContent}
--- END HOMEWORK CONTENT ---

Please acknowledge that you can see their homework and offer to help them work through it. Remember to guide them with hints and questions rather than giving direct answers.`;

    try {
      this.geminiSession.sendClientContent({
        turns: [{ role: 'user', parts: [{ text: contextMessage }] }],
        turnComplete: true,
      });
      console.log(`Homework context injected: ${filename}`);
    } catch (error) {
      console.error('Error injecting homework context:', error);
    }
  }
}
