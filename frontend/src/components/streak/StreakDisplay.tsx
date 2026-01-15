/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Flame, AlertTriangle } from "lucide-react";
import { useStreak } from "@/hooks/query-hooks/useStreak";
import cn from "classnames";

interface StreakDisplayProps {
    userId: string;
}

export default function StreakDisplay({ userId }: StreakDisplayProps) {
    const { data, isLoading, isError } = useStreak({ userId });

    // Check if practiced today
    const isPracticedToday = () => {
        if (!data?.last_practice_date) return false;
        const today = new Date().toISOString().split('T')[0];
        const lastPractice = data.last_practice_date.split('T')[0];
        return today === lastPractice;
    };

    const practicedToday = isPracticedToday();
    const streakCount = data?.current_streak || 0;

    // Loading state
    if (isLoading) {
        return (
            <div className="flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
                <Flame className="h-4 w-4 md:h-5 md:w-5 text-gray-400" />
                <div className="flex flex-col">
                    <span className="text-xs md:text-sm font-bold text-gray-400">--</span>
                    <span className="text-[10px] md:text-xs text-gray-400">days</span>
                </div>
            </div>
        );
    }

    // Error state
    if (isError) {
        return (
            <div className="flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 border-[2px] border-black dark:border-white bg-[#FF6B6B] shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
                <AlertTriangle className="h-4 w-4 md:h-5 md:w-5 text-white" />
                <span className="text-xs md:text-sm font-bold text-white">Error</span>
            </div>
        );
    }

    // Determine background color based on state
    const bgColor = practicedToday
        ? "bg-[#6BCF7F]" // Green for practiced today
        : streakCount > 0
            ? "bg-[#FFD93D]" // Yellow warning for at risk
            : "bg-[#FFFDF5] dark:bg-[#000000]"; // Default

    return (
        <div
            className={cn(
                "flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 border-[2px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] transition-all duration-300",
                bgColor
            )}
        >
            <Flame
                className={cn(
                    "h-4 w-4 md:h-5 md:w-5",
                    practicedToday && "text-[#FF6B6B] animate-pulse",
                    !practicedToday && streakCount > 0 && "text-[#FF6B6B]",
                    streakCount === 0 && "text-gray-400 dark:text-gray-600"
                )}
            />
            <div className="flex flex-col leading-tight">
                <span className="text-sm md:text-base lg:text-lg font-black text-black dark:text-white">
                    {streakCount}
                </span>
                <span className="text-[10px] md:text-xs text-black dark:text-white font-bold">
                    {streakCount === 1 ? 'day' : 'days'}
                </span>
            </div>
        </div>
    );
}
