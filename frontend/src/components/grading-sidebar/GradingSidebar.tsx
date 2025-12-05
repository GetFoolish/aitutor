import React, { useEffect, useRef } from "react";
import cn from "classnames";
import { GraduationCap, ChevronRight, ChevronLeft, TrendingUp, Clock, Target } from "lucide-react";
import data from "../../../data.json";
import { Button } from "@/components/ui/button";
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
    const skillStates = data.skill_states as Record<
        string,
        {
            memory_strength: number;
            last_practice_time: number | null;
            practice_count: number;
            correct_count: number;
        }
    >;

    const scrollToSkill = (skill: string) => {
        if (!scrollContainerRef.current) return;

        const element = document.getElementById(`skill-${skill}`);
        if (element) {
            element.scrollIntoView({ behavior: "smooth", block: "center" });
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
                "fixed top-[70px] left-0 flex flex-col border-r border-white/20 dark:border-white/5 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-xl transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform shadow-2xl",
                "h-[calc(100vh-70px)]",
                open ? "w-[420px]" : "w-[60px]"
            )}
        >
            <header className={cn(
                "flex items-center h-[70px] border-b border-white/20 dark:border-white/5 shrink-0 overflow-hidden transition-all duration-300",
                open ? "justify-between px-6" : "justify-center"
            )}>
                {open ? (
                    <div className="flex items-center gap-2 animate-in fade-in slide-in-from-left-4 duration-300">
                        <GraduationCap className="w-5 h-5 text-purple-500" />
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white whitespace-nowrap">
                            Grading & Skills
                        </h2>
                    </div>
                ) : (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="text-gray-500 hover:text-purple-600 transition-colors"
                    >
                        <GraduationCap className="w-6 h-6" />
                    </Button>
                )}

                {open && (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onToggle}
                        className="text-gray-500 hover:text-gray-900 dark:hover:text-white"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </Button>
                )}
            </header>

            <div className="flex-grow overflow-hidden relative" onClick={handleContainerClick}>
                {open ? (
                    <div
                        ref={scrollContainerRef}
                        className="h-full overflow-y-auto overflow-x-hidden animate-in fade-in duration-500 px-4 py-4"
                    >
                        <Accordion type="single" collapsible className="w-full space-y-3">
                            {Object.entries(skillStates).map(([skillName, stats]) => {
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

                                return (
                                    <AccordionItem
                                        key={skillName}
                                        value={skillName}
                                        id={`skill-${skillName}`}
                                        className="border-none"
                                    >
                                        <div className={cn(
                                            "rounded-xl border transition-all duration-200",
                                            isPracticed ? "bg-white/50 dark:bg-neutral-800/50" : "bg-gray-100/50 dark:bg-neutral-900/50",
                                            "border-gray-200/50 dark:border-neutral-700/50",
                                            isPracticed && "hover:shadow-md hover:border-purple-200 dark:hover:border-purple-800/50",
                                            "backdrop-blur-sm",
                                            !isPracticed && "opacity-60"
                                        )}>
                                            <AccordionTrigger className="hover:no-underline px-4 py-3 [&>svg]:hidden cursor-pointer group">
                                                <div className="flex flex-col gap-2 w-full">
                                                    <div className="flex items-center justify-between w-full">
                                                        <span className={cn(
                                                            "font-semibold text-base text-left",
                                                            isPracticed ? "text-gray-900 dark:text-white" : "text-gray-500 dark:text-gray-500"
                                                        )}>
                                                            {formatSkillName(skillName)}
                                                        </span>
                                                        <div className={cn(
                                                            "px-2.5 py-0.5 rounded-full text-xs font-medium",
                                                            strengthColor === "gray" && "bg-gray-200 dark:bg-gray-800/50 text-gray-600 dark:text-gray-500",
                                                            strengthColor === "emerald" && "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
                                                            strengthColor === "green" && "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400",
                                                            strengthColor === "yellow" && "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400",
                                                            strengthColor === "orange" && "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400",
                                                            strengthColor === "red" && "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                                                        )}>
                                                            {strength.toFixed(1)}
                                                        </div>
                                                    </div>

                                                    {/* Progress bar */}
                                                    <div className="w-full bg-gray-200 dark:bg-neutral-700 rounded-full h-1.5 overflow-hidden">
                                                        <div
                                                            className={cn(
                                                                "h-full transition-all duration-300 rounded-full",
                                                                strengthColor === "gray" && "bg-gray-400 dark:bg-gray-600",
                                                                strengthColor === "emerald" && "bg-gradient-to-r from-emerald-500 to-emerald-400",
                                                                strengthColor === "green" && "bg-gradient-to-r from-green-500 to-green-400",
                                                                strengthColor === "yellow" && "bg-gradient-to-r from-yellow-500 to-yellow-400",
                                                                strengthColor === "orange" && "bg-gradient-to-r from-orange-500 to-orange-400",
                                                                strengthColor === "red" && "bg-gradient-to-r from-red-500 to-red-400"
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
                                                            "rounded-lg p-3 border",
                                                            isPracticed
                                                                ? "bg-gradient-to-br from-purple-50 to-purple-100/50 dark:from-purple-900/20 dark:to-purple-800/10 border-purple-200/50 dark:border-purple-800/30"
                                                                : "bg-gray-100 dark:bg-gray-800/30 border-gray-300/50 dark:border-gray-700/50"
                                                        )}>
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <Target className={cn(
                                                                    "w-3.5 h-3.5",
                                                                    isPracticed ? "text-purple-600 dark:text-purple-400" : "text-gray-500 dark:text-gray-600"
                                                                )} />
                                                                <span className={cn(
                                                                    "text-xs font-medium",
                                                                    isPracticed ? "text-purple-900 dark:text-purple-300" : "text-gray-600 dark:text-gray-500"
                                                                )}>Accuracy</span>
                                                            </div>
                                                            <div className={cn(
                                                                "text-2xl font-bold",
                                                                isPracticed ? "text-purple-700 dark:text-purple-400" : "text-gray-600 dark:text-gray-500"
                                                            )}>
                                                                {accuracyPercent}%
                                                            </div>
                                                            <div className={cn(
                                                                "text-xs mt-1",
                                                                isPracticed ? "text-purple-600/70 dark:text-purple-400/70" : "text-gray-500 dark:text-gray-600"
                                                            )}>
                                                                {stats.correct_count}/{stats.practice_count} correct
                                                            </div>
                                                        </div>

                                                        {/* Practice Count Card */}
                                                        <div className={cn(
                                                            "rounded-lg p-3 border",
                                                            isPracticed
                                                                ? "bg-gradient-to-br from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-800/10 border-blue-200/50 dark:border-blue-800/30"
                                                                : "bg-gray-100 dark:bg-gray-800/30 border-gray-300/50 dark:border-gray-700/50"
                                                        )}>
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <TrendingUp className={cn(
                                                                    "w-3.5 h-3.5",
                                                                    isPracticed ? "text-blue-600 dark:text-blue-400" : "text-gray-500 dark:text-gray-600"
                                                                )} />
                                                                <span className={cn(
                                                                    "text-xs font-medium",
                                                                    isPracticed ? "text-blue-900 dark:text-blue-300" : "text-gray-600 dark:text-gray-500"
                                                                )}>Practice</span>
                                                            </div>
                                                            <div className={cn(
                                                                "text-2xl font-bold",
                                                                isPracticed ? "text-blue-700 dark:text-blue-400" : "text-gray-600 dark:text-gray-500"
                                                            )}>
                                                                {stats.practice_count}
                                                            </div>
                                                            <div className={cn(
                                                                "text-xs mt-1",
                                                                isPracticed ? "text-blue-600/70 dark:text-blue-400/70" : "text-gray-500 dark:text-gray-600"
                                                            )}>
                                                                total attempts
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Last Practice */}
                                                    <div className="mt-3 bg-gray-50 dark:bg-neutral-800/50 rounded-lg p-3 border border-gray-200/50 dark:border-neutral-700/50">
                                                        <div className={cn(
                                                            "flex items-center gap-2 text-xs",
                                                            isPracticed ? "text-gray-600 dark:text-gray-400" : "text-gray-500 dark:text-gray-600"
                                                        )}>
                                                            <Clock className="w-3.5 h-3.5" />
                                                            <span className="font-medium">Last practiced:</span>
                                                            <span className="ml-auto">{formatTime(stats.last_practice_time)}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </AccordionContent>
                                        </div>
                                    </AccordionItem>
                                );
                            })}
                        </Accordion>
                    </div>
                ) : (
                    <div className="h-full w-full flex items-center justify-center cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors pb-[140px]" onClick={onToggle}>
                        <div className="rotate-180 [writing-mode:vertical-rl] text-lg font-bold tracking-widest uppercase whitespace-nowrap select-none bg-gradient-to-b from-purple-600 to-blue-600 dark:from-purple-400 dark:to-blue-400 text-transparent bg-clip-text text-center leading-none">
                            Grades & Skills
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
