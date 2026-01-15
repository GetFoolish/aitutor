import React from "react";
import { toast } from "sonner";
import { Medal, Flame, CheckCircle, Star, Sparkles } from "lucide-react";
import type { Badge } from "@/hooks/query-hooks/useBadges";

// Map backend icon strings to lucide-react components
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  medal: Medal,
  flame: Flame,
  "check-circle": CheckCircle,
  star: Star,
};

// Tier colors for mastery badges
const tierColors: Record<string, string> = {
  bronze: "bg-[#CD7F32]",
  silver: "bg-[#C0C0C0]",
  gold: "bg-[#FFD700]",
};

interface BadgeNotificationContentProps {
  badge: Badge;
}

function BadgeNotificationContent({ badge }: BadgeNotificationContentProps) {
  const Icon = iconMap[badge.icon] || Star;
  const bgColor = badge.tier ? tierColors[badge.tier] : "bg-[#FFD93D]";

  return (
    <div className="flex items-start gap-3 p-1">
      {/* Animated badge icon */}
      <div
        className={`relative w-12 h-12 flex items-center justify-center rounded-lg border-[3px] border-black dark:border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] ${bgColor} animate-badge-pop`}
      >
        <Icon className="w-6 h-6 text-black dark:text-white" />
        {/* Sparkle effect */}
        <Sparkles className="absolute -top-1 -right-1 w-4 h-4 text-yellow-400 animate-badge-sparkle" />
      </div>

      {/* Badge details */}
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-black uppercase tracking-tight text-black dark:text-white">
            🎉 Badge Earned!
          </p>
        </div>
        <p className="text-base font-bold text-black dark:text-white">
          {badge.name}
        </p>
        <p className="text-xs text-gray-600 dark:text-gray-400">
          {badge.description}
        </p>
        {badge.tier && (
          <span className="inline-block mt-1 px-2 py-0.5 text-[10px] font-bold uppercase border-[2px] border-black dark:border-white rounded">
            {badge.tier}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Show a celebration notification when a badge is earned
 * @param badge - The badge that was earned
 * @param duration - Duration in milliseconds (default: 5000)
 */
export function showBadgeNotification(badge: Badge, duration: number = 5000) {
  toast.success(<BadgeNotificationContent badge={badge} />, {
    duration,
    className:
      "border-[3px] border-black dark:border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] bg-[#FFFDF5] dark:bg-[#1A1A1A]",
    style: {
      // Add custom CSS for confetti animation
      background: "var(--background)",
    },
  });
}

/**
 * Show notifications for multiple badges
 * @param badges - Array of badges that were earned
 * @param delayBetween - Delay between notifications in milliseconds (default: 300)
 */
export function showBadgeNotifications(
  badges: Badge[],
  delayBetween: number = 300
) {
  badges.forEach((badge, index) => {
    setTimeout(() => {
      showBadgeNotification(badge);
    }, index * delayBetween);
  });
}

// CSS animations for badge notification (add to global styles or inline)
// These animations are defined here as a reference and should be added to your global CSS:
/*
@keyframes badge-pop {
  0% {
    transform: scale(0.8) rotate(-10deg);
    opacity: 0;
  }
  50% {
    transform: scale(1.1) rotate(5deg);
  }
  100% {
    transform: scale(1) rotate(0deg);
    opacity: 1;
  }
}

@keyframes badge-sparkle {
  0%, 100% {
    opacity: 0;
    transform: scale(0.5) rotate(0deg);
  }
  50% {
    opacity: 1;
    transform: scale(1.2) rotate(180deg);
  }
}

.animate-badge-pop {
  animation: badge-pop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.animate-badge-sparkle {
  animation: badge-sparkle 1.5s ease-in-out infinite;
}
*/

// Export the component for potential custom usage
export default BadgeNotificationContent;
