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

import React from "react";
import { RiSidebarFoldLine, RiSidebarUnfoldLine } from "react-icons/ri";
import { Button } from "@/components/ui/button";
import cn from "classnames";
import { Moon, Sun, User, Settings, LogOut, Medal, Flame, CheckCircle, Star } from "lucide-react";
import { useTheme } from "../theme/theme-provier";
import { useEffect, useState } from "react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from "@/components/ui/avatar";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { Badge as BadgeUI } from "@/components/ui/badge";
import { useEarnedBadges, type Badge } from "@/hooks/query-hooks/useBadges";

interface HeaderProps {
    sidebarOpen: boolean;
    onToggleSidebar: () => void;
}

// Map backend icon strings to lucide-react components
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    medal: Medal,
    flame: Flame,
    "check-circle": CheckCircle,
    star: Star,
};

export default function Header({ sidebarOpen, onToggleSidebar }: HeaderProps) {
    const { theme, setTheme } = useTheme();
    const [isDarkMode, setIsDarkMode] = useState(false);

    // Fetch earned badges (backend extracts user_id from JWT token)
    const { data: earnedBadgesData } = useEarnedBadges({
        userId: "current", // Placeholder - backend uses JWT token
        enabled: true
    });

    useEffect(() => {
        const checkDarkMode = () => {
            if (theme === 'dark') {
                setIsDarkMode(true);
            } else if (theme === 'light') {
                setIsDarkMode(false);
            } else if (theme === 'system') {
                // Check if dark class is applied to document root
                setIsDarkMode(document.documentElement.classList.contains('dark'));
            }
        };

        checkDarkMode();

        // Listen for theme changes when using system theme
        if (theme === 'system') {
            const observer = new MutationObserver(checkDarkMode);
            observer.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['class']
            });

            return () => observer.disconnect();
        }
    }, [theme]);

    const logoSource = isDarkMode ? '/logo_white.png' : '/logo.png';

    const earnedBadges = earnedBadgesData?.earned_badges || [];
    const badgeCount = earnedBadgesData?.total_count || 0;
    // Show up to 5 most recent badges
    const recentBadges = earnedBadges.slice(0, 5);

    return (
        <header className="fixed top-0 left-0 right-0 h-[44px] lg:h-[48px] bg-[#FFFDF5] dark:bg-[#000000] border-b-[3px] lg:border-b-[4px] border-black dark:border-white z-40 flex items-center justify-between px-2 md:px-4 lg:px-5 shadow-[0_2px_0_0_rgba(0,0,0,1)] lg:shadow-[0_2px_0_0_rgba(0,0,0,1)] dark:shadow-[0_2px_0_0_rgba(255,255,255,0.3)]">
            {/* Left side - Logo */}
            <div className="flex items-center gap-1.5 md:gap-2 group cursor-pointer">
                <img
                    src={logoSource}
                    alt="teachr"
                    className="h-7 md:h-8 lg:h-9 w-auto group-hover:translate-x-0.5 group-hover:translate-y-0.5 transition-transform duration-100"
                />
            </div>

            {/* Right side - Actions */}
            <div className="flex items-center gap-1.5 md:gap-2">
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="w-7 h-7 md:w-8 md:h-8 lg:w-8 lg:h-8 border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none shadow-[1px_1px_0_0_rgba(0,0,0,1)] lg:shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] transition-all duration-100 text-black dark:text-white dark:hover:text-black"
                    onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                >
                    <Sun className="h-[0.9rem] w-[0.9rem] md:h-[1rem] md:w-[1rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                    <Moon className="absolute h-[0.9rem] w-[0.9rem] md:h-[1rem] md:w-[1rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                    <span className="sr-only">Toggle theme</span>
                </Button>

                {/* Badge Summary */}
                <Popover>
                    <PopoverTrigger asChild>
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
                    </PopoverTrigger>
                    <PopoverContent
                        align="end"
                        className="w-64 md:w-72 p-3 border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]"
                    >
                        <div className="space-y-3">
                            <div className="flex items-center justify-between pb-2 border-b-[2px] border-black dark:border-white">
                                <h3 className="text-sm lg:text-base font-black uppercase tracking-tight">
                                    Your Badges
                                </h3>
                                <BadgeUI
                                    variant="default"
                                    className="text-xs font-black border-[2px] border-black dark:border-white shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] px-2 py-0.5"
                                >
                                    {badgeCount}
                                </BadgeUI>
                            </div>

                            {recentBadges.length > 0 ? (
                                <div className="space-y-2">
                                    <p className="text-xs font-bold uppercase tracking-tight text-gray-600 dark:text-gray-400">
                                        Recent Achievements
                                    </p>
                                    <div className="space-y-1.5">
                                        {recentBadges.map((badge: Badge) => {
                                            const Icon = iconMap[badge.icon] || Star;
                                            return (
                                                <div
                                                    key={badge.badge_id}
                                                    className="flex items-center gap-2 p-2 rounded-md border-[2px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#1A1A1A] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]"
                                                >
                                                    <div className="w-7 h-7 flex items-center justify-center rounded border-[2px] border-black dark:border-white bg-[#FFD93D] shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]">
                                                        <Icon className="w-4 h-4 text-black" />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-xs font-bold uppercase tracking-tight truncate">
                                                            {badge.name}
                                                        </p>
                                                        <p className="text-[10px] text-gray-600 dark:text-gray-400 truncate">
                                                            {badge.description}
                                                        </p>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            ) : (
                                <div className="py-4 text-center">
                                    <p className="text-xs font-bold text-gray-600 dark:text-gray-400">
                                        No badges earned yet
                                    </p>
                                    <p className="text-[10px] text-gray-500 dark:text-gray-500 mt-1">
                                        Keep learning to earn badges!
                                    </p>
                                </div>
                            )}
                        </div>
                    </PopoverContent>
                </Popover>

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="relative h-7 w-7 md:h-8 md:w-8 lg:h-8 lg:w-8 p-0 border-[2px] border-black dark:border-white bg-[#FF6B6B] hover:bg-[#FF6B6B] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none shadow-[1px_1px_0_0_rgba(0,0,0,1)] lg:shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] transition-all duration-100">
                            <Avatar className="h-full w-full border-none">
                                <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
                                <AvatarFallback className="bg-transparent text-white font-black text-xs">CN</AvatarFallback>
                            </Avatar>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-48 md:w-56" align="end" forceMount>
                        <DropdownMenuLabel className="font-normal">
                            <div className="flex flex-col space-y-1">
                                <p className="text-sm font-medium leading-none">User</p>
                                <p className="text-xs leading-none text-muted-foreground">
                                    user@example.com
                                </p>
                            </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuGroup>
                            <DropdownMenuItem>
                                <User className="mr-2 h-4 w-4" />
                                <span>Account</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                                <Settings className="mr-2 h-4 w-4" />
                                <span>Settings</span>
                            </DropdownMenuItem>
                        </DropdownMenuGroup>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-[#FF6B6B] focus:text-[#FF6B6B]">
                            <LogOut className="mr-2 h-4 w-4" />
                            <span>Log out</span>
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>

                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="w-7 h-7 md:w-8 md:h-8 lg:w-8 lg:h-8 border-[2px] border-black dark:border-white bg-[#FFD93D] hover:bg-[#FFD93D] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none shadow-[1px_1px_0_0_rgba(0,0,0,1)] lg:shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] transition-all duration-100 text-black"
                    onClick={onToggleSidebar}
                >
                    {sidebarOpen ? (
                        <RiSidebarFoldLine className="w-4 h-4 lg:w-[1.1rem] lg:h-[1.1rem] font-black" />
                    ) : (
                        <RiSidebarUnfoldLine className="w-4 h-4 lg:w-[1.1rem] lg:h-[1.1rem] font-black" />
                    )}
                </Button>
            </div>
        </header>
    );
}
