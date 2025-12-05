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
        <div className="framework-perseus relative flex min-h-screen w-full items-center justify-center py-4 md:py-6 px-3 md:px-4">
            {/* Neo-Brutalism Card */}
            <Card className="relative flex w-full max-w-4xl md:max-w-5xl h-auto md:h-[550px] lg:h-[600px] flex-col border-[4px] md:border-[5px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] bg-[#FFFDF5] dark:bg-[#000000] overflow-hidden transition-all duration-200">
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
                            <div className="flex items-center gap-2 md:gap-3">
                                <div className="p-1.5 md:p-2 border-[2px] md:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
                                    <Sparkles className="w-4 h-4 md:w-5 md:h-5 text-black dark:text-white font-bold" />
                                </div>
                                <CardTitle className="text-lg md:text-xl font-black text-black uppercase tracking-tight">
                                    Practice Session
                                </CardTitle>
                            </div>
                            <CardDescription className="text-xs md:text-sm font-bold text-black uppercase tracking-wide">
                                {user ? `Welcome, ${user.name}! Grade: ${user.current_grade}` : `User: ${user_id}`}
                            </CardDescription>
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

                <CardContent className="flex-1 overflow-hidden px-4 md:px-6 bg-[#FFFDF5] dark:bg-[#000000]">
                    <div
                        ref={scrollContainerRef}
                        className="relative h-full w-full overflow-auto scrollbar-thin scrollbar-thumb-black dark:scrollbar-thumb-white scrollbar-track-transparent"
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
                                    <p className="text-xs md:text-sm font-bold text-black uppercase tracking-wide">
                                        Review questions or restart session
                                    </p>
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
                            <div className="space-y-4 md:space-y-6 py-3 md:py-4">
                                <div className="border-[3px] md:border-[4px] border-black dark:border-white bg-white dark:bg-neutral-800 p-4 md:p-5 lg:p-6 shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]">
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

                                {/* Neo-Brutalist feedback */}
                                {isAnswered && (
                                    <div
                                        className={`transform transition-all duration-300 ${showFeedback
                                            ? 'translate-y-0 opacity-100'
                                            : 'translate-y-4 opacity-0'
                                            }`}
                                    >
                                        <div className={`flex items-center gap-2 md:gap-3 px-4 md:px-5 py-3 md:py-4 border-[3px] md:border-[4px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] ${score?.correct
                                            ? "bg-[#ADFF2F]"
                                            : "bg-[#FF006E]"
                                            }`}>
                                            {score?.correct ? (
                                                <div className="p-1 border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-neutral-900">
                                                    <CheckCircle2 className="w-4 h-4 md:w-5 md:h-5 text-black dark:text-white flex-shrink-0 font-bold" />
                                                </div>
                                            ) : (
                                                <div className="p-1 border-[2px] md:border-[3px] border-black dark:border-white bg-white">
                                                    <XCircle className="w-4 h-4 md:w-5 md:h-5 text-black flex-shrink-0 font-bold" />
                                                </div>
                                            )}
                                            <span className={`text-sm md:text-base font-black uppercase tracking-tight ${score?.correct
                                                ? "text-black"
                                                : "text-white"
                                                }`}>
                                                {score?.correct ? "🎯 Excellent! That's correct!" : "📚 Not quite. Keep trying!"}
                                            </span>
                                        </div>
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

                <CardFooter className="flex justify-end gap-2 md:gap-3 px-4 md:px-6 pb-4 md:pb-5 pt-3 md:pt-4 border-t-[3px] md:border-t-[4px] border-black dark:border-white bg-white dark:bg-neutral-900">
                    <Button
                        type="button"
                        size="sm"
                        onClick={handleSubmit}
                        disabled={isLoading || endOfTest || perseusItems.length === 0}
                        className="transition-all duration-100 border-[2px] md:border-[3px] border-black dark:border-white bg-[#C4B5FD] hover:bg-[#C4B5FD] text-black font-black uppercase tracking-wide shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:hover:shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:hover:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)] disabled:opacity-50 disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] text-xs md:text-sm h-9 md:h-10 px-4 md:px-5"
                    >
                        Submit
                    </Button>
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleNext}
                        disabled={isLoading || endOfTest || perseusItems.length === 0}
                        className="transition-all duration-100 border-[2px] md:border-[3px] border-black dark:border-white bg-white dark:bg-neutral-800 hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] text-black dark:text-white dark:hover:text-black font-black uppercase tracking-wide shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] text-xs md:text-sm h-9 md:h-10 px-4 md:px-5"
                    >
                        Next →
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
};

export default RendererComponent;
