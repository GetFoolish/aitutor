/**
 * Streak Display - Duolingo-inspired design
 * Simple, clean, motivating
 */

import { useStreak } from "@/hooks/query-hooks/useStreak";
import cn from "classnames";

interface StreakDisplayProps {
    userId: string;
}

export default function StreakDisplay({ userId }: StreakDisplayProps) {
    const { data, isLoading } = useStreak({ userId });

    const streakCount = data?.current_streak || 0;

    // Check if practiced today
    const practicedToday = (() => {
        if (!data?.last_practice_date) return false;
        const today = new Date().toISOString().split('T')[0];
        const lastPractice = data.last_practice_date.split('T')[0];
        return today === lastPractice;
    })();

    // Streak is "hot" if practiced today, "cold" if at risk
    const isHot = practicedToday;
    const isCold = streakCount > 0 && !practicedToday;

    if (isLoading) {
        return (
            <div className="w-10 h-8 md:w-11 md:h-9 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse border-2 border-gray-200 dark:border-gray-700" />
        );
    }

    return (
        <button
            className={cn(
                "relative flex items-center gap-1 px-2 h-8 md:h-9 rounded-xl",
                "border-2 border-black dark:border-white",
                "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]",
                "hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
                "active:translate-x-1 active:translate-y-1 active:shadow-none",
                "transition-all duration-100",
                // Background based on state
                isHot && "bg-[#FF9600]", // Duolingo orange
                isCold && "bg-[#AFAFAF]", // Gray when at risk
                !isHot && !isCold && streakCount === 0 && "bg-[#E5E5E5] dark:bg-gray-700"
            )}
            title={
                isHot
                    ? `${streakCount} day streak! Keep it going!`
                    : isCold
                        ? `${streakCount} day streak at risk! Practice now!`
                        : "Start your streak today!"
            }
        >
            {/* Flame SVG - Duolingo style */}
            <svg
                viewBox="0 0 24 24"
                className={cn(
                    "w-5 h-5 md:w-6 md:h-6",
                    isHot && "text-white",
                    isCold && "text-white/80",
                    !isHot && !isCold && "text-gray-400"
                )}
                fill="currentColor"
            >
                <path d="M12 23C16.5 23 20 19.5 20 15C20 11.5 17.5 8.5 16 7C15.5 9 14.5 10 13 10C13 7 12 4 9 2C9 5 8 8 6 10C4.5 11.5 4 13.5 4 15C4 19.5 7.5 23 12 23Z"/>
                {/* Inner flame for hot streaks */}
                {isHot && (
                    <path
                        d="M12 20C14.5 20 16 18 16 15.5C16 13.5 15 12 14 11C13.8 12 13.2 12.5 12.5 12.5C12.5 11 12 9.5 10.5 8.5C10.5 10 10 11.5 9 12.5C8.2 13.3 8 14.3 8 15.5C8 18 9.5 20 12 20Z"
                        className="text-[#FFC800]"
                        fill="currentColor"
                    />
                )}
            </svg>

            {/* Streak Number */}
            <span className={cn(
                "text-base md:text-lg font-black tabular-nums pr-0.5",
                isHot && "text-white",
                isCold && "text-white",
                !isHot && !isCold && "text-gray-500 dark:text-gray-400"
            )}>
                {streakCount}
            </span>

            {/* Freeze indicator for cold streaks */}
            {isCold && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-400 rounded-full border border-black flex items-center justify-center">
                    <span className="text-[8px]">❄️</span>
                </div>
            )}
        </button>
    );
}
