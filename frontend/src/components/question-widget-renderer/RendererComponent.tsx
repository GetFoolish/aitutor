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
import { useParams } from "react-router-dom"
import { NULL } from "sass"; 

const RendererComponent = () => {
    const [perseusItem, setPerseusItem] = useState<PerseusItem | null>();
    const [perseusItems, setPerseusItems] = useState<PerseusItem[]>([]);
    const [index, setIndex] = useState(1);
    const [loading, setLoading] = useState(true);
    const [endOfTest, setEndOfTest] = useState(false);
    const [score, setScore] = useState<KEScore>();
    const [isAnswered, setIsAnswered] = useState(false);
    const rendererRef = useRef<ServerItemRenderer>(null);
    const { id } = useParams<{id?: string}>();


    useEffect(() => {
        const url = id ? `http://localhost:8001/api/question/${id}` : "http://localhost:8001/api/questions/10";
        fetch(url)
            .then((response) => response.json())
            .then((data) => {
                console.log("API response:", data);
                if (Array.isArray(data)){
                    setPerseusItems(data)
                    setPerseusItem(data[0])
                } else {
                    setPerseusItem(data)
                }
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch questions:", err);
                setLoading(false);
            });
    }, []);

    const handleNext = () => {
        if (index + 1 >= perseusItems.length) {
            setEndOfTest(true);
            setPerseusItem(null);
        } else {
            const item = perseusItems[index + 1];
            setPerseusItem(item);
            setIsAnswered(false);
            setIndex((prev) => prev + 1);
        }
    };


    const handleSubmit = () => {
        if (!rendererRef.current || !perseusItem) {
            console.warn("Renderer not ready or no item to submit.");
            return;
        }
        const userInput = rendererRef.current.getUserInput();
        const question = perseusItem.question; // perseusItem is guaranteed not null here
        const score = scorePerseusItem(question, userInput, "en");

        // Continue to include an empty guess for the now defunct answer area.
        const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
        const keScore = keScoreFromPerseusScore(score, maxCompatGuess, rendererRef.current.getSerializedState().question);

        // return score for the given question 
        setIsAnswered(true);
        setScore(keScore);
        console.log("Score:", keScore);
    };
    
    return (
            <div className="framework-perseus">
                <div style={{ padding: "20px" }}>
                    <button
                        onClick={handleNext}
                        className="absolute top-19 right-8 bg-black rounded 
                            text-white p-2">Next</button>
                            
                    {endOfTest ? (
                        <p>You've successfully completed your test!</p>
                    ): (
                        loading == false ? (
                        <div>
                            {perseusItem ? ( // Conditionally render ServerItemRenderer
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
                            ) : (
                                <p>No question available.</p> // Or some other placeholder
                            )}
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
                        className="bg-blue-500 absolute rounded text-white p-2 right-8 t0p-[60vh]"
                        onClick={handleSubmit}>
                        Submit
                    </button>
                </div>
            </div>
    );
};

export default RendererComponent;
