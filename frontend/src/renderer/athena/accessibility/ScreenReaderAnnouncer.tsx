/**
 * Screen Reader Announcer
 *
 * Component for making live announcements to screen readers.
 */

import React, { useState, useCallback, useEffect, useRef, createContext, useContext } from 'react';

export type AnnouncementPoliteness = 'polite' | 'assertive' | 'off';

export interface Announcement {
  id: string;
  message: string;
  politeness: AnnouncementPoliteness;
  timestamp: number;
}

export interface ScreenReaderAnnouncerContextValue {
  /** Make an announcement */
  announce: (message: string, politeness?: AnnouncementPoliteness) => void;
  /** Clear all announcements */
  clear: () => void;
}

const ScreenReaderAnnouncerContext = createContext<ScreenReaderAnnouncerContextValue | null>(null);

/**
 * Provider for screen reader announcements
 */
export function ScreenReaderAnnouncerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [politeAnnouncement, setPoliteAnnouncement] = useState('');
  const [assertiveAnnouncement, setAssertiveAnnouncement] = useState('');
  const clearTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const announce = useCallback((message: string, politeness: AnnouncementPoliteness = 'polite') => {
    if (politeness === 'off') return;

    // Clear after announcement is made
    if (clearTimeoutRef.current) {
      clearTimeout(clearTimeoutRef.current);
    }

    if (politeness === 'assertive') {
      setAssertiveAnnouncement(message);
      clearTimeoutRef.current = setTimeout(() => setAssertiveAnnouncement(''), 1000);
    } else {
      setPoliteAnnouncement(message);
      clearTimeoutRef.current = setTimeout(() => setPoliteAnnouncement(''), 1000);
    }
  }, []);

  const clear = useCallback(() => {
    setPoliteAnnouncement('');
    setAssertiveAnnouncement('');
  }, []);

  useEffect(() => {
    return () => {
      if (clearTimeoutRef.current) {
        clearTimeout(clearTimeoutRef.current);
      }
    };
  }, []);

  return (
    <ScreenReaderAnnouncerContext.Provider value={{ announce, clear }}>
      {children}

      {/* Polite live region */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="athena-sr-only"
      >
        {politeAnnouncement}
      </div>

      {/* Assertive live region */}
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="athena-sr-only"
      >
        {assertiveAnnouncement}
      </div>
    </ScreenReaderAnnouncerContext.Provider>
  );
}

/**
 * Hook for making screen reader announcements
 */
export function useScreenReaderAnnouncer(): ScreenReaderAnnouncerContextValue {
  const context = useContext(ScreenReaderAnnouncerContext);

  if (!context) {
    // Return a no-op implementation if not within provider
    return {
      announce: () => {},
      clear: () => {},
    };
  }

  return context;
}

/**
 * Standalone announcer component (without context)
 */
export function ScreenReaderAnnouncer({
  message,
  politeness = 'polite',
  clearDelay = 1000,
}: {
  message: string;
  politeness?: AnnouncementPoliteness;
  clearDelay?: number;
}) {
  const [currentMessage, setCurrentMessage] = useState(message);

  useEffect(() => {
    setCurrentMessage(message);

    const timeout = setTimeout(() => {
      setCurrentMessage('');
    }, clearDelay);

    return () => clearTimeout(timeout);
  }, [message, clearDelay]);

  if (politeness === 'off' || !currentMessage) {
    return null;
  }

  return (
    <div
      role={politeness === 'assertive' ? 'alert' : 'status'}
      aria-live={politeness}
      aria-atomic="true"
      className="athena-sr-only"
    >
      {currentMessage}
    </div>
  );
}

/**
 * Visually hidden component (screen reader only)
 */
export function VisuallyHidden({
  children,
  as: Component = 'span',
}: {
  children: React.ReactNode;
  as?: keyof JSX.IntrinsicElements;
}) {
  return <Component className="athena-sr-only">{children}</Component>;
}

/**
 * Hook for announcing on value changes
 */
export function useAnnounceOnChange<T>(
  value: T,
  getMessage: (value: T) => string,
  options?: {
    politeness?: AnnouncementPoliteness;
    debounce?: number;
  }
) {
  const { announce } = useScreenReaderAnnouncer();
  const previousValue = useRef<T>(value);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (value !== previousValue.current) {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      const makeAnnouncement = () => {
        const message = getMessage(value);
        if (message) {
          announce(message, options?.politeness);
        }
        previousValue.current = value;
      };

      if (options?.debounce) {
        debounceRef.current = setTimeout(makeAnnouncement, options.debounce);
      } else {
        makeAnnouncement();
      }
    }

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [value, getMessage, announce, options?.politeness, options?.debounce]);
}

export default {
  ScreenReaderAnnouncerProvider,
  useScreenReaderAnnouncer,
  ScreenReaderAnnouncer,
  VisuallyHidden,
  useAnnounceOnChange,
};
