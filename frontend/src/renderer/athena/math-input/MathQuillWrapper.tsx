/**
 * MathQuill Wrapper
 *
 * Provides a React wrapper around MathQuill for LaTeX input.
 * Handles initialization, updates, and lifecycle management.
 */

import React, {
  useRef,
  useEffect,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from 'react';

// MathQuill interface types
interface MathQuillInterface {
  latex(): string;
  latex(value: string): void;
  cmd(command: string): void;
  keystroke(keys: string): void;
  typedText(text: string): void;
  focus(): void;
  blur(): void;
  reflow(): void;
  select(): void;
  clearSelection(): void;
  moveToLeftEnd(): void;
  moveToRightEnd(): void;
}

interface MathQuillConfig {
  spaceBehavesLikeTab?: boolean;
  leftRightIntoCmdGoes?: 'up' | 'down';
  restrictMismatchedBrackets?: boolean;
  sumStartsWithNEquals?: boolean;
  supSubsRequireOperand?: boolean;
  charsThatBreakOutOfSupSub?: string;
  autoSubscriptNumerals?: boolean;
  autoCommands?: string;
  autoOperatorNames?: string;
  substituteTextarea?: () => HTMLTextAreaElement;
  handlers?: {
    edit?: (mathField: MathQuillInterface) => void;
    enter?: (mathField: MathQuillInterface) => void;
    upOutOf?: (mathField: MathQuillInterface) => void;
    downOutOf?: (mathField: MathQuillInterface) => void;
    moveOutOf?: (direction: 'up' | 'down' | 'left' | 'right', mathField: MathQuillInterface) => void;
  };
}

interface MathQuillStatic {
  getInterface(version: number): {
    MathField(element: HTMLElement, config?: MathQuillConfig): MathQuillInterface;
    StaticMath(element: HTMLElement): MathQuillInterface;
  };
}

export interface MathQuillWrapperProps {
  /** Initial LaTeX value */
  value?: string;
  /** Callback when value changes */
  onChange?: (latex: string) => void;
  /** Callback when Enter is pressed */
  onEnter?: () => void;
  /** Whether the field is read-only */
  readOnly?: boolean;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Placeholder text (shown as faded LaTeX) */
  placeholder?: string;
  /** CSS class name */
  className?: string;
  /** ARIA label */
  ariaLabel?: string;
  /** Auto-commands (space-separated, e.g., "pi theta sqrt") */
  autoCommands?: string;
  /** Auto-operator names (space-separated, e.g., "sin cos tan") */
  autoOperatorNames?: string;
  /** Whether to focus on mount */
  autoFocus?: boolean;
}

export interface MathQuillWrapperRef {
  /** Get current LaTeX value */
  latex(): string;
  /** Set LaTeX value */
  setLatex(value: string): void;
  /** Execute a MathQuill command (e.g., "\\sqrt", "\\frac") */
  cmd(command: string): void;
  /** Type text as if typed on keyboard */
  typedText(text: string): void;
  /** Simulate keystrokes */
  keystroke(keys: string): void;
  /** Focus the input */
  focus(): void;
  /** Blur the input */
  blur(): void;
  /** Select all content */
  selectAll(): void;
  /** Clear the input */
  clear(): void;
  /** Move cursor to start */
  moveToStart(): void;
  /** Move cursor to end */
  moveToEnd(): void;
  /** Check if input has focus */
  hasFocus(): boolean;
}

/**
 * MathQuill input field wrapper
 */
export const MathQuillWrapper = forwardRef<MathQuillWrapperRef, MathQuillWrapperProps>(
  (
    {
      value = '',
      onChange,
      onEnter,
      readOnly = false,
      disabled = false,
      placeholder,
      className = '',
      ariaLabel = 'Math input',
      autoCommands = 'pi theta sqrt',
      autoOperatorNames = 'sin cos tan log ln',
      autoFocus = false,
    },
    ref
  ) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const mathFieldRef = useRef<MathQuillInterface | null>(null);
    const isInitialized = useRef(false);
    const lastValue = useRef(value);

    // Initialize MathQuill
    useEffect(() => {
      if (!containerRef.current || isInitialized.current) {
        return;
      }

      const initMathQuill = async () => {
        try {
          // Dynamic import of MathQuill
          const MQ = await loadMathQuill();

          if (!containerRef.current) return;

          const config: MathQuillConfig = {
            spaceBehavesLikeTab: true,
            leftRightIntoCmdGoes: 'up',
            restrictMismatchedBrackets: true,
            sumStartsWithNEquals: true,
            supSubsRequireOperand: true,
            autoCommands,
            autoOperatorNames,
            handlers: {
              edit: (mathField) => {
                const newLatex = mathField.latex();
                if (newLatex !== lastValue.current) {
                  lastValue.current = newLatex;
                  onChange?.(newLatex);
                }
              },
              enter: () => {
                onEnter?.();
              },
            },
          };

          mathFieldRef.current = MQ.MathField(containerRef.current, config);

          if (value) {
            mathFieldRef.current.latex(value);
            lastValue.current = value;
          }

          if (autoFocus && !disabled && !readOnly) {
            mathFieldRef.current.focus();
          }

          isInitialized.current = true;
        } catch (error) {
          console.error('Failed to initialize MathQuill:', error);
        }
      };

      initMathQuill();
    }, [autoCommands, autoOperatorNames, autoFocus, disabled, readOnly, onChange, onEnter, value]);

    // Update value from props
    useEffect(() => {
      if (mathFieldRef.current && value !== lastValue.current) {
        mathFieldRef.current.latex(value);
        lastValue.current = value;
      }
    }, [value]);

    // Expose methods via ref
    useImperativeHandle(
      ref,
      () => ({
        latex: () => mathFieldRef.current?.latex() || '',
        setLatex: (val: string) => {
          if (mathFieldRef.current) {
            mathFieldRef.current.latex(val);
            lastValue.current = val;
          }
        },
        cmd: (command: string) => mathFieldRef.current?.cmd(command),
        typedText: (text: string) => mathFieldRef.current?.typedText(text),
        keystroke: (keys: string) => mathFieldRef.current?.keystroke(keys),
        focus: () => mathFieldRef.current?.focus(),
        blur: () => mathFieldRef.current?.blur(),
        selectAll: () => mathFieldRef.current?.select(),
        clear: () => {
          if (mathFieldRef.current) {
            mathFieldRef.current.latex('');
            lastValue.current = '';
            onChange?.('');
          }
        },
        moveToStart: () => mathFieldRef.current?.moveToLeftEnd(),
        moveToEnd: () => mathFieldRef.current?.moveToRightEnd(),
        hasFocus: () => {
          if (!containerRef.current) return false;
          return containerRef.current.contains(document.activeElement);
        },
      }),
      [onChange]
    );

    const handleContainerClick = useCallback(() => {
      if (!disabled && !readOnly && mathFieldRef.current) {
        mathFieldRef.current.focus();
      }
    }, [disabled, readOnly]);

    return (
      <div
        className={`athena-mathquill-wrapper ${className} ${disabled ? 'disabled' : ''} ${readOnly ? 'readonly' : ''}`}
        onClick={handleContainerClick}
      >
        <div
          ref={containerRef}
          className="athena-mathquill-field"
          aria-label={ariaLabel}
          role="textbox"
          aria-disabled={disabled}
          aria-readonly={readOnly}
          data-placeholder={placeholder}
        />
        {placeholder && !value && (
          <div className="athena-mathquill-placeholder">{placeholder}</div>
        )}
      </div>
    );
  }
);

MathQuillWrapper.displayName = 'MathQuillWrapper';

/**
 * Load jQuery if not already loaded
 */
async function loadJQuery(): Promise<void> {
  if ((window as unknown as { jQuery?: unknown }).jQuery) {
    return;
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load jQuery'));
    document.head.appendChild(script);
  });
}

/**
 * Load MathQuill dynamically
 */
async function loadMathQuill(): Promise<{
  MathField: (element: HTMLElement, config?: MathQuillConfig) => MathQuillInterface;
  StaticMath: (element: HTMLElement) => MathQuillInterface;
}> {
  // Check if MathQuill is already loaded
  if ((window as unknown as { MathQuill?: MathQuillStatic }).MathQuill) {
    const MQ = (window as unknown as { MathQuill: MathQuillStatic }).MathQuill;
    return MQ.getInterface(2);
  }

  // Load jQuery first (MathQuill dependency)
  await loadJQuery();

  // Load MathQuill CSS
  if (!document.querySelector('link[href*="mathquill"]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdn.jsdelivr.net/npm/mathquill@0.10.1/build/mathquill.css';
    document.head.appendChild(link);
  }

  // Load MathQuill JS
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/mathquill@0.10.1/build/mathquill.min.js';
    script.onload = () => {
      const MQ = (window as unknown as { MathQuill: MathQuillStatic }).MathQuill;
      if (MQ) {
        resolve(MQ.getInterface(2));
      } else {
        reject(new Error('MathQuill failed to initialize'));
      }
    };
    script.onerror = () => reject(new Error('Failed to load MathQuill'));
    document.body.appendChild(script);
  });
}

/**
 * Static math display component
 */
export function StaticMath({
  latex,
  className = '',
}: {
  latex: string;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const renderMath = async () => {
      try {
        const MQ = await loadMathQuill();
        if (containerRef.current) {
          containerRef.current.innerHTML = '';
          const span = document.createElement('span');
          span.textContent = latex;
          containerRef.current.appendChild(span);
          MQ.StaticMath(span);
        }
      } catch (error) {
        console.error('Failed to render static math:', error);
        if (containerRef.current) {
          containerRef.current.textContent = latex;
        }
      }
    };

    renderMath();
  }, [latex]);

  return (
    <div
      ref={containerRef}
      className={`athena-mathquill-static ${className}`}
      aria-label={`Math: ${latex}`}
    />
  );
}

export default MathQuillWrapper;
