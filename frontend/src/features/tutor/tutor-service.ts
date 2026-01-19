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
import { LiveConnectConfig, LiveServerMessage, Modality } from '@google/genai';
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
        // Token expired - don't throw error here, let http-client handle logout
        // This prevents double error messages
        const error = await response.json().catch(() => ({ detail: 'Authentication required' }));
        throw new Error(error.detail || 'Authentication required. Please log in.');
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

// System prompt cache - keyed by language to support different languages
let systemPromptCache: Map<string, string> = new Map();
let systemPromptLoading: Promise<string> | null = null;
let currentLoadingLanguage: string | null = null;

/**
 * Load system prompt from public directory and inject language preference
 */
async function loadSystemPrompt(preferredLanguage: string = "English"): Promise<string> {
  // Return cached prompt if available for this language
  if (systemPromptCache.has(preferredLanguage)) {
    return systemPromptCache.get(preferredLanguage)!;
  }

  // If already loading for the same language, wait for it
  if (systemPromptLoading && currentLoadingLanguage === preferredLanguage) {
    return systemPromptLoading;
  }

  // Start loading
  currentLoadingLanguage = preferredLanguage;
  systemPromptLoading = (async () => {
    try {
      const response = await fetch('/ai_tutor_system_prompt.md');
      if (!response.ok) {
        console.warn('Could not load system prompt file, using empty prompt');
        return '';
      }
      const prompt = await response.text();
      
      // Inject language instruction
      const languageInstruction = `\n\n## Language Preference\n\nThe student's preferred language is ${preferredLanguage}. You should communicate with the student in ${preferredLanguage} by default. However, if the student explicitly requests to communicate in a different language during the session (e.g., "I want to talk in English", "Can we switch to Spanish?", "Let's speak in Hindi"), you must immediately switch to that requested language and continue the conversation in that language for the remainder of the session. Always prioritize the student's current language preference over the initial default.`;
      
      const fullPrompt = prompt + languageInstruction;
      systemPromptCache.set(preferredLanguage, fullPrompt);
      console.log(`System prompt loaded with language preference: ${preferredLanguage} (${fullPrompt.length} characters)`);
      return fullPrompt;
    } catch (error) {
      console.error('Error loading system prompt:', error);
      return '';
    } finally {
      systemPromptLoading = null;
      currentLoadingLanguage = null;
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
  private _isConnected: boolean = false;
  private _isClosing: boolean = false;
  private _cleanupCallbacks: Set<() => void> = new Set();

  /**
   * Initialize the service
   * Fetches ephemeral token and loads system prompt
   */
  async initialize(preferredLanguage: string = "English"): Promise<void> {
    try {
      // Fetch ephemeral token from backend
      const { token, model } = await fetchGeminiToken();
      this.model = model;

      // Load system prompt with language preference
      this.systemPrompt = await loadSystemPrompt(preferredLanguage);

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
    // CRITICAL: Ensure responseModalities includes AUDIO for voice extraction
    const fullConfig: LiveConnectConfig = {
      ...config,
      systemInstruction: config.systemInstruction || this.systemPrompt,
      // Ensure AUDIO modality is set for voice extraction (use Modality enum, not raw string)
      responseModalities: config.responseModalities ?? [Modality.AUDIO],
    };

    console.log(`Connecting to Gemini model: ${this.model}`);
    console.log(`Voice: ${fullConfig.speechConfig?.voiceConfig?.prebuiltVoiceConfig?.voiceName || 'default'}`);
    console.log(`Response Modalities: ${fullConfig.responseModalities?.join(', ') || 'AUDIO'}`);

    try {
      this.geminiSession = await this.geminiClient.live.connect({
        model: this.model,
        config: fullConfig,
        callbacks: {
          onopen: () => {
            this._isConnected = true;
            this._isClosing = false;
            console.log('Gemini Live API connected');
            callbacks.onopen?.();
          },
          onmessage: (message: LiveServerMessage) => {
            callbacks.onmessage?.(message);
          },
          onerror: (error: ErrorEvent | Error) => {
            const message = 'message' in error ? error.message : String(error);
            // Suppress WebSocket state errors from being logged
            if (!message.includes("CLOSING") && 
                !message.includes("CLOSED") && 
                !message.includes("WebSocket") &&
                !message.includes("already in")) {
              console.error('Gemini error:', message);
            }
            if (error instanceof Error) {
              callbacks.onerror?.(error);
            } else {
              callbacks.onerror?.(new Error(message));
            }
          },
          onclose: (event: { reason?: string }) => {
            const reason = event.reason || 'Unknown reason';
            
            // Log closure reason for debugging
            // Don't suppress any closure messages - we need to see what's happening
            console.log(`Gemini connection closed: ${reason}`);
            
            // Always trigger cleanup when connection closes (stops audio streams)
            // This is necessary to prevent audio from continuing to send
            this._triggerCleanup();
            
            // Call the callback to notify listeners
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
   * Triggers cleanup callbacks to stop audio streams
   */
  disconnect(): void {
    // Trigger cleanup first (stops audio streams)
    this._triggerCleanup();
    
    // Close the session
    if (this.geminiSession) {
      try {
        this.geminiSession.close();
      } catch (error) {
        // Ignore errors during disconnect
      }
      this.geminiSession = null;
      console.log('Gemini session closed');
    }
  }

  /**
   * Get the WebSocket readyState
   * @returns WebSocket readyState or undefined if not accessible
   */
  private getWebSocketReadyState(): number | undefined {
    if (!this.geminiSession) {
      return undefined;
    }

    try {
      // Try multiple ways to access WebSocket state
      let wsState = this.geminiSession.websocket?.readyState;
      
      if (wsState === undefined) {
        // Try alternative property names
        wsState = (this.geminiSession as any)._websocket?.readyState;
      }
      
      if (wsState === undefined) {
        // Try connection property
        wsState = (this.geminiSession as any).connection?.readyState;
      }
      
      if (wsState === undefined) {
        // Try _ws property
        wsState = (this.geminiSession as any)._ws?.readyState;
      }

      return wsState;
    } catch (e) {
      // If we can't access the state, return undefined
      return undefined;
    }
  }

  /**
   * Check if WebSocket is in a valid state for sending data
   * @returns true if ready to send, false otherwise
   */
  private isWebSocketReady(): boolean {
    // First check our internal state flags
    if (!this._isConnected || this._isClosing) {
      return false;
    }

    if (!this.geminiSession) {
      return false;
    }

    // Check WebSocket readyState
    const wsState = this.getWebSocketReadyState();
    
    if (wsState !== undefined) {
      // WebSocket must be OPEN (1) to send data
      // CONNECTING (0), CLOSING (2), CLOSED (3) are not valid
      return wsState === WebSocket.OPEN;
    }

    // If we can't determine state, check internal _state property
    const internalState = (this.geminiSession as any)._state;
    if (internalState === 'closing' || internalState === 'closed') {
      return false;
    }

    // If we can't determine state, assume it's safe to try
    // (will be caught by try-catch if not)
    return true;
  }

  /**
   * Send realtime input (audio/video) to Gemini
   * Includes comprehensive readyState checking to prevent errors
   * STRICT: Only audio is allowed - images/video will cause "Cannot extract voices" error
   */
  sendRealtimeInput(media: { mimeType: string; data: string }): void {
    // Early exit if not connected or closing
    if (!this._isConnected || this._isClosing) {
      return;
    }

    if (!this.geminiSession) {
      // Silently ignore - session not connected
      return;
    }

    // CRITICAL: Gemini Live API ONLY accepts audio via sendRealtimeInput
    // Sending images/video causes "Cannot extract voices from a non-audio request" error
    // Reject any non-audio media immediately
    if (!media.mimeType || !media.mimeType.includes("audio")) {
      // Silently ignore non-audio media (images/video should not be sent here)
      console.debug('Rejected non-audio media:', media.mimeType);
      return;
    }

    // Validate audio format - must be PCM audio for Gemini to extract voices
    if (!media.mimeType.includes("pcm") && !media.mimeType.includes("audio/pcm")) {
      console.debug('Rejected non-PCM audio format:', media.mimeType);
      return;
    }

    // Validate media data before sending
    if (!media.data || media.data.length === 0) {
      // Silently ignore empty data
      return;
    }

    // Validate audio data is substantial enough for Gemini to process
    // Base64 encoded PCM audio should be at least 100 bytes (roughly 25ms of audio at 16kHz)
    if (media.data.length < 100) {
      console.debug('Rejected audio chunk too small:', media.data.length);
      return;
    }

    // Validate base64 format - ensure it's valid base64 encoded audio data
    // Base64 should only contain valid characters
    const base64Regex = /^[A-Za-z0-9+/]*={0,2}$/;
    if (!base64Regex.test(media.data)) {
      console.debug('Rejected invalid base64 audio data');
      return;
    }

    // Comprehensive WebSocket readyState check
    if (!this.isWebSocketReady()) {
      // WebSocket is not in a valid state - trigger cleanup if needed
      const wsState = this.getWebSocketReadyState();
      if (wsState === WebSocket.CLOSING || wsState === WebSocket.CLOSED) {
        // Connection is closing/closed - trigger cleanup
        this._triggerCleanup();
      }
      return;
    }

    // Final check right before sending - WebSocket state can change rapidly
    const finalCheck = this.getWebSocketReadyState();
    if (finalCheck !== undefined && finalCheck !== WebSocket.OPEN) {
      // State changed between checks - trigger cleanup
      if (finalCheck === WebSocket.CLOSING || finalCheck === WebSocket.CLOSED) {
        this._triggerCleanup();
      }
      return;
    }

    // One more check - if cleanup was triggered, don't send
    if (this._isClosing) {
      return;
    }

    // Last check - verify session still exists
    if (!this.geminiSession) {
      return;
    }

    try {
      // Final readyState check INSIDE try block (right before send)
      // This is the last chance to catch state changes
      const lastSecondCheck = this.getWebSocketReadyState();
      if (lastSecondCheck !== undefined && lastSecondCheck !== WebSocket.OPEN) {
        // State changed at the last moment - don't send
        if (lastSecondCheck === WebSocket.CLOSING || lastSecondCheck === WebSocket.CLOSED) {
          this._triggerCleanup();
        }
        return;
      }

      // Final validation: Ensure media object is properly formatted for Gemini
      // Gemini expects: { media: { mimeType: string, data: string } }
      if (!media.mimeType || !media.data) {
        console.debug('Invalid media format, missing mimeType or data');
        return;
      }

      // Ensure mimeType matches expected format for PCM audio
      // Expected formats: "audio/pcm;rate=16000" or "audio/pcm;rate=16000;channels=1"
      // Allow variations but must contain "audio/pcm" and "rate=16000"
      const isValidPCM = media.mimeType.includes("audio/pcm") && 
                         (media.mimeType.includes("rate=16000") || media.mimeType.includes("rate=16k"));
      if (!isValidPCM) {
        console.debug('Audio format mismatch, expected PCM 16kHz:', media.mimeType);
        return;
      }

      // The Google GenAI library's sendRealtimeInput may throw synchronously
      // Wrap in try-catch to handle all possible errors
      // Format: { media: { mimeType: string, data: string } }
      this.geminiSession.sendRealtimeInput({ media });
    } catch (error: any) {
      // Handle WebSocket state errors gracefully
      // The error might be thrown from inside the Google GenAI library
      const errorMsg = error?.message || error?.toString() || String(error);
      
      // If error indicates connection is closed, trigger cleanup immediately
      if (errorMsg.includes("CLOSING") || 
          errorMsg.includes("CLOSED") || 
          errorMsg.includes("WebSocket") ||
          errorMsg.includes("already in")) {
        // Connection is closing/closed - trigger cleanup immediately
        // This will stop the audio recorder from sending more data
        this._triggerCleanup();
        // Don't log or re-throw - this is expected during disconnection
        return;
      }
      
      // Silently ignore expected Gemini errors
      if (errorMsg.includes("Cannot extract voices") ||
          errorMsg.includes("non-audio request")) {
        return;
      }
      
      // Only log truly unexpected errors (use debug to reduce console noise)
      if (errorMsg && !errorMsg.includes("WebSocket")) {
        console.debug('Unexpected error sending realtime input:', errorMsg.substring(0, 100));
      }
    }
  }

  /**
   * Register a cleanup callback to be called when connection closes
   * @param callback Function to call during cleanup
   * @returns Unregister function
   */
  onCleanup(callback: () => void): () => void {
    this._cleanupCallbacks.add(callback);
    // Return unregister function
    return () => {
      this._cleanupCallbacks.delete(callback);
    };
  }

  /**
   * Trigger all registered cleanup callbacks
   * Called automatically when WebSocket closes
   */
  private _triggerCleanup(): void {
    // Only trigger once
    if (this._isClosing) {
      return;
    }
    
    this._isClosing = true;
    this._isConnected = false;
    
    // Call all registered cleanup callbacks
    this._cleanupCallbacks.forEach(callback => {
      try {
        callback();
      } catch (error) {
        console.debug('Error in cleanup callback:', error);
      }
    });
    
    // Clear callbacks after cleanup
    this._cleanupCallbacks.clear();
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
