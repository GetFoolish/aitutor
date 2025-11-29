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
        "fixed top-[70px] right-0 flex flex-col border-l border-white/20 dark:border-white/5 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-xl transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform shadow-2xl",
        "h-[calc(100vh-70px)] w-[420px]",
        open ? "translate-x-0" : "translate-x-full"
      )}
    >
      <header className="flex items-center justify-between h-[70px] px-6 border-b border-white/20 dark:border-white/5 shrink-0 overflow-hidden transition-all duration-300">
        <div className="flex items-center gap-2 animate-in fade-in slide-in-from-left-4 duration-300">
          <Terminal className="w-5 h-5 text-blue-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white whitespace-nowrap">
            Console
          </h2>
        </div>

        {/* Close button inside the panel since it's now fully hidden when closed */}
        {/* The toggle button in the Header will handle opening it */}
      </header>

      <div className="flex flex-col flex-grow overflow-hidden transition-all duration-300 opacity-100 translate-y-0">
        <section className="flex items-center justify-between px-6 py-4 gap-3 shrink-0">
          <Select
            value={filter}
            onValueChange={(value) => setFilter(value as LoggerFilterType)}
          >
            <SelectTrigger className="w-[160px] bg-white/50 dark:bg-white/5 border-gray-200 dark:border-white/10 text-gray-900 dark:text-neutral-200 h-8 text-xs focus:ring-blue-500/20">
              <SelectValue placeholder="Filter logs" />
            </SelectTrigger>
            <SelectContent className="bg-white dark:bg-neutral-800 border-gray-200 dark:border-neutral-700 text-gray-900 dark:text-neutral-200">
              {filterOptions.map((option) => (
                <SelectItem
                  key={option.value}
                  value={option.value}
                  className="focus:bg-gray-100 dark:focus:bg-neutral-700 focus:text-gray-900 dark:focus:text-white cursor-pointer"
                >
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-mono transition-colors shadow-sm",
              connected
                ? "bg-green-500/10 border-green-500/20 text-green-600 dark:text-green-400"
                : "bg-gray-100 dark:bg-neutral-800 border-gray-200 dark:border-white/5 text-gray-500 dark:text-neutral-500"
            )}
          >
            <div
              className={cn(
                "w-2 h-2 rounded-full transition-all duration-300",
                connected ? "bg-green-500 shadow-[0_0_8px_rgba(74,222,128,0.5)] animate-pulse" : "bg-gray-400 dark:bg-neutral-500"
              )}
            />
            <span>{connected ? "Streaming" : "Paused"}</span>
          </div>
        </section>

        <div
          className="flex-grow overflow-y-auto overflow-x-hidden px-6 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-white/10 scrollbar-track-transparent"
          ref={loggerRef}
        >
          <Logger filter={filter} />
        </div>

        <div className={cn(
          "p-6 border-t border-white/20 dark:border-white/5 bg-gray-50/50 dark:bg-black/20 shrink-0 transition-all duration-300",
          { "opacity-50 pointer-events-none": !connected }
        )}>
          <div className="flex items-end gap-3 p-3 bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-2xl focus-within:border-blue-500/50 focus-within:ring-4 focus-within:ring-blue-500/10 transition-all shadow-sm">
            <Textarea
              className="w-full min-h-[24px] max-h-[120px] p-0 text-sm bg-transparent border-0 shadow-none resize-none focus-visible:ring-0 focus-visible:ring-offset-0 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-neutral-500"
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
              className="w-8 h-8 rounded-full bg-blue-600 hover:bg-blue-500 text-white shrink-0 p-0 flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95 shadow-lg shadow-blue-500/20"
              onClick={handleSubmit}
              disabled={!textInput.trim() || !connected}
            >
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
