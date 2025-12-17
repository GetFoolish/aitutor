/**
 * Math Keypad
 *
 * Touch-friendly math input keypad with configurable button sets.
 * Supports multiple layouts for different math contexts.
 */

import React, { useState, useCallback, useMemo } from 'react';
import type { ButtonSet, MathButton, ButtonSetId } from './ButtonSets';
import {
  BASIC_SET,
  ALGEBRA_SET,
  TRIG_SET,
  CALCULUS_SET,
  CHEMISTRY_SET,
  getButtonSet,
} from './ButtonSets';

export interface MathKeypadProps {
  /** Button sets to include */
  buttonSets?: ButtonSetId[];
  /** Callback when a button is pressed */
  onInsert?: (latex: string) => void;
  /** Callback for action buttons (backspace, clear, etc.) */
  onAction?: (action: string) => void;
  /** Position of the keypad */
  position?: 'bottom' | 'inline' | 'floating';
  /** Whether the keypad is visible */
  visible?: boolean;
  /** Whether the keypad is compact */
  compact?: boolean;
  /** Custom class name */
  className?: string;
  /** Whether to show tab navigation between sets */
  showTabs?: boolean;
}

/**
 * Math keypad component
 */
export function MathKeypad({
  buttonSets = ['basic'],
  onInsert,
  onAction,
  position = 'bottom',
  visible = true,
  compact = false,
  className = '',
  showTabs = true,
}: MathKeypadProps) {
  // Get the button set objects
  const sets = useMemo(() => {
    return buttonSets
      .map((id) => getButtonSet(id))
      .filter((set): set is ButtonSet => set !== null);
  }, [buttonSets]);

  // Active tab state
  const [activeTab, setActiveTab] = useState(0);

  // Get current button set
  const currentSet = sets[activeTab] || sets[0] || BASIC_SET;

  // Handle button press
  const handleButtonPress = useCallback(
    (button: MathButton) => {
      if (button.type === 'action') {
        onAction?.(button.id);
      } else if (button.latex) {
        onInsert?.(button.latex);
      }
    },
    [onInsert, onAction]
  );

  // Render a single button
  const renderButton = useCallback(
    (button: MathButton, index: number) => {
      const width = button.width || 1;
      const style = width !== 1 ? { flex: width } : undefined;

      return (
        <button
          key={`${button.id}-${index}`}
          className={`athena-keypad-button athena-keypad-button-${button.type}`}
          onClick={() => handleButtonPress(button)}
          aria-label={button.ariaLabel}
          style={style}
          type="button"
        >
          <span className="athena-keypad-button-label">{button.label}</span>
        </button>
      );
    },
    [handleButtonPress]
  );

  // Render a row of buttons
  const renderRow = useCallback(
    (buttons: MathButton[], rowIndex: number) => {
      return (
        <div key={rowIndex} className="athena-keypad-row">
          {buttons.map((button, buttonIndex) => renderButton(button, buttonIndex))}
        </div>
      );
    },
    [renderButton]
  );

  if (!visible) {
    return null;
  }

  const keypadStyles: React.CSSProperties = {
    backgroundColor: '#f5f5f5',
    borderRadius: '8px',
    padding: '8px',
    border: '1px solid #e0e0e0',
    marginTop: '8px',
  };

  const tabsStyles: React.CSSProperties = {
    display: 'flex',
    gap: '4px',
    marginBottom: '8px',
    borderBottom: '1px solid #e0e0e0',
    paddingBottom: '8px',
  };

  const tabStyles = (isActive: boolean): React.CSSProperties => ({
    padding: '6px 12px',
    border: 'none',
    background: isActive ? '#667eea' : 'transparent',
    color: isActive ? 'white' : '#666',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 500,
  });

  const gridStyles: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  };

  const rowStyles: React.CSSProperties = {
    display: 'flex',
    gap: '4px',
  };

  const buttonStyles: React.CSSProperties = {
    flex: 1,
    padding: '12px 8px',
    border: '1px solid #ddd',
    background: 'white',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: 500,
    minWidth: '40px',
    transition: 'all 0.1s',
  };

  return (
    <div
      className={`athena-keypad athena-keypad-${position} ${compact ? 'athena-keypad-compact' : ''} ${className}`}
      role="group"
      aria-label="Math keypad"
      style={keypadStyles}
    >
      {/* Tab navigation */}
      {showTabs && sets.length > 1 && (
        <div className="athena-keypad-tabs" role="tablist" style={tabsStyles}>
          {sets.map((set, index) => (
            <button
              key={set.id}
              className={`athena-keypad-tab ${index === activeTab ? 'active' : ''}`}
              onClick={() => setActiveTab(index)}
              role="tab"
              aria-selected={index === activeTab}
              aria-controls={`panel-${set.id}`}
              type="button"
              style={tabStyles(index === activeTab)}
            >
              {set.name}
            </button>
          ))}
        </div>
      )}

      {/* Button grid */}
      <div
        className="athena-keypad-grid"
        role="tabpanel"
        id={`panel-${currentSet.id}`}
        aria-labelledby={`tab-${currentSet.id}`}
        style={gridStyles}
      >
        {currentSet.rows.map((row, rowIndex) => (
          <div key={rowIndex} className="athena-keypad-row" style={rowStyles}>
            {row.map((button, buttonIndex) => {
              const width = button.width || 1;
              return (
                <button
                  key={`${button.id}-${buttonIndex}`}
                  className={`athena-keypad-button athena-keypad-button-${button.type}`}
                  onClick={() => handleButtonPress(button)}
                  aria-label={button.ariaLabel}
                  style={{ ...buttonStyles, flex: width }}
                  type="button"
                >
                  <span className="athena-keypad-button-label">{button.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Floating keypad that appears near an input
 */
export function FloatingMathKeypad({
  targetRect,
  ...props
}: MathKeypadProps & {
  targetRect?: DOMRect;
}) {
  const style = useMemo(() => {
    if (!targetRect) {
      return {};
    }

    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;

    // Position below the target by default
    let top = targetRect.bottom + 8;
    let left = targetRect.left;

    // If it would go off the bottom, position above
    if (top + 300 > viewportHeight) {
      top = targetRect.top - 300 - 8;
    }

    // If it would go off the right, align to right edge
    if (left + 320 > viewportWidth) {
      left = viewportWidth - 320 - 16;
    }

    // Ensure not off the left
    if (left < 16) {
      left = 16;
    }

    return {
      position: 'fixed' as const,
      top: `${top}px`,
      left: `${left}px`,
      zIndex: 1000,
    };
  }, [targetRect]);

  return (
    <div style={style} className="athena-floating-keypad">
      <MathKeypad {...props} position="floating" />
    </div>
  );
}

/**
 * Hook for managing keypad visibility and actions
 */
export function useMathKeypad(
  inputRef: React.RefObject<{ cmd: (latex: string) => void; latex: () => string; focus: () => void } | null>
) {
  const [visible, setVisible] = useState(false);
  const [targetRect, setTargetRect] = useState<DOMRect | undefined>();

  const show = useCallback((rect?: DOMRect) => {
    setVisible(true);
    setTargetRect(rect);
  }, []);

  const hide = useCallback(() => {
    setVisible(false);
  }, []);

  const toggle = useCallback(
    (rect?: DOMRect) => {
      if (visible) {
        hide();
      } else {
        show(rect);
      }
    },
    [visible, show, hide]
  );

  const handleInsert = useCallback(
    (latex: string) => {
      if (inputRef.current) {
        inputRef.current.cmd(latex);
        inputRef.current.focus();
      }
    },
    [inputRef]
  );

  const handleAction = useCallback(
    (action: string) => {
      if (!inputRef.current) return;

      switch (action) {
        case 'backspace':
          inputRef.current.cmd('Backspace');
          break;
        case 'clear':
          inputRef.current.cmd('\\selectall');
          inputRef.current.cmd('Backspace');
          break;
        case 'left':
          inputRef.current.cmd('Left');
          break;
        case 'right':
          inputRef.current.cmd('Right');
          break;
      }
      inputRef.current.focus();
    },
    [inputRef]
  );

  return {
    visible,
    targetRect,
    show,
    hide,
    toggle,
    handleInsert,
    handleAction,
  };
}

export default MathKeypad;
