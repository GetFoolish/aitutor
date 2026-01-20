import React from "react";
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { ChartConfig } from "@/components/ui/chart";
import { usePracticeHistory } from "../../hooks/query-hooks/usePracticeHistory";
import { TrendingUp, BarChart3 } from "lucide-react";
import cn from "classnames";

interface PerformanceChartProps {
    className?: string;
}

const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
    });
};

const formatSkillName = (name: string) => {
    return name
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
};

export default function PerformanceChart({ className }: PerformanceChartProps) {
    // Fetch a large number of sessions to show comprehensive charts
    const { data: practiceData, isLoading } = usePracticeHistory({
        page: 1,
        limit: 50,
        enabled: true,
    });

    const sessions = practiceData?.sessions || [];

    // Process data for accuracy trend line chart
    const accuracyData = React.useMemo(() => {
        return sessions
            .map((session) => ({
                date: formatDate(session.date),
                timestamp: session.date,
                accuracy: Math.round(session.accuracy * 100),
            }))
            .sort((a, b) => a.timestamp - b.timestamp);
    }, [sessions]);

    // Process data for questions per skill bar chart
    const skillData = React.useMemo(() => {
        const skillCounts: Record<string, number> = {};

        sessions.forEach((session) => {
            session.skills_practiced.forEach((skill) => {
                const formattedSkill = formatSkillName(skill);
                skillCounts[formattedSkill] = (skillCounts[formattedSkill] || 0) + session.question_count;
            });
        });

        return Object.entries(skillCounts)
            .map(([skill, count]) => ({
                skill,
                questions: count,
            }))
            .sort((a, b) => b.questions - a.questions)
            .slice(0, 8); // Show top 8 skills
    }, [sessions]);

    const accuracyChartConfig = {
        accuracy: {
            label: "Accuracy",
            color: "hsl(var(--chart-1))",
        },
    } satisfies ChartConfig;

    const skillChartConfig = {
        questions: {
            label: "Questions",
            color: "hsl(var(--chart-2))",
        },
    } satisfies ChartConfig;

    if (isLoading) {
        return (
            <div className={cn("p-4 space-y-4", className)}>
                <div className="text-center py-8 text-sm text-gray-500">
                    Loading performance data...
                </div>
            </div>
        );
    }

    if (sessions.length === 0) {
        return (
            <div className={cn("p-4 space-y-4", className)}>
                <div className="text-center py-8 text-sm text-gray-500">
                    No practice data available yet
                </div>
            </div>
        );
    }

    return (
        <div className={cn("p-4 space-y-6", className)}>
            {/* Accuracy Trend Chart */}
            <div className="border-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.2)]">
                <div className="px-4 py-3 border-b-[3px] border-black dark:border-white bg-[#4ADE80] flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 font-bold text-black" />
                    <h3 className="text-xs font-black uppercase tracking-tight text-black">
                        Accuracy Trend
                    </h3>
                </div>
                <div className="p-4">
                    <ChartContainer config={accuracyChartConfig} className="h-[200px] w-full">
                        <LineChart data={accuracyData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="date"
                                tick={{ fontSize: 10, fontWeight: "bold" }}
                                stroke="currentColor"
                            />
                            <YAxis
                                domain={[0, 100]}
                                tick={{ fontSize: 10, fontWeight: "bold" }}
                                stroke="currentColor"
                                label={{
                                    value: "Accuracy %",
                                    angle: -90,
                                    position: "insideLeft",
                                    style: { fontSize: 10, fontWeight: "bold" },
                                }}
                            />
                            <ChartTooltip content={<ChartTooltipContent />} />
                            <Line
                                type="monotone"
                                dataKey="accuracy"
                                stroke="#4ADE80"
                                strokeWidth={3}
                                dot={{ fill: "#4ADE80", strokeWidth: 2, r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                        </LineChart>
                    </ChartContainer>
                </div>
            </div>

            {/* Questions per Skill Chart */}
            <div className="border-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.2)]">
                <div className="px-4 py-3 border-b-[3px] border-black dark:border-white bg-[#C4B5FD] flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 font-bold text-black" />
                    <h3 className="text-xs font-black uppercase tracking-tight text-black">
                        Questions per Skill
                    </h3>
                </div>
                <div className="p-4">
                    <ChartContainer config={skillChartConfig} className="h-[250px] w-full">
                        <BarChart data={skillData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="skill"
                                tick={{ fontSize: 9, fontWeight: "bold" }}
                                stroke="currentColor"
                                angle={-45}
                                textAnchor="end"
                                height={80}
                            />
                            <YAxis
                                tick={{ fontSize: 10, fontWeight: "bold" }}
                                stroke="currentColor"
                                label={{
                                    value: "Questions",
                                    angle: -90,
                                    position: "insideLeft",
                                    style: { fontSize: 10, fontWeight: "bold" },
                                }}
                            />
                            <ChartTooltip content={<ChartTooltipContent />} />
                            <Bar
                                dataKey="questions"
                                fill="#C4B5FD"
                                stroke="#000000"
                                strokeWidth={2}
                                radius={[4, 4, 0, 0]}
                            />
                        </BarChart>
                    </ChartContainer>
                </div>
            </div>
        </div>
    );
}
