import React from "react";
import cn from "classnames";
import { CheckCircle2, XCircle, Clock, Target } from "lucide-react";
import { useSessionDetail } from "../../hooks/query-hooks/useSessionDetail";

interface SessionDetailViewProps {
    sessionId: string;
}

const formatSkillName = (name: string) => {
    return name
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
};

const formatResponseTime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
};

export default function SessionDetailView({ sessionId }: SessionDetailViewProps) {
    const { data: sessionData, isLoading, error } = useSessionDetail({
        sessionId,
        enabled: !!sessionId,
    });

    if (isLoading) {
        return (
            <div className="px-4 py-3 text-center">
                <div className="text-xs font-bold text-black/70 dark:text-white/70">
                    Loading questions...
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="px-4 py-3 text-center">
                <div className="text-xs font-bold text-red-600 dark:text-red-400">
                    Failed to load session details
                </div>
            </div>
        );
    }

    if (!sessionData || !sessionData.questions || sessionData.questions.length === 0) {
        return (
            <div className="px-4 py-3 text-center">
                <div className="text-xs font-bold text-black/70 dark:text-white/70">
                    No questions found in this session
                </div>
            </div>
        );
    }

    const questions = sessionData.questions;

    return (
        <div className="px-4 pb-4 pt-2">
            <div className="space-y-3">
                {questions.map((question, idx) => (
                    <div
                        key={question.question_id || idx}
                        className={cn(
                            "border-[3px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)] transition-all duration-200",
                            "p-3",
                            question.is_correct
                                ? "bg-[#4ADE80]"
                                : "bg-[#FF6B6B]"
                        )}
                    >
                        {/* Header with correct/incorrect indicator */}
                        <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2">
                                {question.is_correct ? (
                                    <CheckCircle2 className="w-4 h-4 text-black flex-shrink-0" />
                                ) : (
                                    <XCircle className="w-4 h-4 text-white flex-shrink-0" />
                                )}
                                <span className={cn(
                                    "text-[10px] font-black uppercase",
                                    question.is_correct ? "text-black" : "text-white"
                                )}>
                                    Question {idx + 1}
                                </span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <Clock className={cn(
                                    "w-3 h-3",
                                    question.is_correct ? "text-black" : "text-white"
                                )} />
                                <span className={cn(
                                    "text-[9px] font-bold",
                                    question.is_correct ? "text-black" : "text-white"
                                )}>
                                    {formatResponseTime(question.response_time_seconds)}
                                </span>
                            </div>
                        </div>

                        {/* Question text */}
                        <div className={cn(
                            "text-xs font-bold leading-relaxed mb-2",
                            question.is_correct ? "text-black" : "text-white"
                        )}>
                            {question.question_text}
                        </div>

                        {/* Skills */}
                        {question.skill_names && question.skill_names.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                                {question.skill_names.map((skill, skillIdx) => (
                                    <span
                                        key={skillIdx}
                                        className={cn(
                                            "px-1.5 py-0.5 border-[2px] border-black dark:border-white text-[8px] font-bold",
                                            question.is_correct
                                                ? "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                                                : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
                                        )}
                                    >
                                        {formatSkillName(skill)}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Summary Stats */}
            {sessionData.metadata && (
                <div className="mt-4 pt-3 border-t-[3px] border-black dark:border-white">
                    <div className="grid grid-cols-2 gap-2">
                        {/* Total Questions */}
                        <div className="p-2 border-[2px] border-black dark:border-white bg-[#FFD93D] dark:bg-[#FFD93D]">
                            <div className="flex items-center gap-1 mb-0.5">
                                <Target className="w-3 h-3 text-black" />
                                <span className="text-[8px] font-black uppercase text-black">Total</span>
                            </div>
                            <div className="text-lg font-black text-black">
                                {sessionData.metadata.question_count}
                            </div>
                        </div>

                        {/* Correct Answers */}
                        <div className="p-2 border-[2px] border-black dark:border-white bg-[#4ADE80]">
                            <div className="flex items-center gap-1 mb-0.5">
                                <CheckCircle2 className="w-3 h-3 text-black" />
                                <span className="text-[8px] font-black uppercase text-black">Correct</span>
                            </div>
                            <div className="text-lg font-black text-black">
                                {Math.round(sessionData.metadata.accuracy * sessionData.metadata.question_count)}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
