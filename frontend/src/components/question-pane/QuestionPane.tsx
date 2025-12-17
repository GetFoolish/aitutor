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
} from 'lucide-react';

import { AthenaRenderer, registerDefaultWidgets, ScoringEngine } from '../../renderer/athena';
import '../../renderer/athena/athena.css';
import type { AthenaItem } from '../../services/sherlockedAPI_New';

// Initialize scoring engine
const scoringEngine = new ScoringEngine();
import { DEMO_WIDGETS } from './demoWidgets';
import {
  fetchQuestionById,
  fetchQuestions,
  checkHealth,
} from '../../services/sherlockedAPI_New';

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
        <div className={`${darkMode ? 'bg-gray-900' : 'bg-gray-100'} rounded-xl p-4 mb-4 text-right`}>
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
          {['7','8','9','÷','4','5','6','×','1','2','3','-','0','.','=','+'].map((btn) => (
            <button
              key={btn}
              onClick={() => {
                if (['÷','×','-','+'].includes(btn)) handleOperator(btn);
                else if (btn === '=') handleEquals();
                else handleNumber(btn);
              }}
              className={`p-3 text-lg font-bold rounded-xl transition-all ${
                btn === '=' ? 'bg-[var(--brilliant-accent)] text-white' : btnClass
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
    <header className={`sticky top-0 z-20 w-full border-b border-black/5 ${darkMode ? 'bg-gray-900' : 'bg-[var(--brilliant-bg-page)]'}`}>
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
          className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
            quizMode === 'practice'
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
  darkMode: boolean;
}> = ({ attemptState, onTryAgain, onSeeAnswer, onNextQuestion, onWhyExplanation, onSkipExplanation, onContinue, darkMode }) => {
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

  // Incorrect answer - yellow/cream feedback with Try again + See answer + Next question
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
}> = ({ hints, currentIndex, onNextHint, darkMode }) => {
  if (!hints?.length) return null;

  return (
    <div className={`mt-4 rounded-2xl px-5 py-4 animate-fadeInUp ${darkMode ? 'bg-blue-900/30' : 'bg-[#F3F4FF]'}`}>
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className={`w-5 h-5 ${darkMode ? 'text-blue-400' : 'text-[#2F7BF6]'}`} />
        <span className={`brilliant-label ${darkMode ? 'text-blue-300' : 'text-[#2F7BF6]'}`}>
          Hint {currentIndex + 1} of {hints.length}
        </span>
      </div>
      <p className={`brilliant-option-text ${darkMode ? 'text-blue-200' : 'text-slate-700'}`}>
        {hints[currentIndex]?.content}
      </p>
      {currentIndex < hints.length - 1 && (
        <button
          onClick={onNextHint}
          className={`mt-3 brilliant-btn-text underline-offset-2 hover:underline ${darkMode ? 'text-blue-400' : 'text-[#2F7BF6]'}`}
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
  const [demoMode, setDemoMode] = useState(false);
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

  const cardRef = useRef<HTMLDivElement>(null);

  // Debug UI toggle
  const showDebugUI = import.meta.env.DEV || window.location.search.includes('debug=true');

  const widgetTypeOptions = [
    'all', 'numeric-input', 'radio', 'dropdown', 'expression', 'input-number',
    'sorter', 'orderer', 'matcher', 'categorizer', 'interactive-graph',
    'grapher', 'plotter', 'image', 'passage', 'table', 'matrix', 'label-image', 'free-response',
  ];

  const activeQuestions = demoMode ? DEMO_WIDGETS : questions;
  const currentQuestion = activeQuestions[currentIndex];
  const hasCalculator = !!(currentQuestion?.answerArea as { calculator?: boolean })?.calculator;

  // Determine if user has answered
  const hasAnswers = Object.keys(answers).length > 0 &&
    Object.values(answers).some(v => v !== undefined && v !== null && v !== '');

  const isCorrect = attemptState === 'checked_correct';
  const isSubmitted = attemptState !== 'idle';
  const isShowingAnswer = attemptState === 'showing_answer';

  // ============================================================================
  // EFFECTS
  // ============================================================================

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
  useEffect(() => { loadQuestions(); }, []);

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

  const loadQuestionById = async () => {
    if (!objectIdInput.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchQuestionById(objectIdInput.trim());
      if (data) {
        setQuestions([data]);
        setCurrentIndex(0);
        resetState();
      } else {
        setError(`Question not found: ${objectIdInput}`);
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

    console.log('[Scoring]', result);
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

  const toggleDemoMode = () => {
    setDemoMode(!demoMode);
    setCurrentIndex(0);
    resetState();
  };

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
    <div className={`min-h-screen flex flex-col transition-colors duration-300 ${darkMode ? 'bg-gray-900' : 'bg-[var(--brilliant-bg-page)]'}`}>
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
                    className={`w-full pl-9 pr-3 py-2 rounded-xl text-sm font-medium border-2 transition-colors focus:outline-none ${
                      darkMode
                        ? 'bg-gray-700 border-gray-600 text-white focus:border-blue-500'
                        : 'bg-white border-gray-200 text-gray-700 focus:border-[var(--brilliant-selected-border)]'
                    }`}
                  />
                </div>
                <button onClick={loadQuestionById} className="px-4 py-2 bg-[var(--brilliant-selected-border)] text-white font-bold rounded-xl text-sm hover:opacity-90 transition-opacity">
                  Load
                </button>
                <button onClick={() => loadQuestions()} className={`p-2 rounded-xl transition-colors ${darkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-600'}`}>
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

              {/* Filters */}
              <select
                value={widgetFilter}
                onChange={(e) => { setWidgetFilter(e.target.value); if (!demoMode) loadQuestions(e.target.value); }}
                className={`px-3 py-2 rounded-xl text-sm font-medium border-2 cursor-pointer focus:outline-none ${
                  darkMode
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'bg-white border-gray-200 text-gray-700'
                }`}
              >
                {widgetTypeOptions.map((type) => (
                  <option key={type} value={type}>{type === 'all' ? '🎯 All Widgets' : type}</option>
                ))}
              </select>

              <button onClick={toggleDemoMode} className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${demoMode ? 'bg-[var(--brilliant-selected-border)] text-white' : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}`}>
                {demoMode ? `📦 Demo (${activeQuestions.length})` : '📦 Demo'}
              </button>

              {/* View mode toggles */}
              <div className="flex gap-1">
                {(['athena', 'perseus', 'comparison'] as ViewMode[]).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    className={`px-3 py-2 rounded-xl text-sm font-bold transition-all ${
                      viewMode === mode
                        ? mode === 'athena' ? 'bg-[var(--brilliant-accent)] text-white' : mode === 'perseus' ? 'bg-orange-500 text-white' : 'bg-purple-500 text-white'
                        : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {mode === 'athena' ? 'Sherlocked' : mode === 'perseus' ? 'Perseus' : 'Compare'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Service warning */}
          {!serviceHealthy && (
            <div className="px-4 py-2 bg-amber-50 dark:bg-amber-900/30 border-t border-amber-200 dark:border-amber-800">
              <p className="text-center text-amber-700 dark:text-amber-300 font-medium text-sm">
                Backend not running. Start: <code className="bg-amber-100 dark:bg-amber-800 px-2 py-0.5 rounded text-xs">cd services/sherlockedAPI_New && python run_backend.py</code>
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
                className={`px-3 py-1 rounded-lg brilliant-label transition-colors ${
                  idx === currentIndex
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
        {isLoading && !demoMode ? (
          <div className="flex flex-col items-center gap-4 py-20">
            <div className="w-10 h-10 border-4 border-[var(--brilliant-accent)] border-t-transparent rounded-full animate-spin" />
            <p className={`brilliant-option-text ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Loading questions...</p>
          </div>
        ) : error && !demoMode ? (
          <div className="text-center py-20">
            <div className="text-6xl mb-4">😢</div>
            <p className="brilliant-question-stem text-red-500 mb-4">{error}</p>
            <div className="flex gap-3 justify-center">
              <button onClick={() => loadQuestions()} className="px-6 py-3 bg-[var(--brilliant-accent)] text-white brilliant-btn-text rounded-2xl shadow-[0_4px_0_var(--brilliant-accent-dark)] active:translate-y-[2px] active:shadow-none">Try Again</button>
              <button onClick={toggleDemoMode} className="px-6 py-3 bg-[var(--brilliant-selected-border)] text-white brilliant-btn-text rounded-2xl">Try Demo</button>
            </div>
          </div>
        ) : currentQuestion ? (
          <div className="w-full max-w-[720px]">
            {/* Tools Row */}
            <div className="flex justify-between items-center mb-4">
              {hasCalculator ? (
                <button
                  onClick={() => setShowCalculator(true)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl brilliant-btn-text transition-colors ${
                    darkMode ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
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
                className={`flex items-center gap-2 px-4 py-2 rounded-xl brilliant-btn-text transition-colors ${
                  bookmarkedQuestions.has(currentIndex)
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
              className={`rounded-3xl shadow-[0_12px_40px_rgba(0,0,0,0.12)] transition-all duration-200 ${
                isTransitioning ? 'opacity-0 translate-x-[-8px]' : 'opacity-100 translate-x-0 animate-cardIn'
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
                            item={{
                              question: currentQuestion.question as any,
                              hints: currentQuestion.hints as any,
                              answerArea: currentQuestion.answerArea as any,
                            }}
                            dependencies={storybookDependenciesV2}
                            apiOptions={{}}
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

                {/* Comparison Mode */}
                {viewMode === 'comparison' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className={`p-4 rounded-2xl border-2 border-[var(--brilliant-accent)] ${darkMode ? 'bg-gray-700' : 'bg-green-50/30'}`}>
                      <h3 className="text-center font-bold text-[var(--brilliant-accent)] mb-4 pb-2 border-b border-[var(--brilliant-accent)]/30 text-sm">Sherlocked</h3>
                      <RendererErrorBoundary key={`athena-cmp-${currentQuestion._id}-${rendererKey}`} name="Athena" onRetry={() => setRendererKey(k => k + 1)}>
                        <AthenaRenderer
                          item={{ question: currentQuestion.question as any, hints: currentQuestion.hints as any, answerArea: currentQuestion.answerArea }}
                          onAnswerChange={handleAnswerChange}
                          readOnly={isSubmitted}
                          reviewMode={isSubmitted}
                          theme={darkMode ? 'dark' : 'light'}
                        />
                      </RendererErrorBoundary>
                    </div>
                    <div className={`p-4 rounded-2xl border-2 border-orange-500 framework-perseus ${darkMode ? 'bg-gray-700' : 'bg-orange-50/30'}`}>
                      <h3 className="text-center font-bold text-orange-500 mb-4 pb-2 border-b border-orange-500/30 text-sm">Perseus</h3>
                      <RendererErrorBoundary key={`perseus-cmp-${currentQuestion._id}-${rendererKey}`} name="Perseus" onRetry={() => setRendererKey(k => k + 1)}>
                        <PerseusI18nContextProvider locale="en" strings={mockStrings}>
                          <RenderStateRoot>
                            <ServerItemRenderer
                              problemNum={0}
                              item={{ question: currentQuestion.question as any, hints: currentQuestion.hints as any, answerArea: currentQuestion.answerArea as any }}
                              dependencies={storybookDependenciesV2}
                              apiOptions={{}}
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

                {/* Hint Panel */}
                {showHints && currentQuestion.hints?.length > 0 && (
                  <HintPanel
                    hints={currentQuestion.hints}
                    currentIndex={currentHintIndex}
                    onNextHint={() => setCurrentHintIndex(i => i + 1)}
                    darkMode={darkMode}
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
                          className={`brilliant-btn-text underline-offset-2 hover:underline ${
                            darkMode ? 'text-blue-400' : 'text-[var(--brilliant-hint-text)]'
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
                        className={`px-5 py-2.5 rounded-2xl brilliant-btn-text transition-all ${
                          darkMode
                            ? 'text-gray-400 border-2 border-gray-600 hover:bg-gray-700'
                            : 'text-gray-500 border-2 border-gray-200 hover:bg-gray-50'
                        }`}
                      >
                        Skip
                      </button>

                      <button
                        onClick={handleSubmit}
                        disabled={!hasAnswers}
                        className={`inline-flex items-center justify-center rounded-2xl px-6 py-2.5 md:px-7 md:py-3 brilliant-btn-text transition-all brilliant-btn-3d ${
                          hasAnswers
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

            {/* Debug: Question ID */}
            {showDebugUI && currentQuestion && (
              <div className={`mt-4 text-center text-xs font-mono ${darkMode ? 'text-gray-600' : 'text-gray-400'}`}>
                {currentQuestion._id}
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
        darkMode={darkMode}
      />

      {/* Footer Navigation - Hidden when feedback banner is shown */}
      <footer className={`py-3 px-4 border-t ${darkMode ? 'border-gray-800 bg-gray-900' : 'border-gray-200 bg-white'} ${attemptState !== 'idle' ? 'hidden' : ''}`}>
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevious}
              disabled={currentIndex === 0}
              className={`p-2 rounded-full transition-colors disabled:opacity-30 ${
                darkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-500'
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
              className={`p-2 rounded-full transition-colors disabled:opacity-30 ${
                darkMode ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-500'
              }`}
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          <button
            onClick={() => setShowSummary(true)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-full brilliant-btn-text transition-colors ${
              darkMode
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
