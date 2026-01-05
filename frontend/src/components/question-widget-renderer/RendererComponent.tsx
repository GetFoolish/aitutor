import React, { useEffect, useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { ServerItemRenderer } from "../../package/perseus/src/server-item-renderer";
import type { PerseusItem } from "@khanacademy/perseus-core";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { scorePerseusItem } from "@khanacademy/perseus-score";
import { keScoreFromPerseusScore } from "../../package/perseus/src/util/scoring";
import { RenderStateRoot } from "@khanacademy/wonder-blocks-core";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";
import { KEScore } from "@khanacademy/perseus-core";
import { toast } from "sonner";
import { CheckCircle2, XCircle, Sparkles, ChevronRight, Lightbulb, BookOpen, PenLine, CheckCheck } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useHint } from "../../contexts/HintContext";
import { apiUtils } from "../../lib/api-utils";
import { jwtUtils } from "../../lib/jwt-utils";
import HintDisplay from "../hint-display/HintDisplay";
import HintButton from "../hint-button/HintButton";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

interface RendererComponentProps {
    onSkillChange?: (skill: string) => void;
    onQuestionChange?: (questionId: string | null) => void;
    watchedVideoIds?: string[];
    onAnswerSubmitted?: () => void;
    // Assessment mode props
    assessmentMode?: boolean;
    assessmentQuestions?: any[];
    onAssessmentAnswer?: (questionId: string, isCorrect: boolean) => void;
    currentQuestionIndex?: number;
}

const RendererComponent = ({ 
    onSkillChange, 
    onQuestionChange,
    watchedVideoIds = [],
    onAnswerSubmitted,
    assessmentMode = false,
    assessmentQuestions = [],
    onAssessmentAnswer,
    currentQuestionIndex = 0
}: RendererComponentProps) => {
    const { user } = useAuth();
    const { setTotalHints, setCurrentHintIndex, showHints, setShowHints } = useHint();
    const queryClient = useQueryClient();
    const [perseusItems, setPerseusItems] = useState<PerseusItem[]>([]);
    const [item, setItem] = useState(0);
    const [endOfTest, setEndOfTest] = useState(false);
    const [score, setScore] = useState<KEScore>();
    const [isAnswered, setIsAnswered] = useState(false);
    const [startTime, setStartTime] = useState<number>(Date.now());
    const [showFeedback, setShowFeedback] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [isError, setIsError] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [isLoadingNextBatch, setIsLoadingNextBatch] = useState(false);
    const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1); // 1=Understand, 2=Plan, 3=Solve, 4=Check
    const [showRecap, setShowRecap] = useState(false);
    const rendererRef = useRef<ServerItemRenderer>(null);
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    // Step tracker steps
    const steps = [
        { id: 1, label: 'Understand', icon: BookOpen },
        { id: 2, label: 'Plan', icon: Lightbulb },
        { id: 3, label: 'Solve', icon: PenLine },
        { id: 4, label: 'Check', icon: CheckCheck },
    ];

    // Generate teacher intro based on question context
    const getTeacherIntro = () => {
        if (perseusItems.length === 0 || isLoading) return null;
        const currentItem = perseusItems[item];
        const metadata = (currentItem as any).dash_metadata || {};
        const exerciseName = metadata.exercise_name || '';
        const skillNames = metadata.skill_names || [];

        // Generate contextual intro based on skill/exercise
        if (exerciseName.toLowerCase().includes('ratio')) {
            return "Let's explore how ratios help us compare quantities...";
        } else if (exerciseName.toLowerCase().includes('fraction')) {
            return "Time to work with fractions — they're like puzzle pieces of a whole!";
        } else if (exerciseName.toLowerCase().includes('percent')) {
            return "Percentages are everywhere — let's see how to work with them!";
        } else if (skillNames.some((s: string) => s.toLowerCase().includes('equation'))) {
            return "Equations are like balanced scales — let's find what makes them equal!";
        } else if (skillNames.some((s: string) => s.toLowerCase().includes('geometry'))) {
            return "Let's put on our geometry glasses and explore shapes!";
        }
        return "Let's work through this together, step by step!";
    };

    // Get user_id from auth context
    const user_id = user?.user_id || 'mongodb_test_user';

    // Fetch questions using apiUtils with JWT authentication
    useEffect(() => {
        // In assessment mode, use provided questions instead of fetching
        if (assessmentMode) {
            setPerseusItems(assessmentQuestions);
            setItem(currentQuestionIndex);
            setIsLoading(false);
            setIsAnswered(false);
            setShowFeedback(false);
            setStartTime(Date.now());
            return;
        }

        const fetchQuestions = async () => {
            if (!jwtUtils.getToken()) {
                setIsLoading(false);
                return;
            }

            setIsLoading(true);
            setIsError(false);
            setError(null);

            // Retry logic for connection errors with exponential backoff
            const maxRetries = 3;
            let retryCount = 0;
            
            const attemptFetch = async (): Promise<void> => {
                try {
                    // First, check for pre-loaded questions
                    const preloadedResponse = await apiUtils.get(`${DASH_API_URL}/api/questions/preloaded`);
                    if (preloadedResponse.ok) {
                        const preloadedData = await preloadedResponse.json();
                        if (preloadedData && preloadedData.length > 0) {
                            setPerseusItems(preloadedData);
                            setItem(0);
                            setEndOfTest(false);
                            setIsAnswered(false);
                            setStartTime(Date.now());
                            setIsLoading(false);
                            return; // Use pre-loaded questions
                        }
                    } else if (preloadedResponse.status === 422) {
                        // 422 means validation error, but we can still try fallback
                        console.warn('Pre-loaded questions endpoint returned 422, using fallback');
                    }
                    
                    // Fallback: Load initial 5 questions
                    const response = await apiUtils.get(`${DASH_API_URL}/api/questions/5`);
                    
                    if (!response.ok) {
                        // Don't retry on HTTP error codes (401, 403, 404, 500, etc.)
                        throw new Error(`Failed to fetch questions: ${response.status}`);
                    }

                    const data = await response.json();
                    setPerseusItems(data);
                    setItem(0);
                    setEndOfTest(false);
                    setIsAnswered(false);
                    setStartTime(Date.now());
                } catch (err) {
                    // Check if it's a network/connection error that we should retry
                    const isNetworkError = err instanceof TypeError && 
                        (err.message.includes('Failed to fetch') || 
                         err.message.includes('NetworkError') ||
                         err.message.includes('ERR_CONNECTION_REFUSED'));
                    
                    if (isNetworkError && retryCount < maxRetries) {
                        retryCount++;
                        const backoffDelay = Math.pow(2, retryCount) * 1000; // Exponential backoff: 2s, 4s, 8s
                        console.log(`Retrying fetch (attempt ${retryCount}/${maxRetries}) after ${backoffDelay}ms...`);
                        await new Promise(resolve => setTimeout(resolve, backoffDelay));
                        return attemptFetch(); // Retry
                    }
                    
                    // Not a retryable error or max retries reached
                    throw err;
                }
            };

            try {
                await attemptFetch();
            } catch (err) {
                console.error('Error fetching questions:', err);
                setIsError(true);
                setError(err instanceof Error ? err : new Error('Unknown error'));
            } finally {
                setIsLoading(false);
            }
        };

        fetchQuestions();
    }, [user_id, assessmentMode, assessmentQuestions, currentQuestionIndex]);

    // Fetch questions using apiUtils with JWT authentication
    useEffect(() => {
        if (isError) {
            const message = error?.message || "Unknown error fetching questions";
            toast.error("Unable to load questions", {
                description: message,
            });
        }
    }, [isError, error]);

    // Log when question is displayed (once per item change) and emit question ID
    useEffect(() => {
        if (perseusItems.length > 0 && !isLoading) {
            const currentItem = perseusItems[item];
            const metadata = (currentItem as any).dash_metadata || {};
            const dashQuestionId = metadata.dash_question_id || null;

            // Emit question ID change for LearningAssetsPanel
            onQuestionChange?.(dashQuestionId);

            // Log question displayed
            apiUtils.post(`${DASH_API_URL}/api/question-displayed`, {
                question_index: item,
                metadata: metadata
            }).catch((err) => {
                console.error('Failed to log question displayed:', err);
            });
        } else {
            // No question loaded, emit null
            onQuestionChange?.(null);
        }
    }, [item, perseusItems, isLoading, user_id, onQuestionChange]);

    // Update current module (unit_id) and URL when question changes
    useEffect(() => {
        if (onSkillChange && perseusItems.length > 0 && !isLoading) {
            const currentItem = perseusItems[item];
            const metadata = (currentItem as any).dash_metadata || {};
            // Extract unit_id from metadata - this is the "current module"
            const unitId = metadata.unit_id || null;
            const mongodbId = metadata.mongodb_id || null;
            
            console.log('[RendererComponent] Question metadata:', {
                question_id: metadata.dash_question_id,
                unit_id: unitId,
                lesson_id: metadata.lesson_id,
                exercise_id: metadata.exercise_id,
                skill_names: metadata.skill_names,
                mongodb_id: mongodbId
            });
            
            if (unitId) {
                onSkillChange(unitId);
            } else {
                console.warn('[RendererComponent] No unit_id found in metadata!');
            }
            
            // Update URL to /app/{mongodb_id}
            if (mongodbId && !assessmentMode) {
                window.history.replaceState(null, '', `/app/${mongodbId}`);
            }
        }
    }, [item, perseusItems, isLoading, onSkillChange, assessmentMode]);

    // Trigger feedback animation and auto-scroll
    useEffect(() => {
        if (isAnswered) {
            setShowFeedback(false);
            // Slight delay before showing to trigger animation
            const timer = setTimeout(() => setShowFeedback(true), 50);
            return () => clearTimeout(timer);
        }
    }, [isAnswered]);

    // Auto-scroll removed - scrolling is now handled by the home screen container

    // Load next batch of questions when approaching end
    const loadNextBatch = async () => {
        if (perseusItems.length === 0) return;
        
        // Prevent concurrent calls
        if (isLoadingNextBatch) {
            return;
        }
        
        setIsLoadingNextBatch(true);
        
        try {
            // Get current question IDs
            const currentQuestionIds = perseusItems.map(
                (item: any) => item.dash_metadata?.dash_question_id || ''
            ).filter(Boolean);
            
            if (currentQuestionIds.length === 0) {
                setIsLoadingNextBatch(false);
                return; // No valid question IDs
            }
            
            // Request next 5 questions
            const response = await apiUtils.post(`${DASH_API_URL}/api/questions/recommend-next`, {
                current_question_ids: currentQuestionIds,
                count: 5
            });
            
            if (!response.ok) {
                console.warn('Failed to fetch next batch:', response.status);
                setIsLoadingNextBatch(false);
                return;
            }
            
            const newQuestions = await response.json();
            
            // Only update if we got new questions (non-empty response means questions changed)
            if (newQuestions.length > 0) {
                setPerseusItems(prev => [...prev, ...newQuestions]);
            }
        } catch (err) {
            console.error('Error loading next batch:', err);
        } finally {
            setIsLoadingNextBatch(false);
        }
    };

    const handleNext = () => {
        setItem((prev) => {
            const index = prev + 1;

            if (index >= perseusItems.length) {
                setEndOfTest(true);
                return prev; // stay at last valid index
            }

            // Load next batch when 2 questions remaining
            if (index === perseusItems.length - 2) {
                loadNextBatch();
            }

            if (index === perseusItems.length - 1) {
                setEndOfTest(true);
            }

            setIsAnswered(false);
            setShowFeedback(false);
            setStartTime(Date.now()); // Reset timer for next question
            return index;
        });
    };

    const handleSubmit = async () => {
        if (rendererRef.current) {
            // getUserInput() returns UserInputMap (the new object format)
            const userInput = rendererRef.current.getUserInput();
            const itemData = perseusItem; // Full item with question AND answer
            
            console.log('[SCORING] User input:', JSON.stringify(userInput, null, 2));
            console.log('[SCORING] Item data keys:', Object.keys(itemData));
            console.log('[SCORING] Has answer key:', !!itemData.answer);
            console.log('[SCORING] Answer:', JSON.stringify(itemData.answer, null, 2));
            
            // Custom scoring since Perseus doesn't have answer keys in our questions
            // Score based on the 'correct' property in widget choices
            let isCorrect = false;
            const question = itemData.question;
            
            // Check each widget in the user input
            for (const [widgetId, widgetInput] of Object.entries(userInput)) {
                const widgetDef = question.widgets?.[widgetId];
                if (!widgetDef) continue;
                
                if (widgetDef.type === 'radio') {
                    const choices = widgetDef.options?.choices || [];
                    const selectedIds = (widgetInput as any).selectedChoiceIds || [];
                    const isMultiSelect = widgetDef.options?.multipleSelect || false;
                    
                    if (isMultiSelect) {
                        // For multi-select: all selected choices must be correct, and all correct choices must be selected
                        const correctIndices = choices
                            .map((c, i) => c.correct ? i : -1)
                            .filter(i => i >= 0);
                        const selectedIndices = selectedIds.map((id: string) => {
                            const match = id.match(/choice-(\d+)-/);
                            return match ? parseInt(match[1]) : -1;
                        }).filter((i: number) => i >= 0);
                        
                        isCorrect = correctIndices.length === selectedIndices.length &&
                                   correctIndices.every((idx: number) => selectedIndices.includes(idx));
                    } else {
                        // For single-select: the one selected choice must be correct
                        if (selectedIds.length === 1) {
                            const selectedId = selectedIds[0];
                            const match = selectedId.match(/choice-(\d+)-/);
                            if (match) {
                                const selectedIndex = parseInt(match[1]);
                                isCorrect = choices[selectedIndex]?.correct === true;
                            }
                        }
                    }
                }
            }
            
            console.log('[SCORING] Custom score - is correct:', isCorrect);
            
            const scoreResult = {
                type: isCorrect ? 'points' : 'points',
                earned: isCorrect ? 1 : 0,
                total: 1,
                message: null
            };

            // Continue to include an empty guess for the now defunct answer area.
            const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
            const keScore = keScoreFromPerseusScore(
                scoreResult,
                maxCompatGuess,
                rendererRef.current.getSerializedState().question,
            );

            console.log('[RendererComponent] KEScore:', {
                correct: keScore.correct,
                empty: keScore.empty,
                guess: keScore.guess
            });

            // Calculate response time
            const responseTimeSeconds = (Date.now() - startTime) / 1000;

            // In assessment mode, call the assessment callback
            if (assessmentMode && onAssessmentAnswer) {
                const currentItem = perseusItems[item];
                const metadata = (currentItem as any).dash_metadata || {};
                const questionId = metadata.dash_question_id || `q_${item}`;
                
                setIsAnswered(true);
                setScore(keScore);
                setShowFeedback(true);
                
                // Call the callback with question ID and correctness
                onAssessmentAnswer(questionId, keScore.correct);
                return;
            }

            // Submit answer to DASH API for tracking and adaptive difficulty (normal mode)
            try {
                const currentItem = perseusItems[item];
                const metadata = (currentItem as any).dash_metadata || {};
                const questionId = metadata.dash_question_id || `q_${item}`;

                await apiUtils.post(`${DASH_API_URL}/api/submit-answer`, {
                    user_id: user_id,
                    question_id: questionId,
                    skill_ids: metadata.skill_ids || ["counting_1_10"],
                    is_correct: keScore.correct,
                    response_time_seconds: responseTimeSeconds
                });
                
                // Invalidate skill-scores cache to trigger refetch with updated data
                queryClient.invalidateQueries({ queryKey: ["skill-scores"] });
                
                // Track watched videos if answer was submitted
                if (watchedVideoIds && watchedVideoIds.length > 0) {
                    try {
                        for (const videoId of watchedVideoIds) {
                            await apiUtils.post(
                                `${DASH_API_URL}/api/videos/mark-helpful?question_id=${encodeURIComponent(questionId)}&video_id=${encodeURIComponent(videoId)}&is_correct=${keScore.correct}`,
                                {}
                            );
                        }
                        // Reset watched videos after tracking
                        onAnswerSubmitted?.();
                    } catch (err) {
                        console.error("Failed to track video helpfulness:", err);
                    }
                }
            } catch (err) {
                console.error("Failed to submit answer to DASH:", err);
            }

            // Display score to user
            setIsAnswered(true);
            setScore(keScore);
            console.log("Score:", keScore);
        }
    };

    const perseusItem = perseusItems[item] || {};
    const progressPercentage = perseusItems.length > 0
        ? ((item + 1) / perseusItems.length) * 100
        : 0;

    // Extract hints from current question
    const hints = (perseusItem as any)?.hints || [];

    // Reset hint index, close hints, and reset step tracker when question changes
    useEffect(() => {
        setCurrentHintIndex(0);
        setShowHints(false); // Auto-close hints when question changes
        setCurrentStep(1); // Reset to "Understand" step
        setShowRecap(false); // Hide recap card
    }, [item, setCurrentHintIndex, setShowHints]);

    // Progress step when hints are viewed (move to Plan)
    useEffect(() => {
        if (showHints && currentStep === 1) {
            setCurrentStep(2);
        }
    }, [showHints, currentStep]);

    // Move to Solve step when user starts interacting (first input)
    useEffect(() => {
        if (currentStep < 3 && !isAnswered && perseusItems.length > 0) {
            // We'll advance to step 3 when they click in the answer area
            // For now, auto-advance after a short delay of viewing the question
            const timer = setTimeout(() => {
                if (currentStep < 3) setCurrentStep(3);
            }, 10000); // 10 seconds to read and plan
            return () => clearTimeout(timer);
        }
    }, [currentStep, isAnswered, perseusItems.length, item]);

    // Move to Check step when answer is submitted
    useEffect(() => {
        if (isAnswered) {
            setCurrentStep(4);
            // Show recap card after a delay
            const timer = setTimeout(() => setShowRecap(true), 2000);
            return () => clearTimeout(timer);
        }
    }, [isAnswered]);

    return (
        <div className="framework-perseus relative flex w-full h-full items-start justify-center px-3 md:px-4">
            {/* Main Content Card - Clean & Professional with dot pattern */}
            <Card className="question-card relative flex w-full max-w-3xl my-6 md:my-8 flex-col border border-gray-200 dark:border-neutral-800 shadow-xl shadow-black/5 dark:shadow-black/20 bg-transparent rounded-2xl overflow-hidden transition-all duration-200">
                {/* Progress bar at top - subtle */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gray-100 dark:bg-neutral-800">
                    <div
                        className="h-full bg-gradient-to-r from-[#7C3AED] to-[#A78BFA] transition-all duration-500 ease-out"
                        style={{ width: `${progressPercentage}%` }}
                    />
                </div>

                <CardHeader className="space-y-0 py-3 px-5 md:px-6 border-b border-gray-200/50 dark:border-neutral-700/50">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex-1 min-w-0">
                            {/* Breadcrumb Navigation - Subtle & Compact */}
                            {perseusItems.length > 0 && !isLoading && (
                                <div className="flex items-center gap-1.5 text-[10px] md:text-xs text-gray-600 dark:text-gray-400">
                                    {(() => {
                                        const currentItem = perseusItems[item];
                                        const metadata = (currentItem as any).dash_metadata || {};
                                        const unitName = metadata.unit_name || 'Unknown Unit';
                                        const lessonName = metadata.lesson_name || 'Unknown Lesson';
                                        const exerciseName = metadata.exercise_name || 'Unknown Exercise';

                                        return (
                                            <>
                                                <span className="font-medium truncate">{unitName}</span>
                                                <ChevronRight className="w-3 h-3 flex-shrink-0 text-gray-400" />
                                                <span className="font-medium truncate">{lessonName}</span>
                                                <ChevronRight className="w-3 h-3 flex-shrink-0 text-gray-400" />
                                                <span className="font-semibold text-black dark:text-white truncate">{exerciseName}</span>
                                            </>
                                        );
                                    })()}
                                </div>
                            )}
                        </div>

                        {/* Compact Progress Indicator */}
                        <div className="flex items-center gap-2 flex-shrink-0">
                            {!isLoading && perseusItems.length > 0 && (
                                <>
                                    <span className="text-[10px] md:text-xs text-gray-500 dark:text-gray-400 font-medium">
                                        Q{item + 1}/{perseusItems.length}
                                    </span>
                                    <div className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800/50 rounded text-[10px] md:text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                                        {Math.round(progressPercentage)}%
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="px-5 md:px-8 py-6 md:py-8">

                    <div
                        ref={scrollContainerRef}
                        className="relative w-full max-w-4xl mx-auto"
                    >
                        {endOfTest ? (
                            <div className="flex h-full items-center justify-center px-3 md:px-4 py-4 md:py-6 text-center">
                                <div className="max-w-sm md:max-w-md border-[4px] md:border-[5px] border-black dark:border-white bg-[#4ADE80] px-6 md:px-8 py-8 md:py-10 shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]">
                                    <div className="text-4xl md:text-6xl mb-3 md:mb-4">🎉</div>
                                    <p className="text-xl md:text-2xl font-black text-black uppercase mb-2 tracking-tight">
                                        Congratulations!
                                    </p>
                                    <p className="text-base md:text-lg font-bold text-black mb-3 md:mb-4">
                                        You've successfully completed your test!
                                    </p>
                                    <p className="text-xs md:text-sm font-bold text-black uppercase tracking-wide mb-6">
                                        Review questions or restart session
                                    </p>
                                    <div className="flex gap-3 justify-center">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            onClick={() => {
                                                setItem(0);
                                                setEndOfTest(false);
                                                setScore(undefined);
                                                setIsAnswered(false);
                                                setIsError(false);
                                            }}
                                            className="border-[2px] border-black bg-white hover:bg-[#FFD93D] text-black font-black uppercase tracking-wide shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)] transition-all"
                                        >
                                            Restart
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="secondary"
                                            onClick={() => {
                                                setItem(0);
                                                setEndOfTest(false);
                                            }}
                                            className="border-[2px] border-black bg-[#C4B5FD] hover:bg-[#A78BFA] text-black font-black uppercase tracking-wide shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)] transition-all"
                                        >
                                            Review
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        ) : isLoading ? (
                            <div className="flex h-full flex-col items-center justify-center gap-3 md:gap-4">
                                <div className="relative w-12 h-12 md:w-16 md:h-16">
                                    <div className="absolute inset-0 border-[3px] md:border-[4px] border-black dark:border-white"></div>
                                    <div className="absolute inset-0 border-[3px] md:border-[4px] border-transparent border-t-[#C4B5FD] animate-spin"></div>
                                </div>
                                <p className="text-xs md:text-sm font-black uppercase text-black dark:text-white tracking-wider animate-pulse">
                                    Loading questions...
                                </p>
                            </div>
                        ) : perseusItems.length > 0 ? (
                            <div className="space-y-4 md:space-y-6">
                                <div id="question-content-container" className="bg-gray-50 dark:bg-neutral-800/50 text-black dark:text-white p-5 md:p-6 lg:p-8 rounded-xl border border-gray-200 dark:border-neutral-700 overflow-x-auto">
                                    <PerseusI18nContextProvider locale="en" strings={mockStrings}>
                                        <RenderStateRoot>
                                            <ServerItemRenderer
                                                ref={rendererRef}
                                                problemNum={0}
                                                item={perseusItem}
                                                dependencies={storybookDependenciesV2}
                                                apiOptions={{}}
                                                linterContext={{
                                                    contentType: "",
                                                    highlightLint: true,
                                                    paths: [],
                                                    stack: [],
                                                }}
                                                showSolutions="none"
                                                hintsVisible={0}
                                                reviewMode={false}
                                            />
                                        </RenderStateRoot>
                                    </PerseusI18nContextProvider>
                                </div>

                                {/* Hints Display */}
                                {hints.length > 0 && (
                                    <HintDisplay hints={hints} />
                                )}

                                {/* Scaffolded Feedback with explanation */}
                                {isAnswered && (
                                    <div
                                        className="fixed top-[60px] lg:top-[64px] left-1/2 transform -translate-x-1/2 z-[200] animate-in slide-in-from-top-4 duration-300 max-w-md w-[90%]"
                                    >
                                        <div className={`flex flex-col gap-2 px-4 md:px-5 py-3 md:py-4 border-[3px] md:border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] md:shadow-[6px_6px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] ${score?.correct
                                            ? "bg-[#ADFF2F]"
                                            : "bg-[#FF006E]"
                                            }`}>
                                            <div className="flex items-center gap-2 md:gap-3">
                                                {score?.correct ? (
                                                    <div className="p-1.5 border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-neutral-900">
                                                        <CheckCircle2 className="w-5 h-5 md:w-6 md:h-6 text-black dark:text-white flex-shrink-0 font-bold" />
                                                    </div>
                                                ) : (
                                                    <div className="p-1.5 border-[2px] md:border-[3px] border-black dark:border-white bg-white">
                                                        <XCircle className="w-5 h-5 md:w-6 md:h-6 text-black flex-shrink-0 font-bold" />
                                                    </div>
                                                )}
                                                <span className={`text-base md:text-lg font-black uppercase tracking-tight ${score?.correct
                                                    ? "text-black"
                                                    : "text-white"
                                                    }`}>
                                                    {score?.correct ? "🎯 Correct!" : "Not yet — keep going!"}
                                                </span>
                                            </div>
                                            {/* Explanation line */}
                                            <p className={`text-xs md:text-sm ${score?.correct ? 'text-black/80' : 'text-white/90'}`}>
                                                {score?.correct
                                                    ? "Great work! You understood the relationship between the quantities."
                                                    : "Let's review together — try using a tape diagram to visualize the ratio."}
                                            </p>
                                            {/* Suggested action */}
                                            {!score?.correct && (
                                                <button
                                                    onClick={() => {
                                                        setShowHints(true);
                                                        setCurrentStep(2);
                                                    }}
                                                    className="mt-1 px-3 py-1.5 bg-white text-black text-xs font-black uppercase border-[2px] border-black shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all self-start"
                                                >
                                                    Get a hint →
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* Recap Card - shows after completing a problem */}
                                {showRecap && isAnswered && (
                                    <div className="mt-4 md:mt-6 p-4 md:p-5 border-[2px] md:border-[3px] border-black dark:border-white bg-[#E0F2FE] dark:bg-[#0c2d48] shadow-[2px_2px_0_0_rgba(0,0,0,1)] animate-in slide-in-from-bottom-4 duration-300">
                                        <div className="flex items-start gap-3">
                                            <div className="w-8 h-8 rounded-full bg-[#0EA5E9] border-[2px] border-black flex items-center justify-center flex-shrink-0">
                                                <BookOpen className="w-4 h-4 text-white" />
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-[10px] md:text-xs font-black uppercase text-[#0369A1] dark:text-[#38BDF8] mb-1">What you practiced:</p>
                                                <p className="text-sm md:text-base text-black dark:text-white font-medium mb-2">
                                                    {(() => {
                                                        const currentItem = perseusItems[item];
                                                        const metadata = (currentItem as any).dash_metadata || {};
                                                        const skillNames = metadata.skill_names || ['Problem solving'];
                                                        return skillNames.slice(0, 2).join(', ');
                                                    })()}
                                                </p>
                                                <p className="text-[10px] md:text-xs font-black uppercase text-[#0369A1] dark:text-[#38BDF8] mb-1">Next up:</p>
                                                <p className="text-sm text-black dark:text-white">
                                                    More practice with similar problems to build mastery!
                                                </p>
                                            </div>
                                        </div>
                                        <button
                                            onClick={handleNext}
                                            className="mt-3 w-full py-2 bg-[#0EA5E9] text-white text-sm font-black uppercase border-[2px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)] transition-all"
                                        >
                                            Continue →
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="flex h-full items-center justify-center">
                                <div className="text-center space-y-2 md:space-y-3 border-[3px] md:border-[4px] border-black dark:border-white bg-white dark:bg-neutral-800 p-6 md:p-8 shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]">
                                    <div className="text-3xl md:text-4xl mb-1 md:mb-2">📝</div>
                                    <p className="text-xs md:text-sm font-black uppercase text-black dark:text-white tracking-wider">
                                        No questions available.
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </CardContent>

                <CardFooter className="flex justify-between items-center gap-3 px-5 md:px-6 py-4 border-t border-gray-200/50 dark:border-neutral-700/50">
                    <HintButton inline={true} />
                    <div className="flex gap-3">
                        <Button
                            type="button"
                            onClick={handleSubmit}
                            disabled={isLoading || endOfTest || perseusItems.length === 0 || isAnswered}
                            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-gradient-to-b from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none disabled:from-gray-400 disabled:to-gray-500"
                        >
                            <CheckCircle2 className="w-4 h-4" />
                            Submit
                        </Button>
                        {!assessmentMode && (
                            <Button
                                type="button"
                                variant="outline"
                                onClick={handleNext}
                                disabled={isLoading || endOfTest || perseusItems.length === 0}
                                className="flex items-center gap-2 px-5 py-2.5 rounded-lg border-2 border-gray-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 hover:bg-gray-50 dark:hover:bg-neutral-700 text-gray-700 dark:text-gray-300 font-semibold text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Next
                                <ChevronRight className="w-4 h-4" />
                            </Button>
                        )}
                    </div>
                </CardFooter>
            </Card>
        </div>
    );
};

export default RendererComponent;
