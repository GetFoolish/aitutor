import { useState, useEffect } from "react";
import {ServerItemRenderer} from "../../package/perseus/src/server-item-renderer";
import { storybookDependenciesV2 } from "../../package/perseus/testing/test-dependencies";
import { PerseusI18nContextProvider } from "../../package/perseus/src/components/i18n-context";
import { mockStrings } from "../../package/perseus/src/strings";
import { useParams, useHistory } from "react-router-dom"
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
    const [itemMetadata, setItemMetadata] = useState<{ source_question_id?: string } | undefined>();
    const { id } = useParams<{id:string}>();
    const history = useHistory();

    const fetchQuestion = (questionId?: string, updateRoute: boolean = false) => {
        setLoading(true);
        const url = questionId 
            ? `http://localhost:8001/api/get-question-for-validation?question_id=${questionId}`
            : `http://localhost:8001/api/get-question-for-validation`;
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                console.log("API response:", data);
                if (!data.question) {
                    throw new Error("No question data in response");
                }
                setOriginalQuestion(data.question); // Store the original question
                setItemMetadata(data.metadata);

                const normalizedGenerated = (data.generated || []).map((item: any) => {
                    if (item.id && !item._id) {
                        return {
                            ...item,
                            _id: typeof item.id === "object" ? item.id.toString() : item.id,
                        };
                    }
                    return item;
                });

                setGeneratedItems(normalizedGenerated);
                setGeneratedIndex(0);
                setIsGenerated(false);
                setPerseusItem(data.question); // Default to original question first
                setLoading(false);
                
                if (updateRoute && data.metadata?.source_question_id) {
                    history.replace(`/admin/question-validation/${data.metadata.source_question_id}`);
                }

                console.log("Generated Items on fetch:", normalizedGenerated);
                console.log("Generated Items Length on fetch:", normalizedGenerated.length);
            })
            .catch((err) => {
                console.error("Failed to fetch questions:", err);
                alert(`Error loading question: ${err.message}. Check console for details.`);
                setLoading(false);
            });
    };

    useEffect(() => { 
        fetchQuestion(id);
    }, [id])

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
        // Fetch a new random question without leaving the page
        fetchQuestion(undefined, true);
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
                        className="bg-green-600 rounded text-white p-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
                        onClick={async () => {
                            console.log("=== APPROVE BUTTON CLICKED ===");
                            console.log("isGenerated:", isGenerated);
                            console.log("generatedIndex:", generatedIndex);
                            console.log("generatedItems:", generatedItems);
                            console.log("generatedItems[generatedIndex]:", generatedItems[generatedIndex]);
                            console.log("generatedItems[generatedIndex]._id:", generatedItems[generatedIndex]?._id);
                            if (!isGenerated) {
                                alert("Please click 'See Generated' first to view a generated question.");
                                return;
                            }
                            if (!generatedItems[generatedIndex] || !generatedItems[generatedIndex]._id) {
                                alert("No generated question selected. Make sure you're viewing a generated question.");
                                return;
                            }
                            
                            const generatedId = generatedItems[generatedIndex]._id;
                            console.log("Approving question:", generatedId);
                            
                            try {
                                const response = await fetch(`http://localhost:8001/api/approve-question/${generatedId}`, {
                                    method: 'POST',
                                    headers: { "content-type": "application/json" },
                                });
                                
                                if (!response.ok) {
                                    const errorText = await response.text();
                                    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
                                }
                                
                                const data = await response.json();
                                console.log("Approval successful:", data);
                                alert("Question approved successfully!");
                                
                                // Remove the approved item from the list
                                const updatedItems = generatedItems.filter((_, idx) => idx !== generatedIndex);
                                setGeneratedItems(updatedItems);
                                
                                // If no more generated items, go back to list
                                if (updatedItems.length === 0) {
                                    // Go back to list to see updated counts
                                    history.push("/admin/question-validation", {
                                        recentAction: "approved",
                                        questionId: (itemMetadata?.source_question_id ?? id),
                                    });
                                } else {
                                    // Show the next generated item (or first if we were on the last one)
                                    const nextIndex = generatedIndex < updatedItems.length ? generatedIndex : 0;
                                    setGeneratedIndex(nextIndex);
                                    const nextItem = { ...updatedItems[nextIndex] };
                                    delete nextItem._id;
                                    setPerseusItem(nextItem);
                                }
                            } catch (error: any) {
                                console.error("Failed to approve question:", error);
                                alert(`Failed to approve question: ${error.message || error}`);
                            }
                        }}
                        disabled={!isGenerated || !generatedItems[generatedIndex] || !generatedItems[generatedIndex]._id}
                        title={!isGenerated ? "Click 'See Generated' first" : (!generatedItems[generatedIndex]?._id ? "No generated question ID" : "Approve this question")}>
                        Approve
                    </button>
                    <button 
                        className="bg-red-600 rounded text-white p-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
                        onClick={async () => {
                            console.log("=== REJECT BUTTON CLICKED ===");
                            console.log("isGenerated:", isGenerated);
                            console.log("generatedIndex:", generatedIndex);
                            console.log("generatedItems:", generatedItems);
                            console.log("generatedItems[generatedIndex]:", generatedItems[generatedIndex]);
                            console.log("generatedItems[generatedIndex]._id:", generatedItems[generatedIndex]?._id);
                            if (!isGenerated) {
                                alert("Please click 'See Generated' first to view a generated question.");
                                return;
                            }
                            if (!generatedItems[generatedIndex] || !generatedItems[generatedIndex]._id) {
                                alert("No generated question selected. Make sure you're viewing a generated question.");
                                return;
                            }
                            
                            if (!window.confirm("Are you sure you want to reject and delete this question?")) {
                                return;
                            }
                            
                            const generatedId = generatedItems[generatedIndex]._id;
                            console.log("Rejecting question:", generatedId);
                            
                            try {
                                const response = await fetch(`http://localhost:8001/api/reject-question/${generatedId}`, {
                                    method: 'POST',
                                    headers: { "content-type": "application/json" },
                                });
                                
                                if (!response.ok) {
                                    const errorText = await response.text();
                                    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
                                }
                                
                                const data = await response.json();
                                console.log("Rejection successful:", data);
                                alert("Question rejected and deleted successfully!");
                                
                                // Remove the rejected item from the list
                                const updatedItems = generatedItems.filter((_, idx) => idx !== generatedIndex);
                                setGeneratedItems(updatedItems);
                                
                                // Always go back to list after reject to see updated counts
                                // This ensures the list refreshes and shows correct data
                                history.push("/admin/question-validation", {
                                    recentAction: "rejected",
                                    questionId: (itemMetadata?.source_question_id ?? id),
                                });
                            } catch (error: any) {
                                console.error("Failed to reject question:", error);
                                alert(`Failed to reject question: ${error.message || error}`);
                            }
                        }}
                        disabled={!isGenerated || !generatedItems[generatedIndex] || !generatedItems[generatedIndex]._id}
                        title={!isGenerated ? "Click 'See Generated' first" : (!generatedItems[generatedIndex]?._id ? "No generated question ID" : "Reject this question")}>
                        Reject
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
