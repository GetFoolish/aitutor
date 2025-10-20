import { useState, useEffect } from "react";
import {ServerItemRenderer} from "../../package/perseus/src/server-item-renderer";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";

// a component that allows viewing current json on screen
const JSONViewer = ({ data }: { data: any }) => {
    return (
        <pre className="bg-gray-900 text-white p-4 rounded-lg overflow-y-scroll max-h-[900px]">
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
    }, [])

    const perseusItem = perseusItems[item] || {};


    const handleSave = () => {
        fetch('http://localhost:8001/api/save-validated-question', {
            method: 'POST',
            headers: { "content-type": "application/json" },
            body: JSON.stringify(perseusItem.generated),
        })
        .then((response) => {   })
        .catch((err) => {
            console.error("Failed to save validated question:", err);
        });   
    }   

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
        <div className="bg-[#f0f0f0] min-h-[100vh] h-fit w-[100vw] flex flex-col items-center">
            <h1 className="text-center font-bold m-4">Question Validation</h1>
            <div className="flex w-[100vw] justify-between items-start relative p-6">
                <div className="w-[84vw] text-black border rounded-2xl p-4 bg-white mb-4">
                    <div className="framework-perseus">
                        <div style={{ padding: "20px" }}>
                                {perseusItems && perseusItems.length > 0 ? (
                                    <div>
                                        <div className="text-zinc-300">
                                            {
                                                isGenerated ?
                                                (
                                                    <div>
                                                        <p>Generated</p>
                                                        <p className="italic">Path: {perseusItem.metadata.generated_file_path}</p>
                                                    </div>
                                                )   :   (
                                                    <div>
                                                        <p>Source</p>
                                                        <p className="italic">Path: {perseusItem.metadata.source_file_path}</p>
                                                    </div>
                                                )
                                            }
                                        </div>
                                
                                        <PerseusI18nContextProvider locale="en" strings={mockStrings}>
                                                <ServerItemRenderer
                                                    problemNum={0}
                                                    item={isGenerated == true ? perseusItem.generated : perseusItem.source}
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
                    {viewJSON && <JSONViewer data={isGenerated ? perseusItem.generated : perseusItem.source} />}
                </div>
                <div className="flex flex-col w-[154px] gap-2">
                    <button
                        onClick={handleNext}
                        className="top-19 bg-gray-500 rounded 
                            text-white p-2">Next
                    </button>
                    <button 
                        className={`${isGenerated == true? "bg-amber-500 text-[white]" : "bg-white text-amber-500" } rounded p-2 border-2 border-amber-500`} 
                        onClick={() => setIsGenerated((prev) => !prev)}>
                            {isGenerated == true ? (<p>See Source</p>) : (<p>See Generated</p>)}
                    </button>
                    <button 
                        className="bg-emerald-500 rounded text-white p-2"
                        onClick={handleSave}>
                        Validate
                    </button>
                    <button 
                        className="bg-black rounded text-white p-2 mt-[53vh]"
                        onClick={() => setViewJSON((prev) => !prev)}>
                        Validate JSON
                    </button>
                </div>
            </div>
        </div>
    );
};