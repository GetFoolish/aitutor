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
import { Moon, Sun, User, Settings, LogOut, Terminal, BookOpen } from "lucide-react";
import { useTheme } from "../theme/theme-provier";
import { useEffect, useState } from "react";
import { Link, useHistory } from "react-router-dom";
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
    hideSidebarToggle?: boolean;
}

export default function Header({ sidebarOpen, onToggleSidebar, hideSidebarToggle = false }: HeaderProps) {
    const { theme, setTheme } = useTheme();
    const [isDarkMode, setIsDarkMode] = useState(false);
    const [userName, setUserName] = useState("User");
    const [userEmail, setUserEmail] = useState("");
    const history = useHistory();

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

    // Fetch user info on component mount
    useEffect(() => {
        const fetchUserInfo = async () => {
            try {
                const token = localStorage.getItem('jwt_token');
                if (!token) return;

                const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';
                const response = await fetch(`${AUTH_SERVICE_URL}/account/info`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    setUserName(data.name || "User");
                    setUserEmail(data.email || "");
                }
            } catch (error) {
                console.error('Failed to fetch user info:', error);
            }
        };

        fetchUserInfo();
    }, []);

    const handleLogout = async () => {
        try {
            const AUTH_SERVICE_URL = import.meta.env.VITE_AUTH_SERVICE_URL || 'http://localhost:8003';

            // Clear token from localStorage
            localStorage.removeItem('jwt_token');

            // Call logout endpoint
            await fetch(`${AUTH_SERVICE_URL}/auth/logout`, {
                method: 'POST'
            });

            // Redirect to login page
            history.push('/login');
        } catch (error) {
            console.error('Logout failed:', error);
            // Still clear token and redirect even if API call fails
            localStorage.removeItem('jwt_token');
            history.push('/login');
        }
    };

    const logoSource = isDarkMode ? '/logo_white.png' : '/logo.png';

    return (
        <header className="fixed top-0 left-0 right-0 h-[44px] lg:h-[48px] bg-[#FFFDF5] dark:bg-[#000000] border-b-[3px] lg:border-b-[4px] border-black dark:border-white z-40 flex items-center justify-between px-2 md:px-4 lg:px-5 shadow-[0_2px_0_0_rgba(0,0,0,1)] lg:shadow-[0_2px_0_0_rgba(0,0,0,1)] dark:shadow-[0_2px_0_0_rgba(255,255,255,0.3)]">
            {/* Left side - Logo (clickable to navigate home) */}
            <Link to="/" className="flex items-center gap-1.5 md:gap-2 group cursor-pointer">
                <img
                    src={logoSource}
                    alt="teachr"
                    className="h-7 md:h-8 lg:h-9 w-auto group-hover:translate-x-0.5 group-hover:translate-y-0.5 transition-transform duration-100"
                />
            </Link>

            {/* Right side - Actions */}
            <div className="flex items-center gap-1.5 md:gap-2">
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
                                <p className="text-sm font-medium leading-none">{userName}</p>
                                {userEmail && (
                                    <p className="text-xs leading-none text-muted-foreground">
                                        {userEmail}
                                    </p>
                                )}
                            </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuGroup>
                            <DropdownMenuItem asChild>
                                <Link to="/account" className="flex items-center">
                                    <User className="mr-2 h-4 w-4" />
                                    <span>Account</span>
                                </Link>
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

                {!hideSidebarToggle && (
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
                )}
            </div>
        </header>
    );
}
