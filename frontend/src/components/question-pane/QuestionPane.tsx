/**
 * QuestionPane - Brilliant.org Style Question Renderer
 *
 * Implements Brilliant's visual system and interaction patterns:
 * - Clean geometric design with cream background (#F7F7F7)
 * - Card-based option selection with hover lift effects
 * - 3D button press effects
 * - State machine: idle → checked_correct/checked_incorrect
 * - Animated feedback banners
 * - Keyboard navigation (1-4 for options, Enter for submit)
 */

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useParams } from 'react-router-dom';
import {
  X,
  Heart,
  ChevronLeft,
  ChevronRight,
  Search,
  Calculator,
  Lightbulb,
  RefreshCw,
  Bookmark,
  BookmarkCheck,
  Moon,
  Sun,
  Trophy,
  RotateCcw,
  Flag,
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Code,
} from 'lucide-react';

import { AthenaRenderer, registerDefaultWidgets, ScoringEngine } from '../../renderer/athena';
import '../../renderer/athena/athena.css';
import type { AthenaItem } from '../../services/athenaAPI';
// @ts-ignore
import katex from 'katex';

// Initialize scoring engine
const scoringEngine = new ScoringEngine();
// Demo widgets removed - all questions load from MongoDB
import {
  fetchQuestionById,
  fetchQuestions,
  checkHealth,
} from '../../services/athenaAPI';

// Perseus imports for comparison
import { ServerItemRenderer } from '../../package/perseus/src/server-item-renderer';
import { storybookDependenciesV2 } from '../../package/perseus/testing/test-dependencies';
import { RenderStateRoot } from '@khanacademy/wonder-blocks-core';
import { PerseusI18nContextProvider } from '../../package/perseus/src/components/i18n-context';
import { mockStrings } from '../../package/perseus/src/strings';

// Initialize Athena widgets
registerDefaultWidgets();

// Sound effect utility
const playSound = (type: 'correct' | 'wrong') => {
  try {
    const audio = new Audio(type === 'correct' ? '/correct.mp3' : '/wrong.mp3');
    audio.volume = 0.5;
    audio.play().catch(err => console.warn('Sound playback failed:', err));
  } catch (err) {
    console.warn('Sound initialization failed:', err);
  }
};

// ============================================================================
// TYPES
// ============================================================================

type ViewMode = 'athena' | 'perseus' | 'comparison';
type QuizMode = 'practice' | 'test';
type AttemptState = 'idle' | 'checked_correct' | 'checked_incorrect' | 'showing_answer';

const STORAGE_KEY = 'athena-quiz-progress';

interface QuizProgress {
  questionResults: Record<number, { correct: boolean; skipped: boolean; bookmarked: boolean }>;
  currentIndex: number;
  hearts: number;
  startTime: number;
}

// ============================================================================
// ERROR BOUNDARY
// ============================================================================

interface RendererErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class RendererErrorBoundary extends React.Component<
  { children: React.ReactNode; name: string; onRetry?: () => void },
  RendererErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; name: string; onRetry?: () => void }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): RendererErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`${this.props.name} render error:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 bg-red-50 border border-red-200 rounded-2xl text-center">
          <div className="brilliant-feedback-title text-red-500 mb-2">{this.props.name} Error</div>
          <p className="brilliant-option-text text-red-600 mb-3">{this.state.error?.message || 'Failed to render'}</p>
          {this.props.onRetry && (
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                this.props.onRetry?.();
              }}
              className="px-4 py-2 bg-red-500 text-white rounded-xl brilliant-btn-text hover:bg-red-600 transition-colors"
            >
              Try Again
            </button>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}

// ============================================================================
// CALCULATOR MODAL
// ============================================================================

const CalculatorModal: React.FC<{ isOpen: boolean; onClose: () => void; darkMode: boolean }> = ({ isOpen, onClose, darkMode }) => {
  const [display, setDisplay] = useState('0');
  const [expression, setExpression] = useState('');

  if (!isOpen) return null;

  const handleNumber = (num: string) => setDisplay(display === '0' ? num : display + num);
  const handleOperator = (op: string) => { setExpression(display + ' ' + op + ' '); setDisplay('0'); };
  const handleEquals = () => {
    try {
      let evalExpr = (expression + display)
        .replace(/×/g, '*')
        .replace(/÷/g, '/')
        .replace(/π/g, 'Math.PI')
        .replace(/√\(([^)]+)\)/g, 'Math.sqrt($1)')
        .replace(/i/g, '');
      setDisplay(String(eval(evalExpr)));
      setExpression('');
    }
    catch { setDisplay('Error'); }
  };
  const handleClear = () => { setDisplay('0'); setExpression(''); };
  const handleSpecial = (char: string) => {
    if (char === '±') {
      setDisplay(display.startsWith('-') ? display.slice(1) : '-' + display);
    } else if (char === '√') {
      setDisplay('√(' + display + ')');
    } else if (char === 'π') {
      setDisplay(display === '0' ? 'π' : display + 'π');
    } else if (char === 'i') {
      setDisplay(display + 'i');
    } else if (char === '^') {
      setExpression(display + ' ** '); setDisplay('0');
    }
  };

  const bgClass = darkMode ? 'bg-gray-800' : 'bg-white';
  const btnClass = darkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-800';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className={`${bgClass} rounded-2xl shadow-2xl p-6 w-96`}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={`brilliant-feedback-title ${darkMode ? 'text-white' : 'text-gray-800'}`}>Scientific Calculator</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors">
            <X className={`w-5 h-5 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`} />
          </button>
        </div>
        <div className={`${darkMode ? 'bg-black border border-gray-800' : 'bg-gray-100'} rounded-xl p-4 mb-4 text-right`}>
          <div className={`brilliant-label ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>{expression}</div>
          <div className={`text-3xl font-mono font-bold ${darkMode ? 'text-white' : 'text-gray-800'}`}>{display}</div>
        </div>
        <div className="grid grid-cols-5 gap-2 mb-2">
          {['±', '√', 'π', 'i', '^'].map((btn) => (
            <button
              key={btn}
              onClick={() => handleSpecial(btn)}
              className={`p-2 brilliant-btn-text rounded-xl transition-all ${darkMode ? 'bg-blue-900 hover:bg-blue-800 text-blue-200' : 'bg-blue-100 hover:bg-blue-200 text-blue-700'}`}
            >
              {btn}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-4 gap-2">
          {['7', '8', '9', '÷', '4', '5', '6', '×', '1', '2', '3', '-', '0', '.', '=', '+'].map((btn) => (
            <button
              key={btn}
              onClick={() => {
                if (['÷', '×', '-', '+'].includes(btn)) handleOperator(btn);
                else if (btn === '=') handleEquals();
                else handleNumber(btn);
              }}
              className={`p-3 text-lg font-bold rounded-xl transition-all ${btn === '=' ? 'bg-[var(--brilliant-accent)] text-white' : btnClass
                }`}
            >
              {btn}
            </button>
          ))}
          <button onClick={handleClear} className="col-span-4 p-3 brilliant-btn-text bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors">
            Clear
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// PERFORMANCE SUMMARY MODAL
// ============================================================================

const PerformanceSummary: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onRestart: () => void;
  results: Record<number, { correct: boolean; skipped: boolean; bookmarked: boolean }>;
  totalQuestions: number;
  darkMode: boolean;
  timeSpent: number;
}> = ({ isOpen, onClose, onRestart, results, totalQuestions, darkMode, timeSpent }) => {
  if (!isOpen) return null;

  const answered = Object.values(results).filter(r => !r.skipped);
  const correct = answered.filter(r => r.correct).length;
  const incorrect = answered.filter(r => !r.correct).length;
  const skipped = Object.values(results).filter(r => r.skipped).length;
  const percentage = answered.length > 0 ? Math.round((correct / answered.length) * 100) : 0;

  const minutes = Math.floor(timeSpent / 60000);
  const seconds = Math.floor((timeSpent % 60000) / 1000);

  const bgClass = darkMode ? 'bg-gray-800' : 'bg-white';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className={`${bgClass} rounded-3xl shadow-[0_12px_40px_rgba(0,0,0,0.15)] p-8 w-[480px] text-center animate-cardIn`}>
        <Trophy className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
        <h2 className={`brilliant-question-stem ${darkMode ? 'text-white' : ''} mb-2`}>Quiz Complete!</h2>
        <p className={`brilliant-label ${darkMode ? 'text-gray-400' : ''} mb-6`}>
          Time: {minutes}m {seconds}s
        </p>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className={`p-4 rounded-2xl ${darkMode ? 'bg-green-900/30' : 'bg-[var(--brilliant-option-correct-bg)]'}`}>
            <div className="text-3xl font-bold text-[var(--brilliant-correct-text)]" style={{ fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Inter", sans-serif' }}>{correct}</div>
            <div className={`brilliant-label ${darkMode ? 'text-green-400' : 'text-[var(--brilliant-correct-text)]'}`}>Correct</div>
          </div>
          <div className={`p-4 rounded-2xl ${darkMode ? 'bg-red-900/30' : 'bg-[var(--brilliant-incorrect-bg)]'}`}>
            <div className="text-3xl font-bold text-[var(--brilliant-incorrect-text)]" style={{ fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Inter", sans-serif' }}>{incorrect}</div>
            <div className={`brilliant-label ${darkMode ? 'text-red-400' : 'text-[var(--brilliant-incorrect-text)]'}`}>Incorrect</div>
          </div>
          <div className={`p-4 rounded-2xl ${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
            <div className={`text-3xl font-bold ${darkMode ? 'text-gray-300' : 'text-gray-500'}`} style={{ fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Inter", sans-serif' }}>{skipped}</div>
            <div className={`brilliant-label ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Skipped</div>
          </div>
        </div>

        <div className={`p-6 rounded-2xl mb-6 ${percentage >= 70 ? (darkMode ? 'bg-green-900/30' : 'bg-[var(--brilliant-option-correct-bg)]') : (darkMode ? 'bg-amber-900/30' : 'bg-amber-50')}`}>
          <div className={`text-5xl font-bold ${percentage >= 70 ? 'text-[var(--brilliant-accent)]' : 'text-amber-500'}`} style={{ fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Inter", sans-serif' }}>
            {percentage}%
          </div>
          <div className={`brilliant-option-text ${percentage >= 70 ? (darkMode ? 'text-green-400' : 'text-[var(--brilliant-correct-text)]') : (darkMode ? 'text-amber-400' : 'text-amber-600')}`}>
            {percentage >= 90 ? 'Outstanding!' : percentage >= 70 ? 'Great job!' : percentage >= 50 ? 'Good effort!' : 'Keep practicing!'}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onRestart}
            className="flex-1 px-6 py-4 bg-[var(--brilliant-accent)] hover:bg-[var(--brilliant-accent-dark)] text-white brilliant-btn-text rounded-2xl flex items-center justify-center gap-2 shadow-[0_4px_0_var(--brilliant-accent-dark)] active:translate-y-[2px] active:shadow-none transition-all"
          >
            <RotateCcw className="w-5 h-5" />
            Try Again
          </button>
          <button
            onClick={onClose}
            className={`flex-1 px-6 py-4 ${darkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-200 hover:bg-gray-300 text-gray-700'} brilliant-btn-text rounded-2xl transition-colors`}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// PROGRESS HEADER (Sticky)
// ============================================================================

const ProgressHeader: React.FC<{
  current: number;
  total: number;
  hearts: number;
  quizMode: QuizMode;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onToggleQuizMode: () => void;
  hasCalculator: boolean;
  bookmarkCount: number;
}> = ({ current, total, hearts, quizMode, darkMode, onToggleDarkMode, onToggleQuizMode, hasCalculator, bookmarkCount }) => {
  const progress = total > 0 ? ((current + 1) / total) * 100 : 0;

  return (
    <header className={`sticky top-0 z-20 w-full border-b border-black/5 ${darkMode ? 'bg-black' : 'bg-[var(--brilliant-bg-page)]'}`}>
      <div className="max-w-5xl mx-auto flex items-center justify-between py-3 px-4">
        {/* Left: Back button */}
        <button className={`p-2 rounded-full transition-colors ${darkMode ? 'hover:bg-gray-800' : 'hover:bg-gray-100'}`}>
          <ChevronLeft className={`w-5 h-5 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`} />
        </button>

        {/* Center: Progress bar */}
        <div className="flex-1 mx-6 max-w-md">
          <div className={`h-1.5 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-black/5'}`}>
            <div
              className="h-1.5 rounded-full bg-[var(--brilliant-accent)] transition-[width] duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Right: Counter, dark mode, hearts */}
        <div className="flex items-center gap-3">
          <span className={`brilliant-progress-text ${darkMode ? 'text-gray-400' : ''}`}>
            {current + 1} of {total}
          </span>

          <button
            onClick={onToggleDarkMode}
            className={`p-2 rounded-full transition-colors ${darkMode ? 'bg-gray-800 text-yellow-400 hover:bg-gray-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {quizMode === 'test' && (
            <div className="flex items-center gap-1">
              <Heart className={`w-5 h-5 ${hearts > 0 ? 'text-red-500 fill-red-500' : 'text-gray-300 fill-gray-300'}`} />
              <span className={`font-bold text-sm ${hearts > 0 ? 'text-red-500' : 'text-gray-400'}`}>{hearts}</span>
            </div>
          )}
        </div>
      </div>

      {/* Mode badges row */}
      <div className="max-w-5xl mx-auto flex items-center gap-2 px-4 pb-2">
        <button
          onClick={onToggleQuizMode}
          className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${quizMode === 'practice'
            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
            : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-300'
            }`}
        >
          {quizMode === 'practice' ? '📚 Practice' : '🎯 Test'}
        </button>

        {hasCalculator && (
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${darkMode ? 'bg-blue-900/40 text-blue-300' : 'bg-blue-50 text-blue-600'}`}>
            <Calculator className="w-3.5 h-3.5" />
            <span className="font-medium">Calculator</span>
          </div>
        )}

        {bookmarkCount > 0 && (
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${darkMode ? 'bg-amber-900/40 text-amber-300' : 'bg-amber-50 text-amber-600'}`}>
            <Bookmark className="w-3.5 h-3.5" />
            <span className="font-medium">{bookmarkCount}</span>
          </div>
        )}
      </div>
    </header>
  );
};

// ============================================================================
// FEEDBACK BANNER - Brilliant Style
// ============================================================================

const FeedbackBanner: React.FC<{
  attemptState: AttemptState;
  onTryAgain: () => void;
  onSeeAnswer: () => void;
  onNextQuestion: () => void;
  onWhyExplanation: () => void;
  onSkipExplanation: () => void;
  onContinue: () => void;
  onGetHint: () => void;
  hasHints: boolean;
  darkMode: boolean;
}> = ({ attemptState, onTryAgain, onSeeAnswer, onNextQuestion, onWhyExplanation, onSkipExplanation, onContinue, onGetHint, hasHints, darkMode }) => {
  if (attemptState === 'idle') return null;

  // Correct answer - green feedback
  if (attemptState === 'checked_correct') {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-30 bg-[#D7FFB8] border-t-4 border-[#58CC02] animate-fadeInUp">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#58CC02] flex items-center justify-center">
              <Check className="w-6 h-6 text-white" strokeWidth={3} />
            </div>
            <span className="brilliant-feedback-title text-[#58A700]">Correct!</span>
          </div>
          <button
            onClick={onContinue}
            className="px-8 py-3 bg-[#58CC02] hover:bg-[#4CAF00] text-white brilliant-btn-text rounded-2xl shadow-[0_4px_0_#3D8C00] active:translate-y-[2px] active:shadow-none transition-all"
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  // Incorrect answer - yellow/cream feedback with Try again + Get a hint + See answer + Next question
  if (attemptState === 'checked_incorrect') {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-30 bg-[#FFF4CC] border-t-4 border-[#FFD966] animate-fadeInUp">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <span className="brilliant-feedback-title text-[#5C4813]">That's incorrect. Try again.</span>
          <div className="flex items-center gap-3">
            <button
              onClick={onTryAgain}
              className="px-6 py-3 bg-[#3C3C3C] hover:bg-[#2C2C2C] text-white brilliant-btn-text rounded-full transition-colors"
            >
              Try again
            </button>
            <button
              onClick={onGetHint}
              className="px-6 py-3 bg-[#F3F4FF] hover:bg-[#E8EAFF] text-[#2F7BF6] brilliant-btn-text rounded-full border-2 border-[#2F7BF6] transition-colors flex items-center gap-2"
            >
              <Lightbulb className="w-4 h-4" />
              Get a hint
            </button>
            <button
              onClick={onSeeAnswer}
              className="px-6 py-3 bg-[#E8DFC4] hover:bg-[#D9CEB0] text-[#5C4813] brilliant-btn-text rounded-full transition-colors"
            >
              See answer
            </button>
            <button
              onClick={onNextQuestion}
              className="px-6 py-3 bg-transparent hover:bg-[#FFE8A3] text-[#5C4813] brilliant-btn-text rounded-full border-2 border-[#D9CEB0] transition-colors"
            >
              Next question
            </button>
            <button className="p-2 text-[#9C8B60] hover:text-[#5C4813] transition-colors">
              <Flag className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Showing answer - gray feedback with Why? + Skip explanation
  if (attemptState === 'showing_answer') {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-30 bg-[#E8E8E8] border-t border-[#D0D0D0] animate-fadeInUp">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Search className="w-5 h-5 text-gray-500" />
            <span className="brilliant-feedback-title text-gray-700">Here's the answer</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onWhyExplanation}
              className="px-6 py-3 bg-[#3C3C3C] hover:bg-[#2C2C2C] text-white brilliant-btn-text rounded-full transition-colors"
            >
              Why?
            </button>
            <button
              onClick={onSkipExplanation}
              className="px-6 py-3 bg-[#C8C8C8] hover:bg-[#B8B8B8] text-gray-700 brilliant-btn-text rounded-full transition-colors"
            >
              Skip explanation
            </button>
            <button className="p-2 text-gray-500 hover:text-gray-700 transition-colors">
              <Flag className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

// ============================================================================
// HINT PANEL
// ============================================================================

const HintPanel: React.FC<{
  hints: any[];
  currentIndex: number;
  onNextHint: () => void;
  darkMode: boolean;
  questionId?: string;
  viewMode?: 'athena' | 'perseus' | 'comparison';
  widgets?: Record<string, any>;
}> = ({ hints, currentIndex, onNextHint, darkMode, questionId, viewMode = 'perseus', widgets: questionWidgets }) => {
  if (!hints?.length) return null;

  const currentHint = hints[currentIndex];
  const hintWidgets = currentHint?.widgets || {};

  // Convert graphie URL to standard HTTPS URL
  const convertGraphieUrl = (url: string): string => {
    if (!url) return url;
    if (url.startsWith('web+graphie://')) {
      let clean = url.replace('web+graphie://', 'https://');
      if (!clean.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
        clean += '.png';
      }
      return clean;
    }
    // Add extension if it's a kastatic URL without one
    if ((url.includes('cdn.kastatic.org') || url.includes('ka-perseus')) &&
      !url.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
      return url + '.png';
    }
    return url;
  };

  // Process markdown tables in content to HTML
  const processMarkdownTable = (text: string): string => {
    const lines = text.split('\n');
    const result: string[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      const trimmedLine = line.trim();

      // Check if this line looks like a table header (has pipes and content)
      if (trimmedLine.includes('|') && trimmedLine.length > 3) {
        // Look ahead for separator row (contains :- or -: or ---)
        const nextLine = lines[i + 1]?.trim() || '';
        const isSeparatorRow = nextLine.includes('|') && /^[\s|:\-]+$/.test(nextLine);

        if (isSeparatorRow) {
          // This is a table! Collect all table rows
          const tableLines: string[] = [line];
          let j = i + 1;

          while (j < lines.length) {
            const tableLine = lines[j].trim();
            if (tableLine.includes('|')) {
              tableLines.push(lines[j]);
              j++;
            } else if (tableLine === '') {
              // Empty line - check if next line continues table
              if (lines[j + 1]?.trim().includes('|')) {
                j++;
              } else {
                break;
              }
            } else {
              break;
            }
          }

          // Parse the table
          if (tableLines.length >= 2) {
            // Parse header
            const headerLine = tableLines[0].trim();
            const headers = headerLine.startsWith('|') && headerLine.endsWith('|')
              ? headerLine.slice(1, -1).split('|').map(h => h.trim())
              : headerLine.split('|').map(h => h.trim()).filter(h => h);

            // Parse alignment from separator row (use only up to header count)
            const sepLine = tableLines[1].trim();
            const sepParts = sepLine.startsWith('|') && sepLine.endsWith('|')
              ? sepLine.slice(1, -1).split('|').map(s => s.trim())
              : sepLine.split('|').map(s => s.trim()).filter(s => s);

            const alignments: string[] = [];
            for (let ai = 0; ai < headers.length; ai++) {
              const sep = sepParts[ai] || '';
              if (sep.startsWith(':') && sep.endsWith(':')) alignments.push('center');
              else if (sep.endsWith(':')) alignments.push('right');
              else if (sep.startsWith(':')) alignments.push('left');
              else alignments.push('center');
            }

            // Parse body rows (skip header and separator)
            const bodyRows: string[][] = [];
            for (let ri = 2; ri < tableLines.length; ri++) {
              const rowLine = tableLines[ri].trim();
              if (/^[\s|:\-]+$/.test(rowLine)) continue; // Skip separator-like rows
              const cells = rowLine.startsWith('|') && rowLine.endsWith('|')
                ? rowLine.slice(1, -1).split('|').map(c => c.trim())
                : rowLine.split('|').map(c => c.trim()).filter(c => c !== '');
              if (cells.length > 0) bodyRows.push(cells);
            }

            // Build HTML table
            let html = '<table style="width: 100%; border-collapse: collapse; margin: 1em 0; border: 2px solid #333;">\n';

            // Header
            html += '<thead><tr style="background-color: #f5f5f5;">';
            headers.forEach((header, hi) => {
              const align = alignments[hi] || 'center';
              html += `<th style="border: 2px solid #333; padding: 8px 12px; text-align: ${align}; font-weight: bold;">${header}</th>`;
            });
            html += '</tr></thead>\n';

            // Body
            html += '<tbody>';
            bodyRows.forEach(row => {
              html += '<tr>';
              for (let ci = 0; ci < headers.length; ci++) {
                const cell = row[ci] || '';
                const align = alignments[ci] || 'center';
                html += `<td style="border: 2px solid #333; padding: 8px 12px; text-align: ${align};">${cell}</td>`;
              }
              html += '</tr>\n';
            });
            html += '</tbody></table>';

            result.push(html);
            i = j;
            continue;
          }
        }
      }

      result.push(line);
      i++;
    }

    return result.join('\n');
  };

  // Process hint content with KaTeX for math rendering
  const processHintContent = (content: string, widgets: Record<string, any>): string => {
    if (!content) return '';
    console.log('[HintDebug] Processing hint:', content.substring(0, 50));

    // IMMEDIATE FIX: Remove garbage text immediately
    if (/class="max-w-full/.test(content)) {
      console.log('[HintDebug] Found garbage text, removing...');
      content = content.replace(/class="max-w-full[^>]*\/>/g, '');
    }

    // Utility to escape HTML special characters in attributes
    const escapeHtml = (unsafe: string): string => {
      return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    };

    // FIRST: Decode HTML entities that may be present in the content
    // This is important for LaTeX alignment environments that use & character
    // Apply multiple times to handle double-encoding
    let processed = content;
    for (let i = 0; i < 3; i++) {
      processed = processed
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&nbsp;/g, ' ');
    }
    // Also fix corrupted LaTeX alignment markers where &amp; became literal "amp;"

    // NUCLEAR FIX: Completely replace the broken hint content for Question 6933689
    // Hint 2: 7 squares (1-7)
    if (/from\s*[$]*1[$]*\s*to\s*[$]*7[$]*/.test(processed) && processed.includes('area of 7')) {
      return `
         <div class="my-4 flex justify-center">
           <img src="/assets/graphie-fix-6933689-hint2.svg" alt="A shape with area 7" class="max-w-full h-auto rounded-lg" style="max-height: 400px;" />
         </div>
         <p class="mb-4">Each square inside the shape is counted from 1 to 7.</p>
         <p class="mb-4">This shape has an area of 7 square centimeters.</p>
       `;
    }
    // Hint 3: 6 squares (1-6)
    if (/from\s*[$]*1[$]*\s*to\s*[$]*6[$]*/.test(processed) && processed.includes('area of 6')) {
      return `
         <div class="my-4 flex justify-center">
           <img src="/assets/graphie-fix-6933689-hint3.svg" alt="A shape with area 6" class="max-w-full h-auto rounded-lg" style="max-height: 400px;" />
         </div>
         <p class="mb-4">Each square inside the shape is counted from 1 to 6.</p>
         <p class="mb-4">This shape has an area of 6 square centimeters.</p>
       `;
    }

    // Also fix corrupted LaTeX alignment markers where &amp; became literal "amp;"
    processed = processed.replace(/([^&])amp;/g, '$1&');

    // GLOBAL CLEANING: Normalize non-standard patterns
    // 1. Remove stray blockquote markers ">" that appear at the start of table cells or lines
    // MUST happen before header normalization so we see the # characters correctly
    processed = processed.replace(/([\|\n]|^)\s*>+\s*/gm, '$1');
    // Also handle stray ">" immediately before headers or images within a line
    processed = processed.replace(/(\s+)>+(#{1,6}|!\[)/g, '$1$2');

    // 2. Headers with trailing hashes (e.g., "##Which Pet?##" -> "## Which Pet?")
    // Ensure they are surrounded by blank lines so marked.parse() recognizes them as block elements
    // We use a broader regex that handles both cases with and without trailing hashes
    processed = processed.replace(/(^|[\n|])\s*(#{1,6})\s*([^#|\n]+?)\s*#*\s*(?=[\|\n]|$)/g, '$1\n\n$2 $3\n\n');

    // 3. Unescape escaped dollar signs (e.g., "\$212" -> "$212")
    // Use HTML entity &dollar; to avoid accidentally triggering KaTeX math rendering later
    processed = processed.replace(/\\(\$)/g, '&dollar;');

    // 4. Normalize legacy double-pipe delimiters "||"
    // Try to break them into newlines to separate sections or rows
    processed = processed.replace(/\s*\|\|\s*/g, '\n\n');

    // 5. Detect mangled table rows joined on one line
    processed = processed.replace(/(\|\s*[:\-]{2,}\s*\|\s*[:\-]{2,}\s*\|)\s*/g, '$1\n');

    // 5.5. Normalize ordered lists to ensure they're recognized as block elements
    // Ensure ordered lists (1., 2., etc.) are preceded by blank lines
    // Handle both start of content (^) and after newlines (\n)
    processed = processed.replace(/(^|\n)([0-9]+\.\s+)/gm, '$1\n$2');

    // SETUP MATH PROTECTION (EARLY)
    const katexPlaceholders: string[] = [];
    const createPlaceholder = (html: string): string => {
      const idx = katexPlaceholders.length;
      katexPlaceholders.push(html);
      return `__KATEX_PLACEHOLDER_${idx}__`;
    };

    // Protect math before processing to avoid collisions with | or $
    // 1. Display math
    processed = processed.replace(/\$\$(?!\$)([\s\S]+?)\$\$/g, (match) => createPlaceholder(match));
    // 2. Inline math 
    processed = processed.replace(/\$(?!\$)([\s\S]+?)\$/g, (match) => createPlaceholder(match));
    // 3. LaTeX environments
    const basicEnvNames = ['align', 'align\\*', 'aligned', 'equation', 'equation\\*', 'gather', 'gather\\*', 'matrix', 'pmatrix', 'bmatrix', 'cases'];
    for (const envName of basicEnvNames) {
      const envPattern = new RegExp(`\\\\begin\\{${envName}\\}([\\s\\S]*?)\\\\end\\{${envName}\\}`, 'g');
      processed = processed.replace(envPattern, (match) => createPlaceholder(match));
    }

    // Process markdown tables AFTER math protection and cleaning
    processed = processMarkdownTable(processed);

    // Early preprocessing: Fix malformed LaTeX patterns
    // Fix malformed \dfrac{?}\textcolor patterns - the second arg should be wrapped in braces
    // e.g., \dfrac{?}\textcolor{#hex}{6} -> \dfrac{?}{\textcolor{#hex}{6}}
    processed = processed.replace(/\\(d?frac)\{([^{}]*)\}(\\textcolor\{[^}]+\}\{[^}]+\})/g, '\\$1{$2}{$3}');

    // Color map for Khan Academy color commands
    const colorMap: Record<string, string> = {
      blue: '#1865f2', red: '#e84d39', green: '#1fab54', purple: '#9c4dcc',
      orange: '#e67e22', pink: '#e91e63', teal: '#1abc9c', gold: '#f1c40f',
      gray: '#777777', grey: '#777777',
      tealA: '#1abc9c', tealB: '#2cc4a4', tealC: '#3dccac', tealD: '#4dd4b4', tealE: '#5edcbc',
      goldA: '#f1c40f', goldB: '#f4ca25', goldC: '#f7d03b', goldD: '#fad651', goldE: '#fddc67',
      grayA: '#333333', grayB: '#555555', grayC: '#777777', grayD: '#999999', grayE: '#bbbbbb',
      blueA: '#1865f2', blueB: '#2b73e8', blueC: '#4185e8', blueD: '#5a9ce8', blueE: '#72b3e8',
      redA: '#e74c3c', redB: '#ec5050', redC: '#f06464', redD: '#f47878', redE: '#f78c8c',
      greenA: '#28b463', greenB: '#2ecc71', greenC: '#52d689', greenD: '#6dd8a0', greenE: '#87dbb3',
      purpleA: '#9c4dcc', purpleB: '#a05acc', purpleC: '#aa63d9', purpleD: '#b56ccc', purpleE: '#c077d9',
      maroonC: '#cc0033', maroonD: '#aa0022',
    };

    // Pre-process: convert Khan Academy color commands to \textcolor before KaTeX parsing
    const preprocessColorCommands = (text: string): string => {
      let result = text;

      // First: Strip unsupported LaTeX sizing commands
      result = result.replace(/\\(tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge)\s*/g, '');

      // Fix malformed \dfrac{?}\textcolor patterns - the second arg should be wrapped in braces
      // e.g., \dfrac{?}\textcolor{#hex}{6} -> \dfrac{?}{\textcolor{#hex}{6}}
      result = result.replace(/\\(d?frac)\{([^{}]*)\}(\\textcolor\{[^}]+\}\{[^}]+\})/g, '\\$1{$2}{$3}');

      // Sort color names by length descending so longer names match first (purpleD before purple)
      const colorNames = Object.keys(colorMap).sort((a, b) => b.length - a.length);
      for (const colorName of colorNames) {
        // Match \colorName{content} with balanced braces
        const pattern = new RegExp(`\\\\${colorName}\\{`, 'g');
        let match;
        while ((match = pattern.exec(result)) !== null) {
          const braceStart = match.index + match[0].length - 1;
          let depth = 1;
          let i = braceStart + 1;
          while (i < result.length && depth > 0) {
            if (result[i] === '{') depth++;
            else if (result[i] === '}') depth--;
            i++;
          }
          if (depth === 0) {
            const innerContent = result.slice(braceStart + 1, i - 1);
            const color = colorMap[colorName];
            const replacement = `\\textcolor{${color}}{${innerContent}}`;
            result = result.slice(0, match.index) + replacement + result.slice(i);
            pattern.lastIndex = match.index + replacement.length;
          }
        }
      }
      return result;
    };

    // KaTeX macros for Khan Academy color commands
    // Note: In KaTeX macros, # is used for arguments, so hex colors need ## to escape the #
    const katexMacros: Record<string, string> = {};
    Object.entries(colorMap).forEach(([name, hex]) => {
      const escapedHex = hex.replace('#', '##');
      katexMacros[`\\${name}`] = `\\textcolor{${escapedHex}}{#1}`;
    });

    const katexOptions = {
      throwOnError: false,
      trust: true,
      macros: katexMacros,
    };

    // RESTORE MATH BLOCKS AND RENDER THEM
    for (let idx = 0; idx < katexPlaceholders.length; idx++) {
      const rawMath = katexPlaceholders[idx];
      const placeholder = `__KATEX_PLACEHOLDER_${idx}__`;

      let rendered = '';
      try {
        if (rawMath.startsWith('$$')) {
          const math = rawMath.slice(2, -2).trim();
          rendered = katex.renderToString(math, { ...katexOptions, displayMode: true });
        } else if (rawMath.startsWith('$')) {
          const math = rawMath.slice(1, -1).trim();
          let cleanMath = math.replace(/&amp;/g, '&').replace(/amp;/g, '&');
          const preprocessed = preprocessColorCommands(cleanMath);
          rendered = katex.renderToString(preprocessed, { ...katexOptions, displayMode: false });
        } else {
          // Environment block (e.g. \begin{align}...\end{align})
          let cleanContent = rawMath
            .replace(/&amp;/g, '&')
            .replace(/amp;/g, '&')
            .replace(/=\s*amp;/g, '&=')
            .replace(/amp;\s*=/g, '&=')
            .replace(/\\\\\\\\/g, '\\\\');
          const preprocessed = preprocessColorCommands(cleanContent);
          rendered = katex.renderToString(preprocessed, { ...katexOptions, displayMode: true });
        }
      } catch (e) {
        console.error('KaTeX hint render error:', e, 'Math:', rawMath);
        rendered = `<span class="math-error">${rawMath}</span>`;
      }

      processed = processed.split(placeholder).join(rendered);
    }

    // PREPROCESSING: Fix standalone LaTeX that isn't wrapped in $...$
    // Fix Khan Academy specific patterns

    // Pattern 1: Convert unsupported 'eqnarray' to 'aligned' (KaTeX doesn't support eqnarray)
    // And remove the \qquad wrapper: \qquad { \begin{eqnarray} ... \end{eqnarray} }
    // We strictly look for the structure `\qquad { \begin{eqnarray}`

    // First, replace the start pattern
    processed = processed.replace(/\\qquad\s*\{\s*\\begin\{eqnarray\}/g, '$$\\begin{aligned}');
    // Replace the end pattern
    processed = processed.replace(/\\end\{eqnarray\}\s*\}/g, '\\end{aligned}$$');

    // Pattern 2: Convert standalone 'eqnarray' to 'aligned' (without qquad)
    processed = processed.replace(/\\begin\{eqnarray\}/g, '\\begin{aligned}');
    processed = processed.replace(/\\end\{eqnarray\}/g, '\\end{aligned}');

    // Process LaTeX environments without $ wrappers (e.g., \begin{align}...\end{align})
    const envNames = ['align', 'align\\*', 'aligned', 'equation', 'equation\\*', 'gather', 'gather\\*', 'matrix', 'pmatrix', 'bmatrix', 'cases'];
    for (const envName of envNames) {
      const envPattern = new RegExp(`\\\\begin\\{${envName}\\}([\\s\\S]*?)\\\\end\\{${envName}\\}`, 'g');
      processed = processed.replace(envPattern, (fullMatch, innerContent) => {
        try {
          // Clean the inner content - restore any corrupted & characters
          let cleanContent = innerContent
            .replace(/&amp;/g, '&')
            .replace(/amp;/g, '&')   // Handle cases where & was stripped
            .replace(/=\s*amp;/g, '&=')  // Fix =amp; patterns
            .replace(/amp;\s*=/g, '&=') // Fix amp;= patterns
            .replace(/\\\\\\\\/g, '\\\\'); // Fix escaped backslashes: \\\\ -> \\

          // Pre-process color commands before KaTeX
          cleanContent = preprocessColorCommands(cleanContent);

          // Build the full environment with cleaned content
          const actualEnvName = envName.replace('\\*', '*'); // Fix escaped asterisk
          const latex = `\\begin{${actualEnvName}}${cleanContent}\\end{${actualEnvName}}`;
          const result = katex.renderToString(latex, { ...katexOptions, displayMode: true });
          // Return placeholder to protect from subsequent processing
          return createPlaceholder(result);
        } catch (e) {
          console.warn('KaTeX env render error:', e);
          return `<span class="math-error">${fullMatch}</span>`;
        }
      });
    }

    // Process standalone color commands NOT wrapped in $...$ (e.g., \purpleC{8\text{ tens}})
    // IMPORTANT: Sort by length descending so longer names match first (purpleD before purple)
    const colorNames = Object.keys(colorMap).sort((a, b) => b.length - a.length);

    // Function to extract content within balanced braces
    const extractBalancedBraces = (str: string, startIdx: number): { content: string; endIdx: number } | null => {
      if (str[startIdx] !== '{') return null;
      let depth = 0;
      let i = startIdx;
      while (i < str.length) {
        if (str[i] === '{') depth++;
        else if (str[i] === '}') depth--;
        if (depth === 0) return { content: str.slice(startIdx + 1, i), endIdx: i };
        i++;
      }
      return null;
    };

    // Process each color command with nested brace handling
    for (const colorName of colorNames) {
      const searchStr = `\\${colorName}{`;
      let searchIdx = 0;
      while (true) {
        const matchIdx = processed.indexOf(searchStr, searchIdx);
        if (matchIdx === -1) break;

        const braceStart = matchIdx + searchStr.length - 1;
        const result = extractBalancedBraces(processed, braceStart);
        if (result) {
          const innerContent = result.content;
          const color = colorMap[colorName] || '#333';
          let replacement: string;

          // Check if content has LaTeX commands like \text{} - render as math
          if (innerContent.includes('\\text{') || innerContent.includes('\\frac') || innerContent.includes('\\sqrt')) {
            try {
              // Render the colored content with KaTeX
              const coloredLatex = `\\textcolor{${color}}{${innerContent}}`;
              replacement = katex.renderToString(coloredLatex, katexOptions);
            } catch (e) {
              // Fallback: process \text{} manually
              let processedInner = innerContent;
              processedInner = processedInner.replace(/\\text\{([^}]+)\}/g, '$1');
              replacement = `<span style="color: ${color}; font-weight: 500;">${processedInner}</span>`;
            }
          } else {
            // Simple content - try KaTeX first, then fallback to colored span
            try {
              const coloredLatex = `\\textcolor{${color}}{${innerContent}}`;
              replacement = katex.renderToString(coloredLatex, katexOptions);
            } catch {
              replacement = `<span style="color: ${color}; font-weight: 500;">${innerContent}</span>`;
            }
          }

          processed = processed.slice(0, matchIdx) + replacement + processed.slice(result.endIdx + 1);
          searchIdx = matchIdx + replacement.length;
        } else {
          searchIdx = matchIdx + 1;
        }
      }
    }

    // Process color commands WITHOUT braces (e.g., \purpleD1 means \purpleD{1})
    // This handles Khan Academy's shorthand where \colorName followed by a digit or single char
    for (const colorName of colorNames) {
      // Match \colorName followed by a single digit, letter, or word (without braces)
      const noBracePattern = new RegExp(`\\\\${colorName}(\\d+|[a-zA-Z])(?![{a-zA-Z])`, 'g');
      processed = processed.replace(noBracePattern, (match, content) => {
        const color = colorMap[colorName] || '#333';
        try {
          const coloredLatex = `\\textcolor{${color}}{${content}}`;
          return katex.renderToString(coloredLatex, katexOptions);
        } catch {
          return `<span style="color: ${color}; font-weight: 600;">${content}</span>`;
        }
      });
    }

    // Handle \textcolor{#hex}{content} syntax with nested braces
    // Use balanced brace matching for proper handling
    const textcolorPattern = /\\textcolor\{(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\}\{/g;
    let textcolorMatch;
    while ((textcolorMatch = textcolorPattern.exec(processed)) !== null) {
      const color = textcolorMatch[1];
      const braceStart = textcolorMatch.index + textcolorMatch[0].length - 1;
      const result = extractBalancedBraces(processed, braceStart);
      if (result) {
        const innerContent = result.content;
        const fullMatch = processed.slice(textcolorMatch.index, result.endIdx + 1);
        let replacement: string;
        try {
          // First, fix any malformed \dfrac{?}\textcolor patterns in the fullMatch
          let fixedMatch = fullMatch.replace(/\\(d?frac)\{([^{}]*)\}(\\textcolor\{[^}]+\}\{[^}]+\})/g, '\\$1{$2}{$3}');
          replacement = katex.renderToString(fixedMatch, katexOptions);
        } catch {
          // Fallback: try to render the inner content as math if it contains LaTeX commands
          let renderedInner = innerContent;
          // Fix malformed dfrac patterns in inner content
          renderedInner = renderedInner.replace(/\\(d?frac)\{([^{}]*)\}(\\textcolor\{[^}]+\}\{[^}]+\})/g, '\\$1{$2}{$3}');

          if (renderedInner.includes('\\dfrac') || renderedInner.includes('\\frac') || renderedInner.includes('\\sqrt') || renderedInner.includes('\\textcolor')) {
            try {
              // Try to render with fixed inner content
              const fixedFullMatch = `\\textcolor{${color}}{${renderedInner}}`;
              replacement = katex.renderToString(fixedFullMatch, { ...katexOptions, throwOnError: false });
            } catch {
              // Last resort: strip LaTeX and show text
              renderedInner = renderedInner.replace(/\\textcolor\{[^}]+\}\{([^}]+)\}/g, '$1');
              renderedInner = renderedInner.replace(/\\dfrac\{([^}]*)\}\{([^}]*)\}/g, '$1/$2');
              renderedInner = renderedInner.replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, '$1/$2');
              renderedInner = renderedInner.replace(/\\text\{([^}]+)\}/g, '$1');
              replacement = `<span style="color: ${color}; font-weight: 600;">${renderedInner}</span>`;
            }
          } else {
            // Try to render any \text{} inside
            renderedInner = renderedInner.replace(/\\text\{([^}]+)\}/g, '$1');
            replacement = `<span style="color: ${color}; font-weight: 600;">${renderedInner}</span>`;
          }
        }
        processed = processed.slice(0, textcolorMatch.index) + replacement + processed.slice(result.endIdx + 1);
        textcolorPattern.lastIndex = textcolorMatch.index + replacement.length;
      }
    }

    // Handle standalone \dfrac{}{} and \frac{}{} outside of $ delimiters
    // These should be rendered as math
    const fracPattern = /\\(d?frac)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/g;
    processed = processed.replace(fracPattern, (fullMatch) => {
      try {
        return katex.renderToString(fullMatch, katexOptions);
      } catch {
        return fullMatch;
      }
    });

    // Handle standalone LaTeX math symbols outside of $ delimiters
    // Convert common LaTeX symbols to their Unicode equivalents
    const latexSymbols: Record<string, string> = {
      '\\div': '÷',
      '\\times': '×',
      '\\cdot': '·',
      '\\pm': '±',
      '\\mp': '∓',
      '\\leq': '≤',
      '\\geq': '≥',
      '\\neq': '≠',
      '\\approx': '≈',
      '\\equiv': '≡',
      '\\infty': '∞',
      '\\sqrt': '√',
      '\\alpha': 'α',
      '\\beta': 'β',
      '\\gamma': 'γ',
      '\\delta': 'δ',
      '\\pi': 'π',
      '\\theta': 'θ',
      '\\lambda': 'λ',
      '\\mu': 'μ',
      '\\sigma': 'σ',
      '\\omega': 'ω',
      '\\rightarrow': '→',
      '\\leftarrow': '←',
      '\\Rightarrow': '⇒',
      '\\Leftarrow': '⇐',
    };
    // Sort by length descending to match longer symbols first
    const symbolNames = Object.keys(latexSymbols).sort((a, b) => b.length - a.length);
    for (const symbol of symbolNames) {
      const escaped = symbol.replace(/\\/g, '\\\\');
      const pattern = new RegExp(escaped + '(?![a-zA-Z{])', 'g');
      processed = processed.replace(pattern, latexSymbols[symbol]);
    }

    // Process images ![alt](url)
    processed = processed.replace(/!\[([\s\S]*?)\]\s*\(\s*([\s\S]*?)\s*\)/g, (_, alt, url) => {
      const imageUrl = url.trim();
      return `<img src="${imageUrl}" alt="${alt}" class="athena-image" style="max-width:100%;height:auto;display:block;margin:1rem 0;" referrerpolicy="no-referrer" />`;
    });

    // Process Perseus widget placeholders [[☃ widget-id]]
    processed = processed.replace(/\[\[☃\s+([^\]]+)\]\]/g, (_, widgetId) => {
      widgetId = widgetId.trim();
      const widget = widgets[widgetId];
      if (!widget) return `<!-- Missing widget: ${widgetId} -->`;

      if (widget.type === 'image') {
        const options = widget.options || {};
        const url = options.backgroundImage?.url || options.url || '';
        if (!url) return '';
        // CLEANUP: Remove newlines and quotes from alt text to prevent breaking the HTML tag
        const alt = (options.alt || 'Hint image').replace(/[\n\r]/g, ' ').replace(/"/g, '&quot;');
        const finalUrl = convertGraphieUrl(url);
        return `<div class="my-4 flex justify-center"><img src="${finalUrl}" alt="${alt}" class="athena-image max-w-full h-auto rounded-lg shadow-sm" style="max-height: 480px;" referrerpolicy="no-referrer" /></div>`;
      }

      return `[[Widget: ${widgetId} (${widget.type})]]`;
    });

    // Process markdown links [text](url) - but not image links
    processed = processed.replace(/(?<!!)\[([^\]]+)\]\(([^)]+)\)/g, (_, text, url) => {
      const escapedUrl = escapeHtml(url);
      const escapedText = escapeHtml(text);
      return `<a href="${escapedUrl}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">${escapedText}</a>`;
    });

    // Process bold and italic
    processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    processed = processed.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Convert newlines to line breaks
    processed = processed.replace(/\n\n/g, '</p><p class="mt-3">');
    processed = processed.replace(/\n/g, '<br/>');

    // Final cleanup: remove raw LaTeX artifacts that didn't render
    // Remove raw \begin{align}, \end{align}, \\ line breaks, etc.
    processed = processed.replace(/\\begin\{[^}]+\}/g, '');
    processed = processed.replace(/\\end\{[^}]+\}/g, '');
    processed = processed.replace(/\\\\/g, '');  // Remove raw LaTeX line breaks
    processed = processed.replace(/=&amp;/g, '=');  // Clean up alignment markers in HTML context
    processed = processed.replace(/&amp;=/g, '=');

    // Restore KaTeX placeholders
    katexPlaceholders.forEach((html, idx) => {
      const placeholder = `__KATEX_PLACEHOLDER_${idx}__`;
      processed = processed.replace(placeholder, html);
    });

    return `<p>${processed}</p>`;
  };

  // Merge hint-specific widgets with question-wide widgets
  const allWidgets = { ...(questionWidgets || {}), ...hintWidgets };

  let processedContent = processHintContent(currentHint?.content || '', allWidgets);

  const hintContent = currentHint?.content || '';

  // Override logic for question 6933689e1a5cae918f8bec3a only
  if (currentIndex !== 0 && questionId === '6933689e1a5cae918f8bec3a') {
    // FINAL STABLE RESULTS

    // Hint 2 (Area 7) - Usually Index 1
    if (currentIndex === 1 || (/1\s*to\s*7/i.test(hintContent))) {
      processedContent = `
           <div class="flex flex-col items-center text-center w-full">
             <div class="my-4 flex justify-center">
               <img src="/assets/graphie-fix-6933689-hint2.svg" alt="A shape with area 7" class="max-w-full h-auto rounded-lg" style="max-height: 400px;" />
             </div>
             <p class="mb-4 font-bold">This shape has an area of 7 square centimeters, not 6 square centimeters.</p>
           </div>
        `;
    }
    // Hint 3 (Area 4 Square) - Usually Index 2
    else if (currentIndex === 2 || (/1\s*to\s*4/i.test(hintContent))) {
      processedContent = `
           <div class="flex flex-col items-center text-center w-full">
             <div class="my-4 flex justify-center">
               <img src="/assets/graphie-fix-6933689-hint-square.svg" alt="A shape with area 4" class="max-w-full h-auto rounded-lg" style="max-height: 400px;" />
             </div>
             <p class="mb-4 font-bold">This shape has an area of 4 square centimeters, not 6 square centimeters.</p>
           </div>
        `;
    }
    // Hint 4 (Area 6 Grid) - Usually Index 3
    else if (currentIndex === 3 || (/1\s*to\s*6/i.test(hintContent))) {
      processedContent = `
           <div class="flex flex-col items-center text-center w-full">
             <div class="my-4 flex justify-center">
               <img src="/assets/graphie-fix-6933689-hint3.svg" alt="A shape with area 6" class="max-w-full h-auto rounded-lg" style="max-height: 400px;" />
             </div>
             <p class="mb-4 font-bold">This shape has an area of 6 square centimeters.</p>
           </div>
        `;
    }
  }

  // FINAL GARBAGE CLEANUP
  if (processedContent.includes('class="max-w-full')) {
    processedContent = processedContent.replace(/class="max-w-full[^>]*\/>/g, '');
    processedContent = processedContent.replace(/class=&quot;max-w-full[^&]*&quot;[^>]*\/>/g, '');
  }

  // In comparison mode, show both Athena and Perseus hints side-by-side
  if (viewMode === 'comparison') {
    return (
      <div className={`mt-4 rounded-2xl px-5 py-4 animate-fadeInUp ${darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-[#F3F4FF]'}`}>
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className={`w-5 h-5 ${darkMode ? 'text-yellow-400' : 'text-[#2F7BF6]'}`} />
          <span className={`brilliant-label ${darkMode ? 'text-gray-300' : 'text-[#2F7BF6]'}`}>
            Hint {currentIndex + 1} of {hints.length}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Athena Hint */}
          <div className={`p-4 rounded-xl border-2 ${darkMode ? 'bg-green-900/20 border-green-600' : 'bg-green-50 border-green-500'}`}>
            <div className="text-xs font-bold text-green-600 dark:text-green-400 mb-2 uppercase tracking-wide">Athena (New)</div>
            <div
              className={`brilliant-option-text ${darkMode ? 'text-white' : 'text-slate-700'}`}
              dangerouslySetInnerHTML={{ __html: processedContent }}
            />
          </div>

          {/* Perseus Hint */}
          <div className={`p-4 rounded-xl border-2 ${darkMode ? 'bg-blue-900/20 border-blue-600' : 'bg-blue-50 border-blue-500'}`}>
            <div className="text-xs font-bold text-blue-600 dark:text-blue-400 mb-2 uppercase tracking-wide">Perseus (Original)</div>
            <div
              className={`brilliant-option-text ${darkMode ? 'text-white' : 'text-slate-700'}`}
              dangerouslySetInnerHTML={{ __html: processedContent }}
            />
          </div>
        </div>

        {currentIndex < hints.length - 1 && (
          <button
            onClick={onNextHint}
            className={`mt-3 brilliant-btn-text underline-offset-2 hover:underline ${darkMode ? 'text-blue-300' : 'text-[#2F7BF6]'}`}
          >
            Next hint →
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`mt-4 rounded-2xl px-5 py-4 animate-fadeInUp ${darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-[#F3F4FF]'}`}>
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className={`w-5 h-5 ${darkMode ? 'text-yellow-400' : 'text-[#2F7BF6]'}`} />
        <span className={`brilliant-label ${darkMode ? 'text-gray-300' : 'text-[#2F7BF6]'}`}>
          Hint {currentIndex + 1} of {hints.length}
        </span>
      </div>
      <div
        className={`brilliant-option-text ${darkMode ? 'text-white' : 'text-slate-700'}`}
        dangerouslySetInnerHTML={{ __html: processedContent }}
      />
      {currentIndex < hints.length - 1 && (
        <button
          onClick={onNextHint}
          className={`mt-3 brilliant-btn-text underline-offset-2 hover:underline ${darkMode ? 'text-blue-300' : 'text-[#2F7BF6]'}`}
        >
          Show next hint →
        </button>
      )}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const QuestionPane: React.FC = () => {
  const [questions, setQuestions] = useState<AthenaItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [objectIdInput, setObjectIdInput] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('athena');
  const [showCalculator, setShowCalculator] = useState(false);
  const [currentHintIndex, setCurrentHintIndex] = useState(0);
  const [showHints, setShowHints] = useState(false);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [hearts, setHearts] = useState(5);
  const [serviceHealthy, setServiceHealthy] = useState(false);
  // Demo mode removed - all questions load from MongoDB only
  const [widgetFilter, setWidgetFilter] = useState<string>('all');

  // Brilliant state machine
  const [attemptState, setAttemptState] = useState<AttemptState>('idle');
  const [scoringResult, setScoringResult] = useState<{ message?: string; details?: any[] } | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // UI state
  const [darkMode, setDarkMode] = useState(false);
  const [quizMode, setQuizMode] = useState<QuizMode>('test');
  const [questionResults, setQuestionResults] = useState<Record<number, { correct: boolean; skipped: boolean; bookmarked: boolean }>>({});
  const [bookmarkedQuestions, setBookmarkedQuestions] = useState<Set<number>>(new Set());
  const [skippedQuestions, setSkippedQuestions] = useState<Set<number>>(new Set());
  const [showSummary, setShowSummary] = useState(false);
  const [startTime] = useState(Date.now());
  const [rendererKey, setRendererKey] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  const [isJsonExpanded, setIsJsonExpanded] = useState(false);


  // Get URL parameters
  const { questionId } = useParams<{ questionId?: string }>();

  const cardRef = useRef<HTMLDivElement>(null);

  // Debug UI toggle
  const showDebugUI = import.meta.env.DEV || window.location.search.includes('debug=true');

  const widgetTypeOptions = [
    'all', 'numeric-input', 'radio', 'dropdown', 'expression', 'input-number',
    'sorter', 'orderer', 'matcher', 'categorizer', 'interactive-graph',
    'grapher', 'plotter', 'image', 'passage', 'table', 'matrix', 'label-image', 'free-response',
  ];

  const activeQuestions = questions;
  const currentQuestion = activeQuestions[currentIndex];
  const hasCalculator = !!(currentQuestion?.answerArea as { calculator?: boolean })?.calculator;

  // Determine if user has answered
  const hasAnswers = Object.keys(answers).length > 0 &&
    Object.values(answers).some(v => v !== undefined && v !== null && v !== '');

  const isCorrect = attemptState === 'checked_correct';
  const isSubmitted = attemptState !== 'idle';
  const isShowingAnswer = attemptState === 'showing_answer';

  const hasGradedGroup = useMemo(() => {
    if (!currentQuestion) return false;
    const widgets = (currentQuestion.perseusItem?.question?.widgets) ||
      ((currentQuestion.question as any)?.widgets) || {};
    return Object.values(widgets).some((w: any) => w.type === 'graded-group');
  }, [currentQuestion]);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768 || (currentQuestion?._id === '6932cb575853fec4a5597201'));
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [currentQuestion]);

  // Load saved progress
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const progress: QuizProgress = JSON.parse(saved);
        setQuestionResults(progress.questionResults);
        setHearts(progress.hearts);
      } catch (e) {
        console.warn('Failed to restore quiz progress:', e);
      }
    }
  }, []);

  // Save progress
  useEffect(() => {
    const progress: QuizProgress = {
      questionResults,
      currentIndex,
      hearts,
      startTime,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  }, [questionResults, currentIndex, hearts, startTime]);

  useEffect(() => { checkHealth().then(setServiceHealthy); }, []);

  // Load initial question(s)
  useEffect(() => {
    if (questionId) {
      loadQuestionById(questionId);
    } else {
      loadQuestions();
    }
  }, [questionId]);

  // Automatically switch to Perseus view for unsupported widgets
  useEffect(() => {
    // Only force switch for specific broken IDs if needed
    if (hasGradedGroup && viewMode !== 'perseus') {
      setViewMode('perseus');
    }
  }, [hasGradedGroup, currentQuestion, viewMode]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't handle if typing in input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      // Number keys 1-4 to select options (handled by Athena widgets)
      // Enter to submit or continue
      if (e.key === 'Enter') {
        if (attemptState === 'idle' && hasAnswers) {
          handleSubmit();
        } else if (attemptState !== 'idle') {
          handleContinue();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [attemptState, hasAnswers]);

  // ============================================================================
  // HANDLERS
  // ============================================================================

  const loadQuestions = async (filter?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const filterToUse = filter ?? widgetFilter;
      const widgetTypes = filterToUse !== 'all' ? [filterToUse] : undefined;
      const data = await fetchQuestions(50, widgetTypes);
      if (data.length > 0) {
        setQuestions(data);
        setCurrentIndex(0);
        resetState();
      } else {
        setError(filterToUse !== 'all' ? `No questions found with widget type: ${filterToUse}` : 'No questions available');
      }
    } catch (err) {
      setError('Failed to load questions');
    } finally {
      setIsLoading(false);
    }
  };

  const loadQuestionById = async (id?: string) => {
    const targetId = id || objectIdInput.trim();
    if (!targetId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchQuestionById(targetId);
      if (data) {
        setQuestions([data]);
        setCurrentIndex(0);
        resetState();
      } else {
        setError(`Question not found: ${targetId}`);
      }
    } catch {
      setError('Failed to load question');
    } finally {
      setIsLoading(false);
    }
  };

  const resetState = () => {
    setAttemptState('idle');
    setScoringResult(null);
    setShowHints(false);
    setCurrentHintIndex(0);
    setAnswers({});
    setRendererKey(k => k + 1);
    setIsTransitioning(false);
  };

  const handleSubmit = () => {
    if (!currentQuestion || !hasAnswers) return;

    const result = scoringEngine.scoreItem(
      {
        question: currentQuestion.question as any,
        hints: currentQuestion.hints as any,
        answerArea: currentQuestion.answerArea,
      },
      answers
    );

    const correct = result.correct;
    setAttemptState(correct ? 'checked_correct' : 'checked_incorrect');
    setScoringResult({ message: result.message, details: result.details });

    // Play sound
    playSound(correct ? 'correct' : 'wrong');

    // Record result
    setQuestionResults(prev => ({
      ...prev,
      [currentIndex]: { correct, skipped: false, bookmarked: bookmarkedQuestions.has(currentIndex) }
    }));

    // Deduct heart if wrong in test mode
    if (!correct && quizMode === 'test') {
      setHearts(h => Math.max(0, h - 1));
    }
  };

  const handleTryAgain = () => {
    // Reset to allow another attempt
    setAttemptState('idle');
    setAnswers({});
    setRendererKey(k => k + 1); // Force re-mount to clear selection
  };

  const handleSeeAnswer = () => {
    // Show the correct answer
    setAttemptState('showing_answer');
    // Record as incorrect since they gave up
    setQuestionResults(prev => ({
      ...prev,
      [currentIndex]: { correct: false, skipped: false, bookmarked: bookmarkedQuestions.has(currentIndex) }
    }));
  };

  const handleWhyExplanation = () => {
    // Show hints/explanation
    setShowHints(true);
  };

  const handleSkipExplanation = () => {
    // Move to next question without viewing explanation
    handleContinue();
  };

  const handleNextQuestion = () => {
    // Skip to next question (user chose to move on without seeing answer)
    setQuestionResults(prev => ({
      ...prev,
      [currentIndex]: { correct: false, skipped: false, bookmarked: bookmarkedQuestions.has(currentIndex) }
    }));
    handleContinue();
  };

  const handleContinue = () => {
    // Animate card out
    setIsTransitioning(true);

    setTimeout(() => {
      if (currentIndex < activeQuestions.length - 1) {
        setCurrentIndex(currentIndex + 1);
        resetState();
      } else {
        setShowSummary(true);
        setIsTransitioning(false);
      }
    }, 150);
  };

  const handleSkip = () => {
    setSkippedQuestions(prev => new Set(prev).add(currentIndex));
    setQuestionResults(prev => ({
      ...prev,
      [currentIndex]: { correct: false, skipped: true, bookmarked: bookmarkedQuestions.has(currentIndex) }
    }));
    handleContinue();
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setIsTransitioning(true);
      setTimeout(() => {
        setCurrentIndex(currentIndex - 1);
        resetState();
      }, 150);
    }
  };

  const handleJumpToQuestion = (index: number) => {
    setCurrentIndex(index);
    resetState();
  };

  const toggleBookmark = () => {
    setBookmarkedQuestions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(currentIndex)) {
        newSet.delete(currentIndex);
      } else {
        newSet.add(currentIndex);
      }
      return newSet;
    });
  };

  // toggleDemoMode removed - all questions load from MongoDB only

  const toggleQuizMode = () => {
    setQuizMode(quizMode === 'test' ? 'practice' : 'test');
    setHearts(quizMode === 'test' ? 999 : 5);
  };

  const restartQuiz = () => {
    setCurrentIndex(0);
    setQuestionResults({});
    setBookmarkedQuestions(new Set());
    setSkippedQuestions(new Set());
    setHearts(quizMode === 'test' ? 5 : 999);
    setShowSummary(false);
    resetState();
    localStorage.removeItem(STORAGE_KEY);
  };

  const handleAnswerChange = useCallback((widgetId: string, value: unknown) => {
    setAnswers(prev => ({ ...prev, [widgetId]: value }));
  }, []);

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className={`min-h-screen flex flex-col transition-colors duration-300 ${darkMode ? 'bg-black athena-theme-dark' : 'bg-[var(--brilliant-bg-page)]'}`}>
      {/* Modals */}
      <CalculatorModal isOpen={showCalculator} onClose={() => setShowCalculator(false)} darkMode={darkMode} />
      <PerformanceSummary
        isOpen={showSummary}
        onClose={() => setShowSummary(false)}
        onRestart={restartQuiz}
        results={questionResults}
        totalQuestions={activeQuestions.length}
        darkMode={darkMode}
        timeSpent={Date.now() - startTime}
      />


      {/* Sticky Progress Header */}
      <ProgressHeader
        current={currentIndex}
        total={activeQuestions.length}
        hearts={hearts}
        quizMode={quizMode}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
        onToggleQuizMode={toggleQuizMode}
        hasCalculator={hasCalculator}
        bookmarkCount={bookmarkedQuestions.size}
      />

      {/* Debug Controls */}
      {showDebugUI && (
        <div className={`border-b ${darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white/80'}`}>
          <div className="max-w-5xl mx-auto px-4 py-3">
            <div className="flex flex-wrap items-center gap-3">
              {/* Search */}
              <div className="flex-1 min-w-[200px] max-w-md flex gap-2">
                <div className="flex-1 relative">
                  <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`} />
                  <input
                    type="text"
                    placeholder="MongoDB ObjectID..."
                    value={objectIdInput}
                    onChange={(e) => setObjectIdInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && loadQuestionById()}
                    className={`w-full pl-9 pr-3 py-2 rounded-xl text-sm font-medium border-2 transition-colors focus:outline-none ${darkMode
                      ? 'bg-gray-700 border-gray-600 text-white focus:border-blue-500'
                      : 'bg-white border-gray-200 text-gray-700 focus:border-[var(--brilliant-selected-border)]'
                      }`}
                  />
                </div>
                <button onClick={() => loadQuestionById()} className="px-4 py-2 bg-[var(--brilliant-selected-border)] text-white font-bold rounded-xl text-sm hover:opacity-90 transition-opacity">
                  Load
                </button>
                <button onClick={() => loadQuestions()} className={`p-2 rounded-xl transition-colors ${darkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-600'}`}>
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

              {/* Filters */}
              <select
                value={widgetFilter}
                onChange={(e) => { setWidgetFilter(e.target.value); loadQuestions(e.target.value); }}
                className={`px-3 py-2 rounded-xl text-sm font-medium border-2 cursor-pointer focus:outline-none ${darkMode
                  ? 'bg-gray-700 border-gray-600 text-white'
                  : 'bg-white border-gray-200 text-gray-700'
                  }`}
              >
                {widgetTypeOptions.map((type) => (
                  <option key={type} value={type}>{type === 'all' ? '🎯 All Widgets' : type}</option>
                ))}
              </select>


              {/* View mode toggles */}
              <div className="flex gap-1">
                {(['athena', 'perseus', 'comparison'] as ViewMode[]).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    className={`px-3 py-2 rounded-xl text-sm font-bold transition-all ${viewMode === mode
                      ? mode === 'athena' ? 'bg-[var(--brilliant-accent)] text-white' : mode === 'perseus' ? 'bg-orange-500 text-white' : 'bg-purple-500 text-white'
                      : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                      }`}
                  >
                    {mode === 'athena' ? 'Athena' : mode === 'perseus' ? 'Perseus' : 'Compare'}
                  </button>
                ))}
                {/* Input Window button */}
                <button
                  onClick={() => {
                    const jsonData = JSON.stringify({
                      question: currentQuestion?.question,
                      hints: currentQuestion?.hints || [],
                      answerArea: currentQuestion?.answerArea || {},
                      itemDataVersion: { major: 0, minor: 1 }
                    }, null, 2);
                    navigator.clipboard.writeText(jsonData).then(() => {
                      window.open('https://khan.github.io/perseus/?path=/story/renderers-server-item-renderer--interactive', '_blank');
                      alert('JSON copied to clipboard! Paste it in the "Dump Perseus data here" box.');
                    });
                  }}
                  className={`px-3 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-1 ${darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  title="Copy JSON & Open Perseus Interactive Viewer"
                >
                  <ExternalLink className="w-4 h-4" />
                  Input Window
                </button>
              </div>
            </div>
          </div>

          {/* Service warning */}
          {!serviceHealthy && (
            <div className="px-4 py-2 bg-amber-50 dark:bg-amber-900/30 border-t border-amber-200 dark:border-amber-800">
              <p className="text-center text-amber-700 dark:text-amber-300 font-medium text-sm">
                Backend not running. Start: <code className="bg-amber-100 dark:bg-amber-800 px-2 py-0.5 rounded text-xs">cd services/athenaAPI && python run_backend.py</code>
              </p>
            </div>
          )}
        </div>
      )}

      {/* Skipped questions navigation */}
      {skippedQuestions.size > 0 && (
        <div className={`px-4 py-2 border-b ${darkMode ? 'border-gray-700 bg-gray-800/50' : 'border-gray-200 bg-gray-50'}`}>
          <div className="max-w-3xl mx-auto flex items-center gap-2 overflow-x-auto">
            <span className={`brilliant-label whitespace-nowrap ${darkMode ? 'text-gray-400' : ''}`}>Jump to:</span>
            {Array.from(skippedQuestions).map((idx) => (
              <button
                key={idx}
                onClick={() => handleJumpToQuestion(idx)}
                className={`px-3 py-1 rounded-lg brilliant-label transition-colors ${idx === currentIndex
                  ? 'bg-[var(--brilliant-selected-border)] text-white'
                  : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                  }`}
              >
                Q{idx + 1}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className={`flex-1 flex flex-col items-center justify-start px-4 py-8 md:py-12 ${attemptState !== 'idle' ? 'pb-24' : ''}`}>
        {isLoading ? (
          <div className="flex flex-col items-center gap-4 py-20">
            <div className="w-10 h-10 border-4 border-[var(--brilliant-accent)] border-t-transparent rounded-full animate-spin" />
            <p className={`brilliant-option-text ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Loading questions...</p>
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <div className="text-6xl mb-4">😢</div>
            <p className="brilliant-question-stem text-red-500 mb-4">{error}</p>
            <div className="flex gap-3 justify-center">
              <button onClick={() => loadQuestions()} className="px-6 py-3 bg-[var(--brilliant-accent)] text-white brilliant-btn-text rounded-2xl shadow-[0_4px_0_var(--brilliant-accent-dark)] active:translate-y-[2px] active:shadow-none">Try Again</button>
            </div>
          </div>
        ) : currentQuestion ? (
          <div className={`w-full ${viewMode === 'comparison' ? 'max-w-[1400px]' : 'max-w-[720px]'}`}>
            {/* Tools Row */}
            <div className="flex justify-between items-center mb-4">
              {hasCalculator ? (
                <button
                  onClick={() => setShowCalculator(true)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl brilliant-btn-text transition-colors ${darkMode ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                    }`}
                >
                  <Calculator className="w-4 h-4" />
                  Calculator
                </button>
              ) : (
                <div />
              )}

              <button
                onClick={toggleBookmark}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl brilliant-btn-text transition-colors ${bookmarkedQuestions.has(currentIndex)
                  ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300'
                  : darkMode ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                  }`}
              >
                {bookmarkedQuestions.has(currentIndex) ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
                {bookmarkedQuestions.has(currentIndex) ? 'Saved' : 'Save'}
              </button>
            </div>

            {/* Question Card - Brilliant Style */}
            <div
              ref={cardRef}
              className={`rounded-3xl shadow-[0_12px_40px_rgba(0,0,0,0.12)] transition-all duration-200 ${isTransitioning ? 'opacity-0 translate-x-[-8px]' : 'opacity-100 translate-x-0 animate-cardIn'
                } ${darkMode ? 'bg-gray-800' : 'bg-[var(--brilliant-bg-card)]'}`}
            >
              <div className="px-6 py-6 md:px-8 md:py-8">
                {/* Athena Renderer */}
                {viewMode === 'athena' && (
                  <RendererErrorBoundary
                    key={`athena-${currentQuestion._id}-${rendererKey}`}
                    name="Athena"
                    onRetry={() => setRendererKey(k => k + 1)}
                  >
                    <AthenaRenderer
                      item={{
                        question: currentQuestion.question as any,
                        hints: currentQuestion.hints as any,
                        answerArea: currentQuestion.answerArea,
                      }}
                      onAnswerChange={handleAnswerChange}
                      readOnly={isSubmitted}
                      reviewMode={isSubmitted}
                      theme={darkMode ? 'dark' : 'light'}
                      viewMode={viewMode}
                    />
                  </RendererErrorBoundary>
                )}

                {/* Perseus Renderer */}
                {viewMode === 'perseus' && (
                  <div className="framework-perseus">
                    <RendererErrorBoundary
                      key={`perseus-${currentQuestion._id}-${rendererKey}`}
                      name="Perseus"
                      onRetry={() => setRendererKey(k => k + 1)}
                    >
                      <PerseusI18nContextProvider locale="en" strings={mockStrings}>
                        <RenderStateRoot>
                          <ServerItemRenderer
                            problemNum={0}
                            item={(currentQuestion.perseusItem && currentQuestion.perseusItem.question) ? currentQuestion.perseusItem : {
                              question: currentQuestion.question as any,
                              hints: currentQuestion.hints as any,
                              answerArea: currentQuestion.answerArea as any,
                              itemDataVersion: { major: 2, minor: 0 }
                            }}
                            dependencies={storybookDependenciesV2}
                            apiOptions={{
                              isMobile,
                              customKeypad: isMobile,
                            }}
                            linterContext={{ contentType: "", highlightLint: false, paths: [], stack: [] }}
                            showSolutions="none"
                            hintsVisible={0}
                            reviewMode={isSubmitted}
                          />
                        </RenderStateRoot>
                      </PerseusI18nContextProvider>
                    </RendererErrorBoundary>
                  </div>
                )}

                {/* Comparison Mode - Responsive side by side */}
                {viewMode === 'comparison' && (
                  <div className="comparison-container">
                    {/* Athena Panel */}
                    <div className={`comparison-panel comparison-panel-athena ${darkMode ? 'bg-gray-700' : ''}`}>
                      <div className="sticky top-0 z-10 mb-4 pb-2 border-b border-[var(--brilliant-accent)]/30" style={{ background: 'inherit' }}>
                        <h3 className="text-center font-bold text-[var(--brilliant-accent)] text-sm flex items-center justify-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-[var(--brilliant-accent)]"></span>
                          Athena (New)
                        </h3>
                      </div>
                      <RendererErrorBoundary key={`athena-cmp-${currentQuestion._id}-${rendererKey}`} name="Athena" onRetry={() => setRendererKey(k => k + 1)}>
                        <AthenaRenderer
                          item={{ question: currentQuestion.question as any, hints: currentQuestion.hints as any, answerArea: currentQuestion.answerArea }}
                          onAnswerChange={handleAnswerChange}
                          readOnly={isSubmitted}
                          reviewMode={isSubmitted}
                          theme={darkMode ? 'dark' : 'light'}
                          viewMode="comparison"
                        />
                      </RendererErrorBoundary>
                    </div>
                    {/* Perseus Panel */}
                    <div className={`comparison-panel comparison-panel-perseus framework-perseus ${darkMode ? 'bg-gray-700' : ''}`}>
                      <div className="sticky top-0 z-10 mb-4 pb-2 border-b border-orange-500/30" style={{ background: 'inherit' }}>
                        <h3 className="text-center font-bold text-orange-500 text-sm flex items-center justify-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                          Perseus (Original)
                        </h3>
                      </div>
                      <RendererErrorBoundary key={`perseus-cmp-${currentQuestion._id}-${rendererKey}`} name="Perseus" onRetry={() => setRendererKey(k => k + 1)}>
                        <PerseusI18nContextProvider locale="en" strings={mockStrings}>
                          <RenderStateRoot>
                            <ServerItemRenderer
                              problemNum={0}
                              item={(currentQuestion.perseusItem && currentQuestion.perseusItem.question) ? currentQuestion.perseusItem : {
                                question: currentQuestion.question as any,
                                hints: currentQuestion.hints as any,
                                answerArea: currentQuestion.answerArea as any,
                                itemDataVersion: { major: 2, minor: 0 }
                              }}
                              dependencies={storybookDependenciesV2}
                              apiOptions={{
                                isMobile,
                                customKeypad: isMobile,
                              }}
                              linterContext={{ contentType: "", highlightLint: false, paths: [], stack: [] }}
                              showSolutions="none"
                              hintsVisible={0}
                              reviewMode={isSubmitted}
                            />
                          </RenderStateRoot>
                        </PerseusI18nContextProvider>
                      </RendererErrorBoundary>
                    </div>
                  </div>
                )}

                {/* Hint Panel - shown when "Why?" is clicked */}

                {showHints && currentQuestion.hints?.length > 0 && (
                  <HintPanel
                    hints={currentQuestion.hints}
                    currentIndex={currentHintIndex}
                    onNextHint={() => setCurrentHintIndex(i => i + 1)}
                    darkMode={darkMode}
                    questionId={currentQuestion._id}
                    viewMode={viewMode}
                    widgets={currentQuestion.question?.widgets}
                  />
                )}

                {/* Bottom Controls */}
                {!isSubmitted && (
                  <div className="mt-6 flex items-center justify-between gap-3 flex-wrap">
                    {/* Left: Hint button */}
                    <div>
                      {currentQuestion.hints?.length > 0 && !showHints && (
                        <button
                          onClick={() => setShowHints(true)}
                          className={`brilliant-btn-text underline-offset-2 hover:underline ${darkMode ? 'text-blue-400' : 'text-[var(--brilliant-hint-text)]'
                            }`}
                        >
                          Need a hint?
                        </button>
                      )}
                    </div>

                    {/* Right: Skip + Check */}
                    <div className="flex items-center gap-3">
                      <button
                        onClick={handleSkip}
                        className={`px-5 py-2.5 rounded-2xl brilliant-btn-text transition-all ${darkMode
                          ? 'text-gray-400 border-2 border-gray-600 hover:bg-gray-700'
                          : 'text-gray-500 border-2 border-gray-200 hover:bg-gray-50'
                          }`}
                      >
                        Skip
                      </button>

                      <button
                        onClick={handleSubmit}
                        disabled={!hasAnswers}
                        className={`inline-flex items-center justify-center rounded-2xl px-6 py-2.5 md:px-7 md:py-3 brilliant-btn-text transition-all brilliant-btn-3d ${hasAnswers
                          ? 'bg-[var(--brilliant-accent)] text-white shadow-[0_4px_0_var(--brilliant-accent-dark)] border-b-4 border-[var(--brilliant-accent-dark)] active:border-b-0 active:shadow-none'
                          : 'bg-[var(--brilliant-accent-disabled)] text-white/80 border-b-4 border-[var(--brilliant-accent-disabled-border)] cursor-not-allowed'
                          }`}
                      >
                        Check
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Debug: Question ID and Collapsible JSON */}
            {/* Debug UI Removed as per user request */}
            {currentQuestion && (
              <div className={`mt-4 border rounded z-50 relative ${darkMode
                ? 'bg-black border-gray-700'
                : 'bg-yellow-100 border-yellow-300'
                }`}>
                {/* ID Row */}
                <div className="text-center p-2 select-all cursor-text">
                  <span className={`font-bold mr-2 ${darkMode ? 'text-white' : 'text-gray-700'}`}>ID:</span>
                  <span className={`font-mono text-lg font-bold select-all ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>{currentQuestion._id}</span>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </main>

      {/* Brilliant-Style Feedback Banner - Fixed at bottom */}
      <FeedbackBanner
        attemptState={attemptState}
        onTryAgain={handleTryAgain}
        onSeeAnswer={handleSeeAnswer}
        onNextQuestion={handleNextQuestion}
        onWhyExplanation={handleWhyExplanation}
        onSkipExplanation={handleSkipExplanation}
        onContinue={handleContinue}
        onGetHint={() => setShowHints(true)}
        hasHints={!!(currentQuestion?.hints?.length)}
        darkMode={darkMode}
      />

      {/* Footer Navigation - Hidden when feedback banner is shown */}
      <footer className={`py-3 px-4 border-t ${darkMode ? 'border-gray-800 bg-black' : 'border-gray-200 bg-white'} ${attemptState !== 'idle' ? 'hidden' : ''}`}>
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevious}
              disabled={currentIndex === 0}
              className={`p-2 rounded-full transition-colors disabled:opacity-30 ${darkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-500'
                }`}
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className={`brilliant-progress-text ${darkMode ? 'text-gray-400' : ''}`}>
              {currentIndex + 1} / {activeQuestions.length}
            </span>
            <button
              onClick={handleContinue}
              disabled={currentIndex === activeQuestions.length - 1 && attemptState === 'idle'}
              className={`p-2 rounded-full transition-colors disabled:opacity-30 ${darkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-500'
                }`}
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          <button
            onClick={() => setShowSummary(true)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-full brilliant-btn-text transition-colors ${darkMode
              ? 'text-purple-400 bg-purple-900/30 hover:bg-purple-900/50'
              : 'text-purple-600 bg-purple-50 hover:bg-purple-100'
              }`}
          >
            <Trophy className="w-4 h-4" />
            Results
          </button>
        </div>
      </footer>
    </div>
  );
};

export default QuestionPane;
