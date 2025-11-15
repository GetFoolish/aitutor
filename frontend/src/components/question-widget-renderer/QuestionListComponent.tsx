import { useState, useEffect } from "react";
import { useHistory, useLocation } from "react-router-dom";

interface QuestionItem {
    _id: string;
    source: string;
    generated_count: number;
    created_at: string;
    generated: Array<{
        _id: string;
        created_at: string;
        generation_cost?: number;
    }>;
}

function QuestionListComponent() {
    const [questions, setQuestions] = useState<QuestionItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [sortBy, setSortBy] = useState<"created_at" | "generated_count">("created_at");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
    const history = useHistory();
    const location = useLocation<{ recentAction?: string; questionId?: string }>();
    const [actionMessage, setActionMessage] = useState<string | null>(null);

    useEffect(() => {
        fetchQuestions();
    }, [sortBy, sortOrder]);

    // Refresh when component mounts or when navigating back from validation page
    useEffect(() => {
        // Refresh immediately when component mounts
        fetchQuestions();
        
        const handleFocus = () => {
            fetchQuestions();
        };
        window.addEventListener('focus', handleFocus);
        
        const handleVisibilityChange = () => {
            if (!document.hidden) {
                fetchQuestions();
            }
        };
        document.addEventListener('visibilitychange', handleVisibilityChange);
        
        // Listen for navigation events (when user comes back from validation page)
        const unlisten = history.listen(() => {
            fetchQuestions();
        });
        
        return () => {
            window.removeEventListener('focus', handleFocus);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            unlisten();
        };
    }, [history]);

    // Show gentle message when redirected back after approve/reject
    useEffect(() => {
        if (location.state && (location.state.recentAction || location.state.questionId)) {
            const action = location.state.recentAction === "approved" ? "approved" : "rejected";
            const questionId = location.state.questionId ? `${location.state.questionId.substring(0, 8)}...` : "this question";
            setActionMessage(
                `Question ${questionId} was ${action}. If it no longer appears here, it means there are no more pending versions of that question.`
            );
            history.replace({
                pathname: history.location.pathname,
                search: history.location.search,
                state: undefined,
            });
        } else {
            setActionMessage(null);
        }
    }, [location.state, history]);

    const fetchQuestions = async () => {
        setLoading(true);
        try {
            const response = await fetch(
                `http://localhost:8001/api/get-questions-pending-approval?sort_by=${sortBy}&order=${sortOrder}`
            );
            const data = await response.json();
            setQuestions(data);
        } catch (error) {
            console.error("Failed to fetch questions:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleQuestionClick = (questionId: string) => {
        history.push(`/admin/question-validation/${questionId}`);
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleString();
    };

    return (
        <div className="bg-[#f0f0f0] min-h-[100vh] h-fit w-[100vw] flex flex-col items-center p-6">
            <h1 className="text-center font-bold m-4 text-2xl">Questions Pending Approval</h1>
            {actionMessage && (
                <div className="w-full max-w-6xl mb-4 p-3 bg-blue-50 border border-blue-200 text-blue-900 rounded text-sm">
                    {actionMessage} Need more questions? Run the generator script to create new pending items.
                </div>
            )}
            <div className="w-full max-w-6xl bg-white rounded-lg shadow-lg p-6">
                {/* Sort Controls */}
                <div className="flex gap-4 mb-4 items-center">
                    <label className="font-semibold">Sort by:</label>
                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as "created_at" | "generated_count")}
                        className="border rounded px-3 py-1"
                    >
                        <option value="created_at">Generation Time</option>
                        <option value="generated_count">Generated Count</option>
                    </select>
                    
                    <label className="font-semibold ml-4">Order:</label>
                    <select
                        value={sortOrder}
                        onChange={(e) => setSortOrder(e.target.value as "asc" | "desc")}
                        className="border rounded px-3 py-1"
                    >
                        <option value="desc">Descending</option>
                        <option value="asc">Ascending</option>
                    </select>
                    
                    <button
                        onClick={fetchQuestions}
                        className="ml-auto bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                    >
                        Refresh
                    </button>
                </div>

                {loading ? (
                    <div className="text-center py-8">Loading...</div>
                ) : questions.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        No questions pending approval
                    </div>
                ) : (
                    <div className="space-y-4">
                        {questions
                            .filter(q => q._id && q.generated_count !== undefined) // Filter out invalid questions
                            .map((question) => (
                            <div
                                key={question._id}
                                onClick={() => handleQuestionClick(question._id)}
                                className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                            >
                                <div className="flex justify-between items-start">
                                    <div className="flex-1">
                                        <div className="font-semibold text-lg mb-2">
                                            Question ID: {question._id ? question._id.substring(0, 8) + "..." : "N/A"}
                                        </div>
                                        <div className="text-sm text-gray-600 space-y-1">
                                            <div>Source: {question.source || "khan"}</div>
                                            <div>Pending Generated: {question.generated_count ?? 0}</div>
                                            <div>Created: {question.created_at ? formatDate(question.created_at) : "N/A"}</div>
                                            <div>Pending Approvals: {question.generated_count ?? 0}</div>
                                            {question.generated.length > 0 && question.generated[0].generation_cost && (
                                                <div>
                                                    Total Cost: ${question.generated.reduce((sum, g) => sum + (g.generation_cost || 0), 0).toFixed(4)}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    <div className="text-blue-500 font-semibold">
                                        View →
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

export default QuestionListComponent;

