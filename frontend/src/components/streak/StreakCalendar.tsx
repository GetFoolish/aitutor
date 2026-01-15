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

import { useStreakCalendar } from "@/hooks/query-hooks/useStreak";
import cn from "classnames";
import { AlertTriangle } from "lucide-react";

interface StreakCalendarProps {
    userId: string;
}

export default function StreakCalendar({ userId }: StreakCalendarProps) {
    const { data, isLoading, isError } = useStreakCalendar({ userId });

    // Generate last 30 days
    const generateLast30Days = () => {
        const days = [];
        const today = new Date();
        for (let i = 29; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(today.getDate() - i);
            days.push(date);
        }
        return days;
    };

    const last30Days = generateLast30Days();
    const todayStr = new Date().toISOString().split('T')[0];

    // Check if a date is practiced
    const isPracticed = (date: Date) => {
        if (!data?.practice_dates) return false;
        const dateStr = date.toISOString().split('T')[0];
        return data.practice_dates.includes(dateStr);
    };

    // Check if a date is today
    const isToday = (date: Date) => {
        const dateStr = date.toISOString().split('T')[0];
        return dateStr === todayStr;
    };

    // Loading state
    if (isLoading) {
        return (
            <div className="border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] p-3 md:p-4">
                <h3 className="text-sm md:text-base font-black text-black dark:text-white mb-2 md:mb-3">
                    Practice Calendar
                </h3>
                <div className="grid grid-cols-7 gap-1 md:gap-1.5">
                    {Array.from({ length: 30 }).map((_, i) => (
                        <div
                            key={i}
                            className="aspect-square border-[2px] border-black dark:border-white bg-gray-200 dark:bg-gray-800 animate-pulse"
                        />
                    ))}
                </div>
            </div>
        );
    }

    // Error state
    if (isError) {
        return (
            <div className="border-[2px] border-black dark:border-white bg-[#FF6B6B] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] p-3 md:p-4">
                <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 md:h-5 md:w-5 text-white" />
                    <span className="text-sm md:text-base font-bold text-white">
                        Failed to load calendar
                    </span>
                </div>
            </div>
        );
    }

    return (
        <div className="border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] p-3 md:p-4">
            <h3 className="text-sm md:text-base font-black text-black dark:text-white mb-2 md:mb-3">
                Practice Calendar
            </h3>
            <div className="grid grid-cols-7 gap-1 md:gap-1.5">
                {last30Days.map((date, index) => {
                    const practiced = isPracticed(date);
                    const today = isToday(date);
                    const dayOfMonth = date.getDate();

                    return (
                        <div
                            key={index}
                            className={cn(
                                "aspect-square border-[2px] border-black dark:border-white flex items-center justify-center text-[10px] md:text-xs font-bold transition-all duration-200",
                                practiced && "bg-[#6BCF7F] text-black",
                                !practiced && "bg-[#FFFDF5] dark:bg-[#1A1A1A] text-gray-400 dark:text-gray-600",
                                today && "ring-2 ring-[#FFD93D] ring-offset-0"
                            )}
                            title={date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        >
                            {dayOfMonth}
                        </div>
                    );
                })}
            </div>
            <div className="mt-2 md:mt-3 flex items-center gap-3 md:gap-4 text-[10px] md:text-xs">
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 md:w-4 md:h-4 border-[2px] border-black dark:border-white bg-[#6BCF7F]" />
                    <span className="text-black dark:text-white font-bold">Practiced</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 md:w-4 md:h-4 border-[2px] border-black dark:border-white ring-2 ring-[#FFD93D] bg-[#FFFDF5] dark:bg-[#1A1A1A]" />
                    <span className="text-black dark:text-white font-bold">Today</span>
                </div>
            </div>
        </div>
    );
}
