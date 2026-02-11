import React from 'react';
import Renderer from '../../package/perseus/src/renderer';
import { PerseusI18nContextProvider } from '../../package/perseus/src/components/i18n-context';
import { mockStrings } from '../../package/perseus/src/strings';
import { storybookDependenciesV2 } from '../../package/perseus/testing/test-dependencies';
import { RenderStateRoot } from '@khanacademy/wonder-blocks-core';
import { useHint } from '../../contexts/HintContext';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import cn from 'classnames';

interface Hint {
  content: string;
  images: Record<string, { width: number; height: number }>;
  replace: boolean;
  widgets: Record<string, any>;
}

interface HintDisplayProps {
  hints: Hint[];
}

const HintDisplay: React.FC<HintDisplayProps> = ({ hints }) => {
  const { showHints, currentHintIndex, setCurrentHintIndex, totalHints, setTotalHints, responsiveHint } = useHint();

  React.useEffect(() => {
    if (hints && hints.length > 0) {
      setTotalHints(hints.length);
    } else {
      setTotalHints(0);
    }
  }, [hints, setTotalHints]);

  if (!showHints && !responsiveHint) {
    return null;
  }

  // Show responsive hint even when pre-baked hints are hidden
  if (responsiveHint && (!showHints || !hints || hints.length === 0)) {
    return (
      <div className="mt-4 md:mt-6 border-[3px] md:border-[4px] border-black dark:border-white bg-[#FFA500] dark:bg-[#E8930C] shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]">
        <div className="p-4 md:p-5 lg:p-6">
          <div className="flex items-center gap-2 md:gap-3 mb-3 pb-2 border-b-[2px] border-black dark:border-white">
            <div className="p-1.5 md:p-2 border-[2px] md:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
              <span className="text-lg md:text-xl">🎯</span>
            </div>
            <h3 className="text-sm md:text-base font-black text-black uppercase tracking-tight">
              Targeted Hint
            </h3>
          </div>
          <div className="bg-white dark:bg-neutral-800 p-3 md:p-4 border-[2px] md:border-[3px] border-black dark:border-white">
            <p className="text-sm md:text-base text-black dark:text-white leading-relaxed">{responsiveHint}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!hints || hints.length === 0) {
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
    <div className="mt-4 md:mt-6 border-[3px] md:border-[4px] border-black dark:border-white bg-[#FFE500] dark:bg-[#FFD93D] shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)] dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]">
      <div className="p-4 md:p-5 lg:p-6">
        {/* Hint Header */}
        <div className="flex items-center justify-between mb-3 md:mb-4 pb-2 md:pb-3 border-b-[2px] md:border-b-[3px] border-black dark:border-white">
          <div className="flex items-center gap-2 md:gap-3">
            <div className="p-1.5 md:p-2 border-[2px] md:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
              <span className="text-lg md:text-xl">💡</span>
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
                "w-8 h-8 md:w-9 md:h-9 flex items-center justify-center",
                "border-[2px] md:border-[3px] border-black dark:border-white",
                "transition-all duration-100",
                canGoPrevious
                  ? "bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#C4B5FD] text-black dark:text-white hover:text-black cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
                  : "bg-[#FFFDF5] dark:bg-[#000000] opacity-50 cursor-not-allowed"
              )}
            >
              <ChevronLeft className="w-4 h-4 md:w-5 md:h-5 font-bold" />
            </button>
            <button
              onClick={handleNext}
              disabled={!canGoNext}
              className={cn(
                "w-8 h-8 md:w-9 md:h-9 flex items-center justify-center",
                "border-[2px] md:border-[3px] border-black dark:border-white",
                "transition-all duration-100",
                canGoNext
                  ? "bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#C4B5FD] text-black dark:text-white hover:text-black cursor-pointer shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
                  : "bg-[#FFFDF5] dark:bg-[#000000] opacity-50 cursor-not-allowed"
              )}
            >
              <ChevronRight className="w-4 h-4 md:w-5 md:h-5 font-bold" />
            </button>
          </div>
        </div>

        {/* Responsive Hint (targeted to student's specific error) */}
        {responsiveHint && (
          <div className="mb-3 md:mb-4 bg-[#FFA500] dark:bg-[#E8930C] p-3 md:p-4 border-[2px] md:border-[3px] border-black dark:border-white">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-base">🎯</span>
              <span className="text-xs font-black text-black uppercase tracking-tight">Targeted Hint</span>
            </div>
            <p className="text-sm md:text-base text-black leading-relaxed">{responsiveHint}</p>
          </div>
        )}

        {/* Hint Content */}
        <div className="bg-white dark:bg-neutral-800 p-3 md:p-4 border-[2px] md:border-[3px] border-black dark:border-white">
          <PerseusI18nContextProvider locale="en" strings={mockStrings}>
            <RenderStateRoot>
              <Renderer
                content={currentHint.content}
                widgets={currentHint.widgets || {}}
                images={currentHint.images || {}}
                apiOptions={{}}
                linterContext={{
                  contentType: "",
                  highlightLint: false,
                  paths: [],
                  stack: [],
                }}
                strings={mockStrings}
                {...storybookDependenciesV2}
              />
            </RenderStateRoot>
          </PerseusI18nContextProvider>
        </div>
      </div>
    </div>
  );
};

export default HintDisplay;
