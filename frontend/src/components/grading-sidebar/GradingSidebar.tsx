import React, { useEffect, useRef } from "react";
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

    // Fetch skill scores from API
    const { data: skillScoresData, isLoading } = useQuery({
        queryKey: ["skill-scores"],
        queryFn: async () => {
            const res = await apiUtils.get(`${DASH_API_URL}/api/skill-scores`);
            if (!res.ok) {
                throw new Error(`Failed to fetch skill scores (${res.status})`);
            }
            return res.json();
        },
        staleTime: 60_000, // Consider data fresh for 60 seconds
        refetchOnWindowFocus: false, // Don't refetch when window regains focus
        refetchOnMount: true, // Only refetch when component mounts
        // Removed refetchInterval - we'll manually invalidate on answer submission
    });

    const skillStates = (skillScoresData?.skill_states || {}) as Record<
        string,
        {
            name: string;
            memory_strength: number;
            last_practice_time: number | null;
            practice_count: number;
            correct_count: number;
        }
    >;

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

    // Auto-scroll when open or currentSkill changes
    useEffect(() => {
        if (open && currentSkill) {
            // If we're transitioning from closed to open, we need to wait for the width transition (500ms)
            // If we're already open and just changing skills, we can scroll faster
            const isOpening = !prevOpenRef.current && open;
            const delay = isOpening ? 600 : 100;

            // Small delay to ensure content is rendered/expanded
            const timeoutId = setTimeout(() => {
                if (!isUserScrollingRef.current) {
                    scrollToSkill(currentSkill);
                }
            }, delay);

            return () => clearTimeout(timeoutId);
        }
        prevOpenRef.current = open;
    }, [open, currentSkill]);

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
                "fixed top-[36px] sm:top-[40px] md:top-[44px] lg:top-[48px] left-0 flex flex-col border-r-[3px] sm:border-r-[4px] lg:border-r-[5px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform",
                "h-[calc(100vh-32px)] xs:h-[calc(100vh-36px)] sm:h-[calc(100vh-40px)] md:h-[calc(100vh-44px)] lg:h-[calc(100vh-48px)]",
                // Responsive width with mobile support
                open
                    ? "w-[85vw] sm:w-[240px] lg:w-[260px]"
                    : "w-[40px]",
                // Mobile: Full overlay with shadow, Desktop: regular shadow
                "shadow-[4px_0_16px_rgba(0,0,0,0.3)] md:shadow-[2px_0_0_0_rgba(0,0,0,1)] dark:shadow-[4px_0_16px_rgba(255,255,255,0.2)] md:dark:shadow-[2px_0_0_0_rgba(255,255,255,0.3)]"
            )}
        >
            <header className={cn(
                "flex items-center h-[44px] lg:h-[48px] border-b-[4px] border-black dark:border-white shrink-0 overflow-hidden transition-all duration-300 bg-[#FF6B6B]",
                open ? "justify-between px-3 lg:px-4" : "justify-center"
            )}>
                {open ? (
                    <div className="flex items-center gap-2 lg:gap-2.5 animate-in fade-in slide-in-from-left-4 duration-300">
                        <div className="px-[0.25rem] pt-[0.15rem] pb-[0.25rem] lg:px-[0.375rem] lg:pt-[0.25rem] lg:pb-[0.375rem] border-[3px] lg:border-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
                            <GraduationCap className="w-4 h-4 text-black dark:text-white font-bold" />
                        </div>
                        <h2 className="text-xs lg:text-sm font-black text-white whitespace-nowrap uppercase tracking-tight">
                            GRADING & SKILLS
                        </h2>
                    </div>
                ) : (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="w-[1.8125rem] h-[1.6rem] lg:w-[2.025rem] lg:h-[1.8125rem] border-[3px] lg:border-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] transition-colors shadow-[1px_1px_0_0_rgba(0,0,0,1)] lg:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
                    >
                        <GraduationCap className="w-3 h-3 text-black dark:text-white dark:hover:text-black font-bold" />
                    </Button>
                )}

                {open && (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="w-[2.125rem] h-[2.125rem] border-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] text-black dark:text-white dark:hover:text-black transition-all shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:shadow-none hover:translate-x-1 hover:translate-y-1"
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
                        <Accordion
                            type="single"
                            collapsible
                            className="w-full space-y-3"
                            onClick={(e) => e.stopPropagation()} // Prevent handleContainerClick from intercepting accordion clicks
                        >
                            {isLoading ? (
                                <div className="text-center py-8 text-sm text-gray-500">
                                    Loading skills...
                                </div>
                            ) : Object.keys(skillStates).length === 0 ? (
                                <div className="text-center py-8 text-sm text-gray-500">
                                    No skills available yet
                                </div>
                            ) : (
                                Object.entries(skillStates).map(([skillName, stats]) => {
                                    const strength = Math.max(-2, Math.min(2, stats.memory_strength ?? 0));
                                    const normalizedStrength = ((strength + 2) / 4) * 100; // 0-100%
                                    const isPracticed = stats.practice_count > 0;

                                    // Determine strength level for color
                                    const getStrengthColor = () => {
                                        if (!isPracticed) return "gray";
                                        if (strength >= 1.5) return "emerald";
                                        if (strength >= 0.5) return "green";
                                        if (strength >= -0.5) return "yellow";
                                        if (strength >= -1.5) return "orange";
                                        return "red";
                                    };

                                    const strengthColor = getStrengthColor();
                                    const accuracyPercent = stats.practice_count > 0
                                        ? Math.round((stats.correct_count / stats.practice_count) * 100)
                                        : 0;

                                    const isCurrentSkill = skillName === currentSkill;

                                    return (
                                        <AccordionItem
                                            key={skillName}
                                            value={skillName}
                                            id={`skill-${skillName}`}
                                            className="border-none"
                                        >
                                            <div className={cn(
                                                "border-[4px] border-black dark:border-white transition-all duration-200 shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)]",
                                                isCurrentSkill && "bg-[#FFE500] dark:bg-[#FFD93D] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(0,0,0,1)] scale-[1.02]",
                                                !isCurrentSkill && isPracticed && "bg-[#FFFDF5] dark:bg-[#000000]",
                                                !isCurrentSkill && !isPracticed && "bg-[#FFFDF5] dark:bg-[#000000] opacity-60",
                                                isPracticed && "hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:translate-x-[-2px] hover:translate-y-[-2px]"
                                            )}>
                                                <AccordionTrigger className="hover:no-underline px-4 py-3 [&>svg]:hidden cursor-pointer group">
                                                    <div className="flex flex-col gap-2 w-full">
                                                        <div className="flex items-center justify-between w-full">
                                                            <span className={cn(
                                                                "font-black text-sm text-left tracking-tight",
                                                                isPracticed ? "text-black dark:text-white" : "text-black/50 dark:text-white/50"
                                                            )}>
                                                                {formatSkillName(stats.name)}
                                                            </span>
                                                            <div className={cn(
                                                                "px-2.5 py-0.5 border-[2px] border-black dark:border-white text-[10px] font-black uppercase",
                                                                strengthColor === "gray" && "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white",
                                                                strengthColor === "emerald" && "bg-[#4ADE80] text-black",
                                                                strengthColor === "green" && "bg-[#4ADE80] text-black",
                                                                strengthColor === "yellow" && "bg-[#FFD93D] text-black",
                                                                strengthColor === "orange" && "bg-[#FF6B6B] text-white",
                                                                strengthColor === "red" && "bg-[#FF6B6B] text-white"
                                                            )}>
                                                                {strength.toFixed(1)}
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
                                                                isPracticed
                                                                    ? "bg-[#FF6B6B] dark:bg-[#FF6B6B]"
                                                                    : "bg-[#FFFDF5] dark:bg-[#000000] opacity-60"
                                                            )}>
                                                                <div className="flex items-center gap-1.5 mb-1">
                                                                    <Target className={cn(
                                                                        "w-3.5 h-3.5 font-bold flex-shrink-0",
                                                                        isPracticed ? "text-white" : "text-black dark:text-white"
                                                                    )} />
                                                                    <span className={cn(
                                                                        "text-[9px] font-black uppercase leading-none",
                                                                        isPracticed ? "text-white" : "text-black dark:text-white"
                                                                    )}>Accuracy</span>
                                                                </div>
                                                                <div className="flex-1 flex flex-col justify-center">
                                                                    <div className={cn(
                                                                        "text-2xl font-black leading-none",
                                                                        isPracticed ? "text-white" : "text-black dark:text-white"
                                                                    )}>
                                                                        {accuracyPercent}%
                                                                    </div>
                                                                    <div className={cn(
                                                                        "text-[9px] mt-1 font-bold",
                                                                        isPracticed ? "text-white" : "text-black dark:text-white"
                                                                    )}>
                                                                        {stats.correct_count}/{stats.practice_count} correct
                                                                    </div>
                                                                </div>
                                                            </div>

                                                            {/* Practice Count Card */}
                                                            <div className={cn(
                                                                "aspect-square p-2.5 border-[3px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.2)] flex flex-col",
                                                                isPracticed
                                                                    ? "bg-[#C4B5FD] dark:bg-[#C4B5FD]"
                                                                    : "bg-[#FFFDF5] dark:bg-[#000000] opacity-60"
                                                            )}>
                                                                <div className="flex items-center gap-1.5 mb-1">
                                                                    <TrendingUp className={cn(
                                                                        "w-3.5 h-3.5 font-bold flex-shrink-0",
                                                                        isPracticed ? "text-black" : "text-black dark:text-white"
                                                                    )} />
                                                                    <span className={cn(
                                                                        "text-[9px] font-black uppercase leading-none",
                                                                        isPracticed ? "text-black" : "text-black dark:text-white"
                                                                    )}>Practice</span>
                                                                </div>
                                                                <div className="flex-1 flex flex-col justify-center">
                                                                    <div className={cn(
                                                                        "text-2xl font-black leading-none",
                                                                        isPracticed ? "text-black" : "text-black dark:text-white"
                                                                    )}>
                                                                        {stats.practice_count}
                                                                    </div>
                                                                    <div className={cn(
                                                                        "text-[9px] mt-1 font-bold",
                                                                        isPracticed ? "text-black" : "text-black dark:text-white"
                                                                    )}>
                                                                        total attempts
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        {/* Last Practice */}
                                                        <div className="mt-2 bg-[#FFFDF5] dark:bg-[#000000] p-2.5 border-[3px] border-black dark:border-white">
                                                            <div className={cn(
                                                                "flex items-center gap-2 text-xs font-bold",
                                                                isPracticed ? "text-black dark:text-white" : "text-black/50 dark:text-white/50"
                                                            )}>
                                                                <Clock className="w-3.5 h-3.5 font-bold flex-shrink-0" />
                                                                <span className="font-black uppercase text-[9px]">Last Practice:</span>
                                                                <span className="ml-auto text-[9px]">{formatTime(stats.last_practice_time)}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </AccordionContent>
                                            </div>
                                        </AccordionItem>
                                    );
                                }))}
                        </Accordion>
                    </div>
                ) : (
                    <div className="h-full w-full flex items-center justify-center cursor-pointer hover:bg-[#FFE500]/20 transition-colors pb-[140px]" onClick={onToggle}>
                        <div className="rotate-180 [writing-mode:vertical-rl] text-lg font-black tracking-widest uppercase whitespace-nowrap select-none text-black dark:text-white text-center leading-none">
                            GRADES & SKILLS
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
