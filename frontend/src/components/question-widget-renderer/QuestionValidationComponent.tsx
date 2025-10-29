import { useState, useEffect } from "react";
import {ServerItemRenderer} from "../../package/perseus/src/server-item-renderer";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";
import { useParams } from "react-router-dom"
import { FaArrowRight } from "react-icons/fa"; // Importing a suitable icon

// a component that allows viewing current json on screen
// import { useState } from 'react';

function QuestionValidationComponent() {
    const [viewJSON, setViewJSON] = useState(false);
    const [originalQuestion, setOriginalQuestion] = useState<any>(null);
    const [perseusItem, setPerseusItem] = useState<any>(null); // This will hold the currently displayed item (original or generated)
    const [generatedItems, setGeneratedItems] = useState<any[]>([]);
    const [generatedIndex, setGeneratedIndex] = useState(0); // Index for navigating generated items
    const [loading, setLoading] = useState(true);
    const [isGenerated, setIsGenerated] = useState(false); // Controls whether generated items are shown
    const [itemMetadata, setItemMetadata] = useState<{}>();
    const { id } = useParams<{id:string}>();

    useEffect(() => { 
        fetch(`http://localhost:8001/api/get-question-for-validation`)
            .then(response => response.json())
            .then((data) => {
                console.log("API response:", data);
                setOriginalQuestion(data.question); // Store the original question
                setPerseusItem(data.question); // Initially display the original question
                setGeneratedItems(data.generated);
                setItemMetadata(data.metadata);
                setLoading(false);
                console.log("Generated Items on fetch:", data.generated); // Debugging line
                console.log("Generated Items Length on fetch:", data.generated ? data.generated.length : 0); // Debugging line
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
        setLoading(true);
        setIsGenerated(false); // Reset to show original question
        setGeneratedIndex(0); // Reset generated index

        fetch(`http://localhost:8001/api/get-question-for-validation`)
            .then(response => response.json())
            .then((data) => {
                console.log("API response:", data);
                setOriginalQuestion(data.question);
                setPerseusItem(data.question);
                setGeneratedItems(data.generated);
                setItemMetadata(data.metadata);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch questions:", err);
                setLoading(false);
            });
    };

    const handleNextGenerated = () => {
        if (generatedIndex + 1 < generatedItems.length) {
            const nextIndex = generatedIndex + 1;
            setGeneratedIndex(nextIndex);
            setPerseusItem(generatedItems[nextIndex]);
        } else {
            // Optionally, loop back to the first generated item or show an end message
            setGeneratedIndex(0);
            setPerseusItem(generatedItems[0]);
        }
    };

    console.log(isGenerated)


    return (
        <div className="bg-[#f0f0f0] min-h-[100vh] h-fit w-[100vw] flex flex-col items-center">
            <h1 className="text-center font-bold m-4">Question Validation</h1>
            <div className="flex w-[100vw] justify-between items-start relative p-6">
                <div className="w-[84vw] text-black border rounded-2xl p-4 bg-white mb-4">
                    <div className="framework-perseus">
                        <div style={{ padding: "20px" }}>
                                {perseusItem ? (
                                    <div>
                                        <div className="flex justify-between items-center" >
                                            <div className="text-zinc-300">
                                                {
                                                    isGenerated ?
                                                    (
                                                        <div>
                                                            <p>Generated (ID)</p>
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
                                            {generatedItems.length > 1 && isGenerated && (
                                                <button
                                                    className="flex items-center gap-2 p-2 rounded text-zinc-300 mb-4"
                                                    onClick={handleNextGenerated}
                                                    disabled={!isGenerated || generatedItems.length === 0}>
                                                    
                                                        next <FaArrowRight />
                                                </button>
                                            )}
                                    
                                        </div>
                                        <PerseusI18nContextProvider locale="en" strings={mockStrings}>
                                            <ServerItemRenderer
                                                problemNum={0}
                                                item={perseusItem} // perseusItem now holds the correct item
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
                    {viewJSON && <JSONViewer data={isGenerated ? perseusItem : originalQuestion} perseusItem={perseusItem} />}
                </div>
                <div className="flex flex-col w-[154px] gap-2">
                    <button
                        onClick={handleNext}
                        className="top-19 bg-gray-500 rounded 
                            text-white p-2">Next (Source)
                    </button>
                    <button 
                        className={`${isGenerated ? "bg-amber-500 text-[white]" : "bg-white text-amber-500" } rounded p-2 border-2 border-amber-500`} 
                        onClick={() => {
                            setIsGenerated((prev) => {
                                const newState = !prev;
                                if (newState) {
                                    // Switched to generated, display the current generated item
                                    const generatedItem = generatedItems[generatedIndex] ? { ...generatedItems[generatedIndex] } : null;
                                    if (generatedItem) {
                                        
                                        delete generatedItem._id; // Remove _id for rendering
                                    }
                                    setPerseusItem(generatedItem);
                                } else {
                                    // Switched to source, display the original question
                                    setPerseusItem(originalQuestion);
                                }
                                return newState;
                            });
                        }}>
                            {isGenerated ? (<p>See Source</p>) : (<p>See Generated</p>)}
                    </button>
                    <button 
                        className="bg-green-600 rounded text-white p-2"
                        onClick={async () => {
                            if (isGenerated && perseusItem && generatedItems[generatedIndex] && generatedItems[generatedIndex]._id) {
                                try {
                                    const response = await fetch(`http://localhost:8001/api/approve-question/${generatedItems[generatedIndex]._id}`, {
                                        method: 'POST',
                                        headers: { "content-type": "application/json" },
                                    });
                                    if (!response.ok) {
                                        throw new Error(`HTTP error! status: ${response.status}`);
                                    }
                                    const data = await response.json();
                                    console.log("Approval successful:", data);
                                    alert("Question approved successfully!");
                                    // Optionally, fetch next question or update UI
                                    handleNext(); // Move to the next question after approval
                                } catch (error) {
                                    console.error("Failed to approve question:", error);
                                    alert("Failed to approve question.");
                                }
                            } else {
                                alert("Please select a generated question to approve.");
                            }
                        }}
                        disabled={!isGenerated || !generatedItems[generatedIndex] || !generatedItems[generatedIndex]._id}>
                        Approve
                    </button>
                    <button 
                        className="bg-black rounded text-white p-2 "
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
