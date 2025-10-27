import { useState, useEffect } from "react";
import {ServerItemRenderer} from "../../package/perseus/src/server-item-renderer";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";
import { useParams } from "react-router-dom"

// a component that allows viewing current json on screen
// import { useState } from 'react';

function QuestionValidationComponent() {
    const [viewJSON, setViewJSON] = useState(false);
    const [perseusItem, setPerseusItem] = useState<any>(null);
    const [item, setItem] = useState(0);
    const [loading, setLoading] = useState(true);
    const [endOfTest, setEndOfTest] = useState(false);
    const [isGenerated, setIsGenerated] = useState(false);
    const [generatedItems, setGeneratedItems] = useState<{}>();
    const [itemMetadata, setItemMetadata] = useState<{}>();
    const { id } = useParams<{id:string}>();

    useEffect(() => {
        fetch(`http://localhost:8001/api/generated-questions/${id}`)
            .then(response => response.json())
            .then((data) => {
                console.log("API response:", data);
                setPerseusItem(data.question);
                setGeneratedItems(data.generated);
                setItemMetadata(data.metadata)
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch questions:", err);
                setLoading(false);
            });
    }, [])

    // const perseusItem = perseusItems && perseusItems.length > 0 ? perseusItems[item]: {};


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
            if (!perseusItem || index >= perseusItem.length) {
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
                                {perseusItem && perseusItem.length > 0 ? (
                                    <div>
                                        <div className="text-zinc-300">
                                            {
                                                isGenerated ?
                                                (
                                                    <div>
                                                        <p>Generated</p>
                                                        {/* <p className="italic">Path: {perseusItem.metadata.generated_file_path}</p> */}
                                                    </div>
                                                )   :   (
                                                    <div>
                                                        <p>Source</p>
                                                        {/* <p className="italic">Path: {perseusItem.metadata.source_file_path}</p> */}
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
                    {viewJSON && <JSONViewer data={isGenerated ? perseusItem.generated : perseusItem.source} perseusItem={perseusItem} />}
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
export default QuestionValidationComponent

interface JSONViewerProps {
    data: any;
    perseusItem: any;
    onDataChange?: (newData: any) => void;
}

const JSONViewer: React.FC<JSONViewerProps> = ({ data, perseusItem, onDataChange }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editedContent, setEditedContent] = useState(JSON.stringify(data, null, 2));

    const handleSave = () => {
        try {
            const parsedData = JSON.parse(editedContent);
            onDataChange?.(parsedData);
            setIsEditing(false);

            fetch("http://localhost:8001/api/regenerate-from-data", {
                method: "POST",
            }).then(() => console.log("Saved successfully"));
        } catch (error) {
            alert("Invalid JSON format");
        }
    }; // <-- FIXED: properly closed handleSave

    const handleCancel = () => {
        setEditedContent(JSON.stringify(data, null, 2));
        setIsEditing(false);
    };

    if (isEditing) {
        return (
            <div className="space-y-2">
                <textarea
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="w-full h-[900px] bg-gray-900 text-white p-4 rounded-lg font-mono text-sm resize-none"
                    spellCheck={false}
                />
                <div className="flex gap-2">
                    <button
                        onClick={handleSave}
                        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                    >
                        Save
                    </button>
                    <button
                        onClick={handleCancel}
                        className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <pre
                className="bg-gray-900 text-white p-4 rounded-lg overflow-y-scroll max-h-[900px] cursor-text"
                onClick={() => setIsEditing(true)}
            >
                {JSON.stringify(data, null, 2)}
            </pre>
            <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
                Edit JSON
            </button>
        </div>
    );
}; 

export { JSONViewer };