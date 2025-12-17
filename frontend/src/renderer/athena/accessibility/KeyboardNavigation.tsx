/**
 * Keyboard Navigation
 *
 * Components and hooks for keyboard accessibility.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';

export interface KeyboardNavigationOptions {
  /** Enable keyboard shortcuts */
  enabled?: boolean;
  /** Trap focus within container */
  trapFocus?: boolean;
  /** Initial focus element selector */
  initialFocus?: string;
  /** On escape callback */
  onEscape?: () => void;
  /** Custom keyboard handlers */
  customHandlers?: Record<string, (e: KeyboardEvent) => void>;
}

/**
 * Hook for keyboard navigation within a container
 */
export function useKeyboardNavigation(
  containerRef: React.RefObject<HTMLElement>,
  options: KeyboardNavigationOptions = {}
) {
  const {
    enabled = true,
    trapFocus = false,
    initialFocus,
    onEscape,
    customHandlers = {},
  } = options;

  const [focusableElements, setFocusableElements] = useState<HTMLElement[]>([]);
  const [currentIndex, setCurrentIndex] = useState(-1);

  // Find all focusable elements
  useEffect(() => {
    if (!containerRef.current || !enabled) return;

    const selector = `
      a[href],
      button:not([disabled]),
      input:not([disabled]),
      select:not([disabled]),
      textarea:not([disabled]),
      [tabindex]:not([tabindex="-1"])
    `;

    const elements = Array.from(
      containerRef.current.querySelectorAll<HTMLElement>(selector)
    );

    setFocusableElements(elements);

    // Set initial focus
    if (initialFocus) {
      const initialElement = containerRef.current.querySelector<HTMLElement>(initialFocus);
      if (initialElement) {
        initialElement.focus();
        setCurrentIndex(elements.indexOf(initialElement));
      }
    }
  }, [containerRef, enabled, initialFocus]);

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // Check custom handlers first
      const key = e.key.toLowerCase();
      if (customHandlers[key]) {
        customHandlers[key](e);
        return;
      }

      switch (e.key) {
        case 'Tab':
          if (trapFocus && focusableElements.length > 0) {
            e.preventDefault();
            const nextIndex = e.shiftKey
              ? (currentIndex - 1 + focusableElements.length) % focusableElements.length
              : (currentIndex + 1) % focusableElements.length;
            focusableElements[nextIndex]?.focus();
            setCurrentIndex(nextIndex);
          }
          break;

        case 'Escape':
          if (onEscape) {
            e.preventDefault();
            onEscape();
          }
          break;

        case 'ArrowDown':
        case 'ArrowRight':
          if (focusableElements.length > 0) {
            e.preventDefault();
            const nextIndex = (currentIndex + 1) % focusableElements.length;
            focusableElements[nextIndex]?.focus();
            setCurrentIndex(nextIndex);
          }
          break;

        case 'ArrowUp':
        case 'ArrowLeft':
          if (focusableElements.length > 0) {
            e.preventDefault();
            const prevIndex = (currentIndex - 1 + focusableElements.length) % focusableElements.length;
            focusableElements[prevIndex]?.focus();
            setCurrentIndex(prevIndex);
          }
          break;

        case 'Home':
          if (focusableElements.length > 0) {
            e.preventDefault();
            focusableElements[0]?.focus();
            setCurrentIndex(0);
          }
          break;

        case 'End':
          if (focusableElements.length > 0) {
            e.preventDefault();
            const lastIndex = focusableElements.length - 1;
            focusableElements[lastIndex]?.focus();
            setCurrentIndex(lastIndex);
          }
          break;
      }
    },
    [enabled, trapFocus, focusableElements, currentIndex, onEscape, customHandlers]
  );

  // Attach event listener
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !enabled) return;

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [containerRef, enabled, handleKeyDown]);

  // Focus management methods
  const focusFirst = useCallback(() => {
    if (focusableElements.length > 0) {
      focusableElements[0]?.focus();
      setCurrentIndex(0);
    }
  }, [focusableElements]);

  const focusLast = useCallback(() => {
    if (focusableElements.length > 0) {
      const lastIndex = focusableElements.length - 1;
      focusableElements[lastIndex]?.focus();
      setCurrentIndex(lastIndex);
    }
  }, [focusableElements]);

  const focusNext = useCallback(() => {
    if (focusableElements.length > 0) {
      const nextIndex = (currentIndex + 1) % focusableElements.length;
      focusableElements[nextIndex]?.focus();
      setCurrentIndex(nextIndex);
    }
  }, [focusableElements, currentIndex]);

  const focusPrevious = useCallback(() => {
    if (focusableElements.length > 0) {
      const prevIndex = (currentIndex - 1 + focusableElements.length) % focusableElements.length;
      focusableElements[prevIndex]?.focus();
      setCurrentIndex(prevIndex);
    }
  }, [focusableElements, currentIndex]);

  return {
    focusableElements,
    currentIndex,
    focusFirst,
    focusLast,
    focusNext,
    focusPrevious,
  };
}

/**
 * Focus trap component
 */
export interface FocusTrapProps {
  /** Whether the trap is active */
  active?: boolean;
  /** Children to wrap */
  children: React.ReactNode;
  /** Initial focus element selector */
  initialFocus?: string;
  /** On escape callback */
  onEscape?: () => void;
  /** Return focus to element when deactivated */
  returnFocus?: boolean;
}

export function FocusTrap({
  active = true,
  children,
  initialFocus,
  onEscape,
  returnFocus = true,
}: FocusTrapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // Store previously focused element
  useEffect(() => {
    if (active) {
      previousActiveElement.current = document.activeElement as HTMLElement;
    }
  }, [active]);

  // Return focus on deactivate
  useEffect(() => {
    return () => {
      if (returnFocus && previousActiveElement.current) {
        previousActiveElement.current.focus();
      }
    };
  }, [returnFocus]);

  useKeyboardNavigation(containerRef, {
    enabled: active,
    trapFocus: active,
    initialFocus,
    onEscape,
  });

  return (
    <div ref={containerRef} className="athena-focus-trap">
      {children}
    </div>
  );
}

/**
 * Skip link component for keyboard users
 */
export function SkipLink({
  targetId,
  children = 'Skip to main content',
}: {
  targetId: string;
  children?: React.ReactNode;
}) {
  const handleClick = useCallback(
    (e: React.MouseEvent | React.KeyboardEvent) => {
      e.preventDefault();
      const target = document.getElementById(targetId);
      if (target) {
        target.focus();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    },
    [targetId]
  );

  return (
    <a
      href={`#${targetId}`}
      className="athena-skip-link"
      onClick={handleClick}
      onKeyDown={(e) => e.key === 'Enter' && handleClick(e)}
    >
      {children}
    </a>
  );
}

/**
 * Roving tabindex hook for lists
 */
export function useRovingTabIndex<T extends HTMLElement>(
  items: Array<React.RefObject<T>>,
  options?: {
    orientation?: 'horizontal' | 'vertical' | 'both';
    wrap?: boolean;
    defaultIndex?: number;
  }
) {
  const {
    orientation = 'vertical',
    wrap = true,
    defaultIndex = 0,
  } = options || {};

  const [activeIndex, setActiveIndex] = useState(defaultIndex);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      const isVertical = orientation === 'vertical' || orientation === 'both';
      const isHorizontal = orientation === 'horizontal' || orientation === 'both';

      let nextIndex = index;

      if (isVertical && e.key === 'ArrowDown') {
        nextIndex = wrap
          ? (index + 1) % items.length
          : Math.min(index + 1, items.length - 1);
      } else if (isVertical && e.key === 'ArrowUp') {
        nextIndex = wrap
          ? (index - 1 + items.length) % items.length
          : Math.max(index - 1, 0);
      } else if (isHorizontal && e.key === 'ArrowRight') {
        nextIndex = wrap
          ? (index + 1) % items.length
          : Math.min(index + 1, items.length - 1);
      } else if (isHorizontal && e.key === 'ArrowLeft') {
        nextIndex = wrap
          ? (index - 1 + items.length) % items.length
          : Math.max(index - 1, 0);
      } else if (e.key === 'Home') {
        nextIndex = 0;
      } else if (e.key === 'End') {
        nextIndex = items.length - 1;
      } else {
        return;
      }

      e.preventDefault();
      setActiveIndex(nextIndex);
      items[nextIndex]?.current?.focus();
    },
    [items, orientation, wrap]
  );

  const getTabIndex = useCallback(
    (index: number) => (index === activeIndex ? 0 : -1),
    [activeIndex]
  );

  return {
    activeIndex,
    setActiveIndex,
    handleKeyDown,
    getTabIndex,
  };
}

export default {
  useKeyboardNavigation,
  FocusTrap,
  SkipLink,
  useRovingTabIndex,
};
