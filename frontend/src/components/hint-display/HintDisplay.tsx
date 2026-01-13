import React from 'react';
import { useHint } from '../../contexts/HintContext';
import { ChevronLeft, ChevronRight, Lightbulb } from 'lucide-react';
import { AthenaRenderer } from '../../renderer/athena';
import cn from 'classnames';

interface Hint {
  content: string;
  images: Record<string, { width: number; height: number; url?: string; alt?: string }>;
  replace: boolean;
  widgets: Record<string, any>;
}

interface HintDisplayProps {
  hints: Hint[];
}

const HintDisplay: React.FC<HintDisplayProps> = ({ hints }) => {
  const { showHints, currentHintIndex, setCurrentHintIndex, totalHints, setTotalHints } = useHint();

  React.useEffect(() => {
    if (hints && hints.length > 0) {
      setTotalHints(hints.length);
    } else {
      setTotalHints(0);
    }
  }, [hints, setTotalHints]);

  if (!showHints || !hints || hints.length === 0) {
    return null;
  }

  const currentHint = hints[currentHintIndex];
  if (!currentHint) {
    return null;
  }

  const canGoPrevious = currentHintIndex > 0;
  const canGoNext = currentHintIndex < hints.length - 1;

  const handlePrevious = () => {
    if (canGoPrevious) {
      setCurrentHintIndex(currentHintIndex - 1);
    }
  };

  const handleNext = () => {
    if (canGoNext) {
      setCurrentHintIndex(currentHintIndex + 1);
    }
  };

  return (
    <div className="mt-4 md:mt-6 border-[3px] md:border-[4px] border-black dark:border-white bg-[#FFE500] dark:bg-[#FFD93D] shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]">
      <div className="p-4 md:p-5 lg:p-6">
        {/* Hint Header */}
        <div className="flex items-center justify-between mb-3 md:mb-4 pb-2 md:pb-3 border-b-[2px] md:border-b-[3px] border-black dark:border-white">
          <div className="flex items-center gap-2 md:gap-3">
            <div className="p-1.5 md:p-2 border-[2px] md:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] rotate-[-5deg]">
              <Lightbulb className="w-5 h-5 md:w-6 md:h-6 text-black dark:text-white" />
            </div>
            <h3 className="text-sm md:text-base font-black text-black uppercase tracking-tight">
              Hint {currentHintIndex + 1} of {totalHints}
            </h3>
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevious}
              disabled={!canGoPrevious}
              className={cn(
                "w-8 h-8 md:w-10 md:h-10 flex items-center justify-center",
                "border-[2px] md:border-[3px] border-black dark:border-white",
                "transition-all duration-100",
                canGoPrevious
                  ? "bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#C4B5FD] text-black dark:text-white hover:text-black cursor-pointer shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
                  : "bg-[#FFFDF5] dark:bg-[#000000] opacity-50 cursor-not-allowed"
              )}
            >
              <ChevronLeft className="w-5 h-5 md:w-6 md:h-6 font-bold" />
            </button>
            <button
              onClick={handleNext}
              disabled={!canGoNext}
              className={cn(
                "w-8 h-8 md:w-10 md:h-10 flex items-center justify-center",
                "border-[2px] md:border-[3px] border-black dark:border-white",
                "transition-all duration-100",
                canGoNext
                  ? "bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#C4B5FD] text-black dark:text-white hover:text-black cursor-pointer shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
                  : "bg-[#FFFDF5] dark:bg-[#000000] opacity-50 cursor-not-allowed"
              )}
            >
              <ChevronRight className="w-5 h-5 md:w-6 md:h-6 font-bold" />
            </button>
          </div>
        </div>

        {/* Hint Content - Athena Only */}
        <div className="bg-white dark:bg-neutral-900 p-4 md:p-6 border-[2px] md:border-[3px] border-black dark:border-white shadow-[inner_2px_2px_0_0_rgba(0,0,0,0.1)]">
          <AthenaRenderer
            item={{
              question: {
                content: currentHint.content,
                widgets: currentHint.widgets || {},
                images: currentHint.images || {},
              },
              hints: [],
              answerArea: {},
            }}
            onAnswerChange={() => { }}
            reviewMode={true}
          />
        </div>
      </div>
    </div>
  );
};

export default HintDisplay;
