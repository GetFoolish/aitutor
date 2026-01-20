/**
 * Tutor Feature - Voice AI Tutor powered by Gemini Live API
 *
 * This module provides all components needed for real-time voice tutoring:
 * - TutorService: Direct Gemini Live API connection
 * - TutorClient: Event-driven wrapper for Gemini communication
 * - AudioStreamer: Plays audio from Gemini
 * - AudioRecorder: Captures microphone audio
 * - TutorContext: React context for app-wide tutor state
 * - useTutor: React hook for tutor functionality
 */

// Context and Provider
export { TutorProvider, useTutorContext, useTutorContextOptional } from './TutorContext';
export type { TutorProviderProps } from './TutorContext';

// React Hook
export { useTutor } from './use-tutor';
export type { UseTutorResults } from './use-tutor';

// Core Services
export { TutorService, clearTokenCache } from './tutor-service';
export { TutorClient } from './tutor-client';
export type { TutorClientEventTypes, TranscriptionData } from './tutor-client';

// Audio Components
export { AudioStreamer } from './audio-streamer';
export { AudioRecorder } from './audio-recorder';

// Backward compatibility aliases (can be removed after full migration)
export { TutorProvider as LiveAPIProvider } from './TutorContext';
export { useTutorContext as useLiveAPIContext } from './TutorContext';
export { useTutor as useLiveAPI } from './use-tutor';
export { TutorClient as GenAIProxyClient } from './tutor-client';
