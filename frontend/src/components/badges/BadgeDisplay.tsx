import React from "react";
import cn from "classnames";
import { Medal, Flame, CheckCircle, Star, Lock } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge as BadgeUI } from "@/components/ui/badge";
import { useBadges, type Badge, type BadgeProgress } from "@/hooks/query-hooks/useBadges";

interface BadgeDisplayProps {
  userId: string;
  className?: string;
}

// Map backend icon strings to lucide-react components
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  medal: Medal,
  flame: Flame,
  "check-circle": CheckCircle,
  star: Star,
};

// Tier colors for mastery badges (neobrutalist theme)
const tierColors: Record<string, string> = {
  bronze: "bg-[#CD7F32] border-[#8B5A2B]",
  silver: "bg-[#C0C0C0] border-[#808080]",
  gold: "bg-[#FFD700] border-[#FFA500]",
};

interface BadgeCardProps {
  badge: Badge;
  progress: BadgeProgress;
}

function BadgeCard({ badge, progress }: BadgeCardProps) {
  const Icon = iconMap[badge.icon] || Star;
  const isEarned = progress.earned;
  const showProgress = !isEarned && progress.percentage > 0;

  // Determine badge styling based on earned state
  const cardClassName = cn(
    "relative overflow-hidden transition-all duration-300",
    "border-[3px] border-black dark:border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]",
    isEarned
      ? "bg-[#FFFDF5] dark:bg-[#1A1A1A] hover:shadow-[6px_6px_0_0_rgba(0,0,0,1)] hover:translate-x-[-2px] hover:translate-y-[-2px]"
      : "bg-[#F5F5F5] dark:bg-[#0A0A0A] opacity-60 hover:opacity-80"
  );

  const iconWrapperClassName = cn(
    "w-12 h-12 lg:w-14 lg:h-14 flex items-center justify-center rounded-lg border-[3px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]",
    isEarned
      ? badge.tier
        ? tierColors[badge.tier]
        : "bg-[#FFD93D]"
      : "bg-[#E0E0E0] dark:bg-[#2A2A2A]"
  );

  const iconClassName = cn(
    "w-6 h-6 lg:w-7 lg:h-7",
    isEarned
      ? "text-black dark:text-white"
      : "text-gray-400 dark:text-gray-600"
  );

  return (
    <Card className={cardClassName}>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className={iconWrapperClassName}>
            {isEarned ? (
              <Icon className={iconClassName} />
            ) : (
              <Lock className={iconClassName} />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm lg:text-base font-black uppercase tracking-tight">
              {badge.name}
            </CardTitle>
            {badge.tier && (
              <BadgeUI
                variant="outline"
                className="mt-1 text-[10px] lg:text-xs font-bold uppercase border-[2px] border-black dark:border-white"
              >
                {badge.tier}
              </BadgeUI>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pb-4">
        <CardDescription className="text-xs lg:text-sm mb-2">
          {badge.description}
        </CardDescription>

        {showProgress && (
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-bold">
              <span className="text-black dark:text-white">
                {Math.floor(progress.current)} / {badge.requirement}
              </span>
              <span className="text-black dark:text-white">
                {Math.floor(progress.percentage)}%
              </span>
            </div>
            <Progress
              value={progress.percentage}
              className="h-2 border-[2px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
            />
          </div>
        )}

        {isEarned && (
          <div className="mt-2 flex items-center gap-1.5">
            <div className="w-2 h-2 lg:w-2.5 lg:h-2.5 rounded-full bg-[#4ADE80] border-[2px] border-black dark:border-white" />
            <span className="text-xs lg:text-sm font-bold text-[#4ADE80] uppercase">
              Earned!
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function BadgeDisplay({ userId, className }: BadgeDisplayProps) {
  const { data, isLoading, error } = useBadges({ userId });

  if (isLoading) {
    return (
      <div className={cn("flex items-center justify-center p-8", className)}>
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-[3px] border-black dark:border-white border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-bold uppercase tracking-tight">Loading badges...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("flex items-center justify-center p-8", className)}>
        <div className="text-center space-y-2">
          <p className="text-sm font-bold text-red-600 dark:text-red-400 uppercase">
            Failed to load badges
          </p>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  const badges = data?.available_badges || [];
  const userProgress = data?.user_progress || {};
  const earnedCount = data?.earned_badges?.length || 0;

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
        <h2 className="text-lg lg:text-xl font-black uppercase tracking-tight">
          Your Badges
        </h2>
        <BadgeUI
          variant="default"
          className="text-sm lg:text-base font-black border-[3px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] px-3 py-1"
        >
          {earnedCount} / {badges.length}
        </BadgeUI>
      </div>

      {/* Badge Grid by Type */}
      {Object.entries(badgesByType).map(([type, typeBadges]) => {
        if (typeBadges.length === 0) return null;

        return (
          <div key={type} className="space-y-3">
            <h3 className="text-sm lg:text-base font-black uppercase tracking-tight text-black dark:text-white">
              {typeLabels[type] || type}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
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
