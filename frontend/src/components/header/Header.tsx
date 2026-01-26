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
import { Moon, Sun, User, Settings, LogOut, Terminal, BookOpen, Upload } from "lucide-react";
import { useTheme } from "../theme/theme-provier";
import { useEffect, useState } from "react";
import { Link, useHistory } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
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
    homeworkMode?: boolean;
    onHomeworkClick?: () => void;
}

export default function Header({ sidebarOpen, onToggleSidebar, homeworkMode, onHomeworkClick }: HeaderProps) {
    const { theme, setTheme } = useTheme();
    const { user, logout } = useAuth();
    const history = useHistory();
    const [isDarkMode, setIsDarkMode] = useState(false);

    const handleLogout = async () => {
        await logout();
        history.push('/app/login');
    };

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
                {/* Homework Mode Button */}
                <Button
                    type="button"
                    variant="ghost"
                    className={cn(
                        "h-7 md:h-8 lg:h-8 px-2 md:px-3 border-[2px] border-black dark:border-white hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none shadow-[1px_1px_0_0_rgba(0,0,0,1)] lg:shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] transition-all duration-100 flex items-center gap-1.5",
                        homeworkMode
                            ? "bg-[#FFD93D] hover:bg-[#FFE566] text-black"
                            : "bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D] text-black dark:text-white dark:hover:text-black"
                    )}
                    onClick={onHomeworkClick}
                >
                    <Upload className="h-[0.9rem] w-[0.9rem] md:h-[1rem] md:w-[1rem]" />
                    <span className="text-[10px] md:text-xs font-black">HOMEWORK</span>
                </Button>

                {/* Dark/Light Mode Toggle */}
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
                                <AvatarFallback className="bg-transparent text-white font-black text-xs">
                                    {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'}
                                </AvatarFallback>
                            </Avatar>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-48 md:w-56" align="end" forceMount>
                        <DropdownMenuLabel className="font-normal">
                            <div className="flex flex-col space-y-1">
                                <p className="text-sm font-medium leading-none">{user?.name || 'User'}</p>
                                <p className="text-xs leading-none text-muted-foreground">
                                    {user?.email || 'user@example.com'}
                                </p>
                            </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuGroup>
                            <DropdownMenuItem asChild>
                                <Link to="/app/account" className="flex items-center">
                                    <User className="mr-2 h-4 w-4" />
                                    <span>Account</span>
                                </Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                                <Settings className="mr-2 h-4 w-4" />
                                <span>Settings</span>
                            </DropdownMenuItem>
                        </DropdownMenuGroup>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                            className="text-[#FF6B6B] focus:text-[#FF6B6B] cursor-pointer"
                            onClick={handleLogout}
                        >
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
                    {import.meta.env.DEV ? (
                        /* Developer Mode: Terminal Icon */
                        <Terminal className={cn("w-5 h-5 md:w-5 md:h-5 transition-transform", sidebarOpen ? "rotate-180" : "")} />
                    ) : (
                        /* Student Mode: Book/Learning Assets Icon */
                        <BookOpen className={cn("w-5 h-5 md:w-5 md:h-5 transition-transform", sidebarOpen ? "rotate-0" : "")} />
                    )}
                </Button>
            </div>
        </header>
    );
}
