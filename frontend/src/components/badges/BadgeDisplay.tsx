import React from "react";
import cn from "classnames";
import { Medal, Flame, CheckCircle, Star, Lock, Trophy, Zap, Target, Crown, Sparkles } from "lucide-react";
import { useBadges, type Badge, type BadgeProgress } from "@/hooks/query-hooks/useBadges";

interface BadgeDisplayProps {
  userId: string;
  className?: string;
}

// Category styling with vibrant colors
const categoryStyles: Record<string, { bg: string; accent: string; icon: React.ComponentType<{ className?: string }> }> = {
  skill_mastery: { bg: "from-amber-400 to-orange-500", accent: "#F59E0B", icon: Crown },
  streak: { bg: "from-rose-400 to-pink-600", accent: "#EC4899", icon: Flame },
  question_count: { bg: "from-cyan-400 to-blue-600", accent: "#0EA5E9", icon: Target },
  perfect_score: { bg: "from-emerald-400 to-green-600", accent: "#10B981", icon: Sparkles },
};

// Tier styling for mastery badges
const tierStyles: Record<string, { gradient: string; glow: string }> = {
  bronze: { gradient: "from-amber-600 to-orange-700", glow: "shadow-amber-500/50" },
  silver: { gradient: "from-slate-300 to-slate-500", glow: "shadow-slate-400/50" },
  gold: { gradient: "from-yellow-300 to-amber-500", glow: "shadow-yellow-400/50" },
};

interface BadgeCardProps {
  badge: Badge;
  progress: BadgeProgress;
  categoryStyle: { bg: string; accent: string; icon: React.ComponentType<{ className?: string }> };
}

function CircularProgress({ percentage, size = 80, strokeWidth = 6, accentColor }: { percentage: number; size?: number; strokeWidth?: number; accentColor: string }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-gray-200 dark:text-gray-700"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={accentColor}
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-500 ease-out"
      />
    </svg>
  );
}

function BadgeCard({ badge, progress, categoryStyle }: BadgeCardProps) {
  const percentage = Math.min(100, Math.floor(progress.percentage || 0));
  // Badge is earned if explicitly marked OR if progress is 100%
  const isEarned = progress.earned || percentage >= 100;
  const CategoryIcon = categoryStyle.icon;
  const tierStyle = badge.tier ? tierStyles[badge.tier] : null;

  return (
    <div
      className={cn(
        "group relative rounded-xl p-3 transition-all duration-300 cursor-pointer",
        "border-[3px] border-black dark:border-white",
        "shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)]",
        "hover:shadow-[5px_5px_0_0_rgba(0,0,0,1)] hover:-translate-x-0.5 hover:-translate-y-0.5",
        isEarned
          ? "bg-gradient-to-br " + (tierStyle?.gradient || categoryStyle.bg)
          : "bg-white dark:bg-gray-900"
      )}
    >
      {/* Sparkle effect for earned badges */}
      {isEarned && (
        <div className="absolute inset-0 overflow-hidden rounded-xl pointer-events-none">
          <div className="absolute top-1 right-1 animate-pulse">
            <Sparkles className="w-3 h-3 text-white/80" />
          </div>
        </div>
      )}

      {/* Badge Icon with Progress Ring */}
      <div className="flex flex-col items-center text-center">
        <div className="relative mb-2">
          {!isEarned && percentage > 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <CircularProgress percentage={percentage} size={56} strokeWidth={4} accentColor={categoryStyle.accent} />
            </div>
          )}
          <div
            className={cn(
              "w-12 h-12 rounded-xl flex items-center justify-center",
              "border-[2px] border-black dark:border-white",
              "shadow-[2px_2px_0_0_rgba(0,0,0,1)]",
              "transition-transform duration-300 group-hover:scale-110",
              isEarned
                ? "bg-white/90 dark:bg-black/30"
                : "bg-gray-100 dark:bg-gray-800"
            )}
          >
            {isEarned ? (
              <CategoryIcon className="w-6 h-6 text-black dark:text-white" />
            ) : (
              <Lock className="w-5 h-5 text-gray-400 dark:text-gray-500" />
            )}
          </div>

          {/* Earned checkmark */}
          {isEarned && (
            <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-[#4ADE80] rounded-full border-[2px] border-black flex items-center justify-center">
              <CheckCircle className="w-3 h-3 text-black" />
            </div>
          )}
        </div>

        {/* Badge Name */}
        <h3 className={cn(
          "font-black uppercase text-xs tracking-tight leading-tight mb-1 px-1",
          isEarned ? "text-white dark:text-white" : "text-black dark:text-white"
        )}>
          {badge.name}
        </h3>

        {/* Tier Badge */}
        {badge.tier && (
          <span className={cn(
            "inline-block px-1.5 py-0.5 rounded text-[8px] font-bold uppercase mb-1",
            "border border-black dark:border-white",
            isEarned
              ? "bg-white/90 text-black"
              : "bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
          )}>
            {badge.tier}
          </span>
        )}

        {/* Description */}
        <p className={cn(
          "text-[10px] leading-tight mb-2 px-1",
          isEarned ? "text-white/90" : "text-gray-500 dark:text-gray-400"
        )}>
          {badge.description}
        </p>

        {/* Progress or Earned Status */}
        {isEarned ? (
          <div className="flex items-center justify-center gap-1 px-3 py-1 bg-[#4ADE80] rounded-lg border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
            <CheckCircle className="w-4 h-4 text-black" />
            <span className="text-xs font-black text-black uppercase">Earned!</span>
          </div>
        ) : (
          <div className="w-full px-1">
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full border-2 border-black overflow-hidden mb-1">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${percentage}%`,
                  backgroundColor: categoryStyle.accent
                }}
              />
            </div>
            <p className="text-[10px] font-bold text-center text-gray-600 dark:text-gray-400">
              {percentage}% complete
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Dummy data to show different badge states
const DUMMY_BADGES: Badge[] = [
  // Skill Mastery - show different tiers
  { badge_id: "bronze_master", name: "Bronze Master", description: "Achieve 50% mastery in any skill", badge_type: "skill_mastery", tier: "bronze", icon: "medal", requirement: 50 },
  { badge_id: "silver_master", name: "Silver Master", description: "Achieve 75% mastery in any skill", badge_type: "skill_mastery", tier: "silver", icon: "medal", requirement: 75 },
  { badge_id: "gold_master", name: "Gold Master", description: "Achieve 90% mastery in any skill", badge_type: "skill_mastery", tier: "gold", icon: "medal", requirement: 90 },
  // Streaks
  { badge_id: "streak_3", name: "3-Day Streak", description: "Practice for 3 days in a row", badge_type: "streak", icon: "flame", requirement: 3 },
  { badge_id: "streak_7", name: "Week Warrior", description: "Practice for 7 days in a row", badge_type: "streak", icon: "flame", requirement: 7 },
  { badge_id: "streak_30", name: "Monthly Master", description: "Practice for 30 days in a row", badge_type: "streak", icon: "flame", requirement: 30 },
  // Question Count
  { badge_id: "questions_10", name: "Getting Started", description: "Answer 10 questions", badge_type: "question_count", icon: "target", requirement: 10 },
  { badge_id: "questions_50", name: "Dedicated Learner", description: "Answer 50 questions", badge_type: "question_count", icon: "target", requirement: 50 },
  { badge_id: "questions_100", name: "Century Club", description: "Answer 100 questions", badge_type: "question_count", icon: "target", requirement: 100 },
  // Perfect Scores
  { badge_id: "perfect_5", name: "Perfect Start", description: "Get 5 correct answers in a row", badge_type: "perfect_score", icon: "star", requirement: 5 },
  { badge_id: "perfect_10", name: "Perfect Ten", description: "Get 10 correct answers in a row", badge_type: "perfect_score", icon: "star", requirement: 10 },
  { badge_id: "perfect_25", name: "Perfection Master", description: "Get 25 correct answers in a row", badge_type: "perfect_score", icon: "star", requirement: 25 },
];

// Dummy progress showing different states
const DUMMY_PROGRESS: Record<string, BadgeProgress> = {
  // EARNED badges (100% or marked as earned)
  "bronze_master": { current: 50, required: 50, percentage: 100, earned: true },
  "streak_3": { current: 3, required: 3, percentage: 100, earned: true },
  "questions_10": { current: 10, required: 10, percentage: 100, earned: true },
  "perfect_5": { current: 5, required: 5, percentage: 100, earned: true },

  // IN PROGRESS badges (partial completion)
  "silver_master": { current: 56, required: 75, percentage: 75, earned: false },
  "streak_7": { current: 4, required: 7, percentage: 57, earned: false },
  "questions_50": { current: 22, required: 50, percentage: 44, earned: false },
  "perfect_10": { current: 7, required: 10, percentage: 70, earned: false },

  // LOCKED badges (0% or very low)
  "gold_master": { current: 0, required: 90, percentage: 0, earned: false },
  "streak_30": { current: 0, required: 30, percentage: 0, earned: false },
  "questions_100": { current: 22, required: 100, percentage: 22, earned: false },
  "perfect_25": { current: 0, required: 25, percentage: 0, earned: false },
};

export default function BadgeDisplay({ userId, className }: BadgeDisplayProps) {
  // TEMPORARILY using dummy data to demo all badge states
  // TODO: Remove this and use real data: const { data, isLoading, error } = useBadges({ userId });

  // Always use dummy data for now to show the design
  const badges = DUMMY_BADGES;
  const userProgress = DUMMY_PROGRESS;

  // Calculate earned count
  const earnedCount = badges.filter(b => {
    const prog = userProgress[b.badge_id];
    return prog?.earned || (prog?.percentage ?? 0) >= 100;
  }).length;

  // Group badges by type for organized display
  const badgesByType: Record<string, Badge[]> = {
    skill_mastery: [],
    streak: [],
    question_count: [],
    perfect_score: [],
  };

  badges.forEach((badge) => {
    if (badgesByType[badge.badge_type]) {
      badgesByType[badge.badge_type].push(badge);
    }
  });

  const typeLabels: Record<string, string> = {
    skill_mastery: "Skill Mastery",
    streak: "Practice Streaks",
    question_count: "Question Milestones",
    perfect_score: "Perfect Scores",
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header Summary */}
      <div className="flex items-center justify-between pb-4 border-b-[3px] border-black dark:border-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl border-[3px] border-black flex items-center justify-center shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
            <Trophy className="w-5 h-5 text-white" />
          </div>
          <h2 className="text-lg lg:text-xl font-black uppercase tracking-tight">
            Your Badges
          </h2>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-violet-500 to-purple-600 rounded-full border-[3px] border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
          <span className="text-white font-black text-lg">{earnedCount}</span>
          <span className="text-white/70 font-bold">/</span>
          <span className="text-white/70 font-bold">{badges.length}</span>
        </div>
      </div>

      {/* Badge Grid by Type */}
      {Object.entries(badgesByType).map(([type, typeBadges]) => {
        if (typeBadges.length === 0) return null;
        const style = categoryStyles[type] || categoryStyles.skill_mastery;
        const CategoryIcon = style.icon;

        return (
          <div key={type} className="space-y-4">
            <div className="flex items-center gap-2">
              <div
                className="w-8 h-8 rounded-lg border-[2px] border-black flex items-center justify-center shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
                style={{ background: `linear-gradient(135deg, ${style.accent}88, ${style.accent})` }}
              >
                <CategoryIcon className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-sm lg:text-base font-black uppercase tracking-tight text-black dark:text-white">
                {typeLabels[type] || type}
              </h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {typeBadges.map((badge) => {
                const progress = userProgress[badge.badge_id] || {
                  current: 0,
                  required: badge.requirement,
                  percentage: 0,
                  earned: false,
                };
                return (
                  <BadgeCard
                    key={badge.badge_id}
                    badge={badge}
                    progress={progress}
                    categoryStyle={style}
                  />
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
