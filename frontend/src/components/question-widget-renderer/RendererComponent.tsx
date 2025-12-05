import React, { useEffect, useState, useRef } from "react";
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
import { CheckCircle2, XCircle, Sparkles } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { apiUtils } from "../../lib/api-utils";
import { jwtUtils } from "../../lib/jwt-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

interface RendererComponentProps {
    onSkillChange?: (skill: string) => void;
}

const RendererComponent = ({ onSkillChange }: RendererComponentProps) => {
    const { user } = useAuth();
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
    const rendererRef = useRef<ServerItemRenderer>(null);
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    // Get user_id from auth context
    const user_id = user?.user_id || 'mongodb_test_user';

    // Fetch questions using apiUtils with JWT authentication
    useEffect(() => {
        const fetchQuestions = async () => {
            if (!jwtUtils.getToken()) {
                setIsLoading(false);
                return;
            }

            setIsLoading(true);
            setIsError(false);
            setError(null);

            try {
                const response = await apiUtils.get(`${DASH_API_URL}/api/questions/16`);
                
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
                console.error('Error fetching questions:', err);
                setIsError(true);
                setError(err instanceof Error ? err : new Error('Unknown error'));
            } finally {
                setIsLoading(false);
            }
        };

        fetchQuestions();
    }, [user_id]);

    useEffect(() => {
        if (isError) {
            const message = error?.message || "Unknown error fetching questions";
            toast.error("Unable to load questions", {
                description: message,
            });
        }
    }, [isError, error]);

    // Log when question is displayed (once per item change)
    useEffect(() => {
        if (perseusItems.length > 0 && !isLoading) {
            const currentItem = perseusItems[item];
            const metadata = (currentItem as any).dash_metadata || {};

            // Log question displayed
            apiUtils.post(`${DASH_API_URL}/api/question-displayed`, {
                question_index: item,
                metadata: metadata
            }).catch((err) => {
                console.error('Failed to log question displayed:', err);
            });
        }
    }, [item, perseusItems, isLoading, user_id]);

    // Mock skill state update
    useEffect(() => {
        if (onSkillChange) {
            // Mock variable as requested
            const mockSkill = "counting_100";
            onSkillChange(mockSkill);
        }
    }, [onSkillChange]);

    // Trigger feedback animation and auto-scroll
    useEffect(() => {
        if (isAnswered) {
            setShowFeedback(false);
            // Slight delay before showing to trigger animation
            const timer = setTimeout(() => setShowFeedback(true), 50);
            return () => clearTimeout(timer);
        }
    }, [isAnswered]);

    // Auto-scroll to bottom when feedback is shown
    useEffect(() => {
        if (showFeedback && scrollContainerRef.current) {
            // Use setTimeout to ensure the DOM has updated with the feedback element
            setTimeout(() => {
                if (scrollContainerRef.current) {
                    scrollContainerRef.current.scrollTo({
                        top: scrollContainerRef.current.scrollHeight,
                        behavior: 'smooth'
                    });
                }
            }, 100);
        }
    }, [showFeedback]);

    const handleNext = () => {
        setItem((prev) => {
            const index = prev + 1;

            if (index >= perseusItems.length) {
                setEndOfTest(true);
                return prev; // stay at last valid index
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
            const userInput = rendererRef.current.getUserInput();
            const question = perseusItem.question;
            const scoreResult = scorePerseusItem(question, userInput, "en");

            // Continue to include an empty guess for the now defunct answer area.
            const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
            const keScore = keScoreFromPerseusScore(
                scoreResult,
                maxCompatGuess,
                rendererRef.current.getSerializedState().question,
            );

            // Calculate response time
            const responseTimeSeconds = (Date.now() - startTime) / 1000;

            // Submit answer to DASH API for tracking and adaptive difficulty
            try {
                const currentItem = perseusItems[item];
                const metadata = (currentItem as any).dash_metadata || {};

                await apiUtils.post(`${DASH_API_URL}/api/submit-answer`, {
                    user_id: user_id,
                    question_id: metadata.dash_question_id || `q_${item}`,
                    skill_ids: metadata.skill_ids || ["counting_1_10"],
                    is_correct: keScore.correct,
                    response_time_seconds: responseTimeSeconds
                });
            } catch (err) {
                console.error("Failed to submit answer to DASH:", err);
            }

            // Display score to user
            setIsAnswered(true);
            setScore(keScore);
            console.log("Score:", keScore);

            // Record question answer with TeachingAssistant
            try {
                const currentItem = perseusItems[item];
                const metadata = (currentItem as any).dash_metadata || {};
                const questionId = metadata.dash_question_id || `q_${item}_${Date.now()}`;
                
                await apiUtils.post(`${TEACHING_ASSISTANT_API_URL}/question/answered`, {
                    question_id: questionId,
                    is_correct: keScore.correct || false
                });
            } catch (err) {
                console.error("Error recording question answer:", err);
            }
        }
    };

    const perseusItem = perseusItems[item] || {};
    const progressPercentage = perseusItems.length > 0
        ? ((item + 1) / perseusItems.length) * 100
        : 0;

    return (
        <div className="framework-perseus relative flex min-h-screen w-full items-center justify-center py-8 px-4">
            {/* Animated gradient background */}
            <div className="fixed inset-0 -z-10 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-slate-950 dark:via-purple-950 dark:to-slate-900" />
                <div className="absolute top-0 -left-4 w-96 h-96 bg-purple-300 dark:bg-purple-600 rounded-full mix-blend-multiply dark:mix-blend-soft-light filter blur-3xl opacity-20 dark:opacity-10 animate-blob" />
                <div className="absolute top-0 -right-4 w-96 h-96 bg-blue-300 dark:bg-blue-600 rounded-full mix-blend-multiply dark:mix-blend-soft-light filter blur-3xl opacity-20 dark:opacity-10 animate-blob animation-delay-2000" />
                <div className="absolute -bottom-8 left-20 w-96 h-96 bg-pink-300 dark:bg-pink-600 rounded-full mix-blend-multiply dark:mix-blend-soft-light filter blur-3xl opacity-20 dark:opacity-10 animate-blob animation-delay-4000" />
            </div>

            {/* Glassmorphism Card */}
            <Card className="relative flex w-full max-w-6xl h-auto md:h-[650px] flex-col border border-white/20 dark:border-white/10 shadow-2xl backdrop-blur-xl bg-white/70 dark:bg-slate-800/40 overflow-hidden transition-all duration-300 hover:shadow-3xl">
                {/* Progress bar at top */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gray-200/50 dark:bg-gray-700/50">
                    <div
                        className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 transition-all duration-500 ease-out"
                        style={{ width: `${progressPercentage}%` }}
                    />
                </div>

                <CardHeader className="space-y-3 pt-6">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                        <div className="space-y-2 flex-1">
                            <div className="flex items-center gap-2">
                                <Sparkles className="w-5 h-5 text-purple-500 dark:text-purple-400" />
                                <CardTitle className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">
                                    Adaptive Practice Session
                                </CardTitle>
                            </div>
                            <CardDescription className="text-sm">
                                {user ? `Welcome, ${user.name}! Grade: ${user.current_grade}` : 'Loading user profile...'}
                            </CardDescription>
                        </div>

                        {/* Modern Progress Indicator */}
                        <div className="flex items-center gap-4">
                            <div className="text-right">
                                <div className="text-xs font-medium text-muted-foreground mb-1">
                                    User: {user?.name || user_id}
                                </div>
                                {!isLoading && perseusItems.length > 0 && (
                                    <div className="text-sm font-semibold text-foreground">
                                        Question <span className="text-blue-600 dark:text-blue-400">{item + 1}</span> of {perseusItems.length}
                                    </div>
                                )}
                            </div>

                            {/* Circular progress */}
                            {!isLoading && perseusItems.length > 0 && (
                                <div className="relative w-14 h-14">
                                    <svg className="transform -rotate-90 w-14 h-14">
                                        <circle
                                            cx="28"
                                            cy="28"
                                            r="24"
                                            stroke="currentColor"
                                            strokeWidth="4"
                                            fill="transparent"
                                            className="text-gray-200 dark:text-gray-700"
                                        />
                                        <circle
                                            cx="28"
                                            cy="28"
                                            r="24"
                                            stroke="url(#gradient)"
                                            strokeWidth="4"
                                            fill="transparent"
                                            strokeDasharray={`${2 * Math.PI * 24}`}
                                            strokeDashoffset={`${2 * Math.PI * 24 * (1 - progressPercentage / 100)}`}
                                            className="transition-all duration-500 ease-out"
                                            strokeLinecap="round"
                                        />
                                        <defs>
                                            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                                <stop offset="0%" stopColor="#3b82f6" />
                                                <stop offset="50%" stopColor="#a855f7" />
                                                <stop offset="100%" stopColor="#ec4899" />
                                            </linearGradient>
                                        </defs>
                                    </svg>
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <span className="text-xs font-bold text-foreground">
                                            {Math.round(progressPercentage)}%
                                        </span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="flex-1 overflow-hidden px-6">
                    <div
                        ref={scrollContainerRef}
                        className="relative h-full w-full overflow-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600 scrollbar-track-transparent"
                    >
                        {endOfTest ? (
                            <div className="flex h-full items-center justify-center px-4 py-6 text-center">
                                <div className="max-w-md rounded-2xl border border-emerald-200/50 dark:border-emerald-800/50 bg-gradient-to-br from-emerald-50/80 to-blue-50/80 dark:from-emerald-950/40 dark:to-blue-950/40 backdrop-blur-sm px-8 py-10 shadow-lg transform transition-all duration-300 hover:scale-105">
                                    <div className="text-6xl mb-4 animate-bounce">🎉</div>
                                    <p className="text-xl font-bold text-emerald-700 dark:text-emerald-300 mb-2">
                                        Congratulations!
                                    </p>
                                    <p className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-4">
                                        You've successfully completed your test!
                                    </p>
                                    <p className="text-sm text-muted-foreground">
                                        You can review questions above or restart the session from the main controls.
                                    </p>
                                </div>
                            </div>
                        ) : isLoading ? (
                            <div className="flex h-full flex-col items-center justify-center gap-4">
                                <div className="relative w-16 h-16">
                                    <div className="absolute inset-0 rounded-full border-4 border-purple-200 dark:border-purple-800"></div>
                                    <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-purple-600 dark:border-t-purple-400 animate-spin"></div>
                                </div>
                                <p className="text-sm font-medium text-muted-foreground animate-pulse">
                                    Loading questions...
                                </p>
                            </div>
                        ) : perseusItems.length > 0 ? (
                            <div className="space-y-6 py-4">
                                <div className="rounded-xl bg-white/50 dark:bg-slate-900/30 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 p-6 shadow-sm transition-all duration-200 hover:shadow-md">
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

                                {/* Enhanced feedback with animation */}
                                {isAnswered && (
                                    <div
                                        className={`transform transition-all duration-300 ${showFeedback
                                            ? 'translate-y-0 opacity-100'
                                            : 'translate-y-4 opacity-0'
                                            }`}
                                    >
                                        <div className={`flex items-center gap-3 rounded-xl px-5 py-4 shadow-lg backdrop-blur-sm border ${score?.correct
                                            ? "bg-gradient-to-r from-emerald-50/90 to-green-50/90 dark:from-emerald-950/50 dark:to-green-950/50 border-emerald-300/50 dark:border-emerald-700/50"
                                            : "bg-gradient-to-r from-red-50/90 to-orange-50/90 dark:from-red-950/50 dark:to-orange-950/50 border-red-300/50 dark:border-red-700/50"
                                            }`}>
                                            {score?.correct ? (
                                                <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400 flex-shrink-0 animate-scale-in" />
                                            ) : (
                                                <XCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 animate-scale-in" />
                                            )}
                                            <span className={`text-base font-semibold ${score?.correct
                                                ? "text-emerald-700 dark:text-emerald-300"
                                                : "text-red-700 dark:text-red-300"
                                                }`}>
                                                {score?.correct ? "🎯 Excellent! That's correct!" : "📚 Not quite. Keep trying!"}
                                            </span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="flex h-full items-center justify-center">
                                <div className="text-center space-y-2">
                                    <div className="text-4xl mb-2">📝</div>
                                    <p className="text-sm font-medium text-muted-foreground">
                                        No questions available.
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </CardContent>

                <CardFooter className="flex justify-end gap-3 px-6 pb-6 pt-4 border-t border-gray-200/50 dark:border-gray-700/50 bg-gradient-to-b from-transparent to-white/30 dark:to-slate-900/30">
                    <Button
                        type="button"
                        variant="outline"
                        size="default"
                        onClick={handleNext}
                        disabled={isLoading || endOfTest || perseusItems.length === 0}
                        className="transition-all duration-200 hover:scale-105 hover:shadow-md border-gray-300 dark:border-gray-600 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm"
                    >
                        Next Question →
                    </Button>
                    <Button
                        type="button"
                        size="default"
                        onClick={handleSubmit}
                        disabled={isLoading || endOfTest || perseusItems.length === 0}
                        className="transition-all duration-200 hover:scale-105 hover:shadow-lg bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 dark:from-blue-500 dark:to-purple-500"
                    >
                        ✓ Submit Answer
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
};

export default RendererComponent;
