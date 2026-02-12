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
import { CheckCircle2, XCircle, Sparkles, ChevronRight } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useHint } from "../../contexts/HintContext";
import { apiUtils, reportQuestionAnalytics } from "../../lib/api-utils";
import { scorePerseusQuestion, hasUserInput } from "../../lib/scoring-utils";
import { jwtUtils } from "../../lib/jwt-utils";
import HintDisplay from "../hint-display/HintDisplay";
import HintButton from "../hint-button/HintButton";
import AudioPlayButton, { extractAudioWord } from "../AudioPlayButton";

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
    const { setTotalHints, setCurrentHintIndex, currentHintIndex, showHints, setShowHints, setResponsiveHint } = useHint();
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
    const rendererRef = useRef<ServerItemRenderer>(null);
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const currentItemRef = useRef(0);
    const mountedRef = useRef(true);

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
                    // Load questions directly — parallel preloaded + fresh fetch
                    // Race: whichever returns valid questions first wins
                    const freshPromise = apiUtils.get(`${DASH_API_URL}/api/questions/5`);
                    const preloadedPromise = apiUtils.get(`${DASH_API_URL}/api/questions/preloaded`)
                        .then(async (r) => {
                            if (!r.ok) return null;
                            const d = await r.json();
                            return d && d.length > 0 ? d : null;
                        })
                        .catch(() => null);

                    // Check preloaded first (fast DB lookup), but don't wait long
                    const preloadedData = await Promise.race([
                        preloadedPromise,
                        new Promise<null>(resolve => setTimeout(() => resolve(null), 300)), // 300ms max wait
                    ]);

                    if (preloadedData) {
                        setPerseusItems(preloadedData);
                        setItem(0);
                        setEndOfTest(false);
                        setIsAnswered(false);
                        setStartTime(Date.now());
                        setIsLoading(false);
                        return;
                    }

                    // Use the already-started fresh fetch (no wasted time)
                    const response = await freshPromise;

                    if (!response.ok) {
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

    // Cleanup: mark component as unmounted to prevent stale state updates
    useEffect(() => {
        return () => { mountedRef.current = false; };
    }, []);

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

            setIsAnswered(false);
            setShowFeedback(false);
            setStartTime(Date.now()); // Reset timer for next question
            return index;
        });
    };

    const handleSubmit = async () => {
        if (rendererRef.current && perseusItem?.question) {
            // getUserInput() returns UserInputMap (the new object format)
            const userInput = rendererRef.current.getUserInput();
            const itemData = perseusItem; // Full item with question AND answer
            const question = itemData.question;

            // Empty submission guard: check if user actually entered/selected something
            if (!hasUserInput(question.widgets || {}, userInput)) {
                toast.error("Please select or enter an answer first");
                return;
            }

            console.log('[SCORING] User input:', JSON.stringify(userInput, null, 2));

            // Custom scoring via shared utility (Perseus doesn't handle our AI answer format)
            const scoringResult = scorePerseusQuestion(question.widgets || {}, userInput);
            const { selectedAnswerText, selectedAnswerIndex } = scoringResult;
            const isCorrect = scoringResult.correct;
            console.log('[SCORING] Custom score - is correct:', isCorrect, `(${scoringResult.correctCount}/${scoringResult.scoreableCount} widgets)`);
            
            const scoreResult = {
                type: 'points' as const,
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

                // Fire-and-forget analytics reporting
                reportQuestionAnalytics({
                    question_id: questionId,
                    correct: keScore.correct,
                    hints_used: currentHintIndex,
                    time_seconds: responseTimeSeconds,
                    skipped: false,
                    skill_id: (metadata.skill_ids || [])[0],
                });
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
                    response_time_seconds: responseTimeSeconds,
                    selected_answer: selectedAnswerText || null,
                    selected_answer_index: selectedAnswerIndex,
                });
                
                // Invalidate skill-scores cache to trigger refetch with updated data
                queryClient.invalidateQueries({ queryKey: ["skill-scores"] });
                queryClient.invalidateQueries({ queryKey: ["grading-panel"] });
                
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

            // On wrong answer, request a responsive hint from Gemini (fire and forget)
            if (!keScore.correct) {
                try {
                    const currentItem = perseusItems[item] as any;
                    const metadata = currentItem?.dash_metadata || {};
                    const questionId = metadata.dash_question_id || `q_${item}`;
                    const skillIds = metadata.skill_ids || [];
                    const qContent = currentItem?.question?.content || '';

                    // Extract selected and correct answer text from widget data
                    let selectedText = '';
                    let correctText = '';
                    const question = currentItem?.question;
                    for (const [widgetId, widgetInput] of Object.entries(userInput)) {
                        const widgetDef = question?.widgets?.[widgetId];
                        if (!widgetDef) continue;
                        if (widgetDef.type === 'radio') {
                            const choices = widgetDef.options?.choices || [];
                            const selectedIds = (widgetInput as any).selectedChoiceIds || [];
                            if (selectedIds.length > 0) {
                                const match = selectedIds[0].match(/choice-(\d+)-/);
                                if (match) selectedText = choices[parseInt(match[1])]?.content || '';
                            }
                            const correct = choices.find((c: any) => c.correct);
                            if (correct) correctText = correct.content || '';
                        } else if (widgetDef.type === 'numeric-input') {
                            selectedText = (widgetInput as any)?.currentValue || '';
                            const answers = widgetDef.options?.answers || [];
                            const ca = answers.find((a: any) => a.status === 'correct');
                            if (ca) correctText = String(ca.value);
                        } else if (widgetDef.type === 'expression') {
                            selectedText = typeof widgetInput === 'string' ? widgetInput : ((widgetInput as any)?.currentValue || '');
                            const forms = widgetDef.options?.answerForms || [];
                            const cf = forms.find((f: any) => f.considered === 'correct');
                            if (cf) correctText = cf.value || '';
                        } else if (widgetDef.type === 'dropdown') {
                            const choices = widgetDef.options?.choices || [];
                            const idx = (widgetInput as any)?.value ?? (widgetInput as any)?.selected;
                            if (idx != null && choices[idx]) selectedText = choices[idx].content || '';
                            const correct = choices.find((c: any) => c.correct);
                            if (correct) correctText = correct.content || '';
                        }
                        if (selectedText) break; // Use first scoreable widget
                    }

                    if (selectedText && skillIds.length > 0) {
                        const questionIdAtRequest = questionId;
                        currentItemRef.current = item;  // Ensure ref is current before async hint fetch
                        apiUtils.post(`${DASH_API_URL}/api/responsive-hint`, {
                            question_id: questionId,
                            skill_id: skillIds[0],
                            question_text: qContent.substring(0, 500),
                            selected_answer: selectedText.substring(0, 200),
                            correct_answer: correctText.substring(0, 200),
                        }).then((resp: Response) => resp.json()).then((data: any) => {
                            if (!mountedRef.current) return;  // component unmounted, skip state update
                            // Guard: only set hint if still on the same question
                            if (currentItemRef.current === item && data?.hint_content) {
                                setResponsiveHint(data.hint_content);
                            }
                        }).catch((err: any) => {
                            console.error("Failed to get responsive hint:", err);
                        });
                    }
                } catch (err) {
                    console.error("Failed to request responsive hint:", err);
                }
            }

            // Fire-and-forget analytics reporting
            {
                const currentItem = perseusItems[item];
                const metadata = (currentItem as any).dash_metadata || {};
                const questionId = metadata.dash_question_id || `q_${item}`;
                reportQuestionAnalytics({
                    question_id: questionId,
                    correct: keScore.correct,
                    hints_used: currentHintIndex,
                    time_seconds: responseTimeSeconds,
                    skipped: false,
                    skill_id: (metadata.skill_ids || [])[0],
                });
            }

            // Display score to user
            setIsAnswered(true);
            setScore(keScore);
            console.log("Score:", keScore);
        }
    };

    const rawPerseusItem = perseusItems[item] || {};
    // Sanitize AI-generated question content — strip stray "widget." text + fix missing widget fields
    const perseusItem = (() => {
        const itemCopy = { ...rawPerseusItem } as any;
        if (itemCopy.question?.content && typeof itemCopy.question.content === 'string') {
            // Remove literal "widget." or "widget" that Gemini sometimes appends after placeholders
            itemCopy.question = { ...itemCopy.question };
            itemCopy.question.content = itemCopy.question.content
                .replace(/\[\[☃\s+[^\]]+\]\]\s*widget\.?/gi, (match: string) => {
                    // Keep the placeholder, strip the trailing "widget." text
                    const placeholder = match.match(/\[\[☃\s+[^\]]+\]\]/)?.[0] || '';
                    return placeholder;
                })
                .replace(/\bwidget\.\s*$/gim, '') // Strip trailing "widget." on any line
                // Strip picture/image references that have no actual images
                .replace(/\b(?:look at|examine|see|observe|study|check out)\s+(?:the\s+)?(?:picture|image|diagram|illustration|photo|figure)s?\b[^.!?\n]*[.!?]?\s*/gi, '')
                .replace(/\b(?:in the (?:picture|image|diagram|illustration) (?:below|above|shown))[^.!?\n]*[.!?]?\s*/gi, '')
                .replace(/\b(?:the (?:picture|image|diagram|illustration) (?:below|above|shows?))[^.!?\n]*[.!?]?\s*/gi, '')
                .trim();
        }
        // Ensure every widget has a placeholder in content (definition+radio combo fix)
        if (itemCopy.question?.widgets && typeof itemCopy.question.content === 'string') {
            for (const wname of Object.keys(itemCopy.question.widgets)) {
                const wtype = (itemCopy.question.widgets[wname] as any)?.type;
                if (wtype === 'image') continue;
                if (!itemCopy.question.content.includes(`[[☃ ${wname}]]`)) {
                    itemCopy.question.content = itemCopy.question.content.trimEnd() + `\n\n[[☃ ${wname}]]`;
                }
            }
        }
        // Patch missing required fields on widgets (fixes AI-generated questions missing Perseus defaults)
        if (itemCopy.question?.widgets) {
            itemCopy.question = { ...itemCopy.question };
            itemCopy.question.widgets = { ...itemCopy.question.widgets };
            for (const [key, widget] of Object.entries(itemCopy.question.widgets)) {
                const w = widget as any;
                // Radio: options is an array instead of {choices: [...]}
                if (w?.type === 'radio' && Array.isArray(w.options)) {
                    const multipleSelect = w.multipleSelect || false;
                    const randomize = w.randomize || false;
                    const { multipleSelect: _ms, randomize: _rz, ...rest } = w;
                    itemCopy.question.widgets[key] = {
                        ...rest,
                        options: { choices: w.options, multipleSelect, randomize },
                    };
                }
                if (w?.type === 'numeric-input' && w.options) {
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            coefficient: false,
                            static: false,
                            labelText: '',
                            size: 'normal',
                            ...w.options,
                        },
                    };
                }
                // Orderer: normalize string options to {content: string} objects
                if (w?.type === 'orderer' && w.options) {
                    const fixArr = (arr: any[]) => arr?.map((item: any) =>
                        typeof item === 'string' ? { content: item } : item
                    );
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            ...w.options,
                            options: fixArr(w.options.options || []),
                            correctOptions: fixArr(w.options.correctOptions || []),
                        },
                    };
                }
                // Expression: ensure buttonSets and other required fields
                if (w?.type === 'expression' && w.options) {
                    const exprOpts = { ...w.options };
                    if (!exprOpts.buttonSets || !Array.isArray(exprOpts.buttonSets) || exprOpts.buttonSets.length === 0) {
                        exprOpts.buttonSets = ['basic'];
                    }
                    if (!exprOpts.functions || !Array.isArray(exprOpts.functions) || exprOpts.functions.length === 0) {
                        exprOpts.functions = ['f', 'g', 'h'];
                    }
                    if (exprOpts.times === undefined) exprOpts.times = false;
                    if (!exprOpts.buttonsVisible) exprOpts.buttonsVisible = 'never';
                    itemCopy.question.widgets[key] = { ...w, options: exprOpts };
                }
                // Definition: ensure togglePrompt, definition, and static fields
                if (w?.type === 'definition' && w.options) {
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            togglePrompt: 'Definition',
                            definition: '',
                            static: false,
                            ...w.options,
                        },
                    };
                }
                // Dropdown: ensure placeholder and static fields
                if (w?.type === 'dropdown' && w.options) {
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            placeholder: 'Select an answer',
                            static: false,
                            ...w.options,
                        },
                    };
                }
                // Matcher: ensure labels and padding
                if (w?.type === 'matcher' && w.options) {
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            labels: ['Left', 'Right'],
                            orderMatters: false,
                            padding: true,
                            ...w.options,
                        },
                    };
                }
                // Sorter: ensure layout
                if (w?.type === 'sorter' && w.options) {
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            layout: 'horizontal',
                            padding: true,
                            ...w.options,
                        },
                    };
                }
                // Categorizer: ensure required fields
                if (w?.type === 'categorizer' && w.options) {
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            randomizeItems: false,
                            static: false,
                            highlightLint: false,
                            ...w.options,
                        },
                    };
                }
                // Number-line: ensure required fields
                if (w?.type === 'number-line' && w.options) {
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            labelRange: [null, null],
                            initialX: null,
                            tickStep: 1,
                            labelStyle: 'decimal',
                            labelTicks: true,
                            isInequality: false,
                            snapDivisions: 2,
                            correctRel: 'eq',
                            numDivisions: null,
                            divisionRange: [1, 10],
                            isTickCtrl: false,
                            static: false,
                            ...w.options,
                        },
                    };
                }
                // Table: ensure required fields
                if (w?.type === 'table' && w.options) {
                    itemCopy.question.widgets[key] = {
                        ...w,
                        options: {
                            headers: [''],
                            rows: 4,
                            columns: 2,
                            ...w.options,
                        },
                    };
                }
            }
        }
        return itemCopy;
    })();
    const progressPercentage = perseusItems.length > 0
        ? Math.min(100, ((item + 1) / perseusItems.length) * 100)
        : 0;

    // Extract hints from current question
    const hints = (perseusItem as any)?.hints || [];

    // Detect if question needs audio (phonics/listening questions)
    const audioWord = React.useMemo(() => {
        const content = (perseusItem as any)?.question?.content || '';
        return extractAudioWord(content);
    }, [perseusItem]);

    // Reset hint index, close hints, and clear responsive hint when question changes
    useEffect(() => {
        currentItemRef.current = item;
        setCurrentHintIndex(0);
        setShowHints(false);
        setResponsiveHint(null);
    }, [item, setCurrentHintIndex, setShowHints, setResponsiveHint]);

    return (
        <div className="framework-perseus relative flex w-full h-full items-start justify-center px-3 md:px-4">
            {/* Neo-Brutalism Card */}
            <Card className="relative flex w-full max-w-4xl md:max-w-5xl my-4 md:my-6 flex-col border-[4px] md:border-[5px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] bg-[#FFFDF5] dark:bg-[#000000] transition-all duration-200">
                {/* Progress bar at top */}
                <div className="absolute top-0 left-0 right-0 h-2 md:h-3 bg-[#FFFDF5] dark:bg-[#000000] border-b-[2px] md:border-b-[3px] border-black dark:border-white">
                    <div
                        className="h-full bg-[#C4B5FD] transition-all duration-500 ease-out"
                        style={{ width: `${progressPercentage}%` }}
                    />
                </div>

                <CardHeader className="space-y-2 pt-6 md:pt-7 px-4 md:px-6 border-b-[3px] md:border-b-[4px] border-black dark:border-white bg-[#FFD93D]">
                    <div className="flex items-start justify-between gap-3 md:gap-4 flex-wrap">
                        <div className="space-y-1.5 flex-1">
                            {/* Breadcrumb Navigation */}
                            {perseusItems.length > 0 && !isLoading && (
                                <div className="flex items-center gap-2 flex-wrap text-xs md:text-sm font-bold text-black">
                                    {(() => {
                                        const currentItem = perseusItems[item];
                                        const metadata = (currentItem as any).dash_metadata || {};
                                        const unitName = metadata.unit_name || 'Unknown Unit';
                                        const lessonName = metadata.lesson_name || 'Unknown Lesson';
                                        const exerciseName = metadata.exercise_name || 'Unknown Exercise';
                                        const isAI = metadata.ai_generated === true;

                                        return (
                                            <>
                                                <span className="uppercase tracking-wide">{unitName}</span>
                                                <ChevronRight className="w-4 h-4 flex-shrink-0" />
                                                <span className="uppercase tracking-wide">{lessonName}</span>
                                                {!isAI && (
                                                    <>
                                                        <ChevronRight className="w-4 h-4 flex-shrink-0" />
                                                        <span className="uppercase tracking-wide">{exerciseName}</span>
                                                    </>
                                                )}
                                            </>
                                        );
                                    })()}
                                </div>
                            )}
                        </div>

                        {/* Neo-Brutalist Progress Badge */}
                        <div className="flex items-center gap-2 md:gap-3">
                            {!isLoading && perseusItems.length > 0 && (
                                <>
                                    <div className="text-right hidden sm:block">
                                        <div className="text-[10px] md:text-xs font-black uppercase tracking-wider text-black mb-0.5">
                                            Progress
                                        </div>
                                        <div className="text-xs md:text-sm font-black text-black">
                                            Q <span className="text-[#FF6B6B]">{item + 1}</span>/{perseusItems.length}
                                        </div>
                                    </div>
                                    <div className="px-3 md:px-4 py-2 md:py-3 border-[2px] md:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
                                        <div className="text-xl md:text-2xl font-black text-black dark:text-white">
                                            {Math.round(progressPercentage)}%
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="px-4 md:px-6 py-4 md:py-6 bg-[#FFFDF5] dark:bg-[#000000]">
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
                        ) : perseusItems.length > 0 && Object.keys(perseusItem?.question?.widgets || {}).length > 0 ? (
                            <div className="space-y-4 md:space-y-6">
                                {/* Audio play button for phonics/listening questions */}
                                {audioWord && (
                                    <div style={{ marginBottom: '16px' }}>
                                        <AudioPlayButton word={audioWord} autoPlay={true} />
                                    </div>
                                )}

                                <div id="question-content-container" className="border-[3px] md:border-[4px] border-black dark:border-white bg-white dark:bg-neutral-800 text-black dark:text-white p-4 md:p-5 lg:p-6 shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]">
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

                                {/* Inline feedback panel — stays visible until "Next" */}
                                {isAnswered && score && (
                                    <div className="mt-4 border-[3px] md:border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] md:shadow-[6px_6px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] animate-in slide-in-from-top-4 duration-300">
                                        <div className={`flex items-center gap-2 md:gap-3 px-5 md:px-6 py-3 md:py-4 ${score.correct
                                            ? "bg-[#ADFF2F]"
                                            : "bg-[#FF006E]"
                                            }`}>
                                            {score.correct ? (
                                                <div className="p-1.5 border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-neutral-900">
                                                    <CheckCircle2 className="w-5 h-5 md:w-6 md:h-6 text-black dark:text-white flex-shrink-0 font-bold" />
                                                </div>
                                            ) : (
                                                <div className="p-1.5 border-[2px] md:border-[3px] border-black dark:border-white bg-white">
                                                    <XCircle className="w-5 h-5 md:w-6 md:h-6 text-black flex-shrink-0 font-bold" />
                                                </div>
                                            )}
                                            <span className={`text-base md:text-lg font-black uppercase tracking-tight ${score.correct
                                                ? "text-black"
                                                : "text-white"
                                                }`}>
                                                {score.correct ? "Correct!" : "Not quite!"}
                                            </span>
                                        </div>
                                        {/* Explanation: show last hint (walkthrough) on wrong answer */}
                                        {!score.correct && hints.length > 0 && (
                                            <div className="px-5 md:px-6 py-4 bg-[#FFF8E1] dark:bg-amber-900/30 border-t-[3px] border-black dark:border-white">
                                                <p className="text-xs font-black uppercase tracking-wider text-black dark:text-white mb-2">Explanation</p>
                                                <p className="text-sm leading-relaxed text-black dark:text-neutral-200">
                                                    {hints[hints.length - 1]?.content || hints[0]?.content || ''}
                                                </p>
                                            </div>
                                        )}
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

                <CardFooter className="flex justify-between items-center gap-2 md:gap-3 px-4 md:px-6 pb-4 md:pb-5 pt-3 md:pt-4 border-t-[3px] md:border-t-[4px] border-black dark:border-white bg-white dark:bg-neutral-900">
                    {hints.length > 0 ? <HintButton inline={true} /> : <div />}
                    <div className="flex gap-2 md:gap-3">
                        <Button
                            type="button"
                            size="sm"
                            onClick={handleSubmit}
                            disabled={isLoading || endOfTest || perseusItems.length === 0 || isAnswered}
                            className="transition-all duration-100 border-[2px] md:border-[3px] border-black dark:border-white bg-[#C4B5FD] hover:bg-[#C4B5FD] text-black font-black uppercase tracking-wide shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:hover:shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:hover:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)] disabled:opacity-50 disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] text-xs md:text-sm h-9 md:h-10 px-4 md:px-5"
                        >
                            Submit
                        </Button>
                        {!assessmentMode && (
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={handleNext}
                                disabled={isLoading || endOfTest || perseusItems.length === 0 || !isAnswered}
                                className="transition-all duration-100 border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-neutral-800 hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] text-black dark:text-white dark:hover:text-black font-black uppercase tracking-wide shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] text-xs md:text-sm h-9 md:h-10 px-4 md:px-5"
                            >
                                Next →
                            </Button>
                        )}
                    </div>
                </CardFooter>
            </Card>
        </div>
    );
};

export default RendererComponent;
