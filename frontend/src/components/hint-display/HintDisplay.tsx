import React from 'react';
import Renderer from '../../package/perseus/src/renderer';
import { PerseusI18nContextProvider } from '../../package/perseus/src/components/i18n-context';
import { mockStrings } from '../../package/perseus/src/strings';
import { storybookDependenciesV2 } from '../../package/perseus/testing/test-dependencies';
import { RenderStateRoot } from '@khanacademy/wonder-blocks-core';
import { useHint } from '../../contexts/HintContext';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import cn from 'classnames';

/**
 * Process markdown tables in hint content to HTML
 * Handles tables with or without leading/trailing pipes:
 *
 * Format 1 (with pipes):
 * | Hundreds | Tens | Ones |
 * |:-:|:-:|:-:|
 * | $1$ | $8$ | $+$ |
 *
 * Format 2 (without leading pipes):
 * Hundred thousands|Ten thousands|Thousands
 * :-:|:-:|:-:
 * 7|0|9
 */
const processTable = (content: string): string => {
  const lines = content.split('\n');
  const result: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Check if this line could be a table header (contains | and has content)
    if (line.includes('|') && line.trim().length > 0) {
      // Check if next line is an alignment row (contains :- patterns)
      const nextLine = lines[i + 1];
      if (nextLine && /^[\s|:-]+$/.test(nextLine) && nextLine.includes('-')) {
        // This looks like a table! Parse it
        const tableLines: string[] = [line, nextLine];
        let j = i + 2;

        // Collect body rows (lines with | that aren't empty)
        while (j < lines.length && lines[j].includes('|') && lines[j].trim().length > 0) {
          tableLines.push(lines[j]);
          j++;
        }

        // Only process if we have at least header + alignment + 1 data row
        if (tableLines.length >= 3) {
          // Parse header
          const headerLine = tableLines[0];
          const headers = headerLine.split('|').map(h => h.trim()).filter(h => h.length > 0);

          // Parse alignment
          const alignLine = tableLines[1];
          const alignCells = alignLine.split('|').map(a => a.trim()).filter(a => a.length > 0);
          const alignments = alignCells.map(a => {
            if (a.startsWith(':') && a.endsWith(':')) return 'center';
            if (a.endsWith(':')) return 'right';
            if (a.startsWith(':')) return 'left';
            return 'center';
          });

          // Parse body rows
          const bodyRows = tableLines.slice(2).map(row =>
            row.split('|').map(c => c.trim()).filter(c => c.length > 0 || c === '')
          ).filter(row => row.length > 0);

          // Build HTML table
          let html = '<table style="width: auto; border-collapse: collapse; margin: 1em 0; border: 2px solid #333;">\n';

          // Header row
          html += '<thead><tr style="background-color: #f5f5f5;">';
          headers.forEach((header, idx) => {
            const align = alignments[idx] || 'center';
            html += `<th style="border: 2px solid #333; padding: 8px 12px; text-align: ${align}; font-weight: bold;">${header}</th>`;
          });
          html += '</tr></thead>\n';

          // Body rows
          html += '<tbody>';
          bodyRows.forEach(row => {
            html += '<tr>';
            row.forEach((cell, idx) => {
              const align = alignments[idx] || 'center';
              html += `<td style="border: 2px solid #333; padding: 8px 12px; text-align: ${align};">${cell}</td>`;
            });
            html += '</tr>\n';
          });
          html += '</tbody></table>';

          result.push(html);
          i = j;
          continue;
        }
      }
    }

    result.push(line);
    i++;
  }

  return result.join('\n');
};

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

        {/* Hint Content */}
        <div className="bg-white dark:bg-neutral-800 p-3 md:p-4 border-[2px] md:border-[3px] border-black dark:border-white">
          <PerseusI18nContextProvider locale="en" strings={mockStrings}>
            <RenderStateRoot>
              <Renderer
                content={processTable(currentHint.content)}
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
