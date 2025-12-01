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
}

const getMemoryStrengthColor = (strength: number | null | undefined) => {
    if (strength === null || strength === undefined)
        return "bg-gray-100 dark:bg-neutral-800 text-gray-900 dark:text-gray-100";

    if (strength >= 1.5)
        return "bg-green-100 dark:bg-green-900/30 text-green-900 dark:text-green-100";
    if (strength >= 0.5)
        return "bg-lime-100 dark:bg-lime-900/30 text-lime-900 dark:text-lime-100";
    if (strength >= -0.5)
        return "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-900 dark:text-yellow-100";
    if (strength >= -1.5)
        return "bg-orange-100 dark:bg-orange-900/30 text-orange-900 dark:text-orange-100";
    return "bg-red-100 dark:bg-red-900/30 text-red-900 dark:text-red-100";
};

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

export default function GradingSidebar({ open, onToggle }: GradingSidebarProps) {
    const skillStates = data.skill_states as Record<
        string,
        {
            memory_strength: number;
            last_practice_time: number | null;
            practice_count: number;
            correct_count: number;
        }
    >;

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

            <div className="flex-grow overflow-hidden relative">
                {open ? (
                    <div className="h-full overflow-y-auto overflow-x-hidden animate-in fade-in duration-500">
                        <Accordion type="single" collapsible className="w-full">
                            {Object.entries(skillStates).map(([skillName, stats]) => (
                                <AccordionItem
                                    key={skillName}
                                    value={skillName}
                                    className={cn(
                                        "border-b border-gray-200 dark:border-white/10 px-6",
                                        getMemoryStrengthColor(stats.memory_strength)
                                    )}
                                >
                                    <AccordionTrigger className="hover:no-underline py-4">
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
                            ))}
                        </Accordion>
                    </div>
                ) : (
                    <div className="h-full w-full flex items-center justify-center cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors" onClick={onToggle}>
                        <div className="rotate-180 [writing-mode:vertical-rl] text-lg font-bold tracking-widest uppercase whitespace-nowrap select-none bg-gradient-to-b from-purple-600 to-blue-600 dark:from-purple-400 dark:to-blue-400 text-transparent bg-clip-text">
                            Grades & Skills
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
