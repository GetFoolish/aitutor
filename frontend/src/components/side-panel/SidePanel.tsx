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

import cn from "classnames";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { useLoggerStore } from "../../lib/store-logger";
import Logger, { LoggerFilterType } from "../logger/Logger";
import { ArrowRight, Terminal } from "lucide-react";

const filterOptions = [
  { value: "conversations", label: "Conversations" },
  { value: "tools", label: "Tool Use" },
  { value: "none", label: "All" },
];

interface SidePanelProps {
  open: boolean;
  onToggle: () => void;
}

export default function SidePanel({ open }: SidePanelProps) {
  const { connected, client } = useLiveAPIContext();
  const loggerRef = useRef<HTMLDivElement>(null);
  const loggerLastHeightRef = useRef<number>(-1);
  const { log, logs } = useLoggerStore();

  const [textInput, setTextInput] = useState("");
  const [filter, setFilter] = useState<LoggerFilterType>("none");

  //scroll the log to the bottom when new logs come in
  useEffect(() => {
    if (loggerRef.current) {
      const el = loggerRef.current;
      const scrollHeight = el.scrollHeight;
      if (scrollHeight !== loggerLastHeightRef.current) {
        el.scrollTop = scrollHeight;
        loggerLastHeightRef.current = scrollHeight;
      }
    }
  }, [logs]);

  // listen for log events and store them
  useEffect(() => {
    client.on("log", log);
    return () => {
      client.off("log", log);
    };
  }, [client, log]);

  const handleSubmit = () => {
    client.send([{ text: textInput }]);
    setTextInput("");
  };

  return (
    <div
      className={cn(
        "fixed top-[44px] lg:top-[48px] right-0 flex flex-col border-l-[3px] lg:border-l-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform shadow-[-2px_0_0_0_rgba(0,0,0,1)] lg:shadow-[-2px_0_0_0_rgba(0,0,0,1)] dark:shadow-[-2px_0_0_0_rgba(255,255,255,0.3)]",
        "h-[calc(100vh-44px)] lg:h-[calc(100vh-48px)] w-[240px] lg:w-[260px]",
        open ? "translate-x-0" : "translate-x-full",
        "max-md:hidden" // Hide on mobile
      )}
    >
      <header className="flex items-center justify-between h-[44px] lg:h-[48px] px-3 lg:px-4 border-b-[3px] border-black dark:border-white shrink-0 overflow-hidden transition-all duration-300 bg-[#C4B5FD]">
        <div className="flex items-center gap-2 lg:gap-2.5 animate-in fade-in slide-in-from-right-4 duration-300">
          <div className="p-1.5 lg:p-2 border-[2px] lg:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
            <Terminal className="w-4 h-4 lg:w-4 lg:h-4 text-black dark:text-white font-bold" />
          </div>
          <h2 className="text-sm lg:text-base font-black text-black uppercase tracking-tight whitespace-nowrap">
            Console
          </h2>
        </div>

        {/* Close button inside the panel since it's now fully hidden when closed */}
        {/* The toggle button in the Header will handle opening it */}
      </header>

      <div className="flex flex-col flex-grow overflow-hidden transition-all duration-300 opacity-100 translate-y-0 bg-[#FFFDF5] dark:bg-[#000000]">
        <section className="flex items-center justify-between px-6 py-4 gap-3 shrink-0 border-b-[3px] border-black dark:border-white">
          <Select
            value={filter}
            onValueChange={(value) => setFilter(value as LoggerFilterType)}
          >
            <SelectTrigger className="w-[160px] bg-[#FFFDF5] dark:bg-[#000000] border-[3px] border-black dark:border-white text-black dark:text-white h-9 text-xs font-black uppercase tracking-wide shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)]">
              <SelectValue placeholder="Filter logs" />
            </SelectTrigger>
            <SelectContent className="bg-[#FFFDF5] dark:bg-[#000000] border-[3px] border-black dark:border-white text-black dark:text-white">
              {filterOptions.map((option) => (
                <SelectItem
                  key={option.value}
                  value={option.value}
                  className="focus:bg-[#FFD93D] dark:focus:bg-[#FFD93D] focus:text-black cursor-pointer font-bold uppercase"
                >
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 border-[3px] border-black dark:border-white text-xs font-black uppercase tracking-wider transition-colors shadow-[3px_3px_0_0_rgba(0,0,0,1)] dark:shadow-[3px_3px_0_0_rgba(255,255,255,0.3)]",
              connected
                ? "bg-[#4ADE80] text-black"
                : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white"
            )}
          >
            <div
              className={cn(
                "w-3 h-3 border-[2px] border-black dark:border-white transition-all duration-300",
                connected ? "bg-black dark:bg-white animate-pulse" : "bg-black dark:bg-white"
              )}
            />
            <span>{connected ? "Streaming" : "Paused"}</span>
          </div>
        </section>

        <div
          className="flex-grow overflow-y-auto overflow-x-hidden px-6 py-4 scrollbar-thin scrollbar-thumb-black dark:scrollbar-thumb-white scrollbar-track-transparent"
          ref={loggerRef}
        >
          <Logger filter={filter} />
        </div>

        <div className={cn(
          "p-6 border-t-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] shrink-0 transition-all duration-300",
          { "opacity-50 pointer-events-none": !connected }
        )}>
          <div className="flex items-end gap-3 p-3 bg-[#FFFDF5] dark:bg-[#000000] border-[3px] border-black dark:border-white focus-within:border-[#C4B5FD] focus-within:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:focus-within:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] transition-all shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]">
            <Textarea
              className="w-full min-h-[24px] max-h-[120px] p-0 text-sm bg-transparent border-0 shadow-none resize-none focus-visible:ring-0 focus-visible:ring-offset-0 text-black dark:text-white placeholder:text-black/50 dark:placeholder:text-white/50 font-bold"
              placeholder="Type a message..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  e.stopPropagation();
                  handleSubmit();
                }
              }}
              onChange={(e) => setTextInput(e.target.value)}
              value={textInput}
            />
            <Button
              type="button"
              className="w-10 h-10 border-[3px] border-black dark:border-white bg-[#C4B5FD] hover:bg-[#C4B5FD] text-black shrink-0 p-0 flex items-center justify-center transition-all duration-100 hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:hover:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50"
              onClick={handleSubmit}
              disabled={!textInput.trim() || !connected}
            >
              <ArrowRight className="w-5 h-5 font-bold" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
