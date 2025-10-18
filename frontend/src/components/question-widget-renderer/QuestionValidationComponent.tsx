import { useState, useEffect } from "react";
import {ServerItemRenderer} from "../../package/perseus/src/server-item-renderer";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";

// a component that allows viewing current json on screen
const JSONViewer = ({ data }: { data: any }) => {
    return (
        <pre className="bg-gray-900 text-white p-4 rounded-lg overflow-auto max-h-[400px]">
            {JSON.stringify(data, null, 2)}
        </pre>
    );
};

export default function QuestionValidationComponent() {
    const [viewJSON, setViewJSON] = useState(false);
    const [perseusItems, setPerseusItems] = useState<any>(null);
    const [item, setItem] = useState(0);
    const [loading, setLoading] = useState(true);
    const [endOfTest, setEndOfTest] = useState(false);
    const [isGenerated, setIsGenerated] = useState(false);

    console.log("End of test:");
    useEffect(() => {
        fetch('http://localhost:8001/api/generated-questions/50')
            .then(response => response.json())
            .then((data) => {
                console.log("API response:", data);
                setPerseusItems(data);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch questions:", err);
                setLoading(false);
            });
    })

    const perseusItem = perseusItems && perseusItems.length > 0 ? perseusItems[item] : {};

    const handleNext = () => {
        setItem((prev) => {
            const index = prev + 1;
            if (!perseusItems || index >= perseusItems.length) {
                setEndOfTest(true);
                return prev; // stay at last valid index
            }
            return index;
        });
    };

    return (
        <div className="bg-[#f0f0f0] h-[100vh] w-[100vw] text-white p-4 flex flex-col items-center">
            <h1>Question Validation</h1>
            <div className="h-[100vh] w-[80vw] text-black border rounded-2xl p-4 bg-white overflow-y-scroll mb-4">
                <div className="framework-perseus">
                    <div style={{ padding: "20px" }}>
                        <button
                            onClick={handleNext}
                            className="absolute top-19 right-8 bg-red-500 rounded 
                                text-white p-2">Next
                        </button>
                        <button onClick={(prev) => setIsGenerated(!prev)}>
                            {isGenerated == true ? (<p>View Source</p>) : (<p>View Generated</p>)}
                        </button>
                            {perseusItems && perseusItems.length > 0 ? (
                                <div>
                                    <div className="text-zinc-300">
                                        {
                                            isGenerated ?
                                            (<p>Generated</p>) :
                                            (<p>Source</p>)
                                        }
                                    </div>
                                    <PerseusI18nContextProvider locale="en" strings={mockStrings}>
                                            <ServerItemRenderer
                                                problemNum={0}
                                                item={isGenerated ? perseusItem.generated : perseusItem.source}
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
                                    </PerseusI18nContextProvider>
                                </div>
                            ) : (
                                <p>Loading...</p>
                            )}
                    </div>
                </div>
                {viewJSON && <JSONViewer data={perseusItem} />}
            </div>
            <button className="bg-blue-500 rounded text-white p-2"
                onClick={() => setViewJSON(!viewJSON)}>
                View JSON
            </button>
        </div>
    );
};