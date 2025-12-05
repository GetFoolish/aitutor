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

import { RiSidebarFoldLine, RiSidebarUnfoldLine } from "react-icons/ri";
import { Button } from "@/components/ui/button";
import cn from "classnames";
import { Sparkles, Moon, Sun, User, Settings, LogOut } from "lucide-react";
import { useTheme } from "../theme/theme-provier";
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

interface HeaderProps {
    sidebarOpen: boolean;
    onToggleSidebar: () => void;
}

export default function Header({ sidebarOpen, onToggleSidebar }: HeaderProps) {
    const { theme, setTheme } = useTheme();

    return (
        <header className="fixed top-0 left-0 right-0 h-[70px] bg-white/70 dark:bg-neutral-900/70 backdrop-blur-xl border-b border-white/20 dark:border-white/5 z-40 flex items-center justify-between px-6 transition-all duration-300">
            {/* Left side - AI Tutor Logo */}
            <div className="flex items-center gap-3 group cursor-pointer">
                <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 group-hover:border-blue-500/40 transition-all duration-300 group-hover:scale-105">
                    <span className="material-symbols-outlined text-2xl text-blue-500 dark:text-blue-400 group-hover:rotate-12 transition-transform duration-300">
                        smart_toy
                    </span>
                </div>
                <div className="flex flex-col">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400 bg-clip-text text-transparent">
                        AI Tutor
                    </h1>
                    <span className="text-[10px] font-medium text-blue-500 dark:text-blue-400 tracking-wider uppercase flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        Interactive
                    </span>
                </div>
            </div>

            {/* Right side - Actions */}
            <div className="flex items-center gap-2">
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="text-gray-500 dark:text-neutral-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/50 dark:hover:bg-white/10 transition-all duration-200 hover:scale-105"
                    onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                >
                    <Sun className="h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                    <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                    <span className="sr-only">Toggle theme</span>
                </Button>

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                            <Avatar className="h-8 w-8 border border-gray-200 dark:border-white/10">
                                <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
                                <AvatarFallback>CN</AvatarFallback>
                            </Avatar>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-56" align="end" forceMount>
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
                        <DropdownMenuItem className="text-red-600 dark:text-red-400 focus:text-red-600 dark:focus:text-red-400">
                            <LogOut className="mr-2 h-4 w-4" />
                            <span>Log out</span>
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>

                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="text-gray-500 dark:text-neutral-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/50 dark:hover:bg-white/10 transition-all duration-200 hover:scale-105"
                    onClick={onToggleSidebar}
                >
                    {sidebarOpen ? (
                        <RiSidebarFoldLine className="w-5 h-5" />
                    ) : (
                        <RiSidebarUnfoldLine className="w-5 h-5" />
                    )}
                </Button>
            </div>
        </header>
    );
}
