/**
 * Table Widget
 *
 * Display and interact with tabular data.
 * Supports:
 * - Static tables (display only)
 * - Editable cells
 * - Column/row headers
 */

import React, { useState, useCallback } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { TableOptions } from '../../core/types';
import { BaseWidgetWrapper } from '../base/BaseWidget';

export interface TableWidgetProps extends WidgetProps<TableOptions> {}

export function TableWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: TableWidgetProps) {
  const options = widget.options || {};
  const headers = options.headers || [];
  const rows = options.rows || 3;
  const columns = options.columns || 3;
  const editableColumns = options.editableColumns || [];

  // Initialize cell values from value prop, data option, or empty strings
  const initialValues = (() => {
    if (value && Array.isArray(value)) {
      return value as string[][];
    }
    // Use data from options if provided
    if (options.data && Array.isArray(options.data)) {
      return options.data as string[][];
    }
    // Create empty grid
    return Array.from({ length: rows }, () =>
      Array.from({ length: columns }, () => '')
    );
  })();

  const [cellValues, setCellValues] = useState<string[][]>(initialValues);

  const handleCellChange = useCallback(
    (rowIdx: number, colIdx: number, newValue: string) => {
      const newValues = cellValues.map((row, ri) =>
        ri === rowIdx
          ? row.map((cell, ci) => (ci === colIdx ? newValue : cell))
          : row
      );
      setCellValues(newValues);
      onChange?.(newValues);
    },
    [cellValues, onChange]
  );

  const isEditable = (colIdx: number): boolean => {
    if (readOnly || disabled || reviewMode) return false;
    if (editableColumns.length === 0) return false;
    return editableColumns.includes(colIdx);
  };

  const themeStyles = {
    light: {
      bg: '#fff',
      headerBg: '#f5f5f5',
      border: '#e0e0e0',
      text: '#333',
      evenRowBg: '#fafafa',
    },
    dark: {
      bg: '#2d2d2d',
      headerBg: '#3d3d3d',
      border: '#4d4d4d',
      text: '#fff',
      evenRowBg: '#333',
    },
    'high-contrast': {
      bg: '#000',
      headerBg: '#fff',
      border: '#fff',
      text: '#fff',
      evenRowBg: '#111',
    },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="table">
      <div className="athena-table-container" style={{ overflowX: 'auto' }}>
        <table
          className="athena-table"
          role="grid"
          aria-label={options.title || 'Data table'}
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            backgroundColor: themeStyles.bg,
            border: `1px solid ${themeStyles.border}`,
            borderRadius: '8px',
            overflow: 'hidden',
          }}
        >
          {/* Header row */}
          {headers.length > 0 && (
            <thead>
              <tr>
                {headers.map((header, idx) => (
                  <th
                    key={idx}
                    scope="col"
                    style={{
                      padding: '12px 16px',
                      backgroundColor: themeStyles.headerBg,
                      borderBottom: `2px solid ${themeStyles.border}`,
                      fontWeight: 600,
                      textAlign: 'left',
                      color: theme === 'high-contrast' ? '#000' : themeStyles.text,
                    }}
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
          )}

          {/* Data rows */}
          <tbody>
            {Array.from({ length: rows }, (_, rowIdx) => (
              <tr
                key={rowIdx}
                style={{
                  backgroundColor:
                    rowIdx % 2 === 1 ? themeStyles.evenRowBg : themeStyles.bg,
                }}
              >
                {Array.from({ length: columns }, (_, colIdx) => {
                  const cellValue = cellValues[rowIdx]?.[colIdx] || '';
                  const editable = isEditable(colIdx);

                  return (
                    <td
                      key={colIdx}
                      style={{
                        padding: editable ? '4px' : '12px 16px',
                        borderBottom: `1px solid ${themeStyles.border}`,
                        color: themeStyles.text,
                      }}
                    >
                      {editable ? (
                        <input
                          type="text"
                          value={cellValue}
                          onChange={(e) =>
                            handleCellChange(rowIdx, colIdx, e.target.value)
                          }
                          disabled={disabled}
                          aria-label={`Row ${rowIdx + 1}, Column ${
                            headers[colIdx] || colIdx + 1
                          }`}
                          style={{
                            width: '100%',
                            padding: '8px 12px',
                            border: `1px solid ${themeStyles.border}`,
                            borderRadius: '4px',
                            backgroundColor: themeStyles.bg,
                            color: themeStyles.text,
                            fontSize: '14px',
                          }}
                        />
                      ) : (
                        cellValue
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        {/* Caption */}
        {options.caption && (
          <div
            className="athena-table-caption"
            style={{
              marginTop: '8px',
              fontSize: '14px',
              color: '#666',
              fontStyle: 'italic',
            }}
          >
            {options.caption}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

export default TableWidget;
