import React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import {
  Upload,
  BookOpen,
  MessageSquare,
  X
} from "lucide-react";
import cn from "classnames";

export interface HomeworkPanelProps {
  isOpen: boolean;
  onClose: () => void;
  position?: "left" | "right";
  className?: string;
}

const HomeworkPanel: React.FC<HomeworkPanelProps> = ({
  isOpen,
  onClose,
  position = "right",
  className,
}) => {
  if (!isOpen) return null;

  return (
    <div
      className={cn(
        "absolute z-50 w-[320px] sm:w-[360px] bg-[#FFFDF5] dark:bg-[#1a1a1a] border-[3px] border-black dark:border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] transition-colors duration-300",
        position === "right" ? "right-0" : "left-0",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b-[3px] border-black dark:border-white bg-[#FFD93D] dark:bg-[#333333]">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-black dark:text-white" />
          <h2 className="text-lg font-black uppercase text-black dark:text-white">
            Homework
          </h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors"
          aria-label="Close homework panel"
        >
          <X className="w-5 h-5 text-black dark:text-white" />
        </button>
      </div>

      {/* Tabs Content */}
      <Tabs defaultValue="upload" className="w-full">
        <TabsList className="w-full grid grid-cols-3 bg-[#FFFDF5] dark:bg-[#1a1a1a] border-b-[3px] border-black dark:border-white rounded-none p-0 h-auto">
          <TabsTrigger
            value="upload"
            className={cn(
              "rounded-none border-r-[3px] border-black dark:border-white py-3 px-2 text-xs sm:text-sm font-black uppercase",
              "data-[state=active]:bg-[#C4B5FD] dark:data-[state=active]:bg-[#4c3d7f]",
              "data-[state=inactive]:bg-[#FFFDF5] dark:data-[state=inactive]:bg-[#1a1a1a]",
              "hover:bg-[#C4B5FD]/50 dark:hover:bg-[#4c3d7f]/50",
              "transition-colors text-black dark:text-white"
            )}
          >
            <Upload className="w-4 h-4 mr-1 inline-block" />
            Upload
          </TabsTrigger>
          <TabsTrigger
            value="list"
            className={cn(
              "rounded-none border-r-[3px] border-black dark:border-white py-3 px-2 text-xs sm:text-sm font-black uppercase",
              "data-[state=active]:bg-[#C4B5FD] dark:data-[state=active]:bg-[#4c3d7f]",
              "data-[state=inactive]:bg-[#FFFDF5] dark:data-[state=inactive]:bg-[#1a1a1a]",
              "hover:bg-[#C4B5FD]/50 dark:hover:bg-[#4c3d7f]/50",
              "transition-colors text-black dark:text-white"
            )}
          >
            <BookOpen className="w-4 h-4 mr-1 inline-block" />
            My Work
          </TabsTrigger>
          <TabsTrigger
            value="chat"
            className={cn(
              "rounded-none py-3 px-2 text-xs sm:text-sm font-black uppercase",
              "data-[state=active]:bg-[#C4B5FD] dark:data-[state=active]:bg-[#4c3d7f]",
              "data-[state=inactive]:bg-[#FFFDF5] dark:data-[state=inactive]:bg-[#1a1a1a]",
              "hover:bg-[#C4B5FD]/50 dark:hover:bg-[#4c3d7f]/50",
              "transition-colors text-black dark:text-white"
            )}
          >
            <MessageSquare className="w-4 h-4 mr-1 inline-block" />
            Chat
          </TabsTrigger>
        </TabsList>

        <div className="max-h-[500px] overflow-y-auto">
          {/* Upload Tab */}
          <TabsContent value="upload" className="m-0 p-4">
            <div className="flex flex-col items-center justify-center min-h-[200px] text-center">
              <Upload className="w-12 h-12 text-black/30 dark:text-white/30 mb-3" />
              <p className="text-sm font-bold text-black dark:text-white mb-2">
                Upload Homework
              </p>
              <p className="text-xs text-black/60 dark:text-white/60">
                Upload functionality coming soon
              </p>
            </div>
          </TabsContent>

          {/* My Homework Tab */}
          <TabsContent value="list" className="m-0 p-4">
            <div className="flex flex-col items-center justify-center min-h-[200px] text-center">
              <BookOpen className="w-12 h-12 text-black/30 dark:text-white/30 mb-3" />
              <p className="text-sm font-bold text-black dark:text-white mb-2">
                No Homework Yet
              </p>
              <p className="text-xs text-black/60 dark:text-white/60">
                Upload your first assignment to get started
              </p>
            </div>
          </TabsContent>

          {/* Chat Tab */}
          <TabsContent value="chat" className="m-0 p-4">
            <div className="flex flex-col items-center justify-center min-h-[200px] text-center">
              <MessageSquare className="w-12 h-12 text-black/30 dark:text-white/30 mb-3" />
              <p className="text-sm font-bold text-black dark:text-white mb-2">
                AI Homework Assistant
              </p>
              <p className="text-xs text-black/60 dark:text-white/60">
                Select homework to start chatting
              </p>
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
};

export default HomeworkPanel;
