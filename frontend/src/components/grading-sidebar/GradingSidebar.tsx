import React, { useEffect, useRef, useState } from "react";
import cn from "classnames";
import { GraduationCap, ChevronRight, ChevronLeft, TrendingUp, Clock, Target } from "lucide-react";
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

const CONTENT_V1_PROFILE_KEY = "content_v1_profile_id";
const CONTENT_V1_STARTED_KEY = "content_v1_started";
const CONTENT_V1_MODE_KEY = "content_v1_mode";


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
    const contentV1Enabled = import.meta.env.VITE_CONTENT_V1_ENABLED === "true";
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const isUserScrollingRef = useRef(false);
    const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const [contentV1ProfileId, setContentV1ProfileId] = useState<string | null>(
        () => localStorage.getItem(CONTENT_V1_PROFILE_KEY),
    );
    const [contentV1Started, setContentV1Started] = useState<boolean>(
        () => sessionStorage.getItem(CONTENT_V1_STARTED_KEY) === "true",
    );
    const [contentV1Mode, setContentV1Mode] = useState<boolean>(
        () => sessionStorage.getItem(CONTENT_V1_MODE_KEY) === "true",
    );

    useEffect(() => {
        const syncContentV1State = () => {
            setContentV1ProfileId(localStorage.getItem(CONTENT_V1_PROFILE_KEY));
            setContentV1Started(sessionStorage.getItem(CONTENT_V1_STARTED_KEY) === "true");
            setContentV1Mode(sessionStorage.getItem(CONTENT_V1_MODE_KEY) === "true");
        };
        const onStorage = (e: StorageEvent) => {
            if (!e.key || e.key === CONTENT_V1_PROFILE_KEY || e.key === CONTENT_V1_STARTED_KEY || e.key === CONTENT_V1_MODE_KEY) syncContentV1State();
        };
        window.addEventListener("storage", onStorage);
        const timer = setInterval(syncContentV1State, 1500);
        return () => {
            window.removeEventListener("storage", onStorage);
            clearInterval(timer);
        };
    }, []);
    
    // Track current subject for query invalidation
    const [currentSubject, setCurrentSubject] = useState<string>(() =>
        sessionStorage.getItem("selected_subject") || ""
    );
    useEffect(() => {
        const syncSubject = () => {
            const s = sessionStorage.getItem("selected_subject") || "";
            if (s !== currentSubject) setCurrentSubject(s);
        };
        const timer = setInterval(syncSubject, 1500);
        return () => clearInterval(timer);
    }, [currentSubject]);

    // Fetch grading panel data from API
    const { data: gradingData, isLoading } = useQuery({
        queryKey: ["grading-panel", contentV1ProfileId, currentSubject],
        queryFn: async () => {
            if (contentV1Enabled) {
                if (contentV1ProfileId && contentV1Started) {
                    const planRes = await apiUtils.get(
                        `${DASH_API_URL}/api/content-v1/plan?learner_profile_id=${encodeURIComponent(contentV1ProfileId)}`,
                    );
                    if (planRes.ok) {
                        const planJson = await planRes.json();
                        return { mode: "content_v1", ...planJson };
                    }
                }
                return { mode: "content_v1_pending", subjects: {}, overall_grade: "N/A", overall_mastery: 0 };
            }
            const res = await apiUtils.get(`${DASH_API_URL}/api/grading-panel`);
            if (!res.ok) {
                throw new Error(`Failed to fetch grading panel (${res.status})`);
            }
            return { mode: "legacy", ...(await res.json()) };
        },
        staleTime: 10_000, // Keep fresh enough to reflect step progression.
        refetchOnWindowFocus: false, // Don't refetch when window regains focus
        refetchOnMount: true, // Only refetch when component mounts
        refetchInterval: contentV1Enabled && contentV1ProfileId && contentV1Started ? 5000 : false,
    });
    
    const isContentV1 = gradingData?.mode === "content_v1";
    const v1Plan = gradingData?.learning_plan || {};
    const v1Steps = v1Plan?.steps || [];
    const v1CurrentStep = Number(gradingData?.current_step_index || 0);
    const v1ReadyCount = Number(gradingData?.next_ready_count || 0);
    const v1ProgressPct = v1Steps.length > 0 ? Math.max(0, Math.min(100, Math.round((v1CurrentStep / v1Steps.length) * 100))) : 0;

    const subjects = isContentV1
        ? {
              "Content V1 Journey": {
                  grade_levels: {
                      "Learning Path": {
                          units: v1Steps.map((step: any, idx: number) => ({
                              id: step?.id || `step_${idx + 1}`,
                              name: step?.title || step?.topic || `Step ${idx + 1}`,
                              mastery: idx < v1CurrentStep ? 100 : idx === v1CurrentStep ? Math.max(5, v1ProgressPct) : 0,
                              questions_answered: idx < v1CurrentStep ? 1 : 0,
                              questions_correct: idx < v1CurrentStep ? 1 : 0,
                              last_practiced: null,
                          })),
                      },
                  },
              },
          }
        : gradingData?.subjects || {};

    const overallGrade = isContentV1
        ? (v1Steps.length ? `${Math.min(v1CurrentStep + 1, v1Steps.length)}/${v1Steps.length}` : "N/A")
        : gradingData?.overall_grade || "N/A";
    const overallMastery = isContentV1 ? v1ProgressPct : gradingData?.overall_mastery || 0;
    const effectiveCurrentSkill =
        isContentV1 && v1Steps.length
            ? v1Steps[Math.min(v1CurrentStep, v1Steps.length - 1)]?.id || `step_${Math.min(v1CurrentStep + 1, v1Steps.length)}`
            : currentSkill;
    
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
        if (effectiveCurrentSkill) {
            console.log('[GradingSidebar] Current skill changed to:', currentSkill);
        }
    }, [effectiveCurrentSkill, currentSkill]);

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
        if (open && effectiveCurrentSkill && !isLoading && gradingData) {
            // If skill changed, reset user scrolling flag and scroll immediately
            const skillChanged = prevSkillRef.current !== effectiveCurrentSkill;
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
                    scrollToSkill(effectiveCurrentSkill);
                }
            }, delay);

            prevSkillRef.current = effectiveCurrentSkill;
            return () => clearTimeout(timeoutId);
        }
        prevOpenRef.current = open;
    }, [open, effectiveCurrentSkill, isLoading, gradingData]);

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
                if (effectiveCurrentSkill && open) {
                    scrollToSkill(effectiveCurrentSkill);
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
    }, [effectiveCurrentSkill, open]);

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

        if (effectiveCurrentSkill && open) {
            scrollToSkill(effectiveCurrentSkill);
        }
    };

    return (
        <div
            className={cn(
                "fixed top-[44px] lg:top-[48px] left-0 flex flex-col border-r-[3px] lg:border-r-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform shadow-[2px_0_0_0_rgba(0,0,0,1)] lg:shadow-[2px_0_0_0_rgba(0,0,0,1)] dark:shadow-[2px_0_0_0_rgba(255,255,255,0.3)]",
                "h-[calc(100vh-44px)] lg:h-[calc(100vh-48px)]",
                open ? "w-[240px] lg:w-[260px]" : "w-[40px]",
                "max-md:hidden" // Hide on mobile
            )}
        >
            <header className={cn(
                "flex items-center h-[44px] lg:h-[48px] border-b-[3px] border-black dark:border-white shrink-0 overflow-hidden transition-all duration-300 bg-[#FF6B6B]",
                open ? "justify-between px-3 lg:px-4" : "justify-center"
            )}>
                {open ? (
                    <div className="flex items-center gap-2 lg:gap-2.5 animate-in fade-in slide-in-from-left-4 duration-300">
                        <div className="px-[0.25rem] pt-[0.15rem] pb-[0.25rem] lg:px-[0.375rem] lg:pt-[0.25rem] lg:pb-[0.375rem] border-[2px] lg:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
                            <GraduationCap className="w-4 h-4 text-black dark:text-white font-bold" />
                        </div>
                        <h2 className="text-xs lg:text-sm font-black text-white whitespace-nowrap tracking-tight">
                            Grading & Skills
                        </h2>
                    </div>
                ) : (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="w-[1.8125rem] h-[1.6rem] lg:w-[2.025rem] lg:h-[1.8125rem] border-[2px] lg:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] transition-colors shadow-[1px_1px_0_0_rgba(0,0,0,1)] lg:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
                    >
                        <GraduationCap className="w-3 h-3 text-black dark:text-white dark:hover:text-black font-bold" />
                    </Button>
                )}

                {open && (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="w-[2.125rem] h-[2.125rem] border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] text-black dark:text-white dark:hover:text-black transition-all shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-1 hover:translate-y-1"
                    >
                        <ChevronLeft className="w-5 h-5 font-bold" />
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
                        {/* Overall Grade Display */}
                        {!isLoading && overallGrade && (
                            <div className="mb-4 border-[4px] border-black dark:border-white bg-[#FFD93D] dark:bg-[#FFD93D] p-4 shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
                                <div className="text-center">
                                    <div className="text-[10px] font-black tracking-wide text-black mb-1">Overall Grade</div>
                                    <div className="text-5xl font-black text-black">{overallGrade}</div>
                                    <div className="text-xs font-bold text-black mt-1">{overallMastery}% Mastery</div>
                                    {isContentV1 ? (
                                        <div className="text-[10px] font-black text-black mt-1">Queue Ready: {v1ReadyCount}</div>
                                    ) : null}
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
                                    {gradingData?.mode === "content_v1_pending"
                                        ? "Choose what to learn first. Your journey will appear here."
                                        : "Start answering questions to see your progress!"}
                                </div>
                            ) : (
                                // Render Subject → Grade → Units hierarchy
                                Object.entries(subjects).map(([subjectName, subjectData]: [string, any]) => (
                                    Object.entries(subjectData.grade_levels || {}).map(([gradeLevel, gradeData]: [string, any]) => (
                                        gradeData.units.map((unit: any) => {
                                const mastery = unit.mastery || 0;
                                const normalizedStrength = mastery; // Already 0-100%
                                const hasPractice = unit.questions_answered > 0;

                                // Mastery level from API (or derive from percentage)
                                const masteryLevelName = unit.mastery_level_name || (
                                    mastery >= 85 ? "EXPERT" :
                                    mastery >= 70 ? "MASTERED" :
                                    mastery >= 50 ? "PROFICIENT" :
                                    mastery >= 30 ? "FAMILIAR" : "ATTEMPTED"
                                );
                                const masteryLabel = ({
                                    EXPERT: "Expert",
                                    MASTERED: "Mastered",
                                    PROFICIENT: "Proficient",
                                    FAMILIAR: "Familiar",
                                    ATTEMPTED: "Attempted",
                                } as Record<string, string>)[masteryLevelName] || masteryLevelName;

                                // Determine strength level for color based on mastery level
                                const getStrengthColor = () => {
                                    if (!hasPractice) return "gray";
                                    if (masteryLevelName === "EXPERT") return "emerald";
                                    if (masteryLevelName === "MASTERED") return "green";
                                    if (masteryLevelName === "PROFICIENT") return "yellow";
                                    if (masteryLevelName === "FAMILIAR") return "orange";
                                    return "red";
                                };

                                const strengthColor = getStrengthColor();
                                const accuracyPercent = unit.questions_answered > 0
                                    ? Math.round((unit.questions_correct / unit.questions_answered) * 100)
                                    : 0;

                                const isCurrentSkill = unit.id === effectiveCurrentSkill;
                                
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
                                                            {hasPractice ? masteryLabel : `${mastery.toFixed(0)}%`}
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
                    <div className="h-full w-full flex items-center justify-center cursor-pointer hover:bg-[#FFE500]/20 transition-colors pb-[140px]" onClick={onToggle}>
                        <div className="rotate-180 [writing-mode:vertical-rl] text-lg font-black tracking-widest whitespace-nowrap select-none text-black dark:text-white text-center leading-none">
                            Grades & Skills
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
