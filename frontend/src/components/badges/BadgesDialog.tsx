/**
 * Badges Dialog - Clean Duolingo-inspired trigger
 */

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Trophy } from "lucide-react";
import BadgeDisplay from "./BadgeDisplay";
import cn from "classnames";

export default function BadgesDialog({
  badgeCount = 0,
  className,
}: {
  badgeCount?: number;
  className?: string;
}) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          className={cn(
            "relative flex items-center gap-1 px-2 h-8 md:h-9 rounded-xl",
            "bg-[#FFC800] border-2 border-black dark:border-white",
            "shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]",
            "hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[1px_1px_0_0_rgba(0,0,0,1)]",
            "active:translate-x-1 active:translate-y-1 active:shadow-none",
            "transition-all duration-100",
            className
          )}
        >
          <Trophy className="w-4 h-4 md:w-5 md:h-5 text-white" />
          {badgeCount > 0 && (
            <span className="text-sm md:text-base font-black text-white tabular-nums">
              {badgeCount}
            </span>
          )}
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto bg-white dark:bg-gray-900 border-0 rounded-2xl shadow-2xl">
        <DialogHeader className="sr-only">
          <DialogTitle>Achievements</DialogTitle>
        </DialogHeader>
        <BadgeDisplay />
      </DialogContent>
    </Dialog>
  );
}
