import React, { useEffect, useRef, useState } from "react";
import cn from "classnames";
import { GraduationCap, ChevronRight, ChevronLeft, TrendingUp, Clock, Target, Flame, Zap, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";

interface GradingSidebarProps {
    open: boolean;
    onToggle: () => void;
    currentSkill?: string | null;
}



const formatSkillName = (name: string) => {
    return name
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
};

const formatTime = (timestamp: number | null) => {
    if (!timestamp) return "Never";
    const date = new Date(timestamp * 1000);
    return (
        date.toLocaleDateString() +
        " " +
        date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    );
};

export default function GradingSidebar({ open, onToggle, currentSkill }: GradingSidebarProps) {
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const isUserScrollingRef = useRef(false);
    const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    
    // Fetch grading panel data from API
    const { data: gradingData, isLoading } = useQuery({
        queryKey: ["grading-panel"],
        queryFn: async () => {
            const res = await apiUtils.get(`${DASH_API_URL}/api/grading-panel`);
            if (!res.ok) {
                throw new Error(`Failed to fetch grading panel (${res.status})`);
            }
            return res.json();
        },
        staleTime: 60_000, // Consider data fresh for 60 seconds
        refetchOnWindowFocus: false, // Don't refetch when window regains focus
        refetchOnMount: true, // Only refetch when component mounts
        // Removed refetchInterval - we'll manually invalidate on answer submission
    });
    
    // Extract data from grading panel response
    const subjects = gradingData?.subjects || {};
    const overallGrade = gradingData?.overall_grade || "N/A";
    const overallMastery = gradingData?.overall_mastery || 0;
    
    // Debug logging
    useEffect(() => {
        if (gradingData) {
            console.log('[GradingSidebar] Grading data received:', {
                subjects: Object.keys(subjects).length,
                overallGrade,
                overallMastery,
                totalUnits: Object.values(subjects).reduce((acc: number, subject: any) => {
                    return acc + Object.values(subject.grade_levels || {}).reduce((gradeAcc: number, grade: any) => {
                        return gradeAcc + (grade.units?.length || 0);
                    }, 0);
                }, 0)
            });
        }
    }, [gradingData]);
    
    // Debug current skill changes
    useEffect(() => {
        if (currentSkill) {
            console.log('[GradingSidebar] Current skill changed to:', currentSkill);
        }
    }, [currentSkill]);

    const scrollToSkill = (skill: string) => {
        const container = scrollContainerRef.current;
        if (!container) return;

        const element = document.getElementById(`skill-${skill}`);
        if (element) {
            // Calculate the element's position relative to the container
            const containerTop = container.getBoundingClientRect().top;
            const elementTop = element.getBoundingClientRect().top;
            const offset = 0; // Position at the very top
            
            // Calculate the target scroll position
            const scrollPosition = container.scrollTop + (elementTop - containerTop) - offset;
            
            // Scroll to position
            container.scrollTo({
                top: Math.max(0, scrollPosition),
                behavior: "smooth"
            });
        }
    };

    const prevOpenRef = useRef(open);
    const prevSkillRef = useRef<string | null>(null);

    // Auto-scroll when open, currentSkill, or data loading state changes
    useEffect(() => {
        if (open && currentSkill && !isLoading && gradingData) {
            // If skill changed, reset user scrolling flag and scroll immediately
            const skillChanged = prevSkillRef.current !== currentSkill;
            if (skillChanged) {
                isUserScrollingRef.current = false;
            }
            
            // If we're transitioning from closed to open, we need to wait for the width transition (500ms)
            // If skill just changed, scroll immediately
            // Otherwise, wait a bit for content to render
            const isOpening = !prevOpenRef.current && open;
            const delay = isOpening ? 600 : (skillChanged ? 0 : 100);

            // Small delay to ensure content is rendered/expanded
            const timeoutId = setTimeout(() => {
                if (!isUserScrollingRef.current) {
                    scrollToSkill(currentSkill);
                }
            }, delay);

            prevSkillRef.current = currentSkill;
            return () => clearTimeout(timeoutId);
        }
        prevOpenRef.current = open;
    }, [open, currentSkill, isLoading, gradingData]);

    // Handle user scrolling and inactivity
    useEffect(() => {
        const container = scrollContainerRef.current;
        if (!container) return;

        const handleScroll = () => {
            isUserScrollingRef.current = true;

            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }

            scrollTimeoutRef.current = setTimeout(() => {
                isUserScrollingRef.current = false;
                if (currentSkill && open) {
                    scrollToSkill(currentSkill);
                }
            }, 3000);
        };

        container.addEventListener("scroll", handleScroll);

        return () => {
            container.removeEventListener("scroll", handleScroll);
            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }
        };
    }, [currentSkill, open]);

    // Handle click elsewhere (on the container background) to re-center immediately
    const handleContainerClick = (e: React.MouseEvent) => {
        // If the user clicks directly on the container (not on an interactive child that stops propagation)
        // we assume they want to re-center.
        // However, checking e.target === e.currentTarget might be too strict if there are wrapper divs.
        // Let's just reset the scrolling flag and scroll immediately if they click anywhere in the sidebar
        // (except maybe on the toggle button which is in the header, outside this div).

        // Reset user scrolling flag
        isUserScrollingRef.current = false;
        if (scrollTimeoutRef.current) {
            clearTimeout(scrollTimeoutRef.current);
        }

        if (currentSkill && open) {
            scrollToSkill(currentSkill);
        }
    };

    return (
        <div
            className={cn(
                "fixed top-[44px] lg:top-[48px] left-0 flex flex-col border-r border-gray-200 dark:border-neutral-800 bg-white dark:bg-[#0a0a0a] transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform",
                "h-[calc(100vh-44px)] lg:h-[calc(100vh-48px)]",
                open ? "w-[220px] lg:w-[240px]" : "w-[40px]",
                "max-md:hidden" // Hide on mobile
            )}
        >
            <header className={cn(
                "flex items-center h-[40px] lg:h-[44px] border-b border-gray-200 dark:border-neutral-700 shrink-0 overflow-hidden transition-all duration-300 bg-white dark:bg-neutral-900",
                open ? "justify-between px-3" : "justify-center"
            )}>
                {open ? (
                    <div className="flex items-center gap-2 animate-in fade-in slide-in-from-left-4 duration-300">
                        <GraduationCap className="w-4 h-4 text-[#C4B5FD]" />
                        <h2 className="text-xs font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">
                            Progress
                        </h2>
                    </div>
                ) : (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="w-7 h-7 hover:bg-gray-100 dark:hover:bg-neutral-800 transition-colors"
                    >
                        <GraduationCap className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                    </Button>
                )}

                {open && (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="w-7 h-7 hover:bg-gray-100 dark:hover:bg-neutral-800 text-gray-500 transition-colors"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </Button>
                )}
            </header>

            <div className="flex-grow overflow-hidden relative">
                {open ? (
                    <div
                        ref={scrollContainerRef}
                        className="h-full overflow-y-auto overflow-x-hidden animate-in fade-in duration-500 px-4 py-4"
                        onClick={handleContainerClick}
                    >
                        {/* Today's Progress Tokens */}
                        {!isLoading && (
                            <div className="mb-4 p-3 border-[3px] border-black dark:border-white bg-white dark:bg-neutral-800 shadow-[1px_1px_0_0_rgba(0,0,0,1)]">
                                <div className="text-[9px] font-black uppercase tracking-wide text-black dark:text-white mb-2 flex items-center gap-1.5">
                                    <Zap className="w-3 h-3 text-[#FFD93D]" />
                                    Today's Progress
                                </div>
                                <div className="flex items-center gap-2">
                                    {/* Problems Solved Token */}
                                    <div className="flex-1 flex items-center gap-1.5 px-2 py-1.5 bg-[#E0F2FE] dark:bg-[#0c2d48] border-[2px] border-[#0EA5E9] rounded-sm">
                                        <div className="w-5 h-5 rounded-full bg-[#0EA5E9] flex items-center justify-center">
                                            <Target className="w-3 h-3 text-white" />
                                        </div>
                                        <div>
                                            <div className="text-[10px] font-black text-[#0369A1] dark:text-[#38BDF8]">
                                                {(() => {
                                                    // Calculate today's problems from subjects data
                                                    let totalAnswered = 0;
                                                    Object.values(subjects).forEach((subject: any) => {
                                                        Object.values(subject.grade_levels || {}).forEach((grade: any) => {
                                                            grade.units?.forEach((unit: any) => {
                                                                totalAnswered += unit.questions_answered || 0;
                                                            });
                                                        });
                                                    });
                                                    return totalAnswered;
                                                })()} solved
                                            </div>
                                        </div>
                                    </div>
                                    {/* Streak Token */}
                                    <div className="flex items-center gap-1.5 px-2 py-1.5 bg-[#FEF3C7] dark:bg-[#422006] border-[2px] border-[#F59E0B] rounded-sm">
                                        <div className="w-5 h-5 rounded-full bg-[#F59E0B] flex items-center justify-center">
                                            <Flame className="w-3 h-3 text-white" />
                                        </div>
                                        <div className="text-[10px] font-black text-[#B45309] dark:text-[#FCD34D]">3</div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Overall Grade Display */}
                        {!isLoading && overallGrade && (
                            <div className="mb-4 border-[4px] border-black dark:border-white bg-[#FFD93D] dark:bg-[#FFD93D] p-4 shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
                                <div className="text-center">
                                    <div className="text-[10px] font-black tracking-wide text-black mb-1">Overall Grade</div>
                                    <div className="text-5xl font-black text-black">{overallGrade}</div>
                                    <div className="text-xs font-bold text-black mt-1">{overallMastery}% Mastery</div>
                                </div>
                            </div>
                        )}

                        <Accordion
                            type="single"
                            collapsible
                            value={currentSkill || undefined}
                            className="w-full space-y-3"
                            onClick={(e) => e.stopPropagation()} // Prevent handleContainerClick from intercepting accordion clicks
                        >
                            {isLoading ? (
                                <div className="text-center py-8 text-sm text-gray-500">
                                    Loading skills...
                                </div>
                            ) : Object.keys(subjects).length === 0 ? (
                                <div className="text-center py-8 text-sm text-gray-500">
                                    Start answering questions to see your progress!
                                </div>
                            ) : (
                                // Render Subject → Grade → Units hierarchy
                                Object.entries(subjects).map(([subjectName, subjectData]: [string, any]) => (
                                    Object.entries(subjectData.grade_levels || {}).map(([gradeLevel, gradeData]: [string, any]) => (
                                        gradeData.units.map((unit: any) => {
                                const mastery = unit.mastery || 0;
                                const normalizedStrength = mastery; // Already 0-100%
                                const hasPractice = unit.questions_answered > 0;

                                // Determine strength level for color based on mastery
                                const getStrengthColor = () => {
                                    if (!hasPractice) return "gray";
                                    if (mastery >= 90) return "emerald";
                                    if (mastery >= 75) return "green";
                                    if (mastery >= 60) return "yellow";
                                    if (mastery >= 50) return "orange";
                                    return "red";
                                };

                                const strengthColor = getStrengthColor();
                                const accuracyPercent = unit.questions_answered > 0
                                    ? Math.round((unit.questions_correct / unit.questions_answered) * 100)
                                    : 0;

                                const isCurrentSkill = unit.id === currentSkill;
                                
                                return (
                                    <AccordionItem
                                        key={unit.id}
                                        value={unit.id}
                                        id={`skill-${unit.id}`}
                                        className="border-none"
                                    >
                                        <div className={cn(
                                            "border-[4px] border-black dark:border-white transition-all duration-200 shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)]",
                                            isCurrentSkill && "bg-[#FFE500] dark:bg-[#FFD93D] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(0,0,0,1)] scale-[1.02]",
                                            !isCurrentSkill && hasPractice && "bg-[#FFFDF5] dark:bg-[#000000]",
                                            !isCurrentSkill && !hasPractice && "bg-[#FFFDF5] dark:bg-[#000000] opacity-60",
                                            hasPractice && "hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:translate-x-[-2px] hover:translate-y-[-2px]"
                                        )}>
                                            <AccordionTrigger className="hover:no-underline px-4 py-3 [&>svg]:hidden cursor-pointer group">
                                                <div className="flex flex-col gap-2 w-full">
                                                    <div className="flex items-center justify-between w-full">
                                                        <div className="flex flex-col items-start gap-1">
                                                            <span className={cn(
                                                                "font-black text-xs text-left tracking-tight",
                                                                hasPractice ? "text-black dark:text-white" : "text-black/50 dark:text-white/50"
                                                            )}>
                                                                {unit.name}
                                                            </span>
                                                            <span className={cn(
                                                                "text-[9px] font-bold",
                                                                hasPractice ? "text-black/70 dark:text-white/70" : "text-black/40 dark:text-white/40"
                                                            )}>
                                                                {subjectName} • Grade {gradeLevel}
                                                            </span>
                                                        </div>
                                                        <div className={cn(
                                                            "px-2.5 py-0.5 border-[2px] border-black dark:border-white text-[10px] font-black",
                                                            strengthColor === "gray" && "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white",
                                                            strengthColor === "emerald" && "bg-[#4ADE80] text-black",
                                                            strengthColor === "green" && "bg-[#4ADE80] text-black",
                                                            strengthColor === "yellow" && "bg-[#FFD93D] text-black",
                                                            strengthColor === "orange" && "bg-[#FF6B6B] text-white",
                                                            strengthColor === "red" && "bg-[#FF6B6B] text-white"
                                                        )}>
                                                            {mastery.toFixed(0)}%
                                                        </div>
                                                    </div>

                                                    {/* Progress bar */}
                                                    <div className="w-full bg-[#FFFDF5] dark:bg-[#000000] border-[2px] border-black dark:border-white h-3 overflow-hidden">
                                                        <div
                                                            className={cn(
                                                                "h-full transition-all duration-300",
                                                                strengthColor === "gray" && "bg-black/30 dark:bg-white/30",
                                                                strengthColor === "emerald" && "bg-[#4ADE80]",
                                                                strengthColor === "green" && "bg-[#4ADE80]",
                                                                strengthColor === "yellow" && "bg-[#FFD93D]",
                                                                strengthColor === "orange" && "bg-[#FF6B6B]",
                                                                strengthColor === "red" && "bg-[#FF6B6B]"
                                                            )}
                                                            style={{ width: `${normalizedStrength}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            </AccordionTrigger>
                                            <AccordionContent>
                                                <div className="px-4 pb-4 pt-2">
                                                    <div className="grid grid-cols-2 gap-3">
                                                        {/* Accuracy Card */}
                                                        <div className={cn(
                                                            "aspect-square p-2.5 border-[3px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)] flex flex-col",
                                                            hasPractice
                                                                ? "bg-[#FF6B6B] dark:bg-[#FF6B6B]"
                                                                : "bg-[#FFFDF5] dark:bg-[#000000] opacity-60"
                                                        )}>
                                                            <div className="flex items-center gap-1.5 mb-1">
                                                                <Target className={cn(
                                                                    "w-3.5 h-3.5 font-bold flex-shrink-0",
                                                                    hasPractice ? "text-white" : "text-black dark:text-white"
                                                                )} />
                                                                <span className={cn(
                                                                    "text-[9px] font-black leading-none",
                                                                    hasPractice ? "text-white" : "text-black dark:text-white"
                                                                )}>Accuracy</span>
                                                            </div>
                                                            <div className="flex-1 flex flex-col justify-center">
                                                                <div className={cn(
                                                                    "text-2xl font-black leading-none",
                                                                    hasPractice ? "text-white" : "text-black dark:text-white"
                                                                )}>
                                                                    {accuracyPercent}%
                                                                </div>
                                                                <div className={cn(
                                                                    "text-[9px] mt-1 font-bold",
                                                                    hasPractice ? "text-white" : "text-black dark:text-white"
                                                                )}>
                                                                    {unit.questions_correct}/{unit.questions_answered} correct
                                                                </div>
                                                            </div>
                                                        </div>

                                                        {/* Practice Count Card */}
                                                        <div className={cn(
                                                            "aspect-square p-2.5 border-[3px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)] flex flex-col",
                                                            hasPractice
                                                                ? "bg-[#C4B5FD] dark:bg-[#C4B5FD]"
                                                                : "bg-[#FFFDF5] dark:bg-[#000000] opacity-60"
                                                        )}>
                                                            <div className="flex items-center gap-1.5 mb-1">
                                                                <TrendingUp className={cn(
                                                                    "w-3.5 h-3.5 font-bold flex-shrink-0",
                                                                    hasPractice ? "text-black" : "text-black dark:text-white"
                                                                )} />
                                                                <span className={cn(
                                                                    "text-[9px] font-black leading-none",
                                                                    hasPractice ? "text-black" : "text-black dark:text-white"
                                                                )}>Questions</span>
                                                            </div>
                                                            <div className="flex-1 flex flex-col justify-center">
                                                                <div className={cn(
                                                                    "text-2xl font-black leading-none",
                                                                    hasPractice ? "text-black" : "text-black dark:text-white"
                                                                )}>
                                                                    {unit.questions_answered}
                                                                </div>
                                                                <div className={cn(
                                                                    "text-[9px] mt-1 font-bold",
                                                                    hasPractice ? "text-black" : "text-black dark:text-white"
                                                                )}>
                                                                    total attempts
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Sub-skills (Lessons) */}
                                                    {unit.sub_skills && unit.sub_skills.length > 0 && (
                                                        <div className="mt-3 bg-[#FFFDF5] dark:bg-[#000000] p-2.5 border-[3px] border-black dark:border-white">
                                                            <div className="text-[9px] font-black tracking-wide text-black dark:text-white mb-2">Sub-Skills (Lessons)</div>
                                                            <div className="space-y-1.5">
                                                                {unit.sub_skills.slice(0, 5).map((subSkill: any) => (
                                                                    <div key={subSkill.id} className="flex items-center justify-between text-[9px]">
                                                                        <span className="font-bold text-black dark:text-white truncate flex-1">{subSkill.name}</span>
                                                                        <span className={cn(
                                                                            "font-black ml-2",
                                                                            subSkill.mastery >= 75 ? "text-green-600 dark:text-green-400" :
                                                                            subSkill.mastery >= 50 ? "text-yellow-600 dark:text-yellow-400" :
                                                                            "text-red-600 dark:text-red-400"
                                                                        )}>
                                                                            {subSkill.mastery}%
                                                                        </span>
                                                                    </div>
                                                                ))}
                                                                {unit.sub_skills.length > 5 && (
                                                                    <div className="text-[8px] font-bold text-black/50 dark:text-white/50">
                                                                        +{unit.sub_skills.length - 5} more...
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </AccordionContent>
                                        </div>
                                    </AccordionItem>
                                );
                            })
                        ))
                    ))
                )}
            </Accordion>
                    </div>
                ) : (
                    <div className="h-full w-full flex items-center justify-center cursor-pointer hover:bg-gray-50 dark:hover:bg-neutral-900 transition-colors pb-[100px]" onClick={onToggle}>
                        <div className="rotate-180 [writing-mode:vertical-rl] text-xs font-medium tracking-wide whitespace-nowrap select-none text-gray-400 dark:text-gray-500 text-center leading-none">
                            Progress
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
