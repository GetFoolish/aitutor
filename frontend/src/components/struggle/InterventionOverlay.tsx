import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useStruggleStatus, Intervention } from "@/hooks/query-hooks/useStruggleStatus";
import { Button } from "@/components/ui/button";
import { X, Lightbulb, Heart, Puzzle, Coffee } from "lucide-react";

interface InterventionOverlayProps {
  className?: string;
  onDismiss?: () => void;
  onAccept?: (type: Intervention["type"]) => void;
}

/**
 * Overlay that displays intervention messages when struggle is detected.
 * Automatically shows when an intervention is triggered.
 * User can dismiss or accept the suggestion.
 */
export default function InterventionOverlay({
  className,
  onDismiss,
  onAccept,
}: InterventionOverlayProps) {
  const { data: status } = useStruggleStatus({
    enabled: true,
    pollingInterval: 10000,
  });

  const [dismissed, setDismissed] = useState(false);
  const [lastInterventionType, setLastInterventionType] = useState<string | null>(null);

  // Reset dismissed state when a new intervention type appears
  useEffect(() => {
    if (status?.intervention?.type && status.intervention.type !== lastInterventionType) {
      setDismissed(false);
      setLastInterventionType(status.intervention.type);
    }
  }, [status?.intervention?.type, lastInterventionType]);

  // Don't show if no intervention or dismissed
  if (!status?.intervention || dismissed) {
    return null;
  }

  const intervention = status.intervention;

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  const handleAccept = () => {
    setDismissed(true);
    onAccept?.(intervention.type);
  };

  // Get icon and styling based on intervention type
  const getInterventionStyle = () => {
    switch (intervention.type) {
      case "hint":
        return {
          icon: Lightbulb,
          bgColor: "bg-blue-50 dark:bg-blue-900/20",
          borderColor: "border-blue-200 dark:border-blue-800",
          iconColor: "text-blue-500",
          title: "Need a hint?",
          acceptText: "Yes, give me a hint",
        };
      case "encouragement":
        return {
          icon: Heart,
          bgColor: "bg-pink-50 dark:bg-pink-900/20",
          borderColor: "border-pink-200 dark:border-pink-800",
          iconColor: "text-pink-500",
          title: "Keep going!",
          acceptText: "Thanks!",
        };
      case "simplification":
        return {
          icon: Puzzle,
          bgColor: "bg-purple-50 dark:bg-purple-900/20",
          borderColor: "border-purple-200 dark:border-purple-800",
          iconColor: "text-purple-500",
          title: "Let's try a different approach",
          acceptText: "Yes, break it down",
        };
      case "break_suggestion":
        return {
          icon: Coffee,
          bgColor: "bg-amber-50 dark:bg-amber-900/20",
          borderColor: "border-amber-200 dark:border-amber-800",
          iconColor: "text-amber-500",
          title: "Time for a break?",
          acceptText: "Yes, take a break",
        };
      default:
        return {
          icon: Heart,
          bgColor: "bg-gray-50 dark:bg-gray-900/20",
          borderColor: "border-gray-200 dark:border-gray-800",
          iconColor: "text-gray-500",
          title: "Here to help",
          acceptText: "Thanks",
        };
    }
  };

  const style = getInterventionStyle();
  const Icon = style.icon;

  return (
    <div
      className={cn(
        "fixed bottom-24 right-6 max-w-sm z-50",
        "animate-in slide-in-from-right duration-300",
        className
      )}
    >
      <div
        className={cn(
          "rounded-xl border-2 shadow-lg p-4",
          style.bgColor,
          style.borderColor
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className={cn("p-2 rounded-full bg-white dark:bg-gray-800", style.iconColor)}>
              <Icon className="w-5 h-5" />
            </div>
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {style.title}
            </span>
          </div>
          <button
            onClick={handleDismiss}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message */}
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
          {intervention.message}
        </p>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            onClick={handleAccept}
            size="sm"
            className="flex-1"
          >
            {style.acceptText}
          </Button>
          <Button
            onClick={handleDismiss}
            variant="ghost"
            size="sm"
          >
            Not now
          </Button>
        </div>

        {/* Urgency indicator */}
        {intervention.urgency === "high" && (
          <div className="mt-3 text-xs text-red-500 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            High priority suggestion
          </div>
        )}
      </div>
    </div>
  );
}
