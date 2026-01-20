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

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Medal } from "lucide-react";
import BadgeDisplay from "./BadgeDisplay";

export default function BadgesDialog({
  trigger,
  className,
  badgeCount = 0,
}: {
  trigger?: React.ReactNode;
  className?: string;
  badgeCount?: number;
}) {
  return (
    <div className={`badges-dialog ${className || ""}`}>
      <Dialog>
        <DialogTrigger asChild>
          {trigger || (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="relative w-7 h-7 md:w-8 md:h-8 lg:w-8 lg:h-8 border-[2px] border-black dark:border-white bg-[#4ADE80] hover:bg-[#4ADE80] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none shadow-[1px_1px_0_0_rgba(0,0,0,1)] lg:shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] transition-all duration-100 text-black"
            >
              <Medal className="h-[0.9rem] w-[0.9rem] md:h-[1rem] md:w-[1rem]" />
              {badgeCount > 0 && (
                <span className="absolute -top-1 -right-1 h-3.5 w-3.5 lg:h-4 lg:w-4 flex items-center justify-center bg-[#FFD93D] border-[2px] border-black dark:border-white rounded-full text-[8px] lg:text-[9px] font-black shadow-[1px_1px_0_0_rgba(0,0,0,1)]">
                  {badgeCount}
                </span>
              )}
              <span className="sr-only">View badges</span>
            </Button>
          )}
        </DialogTrigger>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[8px_8px_0_0_rgba(0,0,0,1)] dark:shadow-[8px_8px_0_0_rgba(255,255,255,0.3)]">
          <DialogHeader>
            <DialogTitle className="text-xl lg:text-2xl font-black uppercase tracking-tight">
              Badges & Achievements
            </DialogTitle>
            <DialogDescription className="text-sm lg:text-base">
              Track your learning progress and earn badges by mastering skills and reaching milestones.
            </DialogDescription>
          </DialogHeader>
          <div className="pt-4">
            <BadgeDisplay userId="current" />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
