import React, { useState } from "react";
import cn from "classnames";
import { History, ChevronLeft, Calendar, Clock, Target, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePracticeHistory } from "../../hooks/query-hooks/usePracticeHistory";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import SessionDetailView from "./SessionDetailView";

interface PracticeHistoryPanelProps {
    open: boolean;
    onToggle: () => void;
}

const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric"
    });
};

const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes < 60) {
        return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
};

const formatSkillName = (name: string) => {
    return name
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
};

export default function PracticeHistoryPanel({ open, onToggle }: PracticeHistoryPanelProps) {
    const [page, setPage] = useState(1);
    const limit = 10;

    const { data: practiceData, isLoading } = usePracticeHistory({
        page,
        limit,
        enabled: true,
    });

    const sessions = practiceData?.sessions || [];
    const totalCount = practiceData?.total_count || 0;
    const hasMore = page * limit < totalCount;
    const hasPrevious = page > 1;

    return (
        <div
            className={cn(
                "fixed top-[44px] lg:top-[48px] right-0 flex flex-col border-l-[3px] lg:border-l-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform shadow-[-2px_0_0_0_rgba(0,0,0,1)] lg:shadow-[-2px_0_0_0_rgba(0,0,0,1)] dark:shadow-[-2px_0_0_0_rgba(255,255,255,0.3)]",
                "h-[calc(100vh-44px)] lg:h-[calc(100vh-48px)]",
                open ? "w-[280px] lg:w-[320px]" : "w-[40px]",
                "max-md:hidden" // Hide on mobile
            )}
        >
            <header className={cn(
                "flex items-center h-[44px] lg:h-[48px] border-b-[3px] border-black dark:border-white shrink-0 overflow-hidden transition-all duration-300 bg-[#C4B5FD]",
                open ? "justify-between px-3 lg:px-4" : "justify-center"
            )}>
                {open ? (
                    <>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={onToggle}
                            className="w-[2.125rem] h-[2.125rem] border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] text-black dark:text-white dark:hover:text-black transition-all shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-1 hover:translate-y-1"
                        >
                            <ChevronLeft className="w-5 h-5 font-bold transform rotate-180" />
                        </Button>
                        <div className="flex items-center gap-2 lg:gap-2.5 animate-in fade-in slide-in-from-right-4 duration-300">
                            <h2 className="text-xs lg:text-sm font-black text-black whitespace-nowrap uppercase tracking-tight">
                                PRACTICE HISTORY
                            </h2>
                            <div className="px-[0.25rem] pt-[0.15rem] pb-[0.25rem] lg:px-[0.375rem] lg:pt-[0.25rem] lg:pb-[0.375rem] border-[2px] lg:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
                                <History className="w-4 h-4 text-black dark:text-white font-bold" />
                            </div>
                        </div>
                    </>
                ) : (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="w-[1.8125rem] h-[1.6rem] lg:w-[2.025rem] lg:h-[1.8125rem] border-[2px] lg:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] transition-colors shadow-[1px_1px_0_0_rgba(0,0,0,1)] lg:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
                    >
                        <History className="w-3 h-3 text-black dark:text-white dark:hover:text-black font-bold" />
                    </Button>
                )}
            </header>

            <div className="flex-grow overflow-hidden relative">
                {open ? (
                    <div className="h-full flex flex-col">
                        <div className="flex-grow overflow-y-auto overflow-x-hidden animate-in fade-in duration-500 px-4 py-4">
                            <Accordion
                                type="single"
                                collapsible
                                className="w-full space-y-3"
                            >
                                {isLoading ? (
                                    <div className="text-center py-8 text-sm text-gray-500">
                                        Loading practice history...
                                    </div>
                                ) : sessions.length === 0 ? (
                                    <div className="text-center py-8 text-sm text-gray-500">
                                        No practice sessions yet
                                    </div>
                                ) : (
                                    sessions.map((session) => {
                                        const accuracyPercent = Math.round(session.accuracy * 100);
                                        const getAccuracyColor = () => {
                                            if (accuracyPercent >= 90) return "emerald";
                                            if (accuracyPercent >= 75) return "green";
                                            if (accuracyPercent >= 60) return "yellow";
                                            if (accuracyPercent >= 40) return "orange";
                                            return "red";
                                        };
                                        const accuracyColor = getAccuracyColor();

                                        return (
                                            <AccordionItem
                                                key={session.session_id}
                                                value={session.session_id}
                                                className="border-none"
                                            >
                                                <div className="border-[4px] border-black dark:border-white transition-all duration-200 shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)] bg-[#FFFDF5] dark:bg-[#000000] hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:translate-x-[-2px] hover:translate-y-[-2px]">
                                                    <AccordionTrigger className="hover:no-underline px-4 py-3 [&>svg]:hidden cursor-pointer group">
                                                        <div className="flex flex-col gap-2 w-full">
                                                            <div className="flex items-center justify-between w-full">
                                                                <span className="font-black text-xs text-left uppercase tracking-tight text-black dark:text-white">
                                                                    {formatDate(session.date)}
                                                                </span>
                                                                <div className={cn(
                                                                    "px-2.5 py-0.5 border-[2px] border-black dark:border-white text-[10px] font-black uppercase",
                                                                    accuracyColor === "emerald" && "bg-[#4ADE80] text-black",
                                                                    accuracyColor === "green" && "bg-[#4ADE80] text-black",
                                                                    accuracyColor === "yellow" && "bg-[#FFD93D] text-black",
                                                                    accuracyColor === "orange" && "bg-[#FF6B6B] text-white",
                                                                    accuracyColor === "red" && "bg-[#FF6B6B] text-white"
                                                                )}>
                                                                    {accuracyPercent}%
                                                                </div>
                                                            </div>

                                                            <div className="flex items-center gap-2 text-[10px] font-bold text-black/70 dark:text-white/70">
                                                                <Clock className="w-3 h-3" />
                                                                <span>{formatTime(session.date)}</span>
                                                                <span>•</span>
                                                                <span>{formatDuration(session.duration)}</span>
                                                            </div>
                                                        </div>
                                                    </AccordionTrigger>
                                                    <AccordionContent>
                                                        <div className="px-4 pb-4 pt-2">
                                                            <div className="grid grid-cols-2 gap-3">
                                                                {/* Questions Card */}
                                                                <div className="aspect-square p-2.5 border-[3px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)] flex flex-col bg-[#FFD93D] dark:bg-[#FFD93D]">
                                                                    <div className="flex items-center gap-1.5 mb-1">
                                                                        <TrendingUp className="w-3.5 h-3.5 font-bold flex-shrink-0 text-black" />
                                                                        <span className="text-[9px] font-black uppercase leading-none text-black">Questions</span>
                                                                    </div>
                                                                    <div className="flex-1 flex flex-col justify-center">
                                                                        <div className="text-2xl font-black leading-none text-black">
                                                                            {session.question_count}
                                                                        </div>
                                                                        <div className="text-[9px] mt-1 font-bold text-black">
                                                                            attempted
                                                                        </div>
                                                                    </div>
                                                                </div>

                                                                {/* Accuracy Card */}
                                                                <div className={cn(
                                                                    "aspect-square p-2.5 border-[3px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)] flex flex-col",
                                                                    accuracyColor === "emerald" && "bg-[#4ADE80]",
                                                                    accuracyColor === "green" && "bg-[#4ADE80]",
                                                                    accuracyColor === "yellow" && "bg-[#FFD93D]",
                                                                    accuracyColor === "orange" && "bg-[#FF6B6B]",
                                                                    accuracyColor === "red" && "bg-[#FF6B6B]"
                                                                )}>
                                                                    <div className="flex items-center gap-1.5 mb-1">
                                                                        <Target className={cn(
                                                                            "w-3.5 h-3.5 font-bold flex-shrink-0",
                                                                            (accuracyColor === "orange" || accuracyColor === "red") ? "text-white" : "text-black"
                                                                        )} />
                                                                        <span className={cn(
                                                                            "text-[9px] font-black uppercase leading-none",
                                                                            (accuracyColor === "orange" || accuracyColor === "red") ? "text-white" : "text-black"
                                                                        )}>Accuracy</span>
                                                                    </div>
                                                                    <div className="flex-1 flex flex-col justify-center">
                                                                        <div className={cn(
                                                                            "text-2xl font-black leading-none",
                                                                            (accuracyColor === "orange" || accuracyColor === "red") ? "text-white" : "text-black"
                                                                        )}>
                                                                            {accuracyPercent}%
                                                                        </div>
                                                                        <div className={cn(
                                                                            "text-[9px] mt-1 font-bold",
                                                                            (accuracyColor === "orange" || accuracyColor === "red") ? "text-white" : "text-black"
                                                                        )}>
                                                                            correct rate
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            </div>

                                                            {/* Skills Practiced */}
                                                            {session.skills_practiced && session.skills_practiced.length > 0 && (
                                                                <div className="mt-2 bg-[#FFFDF5] dark:bg-[#000000] p-2.5 border-[3px] border-black dark:border-white">
                                                                    <div className="text-[9px] font-black uppercase text-black dark:text-white mb-2">
                                                                        Skills Practiced:
                                                                    </div>
                                                                    <div className="flex flex-wrap gap-1">
                                                                        {session.skills_practiced.map((skill, idx) => (
                                                                            <span
                                                                                key={idx}
                                                                                className="px-2 py-0.5 border-[2px] border-black dark:border-white bg-[#C4B5FD] text-[8px] font-bold text-black"
                                                                            >
                                                                                {formatSkillName(skill)}
                                                                            </span>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            )}

                                                            {/* Divider */}
                                                            <div className="mt-3 mb-2 border-t-[3px] border-black dark:border-white"></div>

                                                            {/* Question Details Header */}
                                                            <div className="px-4 mb-2">
                                                                <h3 className="text-[10px] font-black uppercase text-black dark:text-white">
                                                                    Question Details
                                                                </h3>
                                                            </div>
                                                        </div>

                                                        {/* Session Detail View - Question List */}
                                                        <SessionDetailView sessionId={session.session_id} />
                                                    </AccordionContent>
                                                </div>
                                            </AccordionItem>
                                        );
                                    })
                                )}
                            </Accordion>
                        </div>

                        {/* Pagination Controls */}
                        {!isLoading && sessions.length > 0 && (
                            <div className="border-t-[3px] border-black dark:border-white p-3 bg-[#FFFDF5] dark:bg-[#000000]">
                                <div className="flex items-center justify-between gap-2">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setPage(p => p - 1)}
                                        disabled={!hasPrevious}
                                        className={cn(
                                            "h-8 px-3 border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] text-black dark:text-white dark:hover:text-black font-black text-xs uppercase transition-all shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5",
                                            !hasPrevious && "opacity-30 cursor-not-allowed"
                                        )}
                                    >
                                        Previous
                                    </Button>
                                    <span className="text-[10px] font-bold text-black dark:text-white">
                                        Page {page}
                                    </span>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setPage(p => p + 1)}
                                        disabled={!hasMore}
                                        className={cn(
                                            "h-8 px-3 border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] text-black dark:text-white dark:hover:text-black font-black text-xs uppercase transition-all shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5",
                                            !hasMore && "opacity-30 cursor-not-allowed"
                                        )}
                                    >
                                        Next
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="h-full w-full flex items-center justify-center cursor-pointer hover:bg-[#C4B5FD]/20 transition-colors pb-[140px]" onClick={onToggle}>
                        <div className="rotate-180 [writing-mode:vertical-rl] text-lg font-black tracking-widest uppercase whitespace-nowrap select-none text-black dark:text-white text-center leading-none">
                            PRACTICE HISTORY
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
