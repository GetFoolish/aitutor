/**
 * Matrix Widget
 *
 * A grid of input fields for entering matrix values.
 * Users fill in a grid of numbers to complete a matrix.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

interface MatrixOptions {
  matrixBoardSize?: [number, number]; // [rows, cols]
  answers?: (string | number)[][];
  prefix?: string;
  suffix?: string;
  cursorPosition?: [number, number];
}

export interface MatrixWidgetProps extends WidgetProps<MatrixOptions> {}

export function MatrixWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: MatrixWidgetProps) {
  const options = widget.options || {};
  const [rows, cols] = options.matrixBoardSize || [3, 3];
  const prefix = options.prefix || '';
  const suffix = options.suffix || '';
  const correctAnswers = options.answers || [];

  // Initialize matrix state
  const getInitialMatrix = (): string[][] => {
    if (value && Array.isArray(value)) {
      return value as string[][];
    }
    // Create empty matrix
    return Array(rows).fill(null).map(() => Array(cols).fill(''));
  };

  const [matrix, setMatrix] = useState<string[][]>(getInitialMatrix);
  const inputRefs = useRef<(HTMLInputElement | null)[][]>([]);

  // Initialize refs
  useEffect(() => {
    inputRefs.current = Array(rows).fill(null).map(() => Array(cols).fill(null));
  }, [rows, cols]);

  const isDisabled = readOnly || disabled;

  const handleCellChange = useCallback(
    (row: number, col: number, newValue: string) => {
      if (isDisabled) return;

      // Only allow numbers, minus sign, decimal point
      if (newValue && !/^-?\d*\.?\d*$/.test(newValue)) {
        return;
      }

      const newMatrix = matrix.map((r, ri) =>
        ri === row ? r.map((c, ci) => (ci === col ? newValue : c)) : r
      );

      setMatrix(newMatrix);
      onChange?.(newMatrix);
    },
    [isDisabled, matrix, onChange]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, row: number, col: number) => {
      if (isDisabled) return;

      let nextRow = row;
      let nextCol = col;

      switch (e.key) {
        case 'ArrowUp':
          nextRow = Math.max(0, row - 1);
          break;
        case 'ArrowDown':
          nextRow = Math.min(rows - 1, row + 1);
          break;
        case 'ArrowLeft':
          nextCol = Math.max(0, col - 1);
          break;
        case 'ArrowRight':
          nextCol = Math.min(cols - 1, col + 1);
          break;
        case 'Tab':
          // Move to next cell
          if (!e.shiftKey) {
            if (col < cols - 1) {
              nextCol = col + 1;
            } else if (row < rows - 1) {
              nextRow = row + 1;
              nextCol = 0;
            }
          } else {
            if (col > 0) {
              nextCol = col - 1;
            } else if (row > 0) {
              nextRow = row - 1;
              nextCol = cols - 1;
            }
          }
          break;
        case 'Enter':
          // Move to next row
          if (row < rows - 1) {
            nextRow = row + 1;
          }
          break;
        default:
          return;
      }

      if (nextRow !== row || nextCol !== col) {
        e.preventDefault();
        inputRefs.current[nextRow]?.[nextCol]?.focus();
      }
    },
    [isDisabled, rows, cols]
  );

  // Check if a cell value is correct (for review mode)
  const isCellCorrect = (row: number, col: number): boolean | null => {
    if (!reviewMode || !correctAnswers[row] || correctAnswers[row][col] === undefined) {
      return null;
    }
    const userValue = parseFloat(matrix[row][col]);
    const correctValue = parseFloat(String(correctAnswers[row][col]));
    if (isNaN(userValue) || isNaN(correctValue)) {
      return matrix[row][col] === String(correctAnswers[row][col]);
    }
    return Math.abs(userValue - correctValue) < 0.0001;
  };

  const themeStyles = {
    light: {
      bg: '#fff',
      cellBg: '#fff',
      border: '#ccc',
      text: '#333',
      correct: '#e8f5e9',
      incorrect: '#ffebee',
      bracket: '#666',
    },
    dark: {
      bg: '#2d2d2d',
      cellBg: '#3d3d3d',
      border: '#555',
      text: '#fff',
      correct: '#1b5e20',
      incorrect: '#b71c1c',
      bracket: '#aaa',
    },
    'high-contrast': {
      bg: '#000',
      cellBg: '#111',
      border: '#fff',
      text: '#fff',
      correct: '#0f0',
      incorrect: '#f00',
      bracket: '#fff',
    },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="matrix">
      <div
        className="athena-matrix-container"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: themeStyles.text,
        }}
      >
        {/* Prefix text */}
        {prefix && (
          <span
            className="athena-matrix-prefix"
            style={{ fontSize: '16px' }}
          >
            {prefix}
          </span>
        )}

        {/* Matrix with brackets */}
        <div
          className="athena-matrix"
          style={{
            display: 'flex',
            alignItems: 'stretch',
          }}
        >
          {/* Left bracket */}
          <div
            className="athena-matrix-bracket-left"
            style={{
              width: '8px',
              borderLeft: `2px solid ${themeStyles.bracket}`,
              borderTop: `2px solid ${themeStyles.bracket}`,
              borderBottom: `2px solid ${themeStyles.bracket}`,
              borderTopLeftRadius: '4px',
              borderBottomLeftRadius: '4px',
              marginRight: '4px',
            }}
          />

          {/* Matrix grid */}
          <table
            className="athena-matrix-grid"
            style={{
              borderCollapse: 'separate',
              borderSpacing: '4px',
            }}
          >
            <tbody>
              {Array(rows).fill(null).map((_, rowIndex) => (
                <tr key={rowIndex}>
                  {Array(cols).fill(null).map((_, colIndex) => {
                    const cellCorrect = isCellCorrect(rowIndex, colIndex);
                    let cellBg = themeStyles.cellBg;
                    if (cellCorrect === true) cellBg = themeStyles.correct;
                    if (cellCorrect === false) cellBg = themeStyles.incorrect;

                    return (
                      <td key={colIndex} style={{ padding: 0 }}>
                        <input
                          ref={(el) => {
                            if (!inputRefs.current[rowIndex]) {
                              inputRefs.current[rowIndex] = [];
                            }
                            inputRefs.current[rowIndex][colIndex] = el;
                          }}
                          type="text"
                          inputMode="decimal"
                          value={matrix[rowIndex]?.[colIndex] || ''}
                          onChange={(e) =>
                            handleCellChange(rowIndex, colIndex, e.target.value)
                          }
                          onKeyDown={(e) => handleKeyDown(e, rowIndex, colIndex)}
                          disabled={isDisabled}
                          className="athena-matrix-cell"
                          style={{
                            width: '48px',
                            height: '36px',
                            textAlign: 'center',
                            fontSize: '16px',
                            border: `1px solid ${themeStyles.border}`,
                            borderRadius: '4px',
                            backgroundColor: cellBg,
                            color: themeStyles.text,
                            outline: 'none',
                          }}
                          aria-label={`Row ${rowIndex + 1}, Column ${colIndex + 1}`}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Right bracket */}
          <div
            className="athena-matrix-bracket-right"
            style={{
              width: '8px',
              borderRight: `2px solid ${themeStyles.bracket}`,
              borderTop: `2px solid ${themeStyles.bracket}`,
              borderBottom: `2px solid ${themeStyles.bracket}`,
              borderTopRightRadius: '4px',
              borderBottomRightRadius: '4px',
              marginLeft: '4px',
            }}
          />
        </div>

        {/* Suffix text */}
        {suffix && (
          <span
            className="athena-matrix-suffix"
            style={{ fontSize: '16px' }}
          >
            {suffix}
          </span>
        )}
      </div>

      {/* Review mode - show correct answer */}
      {reviewMode && correctAnswers.length > 0 && (
        <div
          className="athena-matrix-correct-answer"
          style={{
            marginTop: '12px',
            padding: '12px',
            backgroundColor: 'rgba(76, 175, 80, 0.1)',
            borderRadius: '4px',
            fontSize: '14px',
          }}
        >
          <strong>Correct answer:</strong>
          <div style={{ marginTop: '8px', fontFamily: 'monospace' }}>
            [
            {correctAnswers.map((row, i) => (
              <span key={i}>
                [{row.join(', ')}]{i < correctAnswers.length - 1 ? ', ' : ''}
              </span>
            ))}
            ]
          </div>
        </div>
      )}
    </BaseWidgetWrapper>
  );
}

export default MatrixWidget;
