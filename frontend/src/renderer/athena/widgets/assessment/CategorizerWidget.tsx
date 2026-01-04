/**
 * Categorizer Widget
 *
 * Drag items into categories.
 * Users sort items by dragging them into the correct category.
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
// @ts-ignore - KaTeX types resolution issue
import katex from 'katex';
import type { WidgetProps } from '../WidgetRegistry';
import type { CategorizerOptions } from '../../core/types';
import { BaseWidgetWrapper } from '../base/BaseWidget';

// Helper to render math in text content
const renderMathContent = (text: string): string => {
  if (!text || typeof text !== 'string') return text || '';

  let processed = text;

  // Process display math $$...$$
  processed = processed.replace(/\$\$([^$]+)\$\$/g, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false });
    } catch {
      return math;
    }
  });

  // Process inline math $...$
  processed = processed.replace(/\$([^$]+)\$/g, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
    } catch {
      return math;
    }
  });

  return processed;
};

export interface CategorizerWidgetProps extends WidgetProps<CategorizerOptions> { }

interface CategoryAssignment {
  [categoryId: string]: string[];
}

// Helper to normalize categories - Perseus uses string array, we need objects
interface NormalizedCategory {
  id: string;
  name: string;
}

function normalizeCategories(categories: unknown): NormalizedCategory[] {
  if (!Array.isArray(categories)) return [];
  return categories.map((cat, index) => {
    // If category is a string (Perseus format), convert to object
    if (typeof cat === 'string') {
      return { id: `cat-${index}`, name: cat };
    }
    // If already an object with id/name, use as is
    if (cat && typeof cat === 'object') {
      const catObj = cat as { id?: string; name?: string };
      return {
        id: catObj.id || `cat-${index}`,
        name: catObj.name || String(cat)
      };
    }
    return { id: `cat-${index}`, name: String(cat) };
  });
}

export function CategorizerWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: CategorizerWidgetProps) {
  const options = widget.options || {};
  const categories = normalizeCategories(options.categories);
  const items = Array.isArray(options.items) ? options.items : [];

  // Handle correct answers - Perseus uses "values" array where index = item index, value = category index
  // Our widget expects { itemName: categoryId }
  const correctAnswers = useMemo(() => {
    // If we have a direct correct object, use it
    if (options.correct && typeof options.correct === 'object' && !Array.isArray(options.correct)) {
      console.log('[CategorizerWidget] Using direct correct object:', options.correct);
      return options.correct as Record<string, string>;
    }

    // Convert values array to correct object format
    if (Array.isArray(options.values) && options.values.length > 0) {
      const result: Record<string, string> = {};
      options.values.forEach((categoryIndex: number, itemIndex: number) => {
        if (itemIndex < items.length && categoryIndex < categories.length) {
          result[items[itemIndex]] = categories[categoryIndex].id;
        }
      });
      console.log('[CategorizerWidget] Converted values to correctAnswers:', {
        values: options.values,
        categories: categories.map(c => ({ id: c.id, name: c.name })),
        items,
        result,
      });
      return result;
    }

    console.log('[CategorizerWidget] No correct answers found:', { correct: options.correct, values: options.values });
    return {};
  }, [options.correct, options.values, items, categories]);

  // Initialize category assignments - memoize based on items and categories
  const getInitialAssignments = useCallback((): CategoryAssignment => {
    if (value && typeof value === 'object') {
      return value as CategoryAssignment;
    }
    // Start with all items unassigned (in "items" pool)
    const initial: CategoryAssignment = { unassigned: [...items] };
    categories.forEach((cat) => {
      initial[cat.id] = [];
    });
    return initial;
  }, [value, items, categories]);

  const [assignments, setAssignments] = useState<CategoryAssignment>(getInitialAssignments);

  // Reset state when widgetId or items change (switching questions)
  useEffect(() => {
    setAssignments(getInitialAssignments());
  }, [widgetId, JSON.stringify(items)]);

  const isDisabled = readOnly || disabled;

  // Check if an item is in the correct category
  const isCorrect = (item: string, categoryId: string): boolean => {
    return correctAnswers[item] === categoryId;
  };

  const themeStyles = {
    light: {
      bg: '#fff',
      itemBg: '#f5f5f5',
      border: '#e0e0e0',
      text: '#333',
      correct: '#e8f5e9',
      incorrect: '#ffebee',
    },
    dark: {
      bg: '#000000',
      itemBg: '#1e1e1e',
      border: '#333333',
      text: '#fff',
      correct: '#1b5e20',
      incorrect: '#b71c1c',
    },
    'high-contrast': {
      bg: '#000',
      itemBg: '#222',
      border: '#fff',
      text: '#fff',
      correct: '#0f0',
      incorrect: '#f00',
    },
  }[theme];

  // Handle radio button selection (Perseus table-style UI)
  const handleRadioSelect = useCallback((item: string, categoryId: string) => {
    if (isDisabled) return;

    const newAssignments = { ...assignments };

    // Remove item from all categories (including unassigned)
    Object.keys(newAssignments).forEach(key => {
      newAssignments[key] = newAssignments[key].filter(i => i !== item);
    });

    // Add to selected category
    if (!newAssignments[categoryId]) {
      newAssignments[categoryId] = [];
    }
    newAssignments[categoryId] = [...newAssignments[categoryId], item];

    setAssignments(newAssignments);
    onChange?.(newAssignments);
  }, [assignments, onChange, isDisabled]);

  // Get current category for an item
  const getItemCategory = useCallback((item: string): string | null => {
    for (const [categoryId, categoryItems] of Object.entries(assignments)) {
      if (categoryId !== 'unassigned' && categoryItems.includes(item)) {
        return categoryId;
      }
    }
    return null;
  }, [assignments]);

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="categorizer">
      <div className="athena-categorizer-container">
        {options.title && (
          <div
            className="athena-categorizer-title"
            style={{
              marginBottom: '12px',
              fontWeight: 600,
              color: themeStyles.text,
            }}
          >
            {options.title}
          </div>
        )}

        {/* Perseus-style table with radio buttons */}
        <div
          className="athena-categorizer-table-wrapper"
          style={{
            overflowX: 'auto',
            backgroundColor: themeStyles.itemBg,
            borderRadius: '8px',
            padding: '4px',
          }}
        >
          <table
            className="athena-categorizer-table"
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              backgroundColor: themeStyles.bg,
            }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    padding: '12px 16px',
                    textAlign: 'left',
                    fontWeight: 600,
                    backgroundColor: themeStyles.itemBg,
                    borderBottom: `2px solid ${themeStyles.border}`,
                    color: themeStyles.text,
                  }}
                >
                  {/* Empty header for items column */}
                </th>
                {categories.map((category) => (
                  <th
                    key={category.id}
                    style={{
                      padding: '12px 16px',
                      textAlign: 'center',
                      fontWeight: 600,
                      backgroundColor: themeStyles.itemBg,
                      borderBottom: `2px solid ${themeStyles.border}`,
                      color: themeStyles.text,
                      minWidth: '100px',
                    }}
                    dangerouslySetInnerHTML={{ __html: renderMathContent(category.name) }}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, rowIndex) => {
                const currentCategory = getItemCategory(item);
                const isRowCorrect = reviewMode && currentCategory && isCorrect(item, currentCategory);
                const isRowIncorrect = reviewMode && currentCategory && !isCorrect(item, currentCategory);

                return (
                  <tr
                    key={item}
                    style={{
                      backgroundColor: rowIndex % 2 === 0 ? themeStyles.bg : themeStyles.itemBg,
                    }}
                  >
                    <td
                      style={{
                        padding: '12px 16px',
                        fontWeight: 500,
                        borderBottom: `1px solid ${themeStyles.border}`,
                        color: themeStyles.text,
                        backgroundColor: isRowCorrect ? themeStyles.correct : (isRowIncorrect ? themeStyles.incorrect : 'transparent'),
                      }}
                      dangerouslySetInnerHTML={{ __html: renderMathContent(item) }}
                    />
                    {categories.map((category) => {
                      const isSelected = currentCategory === category.id;
                      const isCellCorrect = reviewMode && isSelected && isCorrect(item, category.id);
                      const isCellIncorrect = reviewMode && isSelected && !isCorrect(item, category.id);

                      return (
                        <td
                          key={category.id}
                          style={{
                            padding: '12px 16px',
                            textAlign: 'center',
                            borderBottom: `1px solid ${themeStyles.border}`,
                            backgroundColor: isCellCorrect ? themeStyles.correct : (isCellIncorrect ? themeStyles.incorrect : 'transparent'),
                          }}
                        >
                          <label
                            style={{
                              display: 'flex',
                              justifyContent: 'center',
                              alignItems: 'center',
                              cursor: isDisabled ? 'default' : 'pointer',
                            }}
                          >
                            <input
                              type="radio"
                              name={`categorizer-${widgetId}-${item}`}
                              checked={isSelected}
                              onChange={() => handleRadioSelect(item, category.id)}
                              disabled={isDisabled}
                              style={{
                                width: '20px',
                                height: '20px',
                                cursor: isDisabled ? 'default' : 'pointer',
                                accentColor: isCellCorrect ? '#4caf50' : (isCellIncorrect ? '#f44336' : '#2196f3'),
                              }}
                            />
                          </label>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Review mode: show correct answers */}
        {reviewMode && Object.keys(correctAnswers).length > 0 && (
          <div
            style={{
              marginTop: '16px',
              padding: '12px',
              backgroundColor: '#e8f5e9',
              borderRadius: '8px',
              fontSize: '14px',
            }}
          >
            <strong>Correct answers:</strong>
            <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px' }}>
              {items.map(item => {
                const correctCat = categories.find(c => c.id === correctAnswers[item]);
                if (!correctCat) return null;
                return (
                  <li key={item}>
                    <span dangerouslySetInnerHTML={{ __html: renderMathContent(item) }} />
                    {' → '}
                    <span dangerouslySetInnerHTML={{ __html: renderMathContent(correctCat.name) }} />
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

export default CategorizerWidget;
