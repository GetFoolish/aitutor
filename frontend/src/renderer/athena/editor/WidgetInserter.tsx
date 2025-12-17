/**
 * Widget Inserter
 *
 * Modal for adding widgets to content.
 */

import React, { useState, useCallback, useMemo } from 'react';
import { useEditorContext } from './EditorFrame';
import type { AthenaWidget, WidgetType } from '../core/types';

export interface WidgetTemplate {
  type: WidgetType | string;
  label: string;
  description: string;
  category: string;
  icon?: string;
  defaultOptions: Record<string, unknown>;
}

export interface WidgetInserterProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Called when modal is closed */
  onClose: () => void;
  /** Called when widget is inserted */
  onInsert?: (widgetId: string, widget: AthenaWidget) => void;
  /** Available widget templates */
  templates?: WidgetTemplate[];
  /** Custom class name */
  className?: string;
}

const DEFAULT_TEMPLATES: WidgetTemplate[] = [
  // Input widgets
  {
    type: 'numeric-input',
    label: 'Numeric Input',
    description: 'Accept numeric answers with tolerance',
    category: 'Input',
    icon: 'number',
    defaultOptions: {
      answers: [{ value: 0, status: 'correct', maxError: 0 }],
      size: 'normal',
    },
  },
  {
    type: 'radio',
    label: 'Multiple Choice',
    description: 'Single or multiple select from options',
    category: 'Input',
    icon: 'radio',
    defaultOptions: {
      choices: [
        { content: 'Option A', correct: false },
        { content: 'Option B', correct: true },
        { content: 'Option C', correct: false },
      ],
      randomize: false,
      multipleSelect: false,
    },
  },
  {
    type: 'expression',
    label: 'Math Expression',
    description: 'Accept mathematical expressions',
    category: 'Input',
    icon: 'math',
    defaultOptions: {
      answerForms: [{ value: 'x+1', form: true, simplify: false }],
      buttonSets: ['basic'],
      times: false,
    },
  },
  {
    type: 'dropdown',
    label: 'Dropdown',
    description: 'Select from dropdown list',
    category: 'Input',
    icon: 'dropdown',
    defaultOptions: {
      choices: ['Option 1', 'Option 2', 'Option 3'],
      placeholder: 'Select an option',
      correct: 0,
    },
  },
  {
    type: 'free-response',
    label: 'Free Response',
    description: 'Open-ended text response',
    category: 'Input',
    icon: 'text',
    defaultOptions: {
      placeholder: 'Enter your response',
      minLength: 0,
      maxLength: 5000,
    },
  },

  // Display widgets
  {
    type: 'image',
    label: 'Image',
    description: 'Display an image with optional labels',
    category: 'Display',
    icon: 'image',
    defaultOptions: {
      backgroundImage: { url: '', width: 400, height: 300 },
      alt: '',
      caption: '',
    },
  },
  {
    type: 'passage',
    label: 'Passage',
    description: 'Reading passage with line numbers',
    category: 'Display',
    icon: 'text-doc',
    defaultOptions: {
      passageTitle: '',
      passageText: '',
      showLineNumbers: true,
    },
  },
  {
    type: 'video',
    label: 'Video',
    description: 'Embedded video player',
    category: 'Display',
    icon: 'video',
    defaultOptions: {
      location: '',
      alignment: 'center',
    },
  },
  {
    type: 'definition',
    label: 'Definition',
    description: 'Term definition block',
    category: 'Display',
    icon: 'book',
    defaultOptions: {
      term: '',
      definition: '',
    },
  },
  {
    type: 'explanation',
    label: 'Explanation',
    description: 'Collapsible explanation section',
    category: 'Display',
    icon: 'info',
    defaultOptions: {
      title: 'Explanation',
      content: '',
      startExpanded: false,
    },
  },

  // Interactive widgets
  {
    type: 'interactive-graph',
    label: 'Interactive Graph',
    description: 'Coordinate plane with tools',
    category: 'Interactive',
    icon: 'graph',
    defaultOptions: {
      range: [[-10, 10], [-10, 10]],
      step: [1, 1],
      gridStep: [1, 1],
      snapStep: [0.5, 0.5],
      graph: { type: 'linear' },
    },
  },
  {
    type: 'grapher',
    label: 'Function Grapher',
    description: 'Plot mathematical functions',
    category: 'Interactive',
    icon: 'function',
    defaultOptions: {
      range: [[-10, 10], [-10, 10]],
      functions: [],
    },
  },
  {
    type: 'table',
    label: 'Table',
    description: 'Fill-in table with cells',
    category: 'Interactive',
    icon: 'table',
    defaultOptions: {
      rows: 3,
      columns: 3,
      headers: ['Column 1', 'Column 2', 'Column 3'],
    },
  },
  {
    type: 'number-line',
    label: 'Number Line',
    description: 'Number line with points',
    category: 'Interactive',
    icon: 'ruler',
    defaultOptions: {
      range: [-10, 10],
      divisionRange: [-10, 10],
      numDivisions: 10,
    },
  },

  // Assessment widgets
  {
    type: 'categorizer',
    label: 'Categorizer',
    description: 'Drag items into categories',
    category: 'Assessment',
    icon: 'folder',
    defaultOptions: {
      categories: ['Category A', 'Category B'],
      items: ['Item 1', 'Item 2', 'Item 3'],
      values: [0, 1, 0],
    },
  },
  {
    type: 'sorter',
    label: 'Sorter',
    description: 'Drag to sort items',
    category: 'Assessment',
    icon: 'sort',
    defaultOptions: {
      options: ['First', 'Second', 'Third'],
      correct: [0, 1, 2],
      layout: 'vertical',
    },
  },
  {
    type: 'matcher',
    label: 'Matcher',
    description: 'Match pairs of items',
    category: 'Assessment',
    icon: 'connect',
    defaultOptions: {
      left: ['Item A', 'Item B', 'Item C'],
      right: ['Match 1', 'Match 2', 'Match 3'],
      pairs: [[0, 0], [1, 1], [2, 2]],
    },
  },
  {
    type: 'orderer',
    label: 'Orderer',
    description: 'Arrange items in order',
    category: 'Assessment',
    icon: 'list-ordered',
    defaultOptions: {
      options: ['Step 1', 'Step 2', 'Step 3'],
      correctOrder: [0, 1, 2],
    },
  },

  // Specialized widgets
  {
    type: 'molecule',
    label: 'Molecule',
    description: 'Display molecular structures',
    category: 'Specialized',
    icon: 'molecule',
    defaultOptions: {
      smiles: '',
      displayMode: '2d',
    },
  },
  {
    type: 'cs-program',
    label: 'Code Editor',
    description: 'Interactive code editor',
    category: 'Specialized',
    icon: 'code',
    defaultOptions: {
      language: 'python',
      code: '',
      runnable: true,
    },
  },
];

const CATEGORIES = ['Input', 'Display', 'Interactive', 'Assessment', 'Specialized'];

/**
 * Widget inserter modal
 */
export function WidgetInserter({
  isOpen,
  onClose,
  onInsert,
  templates = DEFAULT_TEMPLATES,
  className = '',
}: WidgetInserterProps) {
  // Try to use editor context
  let editorContext: ReturnType<typeof useEditorContext> | null = null;
  try {
    editorContext = useEditorContext();
  } catch {
    // Not within EditorFrame
  }

  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<WidgetTemplate | null>(null);

  // Filter templates
  const filteredTemplates = useMemo(() => {
    return templates.filter((template) => {
      const matchesCategory = !selectedCategory || template.category === selectedCategory;
      const matchesSearch = !searchQuery ||
        template.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        template.type.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [templates, selectedCategory, searchQuery]);

  // Group templates by category
  const templatesByCategory = useMemo(() => {
    return filteredTemplates.reduce((acc, template) => {
      if (!acc[template.category]) {
        acc[template.category] = [];
      }
      acc[template.category].push(template);
      return acc;
    }, {} as Record<string, WidgetTemplate[]>);
  }, [filteredTemplates]);

  // Handle widget insertion
  const handleInsert = useCallback(() => {
    if (!selectedTemplate) return;

    const widget: AthenaWidget = {
      type: selectedTemplate.type as WidgetType,
      options: { ...selectedTemplate.defaultOptions },
      alignment: 'default',
      static: false,
      graded: true,
      version: { major: 0, minor: 0 },
    };

    if (editorContext) {
      const widgetId = editorContext.generateWidgetId(selectedTemplate.type);
      editorContext.updateItem({
        ...editorContext.item,
        question: {
          ...editorContext.item.question,
          widgets: {
            ...editorContext.item.question.widgets,
            [widgetId]: widget,
          },
        },
      });
      onInsert?.(widgetId, widget);
    } else {
      onInsert?.(`widget-${Date.now()}`, widget);
    }

    // Reset and close
    setSelectedTemplate(null);
    onClose();
  }, [selectedTemplate, editorContext, onInsert, onClose]);

  // Handle close
  const handleClose = useCallback(() => {
    setSelectedTemplate(null);
    setSearchQuery('');
    setSelectedCategory(null);
    onClose();
  }, [onClose]);

  if (!isOpen) return null;

  return (
    <div className={`athena-widget-inserter-overlay ${className}`} onClick={handleClose}>
      <div
        className="athena-widget-inserter"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="widget-inserter-title"
      >
        {/* Header */}
        <div className="athena-widget-inserter-header">
          <h2 id="widget-inserter-title">Insert Widget</h2>
          <button
            type="button"
            className="athena-widget-inserter-close"
            onClick={handleClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Search */}
        <div className="athena-widget-inserter-search">
          <input
            type="search"
            placeholder="Search widgets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="athena-widget-inserter-search-input"
          />
        </div>

        {/* Categories */}
        <div className="athena-widget-inserter-categories">
          <button
            type="button"
            className={`athena-widget-inserter-category ${!selectedCategory ? 'athena-widget-inserter-category--active' : ''}`}
            onClick={() => setSelectedCategory(null)}
          >
            All
          </button>
          {CATEGORIES.map((category) => (
            <button
              key={category}
              type="button"
              className={`athena-widget-inserter-category ${selectedCategory === category ? 'athena-widget-inserter-category--active' : ''}`}
              onClick={() => setSelectedCategory(category)}
            >
              {category}
            </button>
          ))}
        </div>

        {/* Widget list */}
        <div className="athena-widget-inserter-content">
          {selectedCategory ? (
            // Single category view
            <div className="athena-widget-inserter-list">
              {filteredTemplates.map((template) => (
                <WidgetTemplateCard
                  key={template.type}
                  template={template}
                  isSelected={selectedTemplate?.type === template.type}
                  onClick={() => setSelectedTemplate(template)}
                />
              ))}
            </div>
          ) : (
            // Grouped view
            CATEGORIES.map((category) => {
              const categoryTemplates = templatesByCategory[category];
              if (!categoryTemplates?.length) return null;

              return (
                <div key={category} className="athena-widget-inserter-group">
                  <h3 className="athena-widget-inserter-group-title">{category}</h3>
                  <div className="athena-widget-inserter-list">
                    {categoryTemplates.map((template) => (
                      <WidgetTemplateCard
                        key={template.type}
                        template={template}
                        isSelected={selectedTemplate?.type === template.type}
                        onClick={() => setSelectedTemplate(template)}
                      />
                    ))}
                  </div>
                </div>
              );
            })
          )}

          {filteredTemplates.length === 0 && (
            <div className="athena-widget-inserter-empty">
              <p>No widgets match your search</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="athena-widget-inserter-footer">
          <button
            type="button"
            className="athena-widget-inserter-btn athena-widget-inserter-btn--secondary"
            onClick={handleClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="athena-widget-inserter-btn athena-widget-inserter-btn--primary"
            onClick={handleInsert}
            disabled={!selectedTemplate}
          >
            Insert Widget
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Widget template card
 */
function WidgetTemplateCard({
  template,
  isSelected,
  onClick,
}: {
  template: WidgetTemplate;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`athena-widget-template-card ${isSelected ? 'athena-widget-template-card--selected' : ''}`}
      onClick={onClick}
    >
      {template.icon && (
        <span className={`athena-widget-template-icon athena-icon athena-icon--${template.icon}`} />
      )}
      <div className="athena-widget-template-info">
        <span className="athena-widget-template-label">{template.label}</span>
        <span className="athena-widget-template-description">{template.description}</span>
      </div>
    </button>
  );
}

export default WidgetInserter;
