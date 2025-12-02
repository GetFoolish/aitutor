import React, { useEffect, useRef } from "react";
import cn from "classnames";
import { GraduationCap, ChevronRight, ChevronLeft } from "lucide-react";
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
                        className="h-full overflow-y-auto overflow-x-hidden animate-in fade-in duration-500"
                    >
                        <Accordion type="single" collapsible className="w-full">
                            {Object.entries(skillStates).map(([skillName, stats]) => {
                                const strength = Math.max(-2, Math.min(2, stats.memory_strength ?? 0));
                                const hue = (strength + 2) * 30; // Maps -2..2 to 0..120 (Red..Green)

                                return (
                                    <AccordionItem
                                        key={skillName}
                                        value={skillName}
                                        id={`skill-${skillName}`}
                                        style={{ "--grade-hue": hue } as React.CSSProperties}
                                        className={cn(
                                            "border-b border-gray-200 dark:border-white/10 px-6",
                                            "bg-[hsl(var(--grade-hue),85%,90%)] dark:bg-[hsl(var(--grade-hue),85%,20%,0.3)]",
                                            "text-[hsl(var(--grade-hue),90%,20%)] dark:text-[hsl(var(--grade-hue),90%,90%)]"
                                        )}
                                    >
                                        <AccordionTrigger className="hover:no-underline py-4 [&>svg]:hidden cursor-pointer">
                                            <span className="font-semibold text-lg text-left">
                                                {formatSkillName(skillName)}
                                            </span>
                                        </AccordionTrigger>
                                        <AccordionContent>
                                            <div className="flex flex-col gap-2 text-sm opacity-90 pb-2">
                                                <div className="flex justify-between">
                                                    <span>Correctness</span>
                                                    <span className="font-medium">
                                                        {stats.correct_count}/{stats.practice_count}
                                                    </span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span>Last Practice</span>
                                                    <span className="font-medium">
                                                        {formatTime(stats.last_practice_time)}
                                                    </span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span>Memory Strength</span>
                                                    <span className="font-medium">
                                                        {stats.memory_strength?.toFixed(2) ?? "N/A"}
                                                    </span>
                                                </div>
                                            </div>
                                        </AccordionContent>
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
