/**
 * Expression Input
 *
 * Combined math expression input component with:
 * - MathQuill-based input field
 * - Optional math keypad
 * - Keyboard shortcut support
 */

import React, {
  useRef,
  useState,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { MathQuillWrapper, type MathQuillWrapperRef } from './MathQuillWrapper';
import { MathKeypad, FloatingMathKeypad, useMathKeypad } from './MathKeypad';
import type { ButtonSetId } from './ButtonSets';

export interface ExpressionInputProps {
  /** Current LaTeX value */
  value?: string;
  /** Callback when value changes */
  onChange?: (latex: string) => void;
  /** Callback when Enter is pressed */
  onSubmit?: (latex: string) => void;
  /** Whether the input is read-only */
  readOnly?: boolean;
  /** Whether the input is disabled */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** ARIA label */
  ariaLabel?: string;
  /** Button sets for the keypad */
  buttonSets?: ButtonSetId[];
  /** Whether to show the keypad */
  showKeypad?: boolean;
  /** Keypad position */
  keypadPosition?: 'bottom' | 'floating' | 'none';
  /** Whether to show keypad toggle button */
  showKeypadToggle?: boolean;
  /** Custom class name */
  className?: string;
  /** Size variant */
  size?: 'small' | 'normal' | 'large';
  /** Error state */
  error?: boolean;
  /** Error message */
  errorMessage?: string;
}

export interface ExpressionInputRef {
  /** Get current LaTeX value */
  getValue(): string;
  /** Set LaTeX value */
  setValue(latex: string): void;
  /** Focus the input */
  focus(): void;
  /** Blur the input */
  blur(): void;
  /** Clear the input */
  clear(): void;
  /** Insert LaTeX at cursor */
  insert(latex: string): void;
  /** Show the keypad */
  showKeypad(): void;
  /** Hide the keypad */
  hideKeypad(): void;
  /** Toggle keypad visibility */
  toggleKeypad(): void;
}

/**
 * Expression input with optional keypad
 */
export const ExpressionInput = forwardRef<ExpressionInputRef, ExpressionInputProps>(
  (
    {
      value = '',
      onChange,
      onSubmit,
      readOnly = false,
      disabled = false,
      placeholder = 'Enter expression...',
      ariaLabel = 'Math expression input',
      buttonSets = ['basic', 'algebra'],
      showKeypad: initialShowKeypad = false,
      keypadPosition = 'bottom',
      showKeypadToggle = true,
      className = '',
      size = 'normal',
      error = false,
      errorMessage,
    },
    ref
  ) => {
    const mathQuillRef = useRef<MathQuillWrapperRef>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [keypadVisible, setKeypadVisible] = useState(initialShowKeypad);
    const [inputRect, setInputRect] = useState<DOMRect | undefined>();

    // Handle value change
    const handleChange = useCallback(
      (latex: string) => {
        onChange?.(latex);
      },
      [onChange]
    );

    // Handle Enter key
    const handleEnter = useCallback(() => {
      const latex = mathQuillRef.current?.latex() || '';
      onSubmit?.(latex);
    }, [onSubmit]);

    // Handle keypad insert
    const handleKeypadInsert = useCallback((latex: string) => {
      mathQuillRef.current?.cmd(latex);
      mathQuillRef.current?.focus();
    }, []);

    // Handle keypad action
    const handleKeypadAction = useCallback((action: string) => {
      if (!mathQuillRef.current) return;

      switch (action) {
        case 'backspace':
          mathQuillRef.current.keystroke('Backspace');
          break;
        case 'clear':
          mathQuillRef.current.clear();
          break;
        case 'left':
          mathQuillRef.current.keystroke('Left');
          break;
        case 'right':
          mathQuillRef.current.keystroke('Right');
          break;
      }
      mathQuillRef.current.focus();
    }, []);

    // Toggle keypad
    const toggleKeypad = useCallback(() => {
      if (!keypadVisible && containerRef.current) {
        setInputRect(containerRef.current.getBoundingClientRect());
      }
      setKeypadVisible((prev) => !prev);
    }, [keypadVisible]);

    // Show keypad
    const showKeypad = useCallback(() => {
      if (containerRef.current) {
        setInputRect(containerRef.current.getBoundingClientRect());
      }
      setKeypadVisible(true);
    }, []);

    // Hide keypad
    const hideKeypad = useCallback(() => {
      setKeypadVisible(false);
    }, []);

    // Handle focus
    const handleFocus = useCallback(() => {
      if (keypadPosition === 'floating' && containerRef.current) {
        setInputRect(containerRef.current.getBoundingClientRect());
      }
    }, [keypadPosition]);

    // Expose methods via ref
    useImperativeHandle(
      ref,
      () => ({
        getValue: () => mathQuillRef.current?.latex() || '',
        setValue: (latex: string) => mathQuillRef.current?.setLatex(latex),
        focus: () => mathQuillRef.current?.focus(),
        blur: () => mathQuillRef.current?.blur(),
        clear: () => mathQuillRef.current?.clear(),
        insert: (latex: string) => mathQuillRef.current?.cmd(latex),
        showKeypad,
        hideKeypad,
        toggleKeypad,
      }),
      [showKeypad, hideKeypad, toggleKeypad]
    );

    return (
      <div
        ref={containerRef}
        className={`athena-expression-input athena-expression-input-${size} ${error ? 'error' : ''} ${className}`}
      >
        {/* Input row */}
        <div className="athena-expression-input-row">
          {/* MathQuill input */}
          <MathQuillWrapper
            ref={mathQuillRef}
            value={value}
            onChange={handleChange}
            onEnter={handleEnter}
            readOnly={readOnly}
            disabled={disabled}
            placeholder={placeholder}
            ariaLabel={ariaLabel}
            className="athena-expression-input-field"
          />

          {/* Keypad toggle button */}
          {showKeypadToggle && keypadPosition !== 'none' && !disabled && !readOnly && (
            <button
              type="button"
              className={`athena-expression-keypad-toggle ${keypadVisible ? 'active' : ''}`}
              onClick={toggleKeypad}
              aria-label={keypadVisible ? 'Hide keypad' : 'Show keypad'}
              aria-expanded={keypadVisible}
            >
              <KeypadIcon />
            </button>
          )}
        </div>

        {/* Error message */}
        {error && errorMessage && (
          <div className="athena-expression-error" role="alert">
            {errorMessage}
          </div>
        )}

        {/* Bottom keypad */}
        {keypadPosition === 'bottom' && keypadVisible && !disabled && !readOnly && (
          <MathKeypad
            buttonSets={buttonSets}
            onInsert={handleKeypadInsert}
            onAction={handleKeypadAction}
            position="inline"
            visible={true}
          />
        )}

        {/* Floating keypad */}
        {keypadPosition === 'floating' && keypadVisible && !disabled && !readOnly && (
          <FloatingMathKeypad
            buttonSets={buttonSets}
            onInsert={handleKeypadInsert}
            onAction={handleKeypadAction}
            targetRect={inputRect}
            visible={true}
          />
        )}
      </div>
    );
  }
);

ExpressionInput.displayName = 'ExpressionInput';

/**
 * Keypad icon component
 */
function KeypadIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <rect x="2" y="2" width="4" height="4" rx="0.5" />
      <rect x="8" y="2" width="4" height="4" rx="0.5" />
      <rect x="14" y="2" width="4" height="4" rx="0.5" />
      <rect x="2" y="8" width="4" height="4" rx="0.5" />
      <rect x="8" y="8" width="4" height="4" rx="0.5" />
      <rect x="14" y="8" width="4" height="4" rx="0.5" />
      <rect x="2" y="14" width="4" height="4" rx="0.5" />
      <rect x="8" y="14" width="4" height="4" rx="0.5" />
      <rect x="14" y="14" width="4" height="4" rx="0.5" />
    </svg>
  );
}

/**
 * Simple expression display (non-editable)
 */
export function ExpressionDisplay({
  latex,
  className = '',
  size = 'normal',
}: {
  latex: string;
  className?: string;
  size?: 'small' | 'normal' | 'large';
}) {
  return (
    <div
      className={`athena-expression-display athena-expression-display-${size} ${className}`}
    >
      <MathQuillWrapper
        value={latex}
        readOnly
        className="athena-expression-display-field"
      />
    </div>
  );
}

export default ExpressionInput;
