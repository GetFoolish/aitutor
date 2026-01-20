/**
 * Badge Display - Duolingo-inspired design
 * Simple circles, clean icons, satisfying progress
 */

import cn from "classnames";
import { Trophy, Flame, Target, Zap, Star, Crown, BookOpen, Award } from "lucide-react";

// Simple badge data
const BADGES = [
  { id: "first_lesson", name: "First Steps", icon: Star, color: "#58CC02", earned: true },
  { id: "streak_3", name: "3 Day Streak", icon: Flame, color: "#FF9600", earned: true },
  { id: "streak_7", name: "Week Warrior", icon: Flame, color: "#FF9600", earned: true, progress: 100 },
  { id: "streak_30", name: "Dedicated", icon: Flame, color: "#FF9600", earned: false, progress: 17 },
  { id: "questions_10", name: "10 Questions", icon: Target, color: "#1CB0F6", earned: true },
  { id: "questions_50", name: "50 Questions", icon: Target, color: "#1CB0F6", earned: false, progress: 44 },
  { id: "questions_100", name: "Century", icon: Target, color: "#1CB0F6", earned: false, progress: 22 },
  { id: "perfect_5", name: "On Fire", icon: Zap, color: "#FF4B4B", earned: true },
  { id: "perfect_10", name: "Unstoppable", icon: Zap, color: "#FF4B4B", earned: false, progress: 70 },
  { id: "mastery_1", name: "Skill Master", icon: Crown, color: "#CE82FF", earned: false, progress: 60 },
  { id: "explorer", name: "Explorer", icon: BookOpen, color: "#58CC02", earned: false, progress: 0 },
  { id: "champion", name: "Champion", icon: Trophy, color: "#FFC800", earned: false, progress: 0 },
];

interface BadgeProps {
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  earned: boolean;
  progress?: number;
}

function Badge({ name, icon: Icon, color, earned, progress = 0 }: BadgeProps) {
  const size = 72;
  const strokeWidth = 4;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Badge Circle */}
      <div className="relative">
        {/* Progress Ring (only for non-earned with progress) */}
        {!earned && progress > 0 && (
          <svg
            width={size}
            height={size}
            className="absolute inset-0 -rotate-90"
          >
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="#E5E5E5"
              strokeWidth={strokeWidth}
            />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-700"
            />
          </svg>
        )}

        {/* Badge Icon Container */}
        <div
          className={cn(
            "w-[72px] h-[72px] rounded-full flex items-center justify-center",
            "border-4 transition-all duration-300",
            earned
              ? "border-current shadow-lg hover:scale-110 cursor-pointer"
              : progress > 0
                ? "border-transparent"
                : "border-gray-200 dark:border-gray-700"
          )}
          style={{
            backgroundColor: earned ? color : "#F7F7F7",
            borderColor: earned ? color : undefined,
            boxShadow: earned ? `0 4px 12px ${color}50` : undefined,
          }}
        >
          <Icon
            className={cn(
              "w-8 h-8 transition-all",
              earned ? "text-white" : "text-gray-300 dark:text-gray-600"
            )}
          />
        </div>

        {/* Checkmark for earned */}
        {earned && (
          <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-white rounded-full border-2 border-[#58CC02] flex items-center justify-center shadow-md">
            <svg className="w-4 h-4 text-[#58CC02]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
      </div>

      {/* Badge Name */}
      <span className={cn(
        "text-xs font-bold text-center max-w-[80px] leading-tight",
        earned ? "text-gray-800 dark:text-white" : "text-gray-400 dark:text-gray-500"
      )}>
        {name}
      </span>
    </div>
  );
}

export default function BadgeDisplay({ className }: { userId?: string; className?: string }) {
  const earnedCount = BADGES.filter(b => b.earned).length;

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-[#FFC800] rounded-2xl flex items-center justify-center shadow-lg">
            <Trophy className="w-7 h-7 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-black text-gray-800 dark:text-white">Achievements</h2>
            <p className="text-sm text-gray-500">{earnedCount} of {BADGES.length} earned</p>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-3 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[#58CC02] to-[#89E219] rounded-full transition-all duration-500"
          style={{ width: `${(earnedCount / BADGES.length) * 100}%` }}
        />
      </div>

      {/* Badges Grid */}
      <div className="grid grid-cols-4 md:grid-cols-6 gap-6 py-4">
        {BADGES.map((badge) => (
          <Badge
            key={badge.id}
            name={badge.name}
            icon={badge.icon}
            color={badge.color}
            earned={badge.earned}
            progress={badge.progress}
          />
        ))}
      </div>
    </div>
  );
}
