import React, { useState, useEffect } from 'react';
import { Clock, FileEdit } from 'lucide-react';

interface AssessmentToolbarProps {
  startTime: number;
  onToggleScratchpad?: () => void;
  isScratchpadOpen?: boolean;
}

/**
 * AssessmentToolbar - Minimal, focused toolbar for assessments
 * No video controls, no session management - just timer and scratchpad
 * Total: ~100 lines (vs 1521 in FloatingControlPanel)
 */
const AssessmentToolbar: React.FC<AssessmentToolbarProps> = ({
  startTime,
  onToggleScratchpad,
  isScratchpadOpen = false,
}) => {
  const [elapsedTime, setElapsedTime] = useState('0:00');
  const [isCollapsed, setIsCollapsed] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      setElapsedTime(`${minutes}:${seconds.toString().padStart(2, '0')}`);
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <div
      className="fixed top-20 right-4 z-[1000] bg-white dark:bg-neutral-800 border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_#000] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]"
      style={{
        width: isCollapsed ? '64px' : '160px',
        transition: 'width 200ms ease',
      }}
    >
      {/* Collapsed state - icon only */}
      {isCollapsed && (
        <div className="flex flex-col items-center p-2 gap-3">
          {/* Timer icon button */}
          <button
            onClick={() => setIsCollapsed(false)}
            className="w-12 h-12 flex items-center justify-center bg-[#FFD93D] dark:bg-[#FFD93D] text-black border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_#000] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_#000] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all duration-100"
            title="Show timer"
          >
            <Clock className="w-5 h-5" />
          </button>

          {/* Scratchpad toggle */}
          {onToggleScratchpad && (
            <button
              onClick={onToggleScratchpad}
              className={`w-12 h-12 flex items-center justify-center border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_#000] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_#000] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all duration-100 ${
                isScratchpadOpen
                  ? 'bg-[#FFD93D] text-black'
                  : 'bg-white dark:bg-neutral-700 text-black dark:text-white'
              }`}
              title="Toggle scratchpad"
            >
              <FileEdit className="w-5 h-5" />
            </button>
          )}
        </div>
      )}

      {/* Expanded state - timer + label */}
      {!isCollapsed && (
        <div className="p-4">
          {/* Header with collapse button */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-black uppercase text-black dark:text-white">
              Time
            </span>
            <button
              onClick={() => setIsCollapsed(true)}
              className="w-6 h-6 flex items-center justify-center text-black dark:text-white hover:bg-gray-100 dark:hover:bg-neutral-700 transition-colors"
              aria-label="Collapse toolbar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Timer display */}
          <div className="mb-4 p-3 bg-[#FFD93D] dark:bg-[#FFD93D] border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_#000] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]">
            <div className="flex items-center gap-2 justify-center">
              <Clock className="w-5 h-5 text-black" />
              <span className="text-2xl font-black text-black font-mono">
                {elapsedTime}
              </span>
            </div>
          </div>

          {/* Scratchpad toggle */}
          {onToggleScratchpad && (
            <button
              onClick={onToggleScratchpad}
              className={`w-full py-3 px-4 font-bold uppercase tracking-wide text-sm border-[4px] border-black dark:border-white shadow-[4px_4px_0_0_#000] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0_0_#000] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all duration-100 flex items-center justify-center gap-2 ${
                isScratchpadOpen
                  ? 'bg-[#FFD93D] text-black'
                  : 'bg-white dark:bg-neutral-700 text-black dark:text-white'
              }`}
            >
              <FileEdit className="w-4 h-4" />
              <span>Notes</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default AssessmentToolbar;
