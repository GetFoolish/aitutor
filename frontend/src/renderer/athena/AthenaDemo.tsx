/**
 * Athena Demo Page
 *
 * Demonstration of all Athena features and capabilities.
 */

import React, { useState, useCallback, useMemo, Suspense } from 'react';
import { AthenaProvider } from './AthenaContext';
import type { AthenaItem, PerseusItem } from './core/types';

// Demo question data
const DEMO_QUESTIONS: Array<{
  id: string;
  title: string;
  subject: string;
  item: PerseusItem;
}> = [
  {
    id: 'algebra-1',
    title: 'Solving Linear Equations',
    subject: 'Mathematics',
    item: {
      question: {
        content: 'Solve for $x$:\n\n$$3x + 7 = 22$$\n\n[[☃ numeric-input 1]]',
        widgets: {
          'numeric-input 1': {
            type: 'numeric-input',
            alignment: 'default',
            static: false,
            graded: true,
            options: {
              answers: [{ value: 5, status: 'correct', maxError: 0 }],
              size: 'normal',
            },
            version: { major: 0, minor: 0 },
          },
        },
        images: {},
      },
      hints: [
        {
          content: 'First, subtract 7 from both sides:\n\n$$3x + 7 - 7 = 22 - 7$$\n$$3x = 15$$',
          widgets: {},
          images: {},
        },
        {
          content: 'Then divide both sides by 3:\n\n$$\\frac{3x}{3} = \\frac{15}{3}$$\n$$x = 5$$',
          widgets: {},
          images: {},
        },
      ],
      answerArea: { type: 'single' },
    },
  },
  {
    id: 'chemistry-1',
    title: 'Chemical Equations',
    subject: 'Chemistry',
    item: {
      question: {
        content: 'Balance the following equation:\n\n$$\\ce{H2 + O2 -> H2O}$$\n\nCoefficient for $\\ce{H2}$: [[☃ numeric-input 1]]\nCoefficient for $\\ce{H2O}$: [[☃ numeric-input 2]]',
        widgets: {
          'numeric-input 1': {
            type: 'numeric-input',
            alignment: 'default',
            static: false,
            graded: true,
            options: { answers: [{ value: 2, status: 'correct' }], size: 'small' },
            version: { major: 0, minor: 0 },
          },
          'numeric-input 2': {
            type: 'numeric-input',
            alignment: 'default',
            static: false,
            graded: true,
            options: { answers: [{ value: 2, status: 'correct' }], size: 'small' },
            version: { major: 0, minor: 0 },
          },
        },
        images: {},
      },
      hints: [
        { content: 'Count atoms on each side. Oxygen is unbalanced.', widgets: {}, images: {} },
      ],
      answerArea: { type: 'multiple' },
    },
  },
  {
    id: 'expression-1',
    title: 'Factoring Quadratics',
    subject: 'Mathematics',
    item: {
      question: {
        content: 'Factor:\n\n$$x^2 + 5x + 6$$\n\n[[☃ expression 1]]',
        widgets: {
          'expression 1': {
            type: 'expression',
            alignment: 'default',
            static: false,
            graded: true,
            options: {
              answerForms: [
                { value: '(x+2)(x+3)', form: true, simplify: false, considered: 'correct' },
                { value: '(x+3)(x+2)', form: true, simplify: false, considered: 'correct' },
              ],
              buttonSets: ['basic'],
            },
            version: { major: 0, minor: 0 },
          },
        },
        images: {},
      },
      hints: [
        { content: 'Find two numbers that multiply to 6 and add to 5.', widgets: {}, images: {} },
      ],
      answerArea: { type: 'single' },
    },
  },
  {
    id: 'multiple-choice-1',
    title: 'Properties of Exponents',
    subject: 'Mathematics',
    item: {
      question: {
        content: 'Which expression equals $x^3 \\cdot x^4$?\n\n[[☃ radio 1]]',
        widgets: {
          'radio 1': {
            type: 'radio',
            alignment: 'default',
            static: false,
            graded: true,
            options: {
              choices: [
                { content: '$x^7$', correct: true },
                { content: '$x^{12}$', correct: false },
                { content: '$x^1$', correct: false },
                { content: '$2x^7$', correct: false },
              ],
              randomize: true,
            },
            version: { major: 0, minor: 0 },
          },
        },
        images: {},
      },
      hints: [
        { content: 'When multiplying powers with the same base, add the exponents: $x^a \\cdot x^b = x^{a+b}$', widgets: {}, images: {} },
      ],
      answerArea: { type: 'single' },
    },
  },
  {
    id: 'dropdown-1',
    title: 'Chemical Properties',
    subject: 'Chemistry',
    item: {
      question: {
        content: 'Which element is a noble gas?\n\n[[☃ dropdown 1]]',
        widgets: {
          'dropdown 1': {
            type: 'dropdown',
            alignment: 'default',
            static: false,
            graded: true,
            options: {
              choices: ['Neon (Ne)', 'Sodium (Na)', 'Chlorine (Cl)', 'Iron (Fe)'],
              placeholder: 'Select an element',
              correct: 0,
            },
            version: { major: 0, minor: 0 },
          },
        },
        images: {},
      },
      hints: [
        { content: 'Noble gases are in Group 18 and have full outer electron shells.', widgets: {}, images: {} },
      ],
      answerArea: { type: 'single' },
    },
  },
];

export interface AthenaDemoProps {
  /** Custom class name */
  className?: string;
}

/**
 * Athena Demo component
 */
export function AthenaDemo({ className = '' }: AthenaDemoProps) {
  const [selectedQuestion, setSelectedQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [visibleHints, setVisibleHints] = useState(0);
  const [scoreResult, setScoreResult] = useState<{ correct: boolean; message: string } | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  const currentQuestion = DEMO_QUESTIONS[selectedQuestion];
  const currentItem = currentQuestion.item;

  // Handle answer change
  const handleAnswerChange = useCallback((widgetId: string, value: unknown) => {
    setAnswers(prev => ({ ...prev, [widgetId]: value }));
    setScoreResult(null);
  }, []);

  // Handle hint reveal
  const handleRevealHint = useCallback(() => {
    if (currentItem.hints && visibleHints < currentItem.hints.length) {
      setVisibleHints(prev => prev + 1);
    }
  }, [currentItem.hints?.length, visibleHints]);

  // Handle question change
  const handleQuestionChange = useCallback((index: number) => {
    setSelectedQuestion(index);
    setAnswers({});
    setVisibleHints(0);
    setScoreResult(null);
  }, []);

  // Simple score check (demo only)
  const handleCheckAnswer = useCallback(() => {
    // Simplified scoring for demo
    const widgets = currentItem.question.widgets;
    let allCorrect = true;

    for (const [widgetId, widget] of Object.entries(widgets)) {
      const answer = answers[widgetId];
      const options = widget.options as Record<string, unknown>;

      if (widget.type === 'numeric-input') {
        const expected = (options.answers as Array<{ value: number }>)?.[0]?.value;
        if (parseFloat(String(answer)) !== expected) {
          allCorrect = false;
        }
      } else if (widget.type === 'radio') {
        const choices = options.choices as Array<{ correct: boolean }>;
        const correctIndex = choices.findIndex(c => c.correct);
        if (answer !== correctIndex) {
          allCorrect = false;
        }
      } else if (widget.type === 'dropdown') {
        if (answer !== options.correct) {
          allCorrect = false;
        }
      }
    }

    setScoreResult({
      correct: allCorrect,
      message: allCorrect ? 'Correct! Great job!' : 'Not quite. Try again or use a hint.',
    });
  }, [currentItem, answers]);

  // Render question content with simple widget placeholders
  const renderContent = useMemo(() => {
    let content = currentItem.question.content;

    // Replace widget placeholders with inputs
    Object.entries(currentItem.question.widgets).forEach(([widgetId, widget]) => {
      const placeholder = `[[☃ ${widgetId}]]`;
      const widgetHtml = renderWidgetPreview(widgetId, widget, answers[widgetId], handleAnswerChange);
      content = content.replace(placeholder, `<widget-placeholder id="${widgetId}"></widget-placeholder>`);
    });

    return content;
  }, [currentItem, answers, handleAnswerChange]);

  return (
    <AthenaProvider theme={theme}>
      <div className={`athena-demo ${className}`} data-theme={theme}>
        {/* Header */}
        <header className="athena-demo-header">
          <div className="athena-demo-logo">
            <h1>Athena Demo</h1>
            <span className="athena-demo-version">v1.0.0</span>
          </div>

          <div className="athena-demo-controls">
            <button
              className={`athena-demo-theme-btn ${theme === 'light' ? 'active' : ''}`}
              onClick={() => setTheme('light')}
            >
              Light
            </button>
            <button
              className={`athena-demo-theme-btn ${theme === 'dark' ? 'active' : ''}`}
              onClick={() => setTheme('dark')}
            >
              Dark
            </button>
            <button
              className="athena-demo-editor-btn"
              onClick={() => setShowEditor(!showEditor)}
            >
              {showEditor ? 'Hide Editor' : 'Show Editor'}
            </button>
          </div>
        </header>

        <main className="athena-demo-main">
          {/* Sidebar - Question list */}
          <aside className="athena-demo-sidebar">
            <h2>Questions</h2>
            <ul className="athena-demo-question-list">
              {DEMO_QUESTIONS.map((q, index) => (
                <li key={q.id}>
                  <button
                    className={`athena-demo-question-item ${selectedQuestion === index ? 'active' : ''}`}
                    onClick={() => handleQuestionChange(index)}
                  >
                    <span className="athena-demo-question-subject">{q.subject}</span>
                    <span className="athena-demo-question-title">{q.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          {/* Content */}
          <div className="athena-demo-content">
            {/* Question */}
            <section className="athena-demo-question">
              <h2>{currentQuestion.title}</h2>
              <span className="athena-demo-subject-badge">{currentQuestion.subject}</span>

              <div className="athena-demo-question-content">
                <QuestionRenderer
                  content={currentItem.question.content}
                  widgets={currentItem.question.widgets}
                  answers={answers}
                  onAnswerChange={handleAnswerChange}
                />
              </div>

              {/* Actions */}
              <div className="athena-demo-actions">
                <button
                  className="athena-demo-btn athena-demo-btn--primary"
                  onClick={handleCheckAnswer}
                >
                  Check Answer
                </button>
                <button
                  className="athena-demo-btn athena-demo-btn--secondary"
                  onClick={handleRevealHint}
                  disabled={visibleHints >= (currentItem.hints?.length ?? 0)}
                >
                  Show Hint ({visibleHints}/{currentItem.hints?.length ?? 0})
                </button>
              </div>

              {/* Score result */}
              {scoreResult && (
                <div className={`athena-demo-result ${scoreResult.correct ? 'correct' : 'incorrect'}`}>
                  {scoreResult.message}
                </div>
              )}

              {/* Hints */}
              {visibleHints > 0 && currentItem.hints && (
                <div className="athena-demo-hints">
                  <h3>Hints</h3>
                  {currentItem.hints.slice(0, visibleHints).map((hint, index) => (
                    <div key={index} className="athena-demo-hint">
                      <strong>Hint {index + 1}:</strong>
                      <div dangerouslySetInnerHTML={{ __html: formatContent(hint.content) }} />
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Editor panel (if shown) */}
            {showEditor && (
              <section className="athena-demo-editor">
                <h3>JSON View</h3>
                <pre className="athena-demo-json">
                  {JSON.stringify(currentItem, null, 2)}
                </pre>
              </section>
            )}
          </div>
        </main>

        {/* Footer */}
        <footer className="athena-demo-footer">
          <p>
            Athena Content Renderer - A modern replacement for Perseus with multi-subject support.
          </p>
          <p>
            Features: Math (KaTeX), Chemistry (mhchem), Code (Prism.js), and more.
          </p>
        </footer>

        {/* Styles */}
        <style>{DEMO_STYLES}</style>
      </div>
    </AthenaProvider>
  );
}

/**
 * Question renderer component
 */
function QuestionRenderer({
  content,
  widgets,
  answers,
  onAnswerChange,
}: {
  content: string;
  widgets: Record<string, any>;
  answers: Record<string, unknown>;
  onAnswerChange: (widgetId: string, value: unknown) => void;
}) {
  // Split by widget placeholders
  const parts = content.split(/(\[\[☃\s*[^\]]+\]\])/g);

  return (
    <div className="athena-question-rendered">
      {parts.map((part, index) => {
        const match = part.match(/\[\[☃\s*([^\]]+)\]\]/);
        if (match) {
          const widgetId = match[1].trim();
          const widget = widgets[widgetId];
          if (!widget) return <span key={index}>[Missing widget]</span>;

          return (
            <WidgetPreview
              key={index}
              widgetId={widgetId}
              widget={widget}
              value={answers[widgetId]}
              onChange={(v) => onAnswerChange(widgetId, v)}
            />
          );
        }

        // Render text content
        return (
          <span
            key={index}
            dangerouslySetInnerHTML={{ __html: formatContent(part) }}
          />
        );
      })}
    </div>
  );
}

/**
 * Widget preview component
 */
function WidgetPreview({
  widgetId,
  widget,
  value,
  onChange,
}: {
  widgetId: string;
  widget: any;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  switch (widget.type) {
    case 'numeric-input':
      return (
        <input
          type="text"
          className="athena-widget-input"
          value={String(value || '')}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter answer"
        />
      );

    case 'expression':
      return (
        <input
          type="text"
          className="athena-widget-input athena-widget-input--expression"
          value={String(value || '')}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter expression"
        />
      );

    case 'radio':
      const choices = widget.options?.choices || [];
      return (
        <div className="athena-widget-radio">
          {choices.map((choice: any, i: number) => (
            <label key={i} className="athena-widget-radio-option">
              <input
                type="radio"
                name={widgetId}
                checked={value === i}
                onChange={() => onChange(i)}
              />
              <span dangerouslySetInnerHTML={{ __html: formatContent(choice.content) }} />
            </label>
          ))}
        </div>
      );

    case 'dropdown':
      const options = widget.options?.choices || [];
      return (
        <select
          className="athena-widget-dropdown"
          value={value !== undefined ? String(value) : ''}
          onChange={(e) => onChange(parseInt(e.target.value))}
        >
          <option value="">{widget.options?.placeholder || 'Select...'}</option>
          {options.map((opt: string, i: number) => (
            <option key={i} value={i}>{opt}</option>
          ))}
        </select>
      );

    default:
      return <span>[{widget.type}]</span>;
  }
}

function renderWidgetPreview(widgetId: string, widget: any, value: unknown, onChange: (id: string, v: unknown) => void) {
  return `<span data-widget-id="${widgetId}">[Widget: ${widget.type}]</span>`;
}

/**
 * Format content with basic math rendering
 */
function formatContent(content: string): string {
  return content
    // Display math
    .replace(/\$\$([\s\S]*?)\$\$/g, '<div class="athena-math-display">$1</div>')
    // Inline math
    .replace(/\$(.*?)\$/g, '<span class="athena-math-inline">$1</span>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Code blocks
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="athena-code"><code>$2</code></pre>')
    // Inline code
    .replace(/`(.*?)`/g, '<code>$1</code>')
    // Line breaks
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br />');
}

// Demo styles
const DEMO_STYLES = `
.athena-demo {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
  color: #333;
}

.athena-demo[data-theme="dark"] {
  background: #1a1a2e;
  color: #eee;
}

.athena-demo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #3b82f6;
  color: white;
}

.athena-demo-logo {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.athena-demo-logo h1 {
  margin: 0;
  font-size: 1.5rem;
}

.athena-demo-version {
  opacity: 0.7;
  font-size: 0.875rem;
}

.athena-demo-controls {
  display: flex;
  gap: 0.5rem;
}

.athena-demo-theme-btn,
.athena-demo-editor-btn {
  padding: 0.5rem 1rem;
  border: 1px solid rgba(255,255,255,0.3);
  background: transparent;
  color: white;
  border-radius: 4px;
  cursor: pointer;
}

.athena-demo-theme-btn.active {
  background: rgba(255,255,255,0.2);
}

.athena-demo-main {
  display: flex;
  flex: 1;
}

.athena-demo-sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e0e0e0;
  padding: 1rem;
}

[data-theme="dark"] .athena-demo-sidebar {
  background: #252540;
  border-color: #333;
}

.athena-demo-sidebar h2 {
  margin: 0 0 1rem;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #666;
}

.athena-demo-question-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.athena-demo-question-item {
  width: 100%;
  padding: 0.75rem;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
  margin-bottom: 0.25rem;
  display: flex;
  flex-direction: column;
}

.athena-demo-question-item:hover {
  background: #f0f0f0;
}

[data-theme="dark"] .athena-demo-question-item:hover {
  background: #333;
}

.athena-demo-question-item.active {
  background: #3b82f6;
  color: white;
}

.athena-demo-question-subject {
  font-size: 0.75rem;
  opacity: 0.7;
}

.athena-demo-question-title {
  font-size: 0.875rem;
  font-weight: 500;
}

.athena-demo-content {
  flex: 1;
  padding: 2rem;
  max-width: 900px;
}

.athena-demo-question {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

[data-theme="dark"] .athena-demo-question {
  background: #252540;
}

.athena-demo-question h2 {
  margin: 0 0 0.5rem;
}

.athena-demo-subject-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background: #e0e7ff;
  color: #3b82f6;
  border-radius: 4px;
  font-size: 0.75rem;
  margin-bottom: 1.5rem;
}

.athena-demo-question-content {
  font-size: 1.125rem;
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.athena-math-display {
  display: block;
  text-align: center;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 4px;
  margin: 1rem 0;
  font-family: 'Times New Roman', serif;
  font-size: 1.25rem;
}

[data-theme="dark"] .athena-math-display {
  background: #1a1a2e;
}

.athena-math-inline {
  font-family: 'Times New Roman', serif;
  padding: 0 0.25rem;
}

.athena-widget-input {
  padding: 0.5rem 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
  min-width: 100px;
}

.athena-widget-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.athena-widget-radio {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 1rem 0;
}

.athena-widget-radio-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 4px;
  cursor: pointer;
}

[data-theme="dark"] .athena-widget-radio-option {
  background: #1a1a2e;
}

.athena-widget-radio-option:hover {
  background: #f0f0f0;
}

.athena-widget-dropdown {
  padding: 0.5rem 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
  min-width: 200px;
}

.athena-demo-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.athena-demo-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}

.athena-demo-btn--primary {
  background: #3b82f6;
  color: white;
}

.athena-demo-btn--secondary {
  background: #e0e0e0;
  color: #333;
}

.athena-demo-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.athena-demo-result {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 4px;
  font-weight: 500;
}

.athena-demo-result.correct {
  background: #d1fae5;
  color: #065f46;
}

.athena-demo-result.incorrect {
  background: #fee2e2;
  color: #991b1b;
}

.athena-demo-hints {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.athena-demo-hint {
  padding: 1rem;
  background: #fffbeb;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

[data-theme="dark"] .athena-demo-hint {
  background: #3d3d1e;
}

.athena-demo-editor {
  margin-top: 2rem;
}

.athena-demo-json {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.875rem;
}

.athena-demo-footer {
  padding: 1rem 2rem;
  background: #333;
  color: #999;
  text-align: center;
  font-size: 0.875rem;
}

.athena-demo-footer p {
  margin: 0.25rem 0;
}

.athena-code {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
}
`;

export default AthenaDemo;
