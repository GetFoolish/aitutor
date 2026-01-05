import React from "react";
import cn from "classnames";
import { Lightbulb } from "lucide-react";
import { useHint } from "../../contexts/HintContext";

interface HintButtonProps {
  isGradingSidebarOpen?: boolean;
  inline?: boolean;
}

const HintButton: React.FC<HintButtonProps> = ({ isGradingSidebarOpen = false, inline = false }) => {
  const { showHints, toggleHints } = useHint();

  return (
    <button
      onClick={toggleHints}
      className={cn(
        "flex items-center gap-2 px-4 py-2.5 rounded-lg",
        "border transition-all duration-200",
        showHints
          ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700/50 text-amber-700 dark:text-amber-400"
          : "bg-white dark:bg-neutral-800 border-gray-200 dark:border-neutral-700 text-gray-600 dark:text-gray-400",
        "hover:bg-amber-50/50 hover:border-amber-200 dark:hover:bg-amber-900/10",
        "active:scale-[0.98]",
        !inline && "fixed bottom-4 z-40",
        !inline && (isGradingSidebarOpen
          ? "left-[264px] md:left-[268px]"
          : "left-[48px] md:left-[48px]")
      )}
      style={!inline ? {
        transition: "left 0.5s cubic-bezier(0.16, 1, 0.3, 1)"
      } : undefined}
      title={showHints ? "Hide Hint" : "Show Hint"}
    >
      <Lightbulb className={cn(
        "w-4 h-4",
        showHints ? "text-amber-500 fill-amber-100" : "text-gray-400"
      )} />
      <span className="text-sm font-medium">
        Hint
      </span>
    </button>
  );
};

export default HintButton;
