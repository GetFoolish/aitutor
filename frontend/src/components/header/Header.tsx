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
        <header className="fixed top-0 left-0 right-0 h-[44px] lg:h-[48px] bg-[#FFFDF5] dark:bg-[#000000] border-b-[3px] lg:border-b-[4px] border-black dark:border-white z-40 flex items-center justify-between px-2 md:px-4 lg:px-5 shadow-[0_2px_0_0_rgba(0,0,0,1)] lg:shadow-[0_2px_0_0_rgba(0,0,0,1)] dark:shadow-[0_2px_0_0_rgba(255,255,255,0.3)]">
            {/* Left side - AI Tutor Logo */}
            <div className="flex items-center gap-1.5 md:gap-2 group cursor-pointer">
                <div className="relative flex items-center justify-center w-7 h-7 md:w-8 md:h-8 lg:w-9 lg:h-9 border-[2px] lg:border-[3px] border-black dark:border-white bg-[#FFD93D] group-hover:translate-x-0.5 group-hover:translate-y-0.5 transition-transform duration-100">
                    <span className="material-symbols-outlined text-base md:text-lg text-black group-hover:rotate-12 transition-transform duration-300 font-black">
                        smart_toy
                    </span>
                </div>
                <div className="flex flex-col">
                    <h1 className="text-sm md:text-base lg:text-base font-black text-black dark:text-white uppercase tracking-tight leading-none">
                        AI TUTOR
                    </h1>
                    <span className="text-[7px] md:text-[8px] lg:text-[8px] font-bold text-black tracking-wider uppercase flex items-center gap-0.5 md:gap-1 bg-[#C4B5FD] px-1 md:px-1.5 py-0.5 border-[1.5px] border-black dark:border-white -ml-0.5 md:-ml-1">
                        <Sparkles className="w-1.5 h-1.5 md:w-2 md:h-2" />
                        <span className="hidden sm:inline">INTERACTIVE</span>
                        <span className="sm:hidden">AI</span>
                    </span>
                </div>
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
