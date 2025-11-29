import React, { useEffect, useState, useRef } from "react";
import {ServerItemRenderer} from "../../package/perseus/src/server-item-renderer";
import type { PerseusItem } from "@khanacademy/perseus-core";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { scorePerseusItem } from "@khanacademy/perseus-score";
import { keScoreFromPerseusScore } from "../../package/perseus/src/util/scoring";
import { RenderStateRoot } from "@khanacademy/wonder-blocks-core";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";
import { KEScore } from "@khanacademy/perseus-core";
import { useAuth } from "../../contexts/AuthContext";
import { jwtUtils } from "../../lib/jwt-utils";
import { apiUtils } from "../../lib/api-utils";

const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';
const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

const RendererComponent = () => {
    const { user } = useAuth();
    const [perseusItems, setPerseusItems] = useState<PerseusItem[]>([]);
    const [item, setItem] = useState(0);
    const [loading, setLoading] = useState(true);
    const [endOfTest, setEndOfTest] = useState(false);
    const [score, setScore] = useState<KEScore>();
    const [isAnswered, setIsAnswered] = useState(false);
    const [startTime, setStartTime] = useState<number>(Date.now());
    const rendererRef = useRef<ServerItemRenderer>(null);
    
    // Get user_id from authenticated user
    const user_id = user?.user_id;

    useEffect(() => {
        if (!user_id) return; // Wait for user to be loaded
        
        // Use DASH API with intelligent question selection
        // Age is fetched from MongoDB based on user_id
        setLoading(true);
        setItem(0);
        setEndOfTest(false);
        setIsAnswered(false);
        
        const token = jwtUtils.getToken();
        if (!token) {
            console.error("No authentication token");
            setLoading(false);
            return;
        }
        
        apiUtils.get(`${DASH_API_URL}/api/questions/16`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                console.log("API response:", data);
                setPerseusItems(data);
                setLoading(false);
                setStartTime(Date.now()); // Reset timer for first question
            })
            .catch((err) => {
                console.error("Failed to fetch questions:", err);
                setLoading(false);
            });
    }, [user_id]); // Re-fetch when user_id changes

    // Log when question is displayed
    useEffect(() => {
        if (perseusItems.length > 0 && !loading && user_id) {
            const currentItem = perseusItems[item];
            const metadata = (currentItem as any).dash_metadata || {};
            const token = jwtUtils.getToken();
            
            if (!token) return;
            
            apiUtils.post(`${DASH_API_URL}/api/question-displayed`, {
                question_index: item,
                metadata: metadata
            }).catch(err => console.error('Failed to log question display:', err));
        }
    }, [item, perseusItems, loading, user_id]);

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
            setStartTime(Date.now()); // Reset timer for next question
            return index;
        });
    };


    const handleSubmit = async () => {
        if (rendererRef.current) {
            const userInput = rendererRef.current.getUserInput();
            const question = perseusItem.question;
            const score = scorePerseusItem(question, userInput, "en");

            // Continue to include an empty guess for the now defunct answer area.
            const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
            const keScore = keScoreFromPerseusScore(score, maxCompatGuess, rendererRef.current.getSerializedState().question);

            // Calculate response time
            const responseTimeSeconds = (Date.now() - startTime) / 1000;

            // Get metadata for use in both API calls
            const currentItem = perseusItems[item];
            const metadata = (currentItem as any).dash_metadata || {};

            // Submit answer to DASH API for tracking and adaptive difficulty
            try {
                const answerData = {
                    question_id: metadata.dash_question_id || `q_${item}`,
                    skill_ids: metadata.skill_ids || ["counting_1_10"],
                    is_correct: keScore.correct,
                    response_time_seconds: responseTimeSeconds
                };

                const token = jwtUtils.getToken();
                if (!token) {
                    console.error("No authentication token");
                    return;
                }

                const response = await apiUtils.post(`${DASH_API_URL}/api/submit-answer`, answerData);

                const result = await response.json();
                console.log("Answer submitted to DASH:", result);
            } catch (error) {
                console.error("Failed to submit answer to DASH:", error);
            }

            // Display score to user
            setIsAnswered(true);
            setScore(keScore);
            console.log("Score:", keScore);

            // Record question answer with TeachingAssistant
            try {
                const questionId = metadata.dash_question_id || `q_${item}_${Date.now()}`;
                const token = jwtUtils.getToken();
                if (token) {
                    fetch(`${TEACHING_ASSISTANT_API_URL}/question/answered`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            question_id: questionId,
                            is_correct: keScore.correct || false,
                        }),
                    }).catch((error) => {
                        console.error('Failed to record question answer to TeachingAssistant:', error);
                    });
                }
            } catch (error) {
                console.error('Error recording question answer:', error);
            }
        }
    };

    const perseusItem = perseusItems[item] || {};

    return (
            <div className="framework-perseus">
                <div style={{ padding: "20px" }}>
                    {/* User Info Display (Age from MongoDB) */}
                    <div className="mb-6 p-4 bg-gray-100 rounded-lg border border-gray-300">
                        <div className="flex items-center gap-4">
                            <span className="font-semibold text-gray-700">
                                User: {user_id}
                            </span>
                            <span className="text-sm text-gray-600 italic">
                                {loading ? "Loading questions..." : `${perseusItems.length} questions loaded`}
                            </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                            💡 Age and grade are loaded from MongoDB based on user profile.
                        </p>
                    </div>

                    <button
                        onClick={handleNext}
                        className="absolute top-19 right-8 bg-black rounded 
                            text-white p-2">Next</button>
                            
                    {endOfTest ? (
                        <p>You've successfully completed your test!</p>
                    ): (
                        perseusItems.length > 0 ? (
                        <div>
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
                            {isAnswered && <div 
                                className="flex justify-between mt-9">
                                    <span className={score?.correct ? "text-green-400 italic" : "text-red-400 italic"}>
                                        {score?.correct ?(<p>Correct Answer!</p>):(<p>Wrong Answer.</p>)}
                                    </span>
                            </div>}
                        </div>
                        ) : (
                            <p>Loading...</p>
                        )
                    )}
                    <button 
                        className="bg-blue-500 absolute rounded text-white p-2 right-8 mt-8"
                        onClick={handleSubmit}>
                        Submit
                    </button>
                </div>
            </div>
    );
};

export default RendererComponent;
