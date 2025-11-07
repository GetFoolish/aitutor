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

const RendererComponent = () => {
    const { user } = useAuth();
    const [perseusItem, setPerseusItem] = useState<PerseusItem | null>(null);
    const [questionId, setQuestionId] = useState<string>("");
    const [skillIds, setSkillIds] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [score, setScore] = useState<KEScore>();
    const [isAnswered, setIsAnswered] = useState(false);
    const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());
    const rendererRef = useRef<ServerItemRenderer>(null);

    // Fetch next question from DASH system
    const fetchNextQuestion = async () => {
        if (!user?.user_id) {
            console.error("No user_id available");
            return;
        }

        setLoading(true);
        setIsAnswered(false);

        try {
            const response = await fetch(`http://localhost:8000/next-question/${user.user_id}`);
            const data = await response.json();

            console.log("[DASH] Received question:", data);

            setQuestionId(data.question_id);
            setSkillIds(data.skill_ids);
            setPerseusItem(data.content);
            setQuestionStartTime(Date.now());
            setLoading(false);
        } catch (err) {
            console.error("[DASH] Failed to fetch next question:", err);
            setLoading(false);
        }
    };

    // Load first question on mount
    useEffect(() => {
        if (user?.user_id) {
            fetchNextQuestion();
        }
    }, [user?.user_id]);

    const handleNext = () => {
        // Fetch next question dynamically from DASH system
        fetchNextQuestion();
    };

    const handleSubmit = async () => {
        if (!rendererRef.current || !perseusItem || !user?.user_id) return;

        const userInput = rendererRef.current.getUserInput();
        const question = perseusItem.question;
        const scoreResult = scorePerseusItem(question, userInput, "en");

        // Continue to include an empty guess for the now defunct answer area.
        const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
        const keScore = keScoreFromPerseusScore(scoreResult, maxCompatGuess, rendererRef.current.getSerializedState().question);

        // Calculate response time for spaced repetition
        const responseTimeSeconds = (Date.now() - questionStartTime) / 1000;

        // Update local state
        setIsAnswered(true);
        setScore(keScore);
        console.log("[DASH] Score:", keScore);

        // Submit answer to DASH system for memory strength tracking
        try {
            const response = await fetch(`http://localhost:8000/submit-answer/${user.user_id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question_id: questionId,
                    skill_ids: skillIds,
                    is_correct: keScore.correct || false,
                    response_time_seconds: responseTimeSeconds,
                }),
            });

            const result = await response.json();
            console.log("[DASH] Answer submitted:", result);

            // Log skill updates for debugging
            if (result.skill_details) {
                result.skill_details.forEach((skill: any) => {
                    console.log(`[DASH] Skill ${skill.name}: memory_strength = ${skill.memory_strength.toFixed(3)}`);
                });
            }
        } catch (err) {
            console.error("[DASH] Failed to submit answer:", err);
        }
    };

    return (
            <div className="framework-perseus">
                <div style={{ padding: "20px", position: "relative", minHeight: "500px" }}>
                    {loading ? (
                        <p style={{ color: "#000000", fontSize: "16px" }}>Loading next question...</p>
                    ) : perseusItem ? (
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

                            {/* Answer feedback */}
                            {isAnswered && <div style={{ marginTop: "20px", padding: "10px", borderRadius: "8px", backgroundColor: score?.correct ? "#d4edda" : "#f8d7da" }}>
                                <span style={{ color: score?.correct ? "#155724" : "#721c24", fontWeight: "bold", fontSize: "16px" }}>
                                    {score?.correct ? "✓ Correct Answer!" : "✗ Wrong Answer"}
                                </span>
                            </div>}

                            {/* Action buttons */}
                            <div style={{
                                display: "flex",
                                gap: "12px",
                                marginTop: "24px",
                                justifyContent: "flex-end"
                            }}>
                                <button
                                    onClick={handleSubmit}
                                    disabled={isAnswered}
                                    style={{
                                        backgroundColor: isAnswered ? "#6c757d" : "#2563EB",
                                        color: "white",
                                        padding: "12px 24px",
                                        borderRadius: "8px",
                                        border: "none",
                                        fontSize: "16px",
                                        fontWeight: "600",
                                        cursor: isAnswered ? "not-allowed" : "pointer",
                                        opacity: isAnswered ? 0.6 : 1
                                    }}>
                                    Submit Answer
                                </button>
                                <button
                                    onClick={handleNext}
                                    disabled={!isAnswered}
                                    style={{
                                        backgroundColor: !isAnswered ? "#6c757d" : "#000000",
                                        color: "white",
                                        padding: "12px 24px",
                                        borderRadius: "8px",
                                        border: "none",
                                        fontSize: "16px",
                                        fontWeight: "600",
                                        cursor: !isAnswered ? "not-allowed" : "pointer",
                                        opacity: !isAnswered ? 0.6 : 1
                                    }}>
                                    Next Question →
                                </button>
                            </div>
                        </div>
                    ) : (
                        <p style={{ color: "#000000", fontSize: "16px" }}>No question available</p>
                    )}
                </div>
            </div>
    );
};

export default RendererComponent;
