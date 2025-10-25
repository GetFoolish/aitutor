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

const RendererComponent = () => {
    const [perseusItem, setPerseusItem] = useState<PerseusItem[]>([]);
    const [item, setItem] = useState(0);
    const [loading, setLoading] = useState(true);
    const [endOfTest, setEndOfTest] = useState(false);
    const [score, setScore] = useState<KEScore>();
    const [isAnswered, setIsAnswered] = useState(false);
    const rendererRef = useRef<ServerItemRenderer>(null);

    useEffect(() => {
        fetch("http://localhost:8001/api/question")
            .then((response) => response.json())
            .then((data) => {
                console.log("API response:", data);
                if (!data.finished){
                    setPerseusItem(data.question);
                } else {
                    setEndOfTest(true)
                }
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch questions:", err);
                setLoading(false);
            });

        //     const canvas = document.querySelector('canvas') as HTMLCanvasElement;
        //     if (canvas) {
        //     const dataUrl = canvas.toDataURL('image/png');
        //     console.log(`The Canvas Image: ${dataUrl}`);
            
        //     if (dataUrl) {
        //         const link = document.createElement('a');
        //         const cleanDataUrl = dataUrl.replace(/^data:image\/png;base64,/, "");
        //         link.href = dataUrl; // Use the original dataUrl for href
        //         link.download = 'output.png';
        //         document.body.appendChild(link);
        //         link.click();
        //         document.body.removeChild(link);
        //     }
        // }
  }, []);

    const handleNext = () => {
            fetch("http://localhost:8001/api/question")
                .then((response) => response.json())
                .then((data) => {
                    console.log("API response:", data);
                    if (!data.finished){
                        setPerseusItem(data.question);
                    } else {
                        setEndOfTest(true)
                    }
                })
                .catch((err) => {
                    console.error("Failed to fetch questions:", err);
                    setLoading(false);
                });
            
                setIsAnswered(false);
        };


    const handleSubmit = () => {
        if (rendererRef.current) {
            const userInput = rendererRef.current.getUserInput();
            const question = perseusItem.question;
            const score = scorePerseusItem(question, userInput, "en");

            // Continue to include an empty guess for the now defunct answer area.
            const maxCompatGuess = [rendererRef.current.getUserInputLegacy(), []];
            const keScore = keScoreFromPerseusScore(score, maxCompatGuess, rendererRef.current.getSerializedState().question);

            // return score for the given question 
            setIsAnswered(true);
            setScore(keScore);
            console.log("Score:", keScore);
        }
    };

    // const perseusItem = perseusItems && perseusItems.length > 0 ? perseusItems[item]: {};
    
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