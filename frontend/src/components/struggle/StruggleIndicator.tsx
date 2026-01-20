import { cn } from "@/lib/utils";
import { useStruggleStatus } from "@/hooks/query-hooks/useStruggleStatus";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface StruggleIndicatorProps {
  className?: string;
  showDetails?: boolean;
}

/**
 * Visual indicator showing current struggle level.
 * Changes color based on struggle score:
 * - Green (0-0.3): Doing well
 * - Yellow (0.3-0.6): Some difficulty
 * - Orange (0.6-0.8): Struggling
 * - Red (0.8-1.0): High struggle
 */
export default function StruggleIndicator({
  className,
  showDetails = false,
}: StruggleIndicatorProps) {
  const { data: status, isLoading } = useStruggleStatus({
    enabled: true,
    pollingInterval: 10000,
  });

  if (isLoading || !status || !status.session_id) {
    return null; // Don't show if no active session
  }

  const score = status.struggle_score;

  // Determine color and label based on score
  const getIndicatorState = () => {
    if (score < 0.3) {
      return {
        color: "bg-green-500",
        borderColor: "border-green-400",
        label: "Doing great!",
        emoji: "😊",
      };
    } else if (score < 0.5) {
      return {
        color: "bg-yellow-500",
        borderColor: "border-yellow-400",
        label: "Some challenge",
        emoji: "🤔",
      };
    } else if (score < 0.7) {
      return {
        color: "bg-orange-500",
        borderColor: "border-orange-400",
        label: "Needs support",
        emoji: "😓",
      };
    } else {
      return {
        color: "bg-red-500",
        borderColor: "border-red-400",
        label: "Struggling",
        emoji: "😰",
      };
    }
  };

  const state = getIndicatorState();

  // Build signals summary for tooltip
  const getSignalsSummary = () => {
    const signals = status.signals;
    const active: string[] = [];

    if (signals.interaction.repeated_errors) active.push("Repeated errors");
    if (signals.interaction.long_pause) active.push("Long pause");
    if (signals.interaction.inactivity) active.push("Inactive");
    if (signals.interaction.high_hint_usage) active.push("Many hints");

    if (signals.audio) {
      if (signals.audio.hesitation) active.push("Voice hesitation");
      if (signals.audio.long_pauses) active.push("Audio pauses");
    }

    if (signals.visual) {
      if (signals.visual.frustrated_or_confused) active.push(`Emotion: ${signals.visual.emotion}`);
      if (signals.visual.disengaged) active.push("Disengaged");
      if (signals.visual.looking_away) active.push("Looking away");
    }

    return active.length > 0 ? active : ["All good"];
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full border-2",
              "bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm",
              "transition-all duration-300",
              state.borderColor,
              className
            )}
          >
            {/* Animated pulse indicator */}
            <div className="relative">
              <div
                className={cn(
                  "w-3 h-3 rounded-full",
                  state.color,
                  score >= 0.5 && "animate-pulse"
                )}
              />
              {score >= 0.7 && (
                <div
                  className={cn(
                    "absolute inset-0 w-3 h-3 rounded-full",
                    state.color,
                    "animate-ping opacity-75"
                  )}
                />
              )}
            </div>

            {showDetails && (
              <>
                <span className="text-sm font-medium">
                  {state.emoji} {state.label}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  ({Math.round(score * 100)}%)
                </span>
              </>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <div className="space-y-2">
            <div className="font-semibold">
              {state.emoji} {state.label}
            </div>
            <div className="text-sm text-gray-500">
              Struggle Score: {Math.round(score * 100)}%
            </div>
            <div className="text-xs text-gray-400">
              <div className="font-medium mb-1">Detected signals:</div>
              <ul className="list-disc list-inside">
                {getSignalsSummary().map((signal, i) => (
                  <li key={i}>{signal}</li>
                ))}
              </ul>
            </div>
            <div className="text-xs text-gray-400">
              Mode: {status.signal_mode === "multi_signal" ? "Audio + Visual" : "Interaction only"}
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
