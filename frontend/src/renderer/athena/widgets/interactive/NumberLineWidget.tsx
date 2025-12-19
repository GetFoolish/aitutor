/**
 * Number Line Widget
 *
 * Interactive number line for placing points.
 */

import React, { useState, useCallback, useRef } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

interface NumberLineOptions {
  range?: [number, number];
  numDivisions?: number;
  snapDivisions?: number;
  tickStep?: number;
  labelRange?: [number, number];
  labelStyle?: 'decimal' | 'fraction' | 'mixed';
  labelTicks?: boolean;
  correctX?: number;
  initialX?: number;
  divisionRange?: [number, number]; // Min/max divisions user can select
  isTickCtrl?: boolean; // Whether to show tick/division control
}

export interface NumberLineWidgetProps extends WidgetProps<NumberLineOptions> {}

export function NumberLineWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: NumberLineWidgetProps) {
  const options = widget.options || {};
  const range = options.range || [-5, 5];
  const tickStep = options.tickStep || 1;
  const correctX = options.correctX;

  const containerRef = useRef<HTMLDivElement>(null);
  // Initialize to range start if no value/initialX provided (so dot is visible)
  const [pointX, setPointX] = useState<number | null>(
    value !== undefined ? (value as number) : (options.initialX ?? range[0])
  );
  const [isDragging, setIsDragging] = useState(false);

  // Division control - allow user to change number of tick marks
  // For small ranges like [0,1], we need more divisions to be useful
  const isSmallRange = Math.abs(range[1] - range[0]) <= 1;
  const defaultMinDivisions = isSmallRange ? 2 : 2;
  const divisionRange = options.divisionRange || [defaultMinDivisions, 12];
  const showDivisionControl = options.isTickCtrl !== false; // Show by default
  // Calculate initial divisions - use numDivisions if set, otherwise default to something reasonable
  const getInitialDivisions = () => {
    if (options.numDivisions) return options.numDivisions;
    const minDiv = options.divisionRange?.[0] || defaultMinDivisions;
    const maxDiv = options.divisionRange?.[1] || 12;
    // For small ranges, start with more divisions
    const calculated = isSmallRange
      ? 4 // Default to 4 divisions for [0,1] type ranges
      : Math.round((range[1] - range[0]) / tickStep) || 4;
    return Math.max(minDiv, Math.min(maxDiv, calculated));
  };
  const [userDivisions, setUserDivisions] = useState<number>(getInitialDivisions);

  const themeStyles = {
    light: { bg: '#fff', line: '#374151', tick: '#6b7280', point: '#22c55e', correct: '#22c55e', incorrect: '#ef4444', label: '#1f2937' },
    dark: { bg: '#1f2937', line: '#e5e7eb', tick: '#9ca3af', point: '#4ade80', correct: '#4ade80', incorrect: '#f87171', label: '#e5e7eb' },
    'high-contrast': { bg: '#000', line: '#fff', tick: '#fff', point: '#0f0', correct: '#0f0', incorrect: '#f00', label: '#fff' },
  }[theme];

  const isDisabled = readOnly || disabled;

  // Calculate position from value
  const valueToPosition = (val: number): number => {
    const width = 100; // percentage
    return ((val - range[0]) / (range[1] - range[0])) * width;
  };

  // Calculate value from position (uses userDivisions for snapping)
  const positionToValue = (pos: number, containerWidth: number): number => {
    const percentage = pos / containerWidth;
    const val = range[0] + percentage * (range[1] - range[0]);

    // Snap to nearest tick based on current user divisions
    const snapStep = (range[1] - range[0]) / userDivisions;
    const snapped = Math.round(val / snapStep) * snapStep;

    // Clamp to range and round to avoid floating point issues
    return Math.round(Math.max(range[0], Math.min(range[1], snapped)) * 10000) / 10000;
  };

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (isDisabled) return;
    setIsDragging(true);

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const newValue = positionToValue(x, rect.width);
    setPointX(newValue);
    onChange?.(newValue);
  }, [isDisabled, onChange, range, options.snapDivisions, tickStep]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || isDisabled) return;

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const newValue = positionToValue(x, rect.width);
    setPointX(newValue);
    onChange?.(newValue);
  }, [isDragging, isDisabled, onChange, range, options.snapDivisions, tickStep]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Touch event handlers for mobile support
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (isDisabled) return;
    e.preventDefault();
    setIsDragging(true);

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const touch = e.touches[0];
    const x = touch.clientX - rect.left;
    const newValue = positionToValue(x, rect.width);
    setPointX(newValue);
    onChange?.(newValue);
  }, [isDisabled, onChange, range, options.snapDivisions, tickStep]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isDragging || isDisabled) return;
    e.preventDefault();

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const touch = e.touches[0];
    const x = touch.clientX - rect.left;
    const newValue = positionToValue(x, rect.width);
    setPointX(newValue);
    onChange?.(newValue);
  }, [isDragging, isDisabled, onChange, range, options.snapDivisions, tickStep]);

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (isDisabled || pointX === null) return;

    // Use userDivisions for step size
    const snapStep = (range[1] - range[0]) / userDivisions;

    let newValue = pointX;

    switch (e.key) {
      case 'ArrowLeft':
      case 'ArrowDown':
        e.preventDefault();
        newValue = Math.max(range[0], pointX - snapStep);
        break;
      case 'ArrowRight':
      case 'ArrowUp':
        e.preventDefault();
        newValue = Math.min(range[1], pointX + snapStep);
        break;
      case 'Home':
        e.preventDefault();
        newValue = range[0];
        break;
      case 'End':
        e.preventDefault();
        newValue = range[1];
        break;
      default:
        return;
    }

    // Round to avoid floating point issues
    newValue = Math.round(newValue * 10000) / 10000;
    setPointX(newValue);
    onChange?.(newValue);
  }, [isDisabled, pointX, range, userDivisions, onChange]);

  // Generate tick marks using userDivisions (user-controlled)
  const ticks: number[] = [];
  const numDivisions = userDivisions;
  const actualTickStep = (range[1] - range[0]) / numDivisions;

  for (let i = 0; i <= numDivisions; i++) {
    const tickValue = range[0] + i * actualTickStep;
    ticks.push(Math.round(tickValue * 10000) / 10000); // Round to avoid floating point issues
  }

  // Handle division change
  const handleDivisionChange = (newDivisions: number) => {
    const clamped = Math.max(divisionRange[0], Math.min(divisionRange[1], newDivisions));
    setUserDivisions(clamped);
    // Snap current point to nearest valid position with new divisions
    if (pointX !== null) {
      const newStep = (range[1] - range[0]) / clamped;
      const snappedValue = Math.round(pointX / newStep) * newStep;
      const clampedValue = Math.max(range[0], Math.min(range[1], snappedValue));
      setPointX(Math.round(clampedValue * 10000) / 10000);
      onChange?.(Math.round(clampedValue * 10000) / 10000);
    }
  };

  // Check if answer is correct in review mode
  const isCorrect = reviewMode && pointX !== null && correctX !== undefined && Math.abs(pointX - correctX) < 0.01;
  const isIncorrect = reviewMode && pointX !== null && correctX !== undefined && Math.abs(pointX - correctX) >= 0.01;

  // Convert decimal to fraction string
  const decimalToFraction = (decimal: number): string | null => {
    // Common fractions lookup
    const fractionMap: Record<string, string> = {
      '0.125': '⅛', '0.25': '¼', '0.333': '⅓', '0.375': '⅜',
      '0.5': '½', '0.625': '⅝', '0.667': '⅔', '0.75': '¾', '0.875': '⅞',
      '0.2': '⅕', '0.4': '⅖', '0.6': '⅗', '0.8': '⅘',
      '0.167': '⅙', '0.833': '⅚',
    };

    const rounded = Math.round(decimal * 1000) / 1000;
    const key = rounded.toString();
    return fractionMap[key] || null;
  };

  // Format number for display (handle fractions if needed)
  const formatLabel = (num: number): string => {
    const whole = Math.floor(num);
    const decimal = Math.round((num - whole) * 1000) / 1000;

    if (options.labelStyle === 'fraction' || options.labelStyle === 'mixed') {
      if (decimal === 0) {
        return String(whole);
      }

      const fractionPart = decimalToFraction(decimal);
      if (fractionPart) {
        if (whole === 0) {
          return fractionPart;
        }
        return options.labelStyle === 'mixed' ? `${whole}${fractionPart}` : fractionPart;
      }
    }

    // Default: decimal format
    if (Number.isInteger(num)) {
      return String(num);
    }
    return num.toFixed(2).replace(/\.?0+$/, '');
  };

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="number-line">
      <div
        className="athena-number-line"
        style={{
          padding: '24px 24px 16px 24px',
          backgroundColor: themeStyles.bg,
          borderRadius: '8px',
        }}
      >
        {/* Division Control - lets user change number of tick marks */}
        {showDivisionControl && !isDisabled && (
          <div
            style={{
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              flexWrap: 'wrap',
            }}
          >
            <span style={{ fontSize: '14px', color: themeStyles.label }}>
              Number of divisions:
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => handleDivisionChange(userDivisions - 1)}
                disabled={userDivisions <= divisionRange[0]}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: `2px solid ${themeStyles.tick}`,
                  backgroundColor: 'transparent',
                  color: themeStyles.label,
                  fontSize: '18px',
                  fontWeight: 'bold',
                  cursor: userDivisions <= divisionRange[0] ? 'not-allowed' : 'pointer',
                  opacity: userDivisions <= divisionRange[0] ? 0.4 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                aria-label="Decrease divisions"
              >
                −
              </button>
              <span
                style={{
                  minWidth: '40px',
                  textAlign: 'center',
                  fontSize: '18px',
                  fontWeight: 'bold',
                  color: themeStyles.point,
                }}
              >
                {userDivisions}
              </span>
              <button
                onClick={() => handleDivisionChange(userDivisions + 1)}
                disabled={userDivisions >= divisionRange[1]}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: `2px solid ${themeStyles.tick}`,
                  backgroundColor: 'transparent',
                  color: themeStyles.label,
                  fontSize: '18px',
                  fontWeight: 'bold',
                  cursor: userDivisions >= divisionRange[1] ? 'not-allowed' : 'pointer',
                  opacity: userDivisions >= divisionRange[1] ? 0.4 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                aria-label="Increase divisions"
              >
                +
              </button>
            </div>
          </div>
        )}

        <div
          ref={containerRef}
          tabIndex={isDisabled ? -1 : 0}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onKeyDown={handleKeyDown}
          role="slider"
          aria-valuemin={range[0]}
          aria-valuemax={range[1]}
          aria-valuenow={pointX ?? undefined}
          aria-label="Number line - use arrow keys to move point"
          style={{
            position: 'relative',
            height: '70px',
            cursor: isDisabled ? 'default' : 'pointer',
            userSelect: 'none',
            outline: 'none',
          }}
        >
          {/* Main line with arrows */}
          <div
            style={{
              position: 'absolute',
              top: '20px',
              left: '0',
              right: '0',
              height: '3px',
              backgroundColor: themeStyles.line,
              borderRadius: '2px',
            }}
          />
          {/* Left arrow */}
          <div
            style={{
              position: 'absolute',
              top: '14px',
              left: '-2px',
              width: '0',
              height: '0',
              borderTop: '8px solid transparent',
              borderBottom: '8px solid transparent',
              borderRight: `10px solid ${themeStyles.line}`,
            }}
          />
          {/* Right arrow */}
          <div
            style={{
              position: 'absolute',
              top: '14px',
              right: '-2px',
              width: '0',
              height: '0',
              borderTop: '8px solid transparent',
              borderBottom: '8px solid transparent',
              borderLeft: `10px solid ${themeStyles.line}`,
            }}
          />

          {/* Tick marks */}
          {ticks.map((tick, index) => {
            const pos = valueToPosition(tick);
            const isEndpoint = tick === range[0] || tick === range[1];
            // Show label every few ticks, or on endpoints
            const labelEveryN = numDivisions <= 10 ? 1 : Math.ceil(numDivisions / 8);
            const shouldShowLabel = isEndpoint || (index % labelEveryN === 0);
            const isMajor = shouldShowLabel;

            return (
              <React.Fragment key={tick}>
                {/* Tick mark */}
                <div
                  style={{
                    position: 'absolute',
                    left: `${pos}%`,
                    top: '15px',
                    width: isEndpoint ? '3px' : isMajor ? '2px' : '1px',
                    height: isEndpoint ? '20px' : isMajor ? '14px' : '10px',
                    backgroundColor: themeStyles.tick,
                    transform: 'translateX(-50%)',
                  }}
                />
                {/* Tick label - positioned separately below the line */}
                {options.labelTicks !== false && shouldShowLabel && (
                  <div
                    style={{
                      position: 'absolute',
                      left: `${pos}%`,
                      top: '40px',
                      transform: 'translateX(-50%)',
                      fontSize: isEndpoint ? '14px' : '12px',
                      fontWeight: isEndpoint ? 600 : 500,
                      color: themeStyles.label,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {formatLabel(tick)}
                  </div>
                )}
              </React.Fragment>
            );
          })}

          {/* Show correct answer in review mode (if different from user's answer) */}
          {reviewMode && correctX !== undefined && (pointX === null || Math.abs(pointX - correctX) >= 0.01) && (
            <div
              style={{
                position: 'absolute',
                left: `${valueToPosition(correctX)}%`,
                top: '10px',
                width: '22px',
                height: '22px',
                backgroundColor: themeStyles.correct,
                borderRadius: '50%',
                transform: 'translateX(-50%)',
                border: '2px dashed white',
                opacity: 0.7,
                zIndex: 5,
              }}
              title={`Correct answer: ${formatLabel(correctX)}`}
            />
          )}

          {/* User's point - larger green draggable dot */}
          {pointX !== null && (
            <div
              style={{
                position: 'absolute',
                left: `${valueToPosition(pointX)}%`,
                top: '6px',
                width: '28px',
                height: '28px',
                backgroundColor: isCorrect ? themeStyles.correct : isIncorrect ? themeStyles.incorrect : themeStyles.point,
                borderRadius: '50%',
                transform: 'translateX(-50%)',
                border: '3px solid white',
                boxShadow: '0 3px 8px rgba(0,0,0,0.3)',
                cursor: isDisabled ? 'default' : isDragging ? 'grabbing' : 'grab',
                transition: isDragging ? 'none' : 'left 0.15s ease-out',
                zIndex: 10,
              }}
            >
              {/* Inner dot highlight */}
              <div
                style={{
                  position: 'absolute',
                  top: '4px',
                  left: '4px',
                  width: '8px',
                  height: '8px',
                  backgroundColor: 'rgba(255,255,255,0.4)',
                  borderRadius: '50%',
                }}
              />
            </div>
          )}
        </div>

        {/* Instructions / Current value display */}
        <div
          style={{
            marginTop: '12px',
            textAlign: 'center',
            fontSize: '14px',
            color: themeStyles.label,
          }}
        >
          {isDisabled ? (
            pointX !== null ? (
              <span>Your answer: <strong style={{ color: themeStyles.point }}>{formatLabel(pointX)}</strong></span>
            ) : 'No point placed'
          ) : (
            pointX !== null ? (
              <span>Selected: <strong style={{ color: themeStyles.point, fontSize: '16px' }}>{formatLabel(pointX)}</strong> <span style={{ color: themeStyles.tick, fontSize: '12px' }}>(drag to change)</span></span>
            ) : (
              <span style={{ fontStyle: 'italic' }}>Click or drag on the number line to place a point</span>
            )
          )}
        </div>

        {/* Review feedback */}
        {reviewMode && (
          <div
            style={{
              marginTop: '8px',
              textAlign: 'center',
              fontSize: '14px',
              fontWeight: 500,
              color: isCorrect ? themeStyles.correct : isIncorrect ? themeStyles.incorrect : themeStyles.tick,
            }}
          >
            {isCorrect ? '✓ Correct!' : isIncorrect ? `✗ Correct answer: ${formatLabel(correctX!)}` : ''}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

export default NumberLineWidget;
