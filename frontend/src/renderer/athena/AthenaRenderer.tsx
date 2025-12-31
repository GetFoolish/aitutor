/**
 * Athena Renderer - Main Entry Point
 *
 * A modern, performant content renderer for educational content.
 * Supports Perseus JSON format for backward compatibility while
 * providing improved performance and multi-subject notation support.
 */

import React, {
  forwardRef,
  useImperativeHandle,
  useRef,
  useCallback,
  useMemo,
  useEffect,
  useState,
  Suspense,
} from 'react';
import ReactDOM from 'react-dom';
import { AthenaProvider, useAthena } from './AthenaContext';
import { WidgetFactory } from './widgets/WidgetFactory';
import { GraphieImage } from './widgets/display/GraphieImage';
// @ts-ignore - KaTeX types resolution issue
import katex from 'katex';
import 'katex/dist/katex.min.css';
import './athena.css';
import type {
  AthenaRendererProps,
  AthenaRendererRef,
  PerseusItem,
  AthenaItem,
  SerializedState,
  ScoringResult,
  WidgetScoreDetail,
  NotationType,
} from './core/types';

// ============================================================================
// CONTENT RENDERER (Internal Component)
// ============================================================================

interface ContentRendererProps {
  item: PerseusItem | AthenaItem;
  problemNum: number;
}

const ContentRenderer = forwardRef<AthenaRendererRef, ContentRendererProps>(
  function ContentRenderer({ item, problemNum }, ref) {
    const { state, setAnswer, dispatchEvent, resolveStaticUrl } = useAthena();
    const containerRef = useRef<HTMLDivElement>(null);
    const widgetRefs = useRef<Map<string, unknown>>(new Map());

    // Detect notation types in content
    const detectedNotations = useMemo(() => {
      const notations = new Set<NotationType>();
      const content = item.question?.content || '';

      // Math detection
      if (/\$[^$]+\$|\\\[|\\\(|\\frac|\\sqrt|\\int|\\sum/.test(content)) {
        notations.add('math');
      }

      // Chemistry detection
      if (/\\ce\{|\\pu\{|->|<->/.test(content)) {
        notations.add('chemistry');
      }

      // Code detection
      if (/```[\w]*\n/.test(content)) {
        notations.add('code');
      }

      // Diagram detection
      if (/```mermaid|graph\s+(TD|LR)|sequenceDiagram|gantt/.test(content)) {
        notations.add('diagram');
      }

      return notations;
    }, [item.question?.content]);

    // Parse content and extract widget placeholders
    const parsedContent = useMemo(() => {
      let content = item?.question?.content || '';
      const widgets = item?.question?.widgets || {};

      // FIRST: Process ALL image markdown BEFORE anything else
      // This ensures images are converted to HTML tags early in the pipeline
      const processImageMarkdown = (text: string): string => {
        if (!text.includes('![')) return text;

        let processed = text;
        let graphieCounter = 0;

        // Helper to check if URL is a graphie URL (needs labels from data.json)
        const isGraphieUrl = (url: string): boolean => {
          return url.startsWith('web+graphie://') ||
            url.includes('ka-perseus-graphie') ||
            (url.includes('kastatic.org') && url.includes('graphie'));
        };

        // Helper to convert URL to img tag or graphie placeholder
        const toImgTag = (alt: string, url: string): string => {
          let imageUrl = url.trim();

          // For graphie images, create a placeholder that will be replaced with GraphieImage component
          if (isGraphieUrl(imageUrl)) {
            // Normalize the graphie URL (remove extension if present)
            let graphieUrl = imageUrl;
            if (graphieUrl.startsWith('web+graphie://')) {
              graphieUrl = 'web+graphie://' + graphieUrl.replace('web+graphie://', '').replace(/\.(png|svg)$/, '');
            } else {
              graphieUrl = graphieUrl.replace(/\.(png|svg)$/, '');
            }
            const placeholderId = `athena-graphie-${graphieCounter++}`;
            return `<span class="athena-graphie-placeholder" data-graphie-url="${graphieUrl}" data-graphie-alt="${alt}" id="${placeholderId}" style="display:block;margin:1rem 0;overflow:hidden;"></span>`;
          }

          // For non-graphie images, use regular img tag
          if (imageUrl.startsWith('web+graphie://')) {
            imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
          } else if ((imageUrl.includes('cdn.kastatic.org') || imageUrl.includes('ka-perseus')) &&
            !imageUrl.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
            imageUrl = imageUrl + '.png';
          }
          return `<img src="${imageUrl}" alt="${alt}" class="athena-image" style="max-width:100%;height:auto;display:block;margin:1rem 0;" referrerpolicy="no-referrer" />`;
        };

        // Pattern 1: Standard ![alt](url) with closing paren
        processed = processed.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
          console.log('[Athena] Early processing: Standard image:', url.substring(0, 80));
          return toImgTag(alt, url);
        });

        // Pattern 2: Truncated URL without closing paren
        processed = processed.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s\n<]+)/g, (_, alt, url) => {
          console.log('[Athena] Early processing: Truncated image:', url.substring(0, 80));
          return toImgTag(alt, url.replace(/[)\s]+$/, ''));
        });

        return processed;
      };

      // Process images in content FIRST
      content = processImageMarkdown(content);

      // Also process images in all widget options that might contain markdown
      const processedWidgets = { ...widgets };
      Object.keys(processedWidgets).forEach(widgetId => {
        const widget = processedWidgets[widgetId];
        if (widget?.options) {
          const newOptions = { ...widget.options };
          let changed = false;

          // Process passageText
          if (newOptions.passageText && typeof newOptions.passageText === 'string') {
            console.log('[Athena] Processing passageText for widget:', widgetId);
            newOptions.passageText = processImageMarkdown(newOptions.passageText);
            changed = true;
          }

          // Process passageTitle
          if (newOptions.passageTitle && typeof newOptions.passageTitle === 'string') {
            console.log('[Athena] Processing passageTitle for widget:', widgetId);
            newOptions.passageTitle = processImageMarkdown(newOptions.passageTitle);
            changed = true;
          }

          if (changed) {
            processedWidgets[widgetId] = {
              ...widget,
              options: newOptions,
            };
          }
        }
      });

      // Check if content contains tables with widget placeholders
      // If so, process as a single block to preserve table structure
      const hasTableWithWidgets = content.includes('|') && content.includes('[[☃');

      // DEBUG: Check for image markdown in content (after processing)
      const hasImageMarkdown = content.includes('![');
      console.log('[Athena] parsedContent:', {
        hasTableWithWidgets,
        hasImageMarkdown,
        contentPreview: content.substring(0, 500),
        widgetCount: Object.keys(processedWidgets).length,
        widgetTypes: Object.values(processedWidgets).map((w: any) => w.type),
      });

      // DEBUG: If image markdown still exists after processing, log it
      if (hasImageMarkdown) {
        const imageMatch = content.match(/!\[[^\]]*\]\([^)]{0,150}/);
        console.log('[Athena] WARNING: Still has image markdown after early processing:', imageMatch?.[0]);
      }

      if (hasTableWithWidgets) {
        // Process entire content as one block - widgets inside tables will be handled by renderHtmlWithInlineWidgets
        console.log('[Athena] Detected table with widgets - processing as single block');
        return {
          parts: [{ type: 'text' as const, content }],
          widgets: processedWidgets,
        };
      }

      // Otherwise, split content by widget placeholders [[☃ widget-id]]
      const parts: Array<{ type: 'text' | 'widget'; content: string; widgetId?: string }> = [];
      const widgetPattern = /\[\[☃\s+([^\]]+)\]\]/g;

      let lastIndex = 0;
      let match;

      while ((match = widgetPattern.exec(content)) !== null) {
        // Add text before widget
        if (match.index > lastIndex) {
          parts.push({
            type: 'text',
            content: content.slice(lastIndex, match.index),
          });
        }

        // Add widget placeholder
        const widgetId = match[1].trim();
        parts.push({
          type: 'widget',
          content: '',
          widgetId,
        });

        lastIndex = match.index + match[0].length;
      }

      // Add remaining text
      if (lastIndex < content.length) {
        parts.push({
          type: 'text',
          content: content.slice(lastIndex),
        });
      }

      return { parts, widgets: processedWidgets };
    }, [item.question?.content, item.question?.widgets]);

    // Get user input for all widgets
    const getUserInput = useCallback((): Record<string, unknown> => {
      return { ...state.answers };
    }, [state.answers]);

    // Get legacy user input format
    const getUserInputLegacy = useCallback((): unknown[] => {
      return Object.values(state.answers);
    }, [state.answers]);

    // Get serialized state
    const getSerializedState = useCallback((): SerializedState => {
      return {
        question: state.answers,
      };
    }, [state.answers]);

    // Restore state
    const restoreState = useCallback(
      (serializedState: SerializedState) => {
        if (serializedState.question) {
          Object.entries(serializedState.question).forEach(([widgetId, value]) => {
            setAnswer(widgetId, value);
          });
        }
      },
      [setAnswer]
    );

    // Focus management
    const focus = useCallback(() => {
      containerRef.current?.focus();
    }, []);

    const blur = useCallback(() => {
      containerRef.current?.blur();
    }, []);

    // Scoring (basic implementation - will be enhanced in Phase 4)
    const score = useCallback((): ScoringResult => {
      const widgets = item.question?.widgets || {};
      const details: WidgetScoreDetail[] = [];
      let totalEarned = 0;
      let totalPossible = 0;
      let allCorrect = true;
      let isEmpty = true;

      Object.entries(widgets).forEach(([widgetId, widget]) => {
        const userAnswer = state.answers[widgetId];
        const widgetType = widget.type as any;

        // Skip ungraded widgets
        if (!widget.graded) {
          return;
        }

        totalPossible += 1;

        if (userAnswer !== undefined && userAnswer !== null && userAnswer !== '') {
          isEmpty = false;
        }

        // Basic scoring logic (to be expanded in Phase 4)
        let correct = false;

        if (widgetType === 'radio' && widget.options) {
          const options = widget.options as any;
          const choices = Array.isArray(options?.choices) ? options.choices : [];
          const selectedIndex = userAnswer as number;
          correct = choices[selectedIndex]?.correct === true;
        } else if (widgetType === 'numeric-input' && widget.options) {
          const options = widget.options as any;
          const answers = Array.isArray(options?.answers) ? options.answers : [];
          const numericAnswer = parseFloat(String(userAnswer));
          correct = answers.some((ans: any) => {
            if (!ans) return false;
            const tolerance = ans.maxError || 0;
            return (
              ans.status === 'correct' &&
              Math.abs(numericAnswer - ans.value) <= tolerance
            );
          });
        }

        if (correct) {
          totalEarned += 1;
        } else {
          allCorrect = false;
        }

        details.push({
          widgetId,
          widgetType,
          correct,
          earned: correct ? 1 : 0,
          total: 1,
        });
      });

      return {
        correct: allCorrect && !isEmpty,
        empty: isEmpty,
        earned: totalEarned,
        total: totalPossible,
        details,
      };
    }, [item.question?.widgets, state.answers]);

    // Expose ref methods
    useImperativeHandle(
      ref,
      () => ({
        getUserInput,
        getUserInputLegacy,
        getSerializedState,
        restoreState,
        focus,
        blur,
        score,
      }),
      [getUserInput, getUserInputLegacy, getSerializedState, restoreState, focus, blur, score]
    );

    // Dispatch render events
    useEffect(() => {
      dispatchEvent({
        type: 'render-start',
        timestamp: Date.now(),
        data: { problemNum },
      });

      return () => {
        dispatchEvent({
          type: 'render-complete',
          timestamp: Date.now(),
          data: { problemNum },
        });
      };
    }, [problemNum, dispatchEvent]);

    // KaTeX macros for Khan Academy color commands
    // Note: In KaTeX macros, # is used for arguments, so hex colors need ## to escape the #
    const katexMacros = {
      // Color commands (Khan Academy style)
      '\\blue': '\\textcolor{##1865f2}{#1}',
      '\\red': '\\textcolor{##e84d39}{#1}',
      '\\green': '\\textcolor{##1fab54}{#1}',
      '\\purple': '\\textcolor{##9c4dcc}{#1}',
      '\\orange': '\\textcolor{##e67e22}{#1}',
      '\\pink': '\\textcolor{##e91e63}{#1}',
      '\\teal': '\\textcolor{##1abc9c}{#1}',
      '\\gold': '\\textcolor{##f1c40f}{#1}',
      '\\gray': '\\textcolor{##777777}{#1}',
      '\\grey': '\\textcolor{##777777}{#1}',
      // Variant colors
      '\\blueA': '\\textcolor{##1865f2}{#1}',
      '\\blueB': '\\textcolor{##2b73e8}{#1}',
      '\\blueC': '\\textcolor{##4185e8}{#1}',
      '\\blueD': '\\textcolor{##5a9ce8}{#1}',
      '\\blueE': '\\textcolor{##72b3e8}{#1}',
      '\\redA': '\\textcolor{##e74c3c}{#1}',
      '\\redB': '\\textcolor{##ec5050}{#1}',
      '\\redC': '\\textcolor{##f06464}{#1}',
      '\\redD': '\\textcolor{##f47878}{#1}',
      '\\redE': '\\textcolor{##f78c8c}{#1}',
      '\\greenA': '\\textcolor{##28b463}{#1}',
      '\\greenB': '\\textcolor{##2ecc71}{#1}',
      '\\greenC': '\\textcolor{##52d689}{#1}',
      '\\greenD': '\\textcolor{##6dd8a0}{#1}',
      '\\greenE': '\\textcolor{##87dbb3}{#1}',
      '\\purpleA': '\\textcolor{##9c4dcc}{#1}',
      '\\purpleB': '\\textcolor{##a05acc}{#1}',
      '\\purpleC': '\\textcolor{##aa63d9}{#1}',
      '\\purpleD': '\\textcolor{##b56ccc}{#1}',
      '\\purpleE': '\\textcolor{##c077d9}{#1}',
      '\\goldA': '\\textcolor{##f1c40f}{#1}',
      '\\goldB': '\\textcolor{##f4ca25}{#1}',
      '\\goldC': '\\textcolor{##f7d03b}{#1}',
      '\\goldD': '\\textcolor{##fad651}{#1}',
      '\\goldE': '\\textcolor{##fddc67}{#1}',
      '\\grayA': '\\textcolor{##333333}{#1}',
      '\\grayB': '\\textcolor{##555555}{#1}',
      '\\grayC': '\\textcolor{##777777}{#1}',
      '\\grayD': '\\textcolor{##999999}{#1}',
      '\\grayE': '\\textcolor{##bbbbbb}{#1}',
      // Khan Academy specific
      '\\kaBlue': '\\textcolor{##1865f2}{#1}',
      '\\kaGreen': '\\textcolor{##1fab54}{#1}',
      // Maroon for negative numbers
      '\\maroonC': '\\textcolor{##c03}{#1}',
      '\\maroonD': '\\textcolor{##a02}{#1}',
    };

    // KaTeX options with macros
    const katexOptions = {
      throwOnError: false,
      macros: katexMacros,
      trust: true,
    };

    // Helper function to render math with KaTeX
    const renderMath = (text: string): string => {
      if (!text || typeof text !== 'string') return text || '';

      // STEP 1: Decode HTML entities FIRST (before any other processing)
      // This fixes &amp; → & which is critical for align environments
      let processed = text
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#039;/g, "'")
        .replace(/&nbsp;/g, ' ');

      // STEP 2: Use placeholders to protect KaTeX output from subsequent processing
      const katexPlaceholders: string[] = [];
      const createPlaceholder = (html: string): string => {
        const idx = katexPlaceholders.length;
        katexPlaceholders.push(html);
        return `__KATEX_PLACEHOLDER_${idx}__`;
      };

      // Helper: preprocess Khan Academy color commands to \textcolor
      const preprocessColorCommands = (latex: string): string => {
        const colorMap: Record<string, string> = {
          blueA: '#1865f2', blueB: '#2b73e8', blueC: '#4185e8', blueD: '#5a9ce8', blueE: '#72b3e8',
          redA: '#e74c3c', redB: '#ec5050', redC: '#f06464', redD: '#f47878', redE: '#f78c8c',
          greenA: '#28b463', greenB: '#2ecc71', greenC: '#52d689', greenD: '#6dd8a0', greenE: '#87dbb3',
          purpleA: '#9c4dcc', purpleB: '#a05acc', purpleC: '#aa63d9', purpleD: '#b56ccc', purpleE: '#c077d9',
          goldA: '#f1c40f', goldB: '#f4ca25', goldC: '#f7d03b', goldD: '#fad651', goldE: '#fddc67',
          grayA: '#333333', grayB: '#555555', grayC: '#777777', grayD: '#999999', grayE: '#bbbbbb',
          maroonC: '#cc0033', maroonD: '#aa0022',
          blue: '#1865f2', red: '#e84d39', green: '#1fab54', purple: '#9c4dcc',
          orange: '#e67e22', pink: '#e91e63', teal: '#1abc9c', gold: '#f1c40f', gray: '#777777',
        };
        let result = latex;
        // Sort by length descending to match longer names first (purpleD before purple)
        const colorNames = Object.keys(colorMap).sort((a, b) => b.length - a.length);
        for (const colorName of colorNames) {
          const hex = colorMap[colorName];
          const pattern = new RegExp(`\\\\${colorName}\\{([^{}]*(?:\\{[^{}]*\\}[^{}]*)*)\\}`, 'g');
          result = result.replace(pattern, `\\textcolor{${hex}}{$1}`);
        }
        return result;
      };

      // STEP 3: Handle $\begin{align}...\end{align}$ patterns BEFORE general math processing
      // This is the special case that needs careful handling of & alignment markers
      processed = processed.replace(/\$\\begin\{(align\*?|aligned)\}([\s\S]*?)\\end\{\1\}\$/g, (fullMatch, envName, innerContent) => {
        try {
          // Clean the inner content - restore any corrupted & characters
          let cleanContent = innerContent
            .replace(/&amp;/g, '&')
            .replace(/amp;/g, '&')   // Handle cases where & was stripped
            .replace(/=\s*amp;/g, '&=')  // Fix =amp; patterns
            .replace(/amp;\s*=/g, '&=') // Fix amp;= patterns
            .replace(/\\\\\\\\/g, '\\\\'); // Fix escaped backslashes: \\\\ -> \\

          // Pre-process color commands before KaTeX
          cleanContent = preprocessColorCommands(cleanContent);

          // Render the full align environment
          const latex = `\\begin{${envName}}${cleanContent}\\end{${envName}}`;
          const result = katex.renderToString(latex, { ...katexOptions, displayMode: true });
          // Return placeholder to protect from subsequent processing
          return createPlaceholder(result);
        } catch (e) {
          console.error('[Athena] KaTeX align error:', e, 'Content:', innerContent);
          return `<span class="math-error">${fullMatch}</span>`;
        }
      });

      // STEP 3b: Handle standalone \begin{align}...\end{align} (without $ wrapper)
      processed = processed.replace(/\\begin\{(align\*?|aligned)\}([\s\S]*?)\\end\{\1\}/g, (fullMatch, envName, innerContent) => {
        try {
          // Clean the inner content - restore any corrupted & characters
          let cleanContent = innerContent
            .replace(/&amp;/g, '&')
            .replace(/amp;/g, '&')
            .replace(/=\s*amp;/g, '&=')
            .replace(/amp;\s*=/g, '&=')
            .replace(/\\\\\\\\/g, '\\\\');

          // Pre-process color commands before KaTeX
          cleanContent = preprocessColorCommands(cleanContent);

          // Render the full align environment
          const latex = `\\begin{${envName}}${cleanContent}\\end{${envName}}`;
          const result = katex.renderToString(latex, { ...katexOptions, displayMode: true });
          return createPlaceholder(result);
        } catch (e) {
          console.error('[Athena] KaTeX standalone align error:', e);
          return `<span class="math-error">${fullMatch}</span>`;
        }
      });

      // Color map for preprocessing color commands without braces
      const colorHexMap: Record<string, string> = {
        blue: '#1865f2', red: '#e84d39', green: '#1fab54', purple: '#9c4dcc',
        orange: '#e67e22', pink: '#e91e63', teal: '#1abc9c', gold: '#f1c40f',
        gray: '#777777', grey: '#777777',
        blueA: '#1865f2', blueB: '#2b73e8', blueC: '#4185e8', blueD: '#5a9ce8', blueE: '#72b3e8',
        redA: '#e74c3c', redB: '#ec5050', redC: '#f06464', redD: '#f47878', redE: '#f78c8c',
        greenA: '#28b463', greenB: '#2ecc71', greenC: '#52d689', greenD: '#6dd8a0', greenE: '#87dbb3',
        purpleA: '#9c4dcc', purpleB: '#a05acc', purpleC: '#aa63d9', purpleD: '#b56ccc', purpleE: '#c077d9',
        tealA: '#1abc9c', tealB: '#2cc4a4', tealC: '#3dccac', tealD: '#4dd4b4', tealE: '#5edcbc',
        goldA: '#f1c40f', goldB: '#f4ca25', goldC: '#f7d03b', goldD: '#fad651', goldE: '#fddc67',
        grayA: '#333333', grayB: '#555555', grayC: '#777777', grayD: '#999999', grayE: '#bbbbbb',
        maroonC: '#cc0033', maroonD: '#aa0022',
        kaBlue: '#1865f2', kaGreen: '#1fab54',
      };

      // NOTE: Braceless color commands like \blueD7 are now handled INSIDE the inline math processor
      // to avoid inserting KaTeX HTML inside $...$ blocks which causes escaping issues

      // First, handle escaped dollar signs \$ -> $ (currency)
      // Use a placeholder to protect them from math processing
      const dollarPlaceholder = '__DOLLAR_SIGN__';
      processed = processed.replace(/\\\$/g, dollarPlaceholder);

      // Clean up stray/empty $$ patterns FIRST (before valid processing)
      // Remove $$ followed immediately by whitespace or non-math content (likely malformed)
      // Clean up stray/empty $$ patterns FIRST (before valid processing)
      // Remove $$ followed immediately by whitespace or non-math content (valid display math usually starts with content or newline)
      // processed = processed.replace(/\$\$\s*$/gm, ''); // $$ at end of line with optional whitespace

      // Process display math $$...$$ first (multiline support with [\s\S])
      processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
        // Preprocess: Remove unsupported LaTeX sizing commands
        let cleanMath = math.trim();
        cleanMath = cleanMath.replace(/\\(tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge)\s*/g, '');

        try {
          return katex.renderToString(cleanMath, { ...katexOptions, displayMode: true });
        } catch (e) {
          console.warn('[Athena] KaTeX display math error:', e, 'for:', cleanMath);
          return `<span class="athena-math-error">${cleanMath}</span>`;
        }
      });

      // Process LaTeX environments \begin{...}...\end{...} (gather, equation, array, matrix, cases)
      // Note: align/aligned are handled above with special & character cleaning
      // First: with $ wrapper
      processed = processed.replace(/\$\\?(large|Large|LARGE|huge|Huge)?\s*\\begin\{(gather|gathered|equation|array|matrix|pmatrix|bmatrix|cases)\}([\s\S]*?)\\end\{\2\}\s*\$/g, (_, size, env, content) => {
        try {
          // Clean up any HTML-encoded & characters
          let cleanContent = content
            .replace(/&amp;/g, '&')
            .replace(/amp;/g, '&')
            .replace(/\\\\\\\\/g, '\\\\');
          cleanContent = preprocessColorCommands(cleanContent);
          const latex = `\\begin{${env}}${cleanContent}\\end{${env}}`;
          const result = katex.renderToString(latex, { ...katexOptions, displayMode: true });
          return createPlaceholder(result);
        } catch (e) {
          console.error('KaTeX env error:', e);
          return `<span class="athena-math-error">${content}</span>`;
        }
      });

      // Second: without $ wrapper (standalone \begin{...}...\end{...})
      processed = processed.replace(/\\begin\{(gather|gathered|equation|array|matrix|pmatrix|bmatrix|cases)\}([\s\S]*?)\\end\{\1\}/g, (_, env, content) => {
        try {
          // Clean up any HTML-encoded & characters
          let cleanContent = content
            .replace(/&amp;/g, '&')
            .replace(/amp;/g, '&')
            .replace(/\\\\\\\\/g, '\\\\');
          cleanContent = preprocessColorCommands(cleanContent);
          const latex = `\\begin{${env}}${cleanContent}\\end{${env}}`;
          const result = katex.renderToString(latex, { ...katexOptions, displayMode: true });
          return createPlaceholder(result);
        } catch (e) {
          console.error('KaTeX env error:', e);
          return `<span class="athena-math-error">${content}</span>`;
        }
      });

      // Process inline math $...$ (but not $$)
      // Note: $28$ IS valid math (renders 28 in math font), different from $28 (currency)
      // Currency like $28 without closing $ won't match this regex anyway
      processed = processed.replace(/\$([^$]+)\$/g, (match, math) => {
        // Skip if it looks like already processed or is $$
        if (match.startsWith('$$')) return match;

        // Preprocess: Remove unsupported LaTeX sizing commands
        let cleanMath = math.trim();
        cleanMath = cleanMath.replace(/\\(tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge)\s*/g, '');

        // Preprocess: Expand Khan Academy color commands to standard \textcolor format
        // This is more reliable than using KaTeX macros
        const colorExpansions: Record<string, string> = {
          'blueD': '#5a9ce8', 'blueE': '#72b3e8', 'blueC': '#4185e8', 'blueB': '#2b73e8', 'blueA': '#1865f2',
          'greenD': '#6dd8a0', 'greenE': '#87dbb3', 'greenC': '#52d689', 'greenB': '#2ecc71', 'greenA': '#28b463',
          'purpleD': '#b56ccc', 'purpleE': '#c077d9', 'purpleC': '#aa63d9', 'purpleB': '#a05acc', 'purpleA': '#9c4dcc',
          'redD': '#f47878', 'redE': '#f78c8c', 'redC': '#f06464', 'redB': '#ec5050', 'redA': '#e74c3c',
          'goldD': '#fad651', 'goldE': '#fddc67', 'goldC': '#f7d03b', 'goldB': '#f4ca25', 'goldA': '#f1c40f',
          'grayD': '#999999', 'grayE': '#bbbbbb', 'grayC': '#777777', 'grayB': '#555555', 'grayA': '#333333',
          'maroonD': '#a02', 'maroonC': '#c03',
          'blue': '#1865f2', 'red': '#e84d39', 'green': '#1fab54', 'purple': '#9c4dcc',
          'orange': '#e67e22', 'pink': '#e91e63', 'teal': '#1abc9c', 'gold': '#f1c40f', 'gray': '#777777',
        };
        // Sort by length descending to match longer names first
        const colorCmdNames = Object.keys(colorExpansions).sort((a, b) => b.length - a.length);
        for (const colorName of colorCmdNames) {
          const hex = colorExpansions[colorName];
          // Match \colorName{content} and expand to \textcolor{#hex}{content}
          const pattern = new RegExp(`\\\\${colorName}\\{([^{}]*(?:\\{[^{}]*\\}[^{}]*)*)\\}`, 'g');
          cleanMath = cleanMath.replace(pattern, `\\textcolor{${hex}}{$1}`);
        }

        // Also handle braceless color commands like \blueE5 -> \textcolor{#hex}{5}
        // These are Khan Academy shorthand where \colorX followed by a single character applies color to that char
        for (const colorName of colorCmdNames) {
          const hex = colorExpansions[colorName];
          // Match \colorName followed by a digit or letter (not a brace)
          const bracelessPattern = new RegExp(`\\\\${colorName}([0-9a-zA-Z])(?![{a-zA-Z])`, 'g');
          cleanMath = cleanMath.replace(bracelessPattern, `\\textcolor{${hex}}{$1}`);
        }

        try {
          return katex.renderToString(cleanMath, { ...katexOptions, displayMode: false });
        } catch (e) {
          console.warn('[Athena] KaTeX inline math error:', e, 'for:', cleanMath);
          // Use cleanMath (without \huge etc) to avoid double-rendering color commands
          return `<span class="athena-math-error">${cleanMath}</span>`;
        }
      });

      // Handle LaTeX commands like \dfrac, \frac without $ delimiters
      processed = processed.replace(/\\(dfrac|frac|sqrt|int|sum|prod|lim)\{([^}]+)\}\{([^}]+)\}/g, (match, cmd, arg1, arg2) => {
        try {
          return katex.renderToString(`\\${cmd}{${arg1}}{${arg2}}`, { ...katexOptions, displayMode: false });
        } catch {
          return match;
        }
      });

      // Handle color commands WITH braces outside of $ delimiters (e.g., \greenD{\text{starts}})
      // These commands take one argument in braces
      // IMPORTANT: Sort by length descending so longer names match first (purpleD before purple)
      const colorCommandNames = Object.keys(colorHexMap).sort((a, b) => b.length - a.length);
      for (const colorName of colorCommandNames) {
        // Match \colorName{...} where ... can contain nested braces (like \text{...})
        // Using a more permissive pattern to handle nested content
        const colorPattern = new RegExp(`\\\\${colorName}\\{([^{}]*(?:\\{[^{}]*\\}[^{}]*)*)\\}`, 'g');
        processed = processed.replace(colorPattern, (match, content) => {
          const color = colorHexMap[colorName];
          try {
            // Try to render as KaTeX with the color
            return katex.renderToString(`\\textcolor{${color}}{${content}}`, { ...katexOptions, displayMode: false });
          } catch {
            // Fallback to HTML span with color
            // Also process any \text{} inside to just show the text
            const textContent = content.replace(/\\text\{([^}]+)\}/g, '$1');
            return `<span style="color:${color};font-weight:600">${textContent}</span>`;
          }
        });
      }

      // Handle explicit \textcolor{#hex}{content} with nested braces
      // This handles cases like \textcolor{#b56ccc}{7\text{ hundreds}}
      const extractBraces = (str: string, start: number): { content: string; end: number } | null => {
        if (str[start] !== '{') return null;
        let depth = 0;
        let i = start;
        while (i < str.length) {
          if (str[i] === '{') depth++;
          else if (str[i] === '}') depth--;
          if (depth === 0) return { content: str.slice(start + 1, i), end: i };
          i++;
        }
        return null;
      };

      const textcolorRegex = /\\textcolor\{(#[0-9a-fA-F]{3,6})\}\{/g;
      let tcMatch;
      while ((tcMatch = textcolorRegex.exec(processed)) !== null) {
        const color = tcMatch[1];
        const braceStart = tcMatch.index + tcMatch[0].length - 1;
        const result = extractBraces(processed, braceStart);
        if (result) {
          const fullMatch = processed.slice(tcMatch.index, result.end + 1);
          let replacement: string;
          try {
            replacement = katex.renderToString(fullMatch, { ...katexOptions, displayMode: false });
          } catch {
            // Fallback: process \text{} and wrap with color span
            let inner = result.content.replace(/\\text\{([^}]+)\}/g, '$1');
            replacement = `<span style="color:${color};font-weight:600">${inner}</span>`;
          }
          processed = processed.slice(0, tcMatch.index) + replacement + processed.slice(result.end + 1);
          textcolorRegex.lastIndex = tcMatch.index + replacement.length;
        }
      }

      // Restore dollar signs
      processed = processed.replace(/__DOLLAR_SIGN__/g, '$');

      // FINAL STEP: Restore KaTeX placeholders (protected from subsequent processing)
      katexPlaceholders.forEach((html, idx) => {
        processed = processed.replace(`__KATEX_PLACEHOLDER_${idx}__`, html);
      });

      return processed;
    };

    // Process markdown tables - handles both strict and loose table formats
    const processTable = (text: string): string => {
      if (!text || typeof text !== 'string') return text || '';

      console.log('[Athena] processTable input:', text.substring(0, 800));

      const lines = text.split('\n');
      const result: string[] = [];
      let i = 0;
      let tablesFound = 0;

      // Helper to check if a line looks like a real table row (not just separators or short)
      const isValidTableRow = (line: string): boolean => {
        const trimmed = line.trim();
        // Skip lines that are too short
        if (trimmed.length < 5) return false;
        // Skip lines that are just pipes and dashes (separator-like but not standalone)
        if (/^[\s|:\-]+$/.test(trimmed) && !trimmed.includes('|---|')) return false;
        // Skip lines that are just || or similar
        if (/^\|+$/.test(trimmed.replace(/\s/g, ''))) return false;
        // ALLOW lines with widget placeholders - they should render in table cells
        return true;
      };

      // Helper to convert widget placeholders to data attributes for later processing
      const preserveWidgetPlaceholders = (cell: string): string => {
        // Convert [[☃ widget-id]] to <span class="athena-widget-inline" data-widget-id="widget-id"></span>
        return cell.replace(/\[\[☃\s+([^\]]+)\]\]/g, (_, widgetId) => {
          return `<span class="athena-widget-inline" data-widget-id="${widgetId.trim()}"></span>`;
        });
      };

      // Helper to process cell content - preserves math for later processing by renderMath
      // DO NOT process math here - it will be double-processed by renderMath later
      const processCellContent = (cell: string): string => {
        let processed = preserveWidgetPlaceholders(cell);

        // Process markdown bold **text** and italic *text*
        processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        processed = processed.replace(/(?<!\*)\*(?!\*)([^*]+)\*(?!\*)/g, '<em>$1</em>');

        return processed;
      };

      // Helper to parse cells from a line
      const parseCells = (line: string): string[] => {
        const trimmed = line.trim();
        // Handle lines that start and end with |
        if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
          return trimmed.slice(1, -1).split('|').map(c => c.trim());
        }
        // Handle lines that start with | but don't end with |
        if (trimmed.startsWith('|')) {
          return trimmed.slice(1).split('|').map(c => c.trim());
        }
        // Handle lines without leading |
        return trimmed.split('|').map(c => c.trim());
      };

      // Helper to check if cells have meaningful content
      const hasMeaningfulContent = (cells: string[]): boolean => {
        // At least one cell should have content that's not just dashes or empty
        return cells.some(cell => cell.length > 0 && !/^[-:]+$/.test(cell));
      };

      while (i < lines.length) {
        const line = lines[i];
        const trimmedLine = line.trim();

        // Check if this line looks like a table row
        // Must have pipes, be a valid table row, have 2+ cells with meaningful content
        const hasPipes = trimmedLine.includes('|');
        const isValid = isValidTableRow(trimmedLine);
        const cells = parseCells(trimmedLine);
        const hasCells = cells.length >= 2;
        const hasMeaningful = hasMeaningfulContent(cells);

        if (hasPipes && trimmedLine.length > 3) {
          console.log('[Athena] Checking line for table:', {
            line: trimmedLine.substring(0, 100),
            hasPipes,
            isValid,
            cellCount: cells.length,
            cells: cells.slice(0, 3),
            hasMeaningful,
          });
        }

        if (hasPipes && isValid && hasCells && hasMeaningful) {
          const tableLines: string[] = [];
          let j = i;

          // Collect consecutive lines with pipes (allowing empty lines between)
          let emptyLineCount = 0;
          while (j < lines.length) {
            const nextLine = lines[j].trim();
            const isSeparatorRow = nextLine.includes('-') && /^[\s|:\-]+$/.test(nextLine);

            if (nextLine.includes('|') &&
              (isSeparatorRow || (isValidTableRow(nextLine) && parseCells(nextLine).length >= 2))) {
              tableLines.push(lines[j]);
              emptyLineCount = 0;
              j++;
            } else if (nextLine === '' && emptyLineCount === 0) {
              // Allow one empty line
              emptyLineCount++;
              j++;
            } else {
              break;
            }
          }

          // Need at least 2 rows to be a table, and must have a proper separator OR meaningful data
          const hasSeparator = tableLines.some(l => /^[\s|:\-]+$/.test(l.trim()) && l.includes('-'));
          if (tableLines.length >= 2 && (hasSeparator || tableLines.length >= 3)) {
            // Look for a separator row (contains only |, -, :, and spaces)
            const separatorIndex = tableLines.findIndex(l => {
              const t = l.trim();
              // Must have at least one - and multiple |, and only contain |, -, :, whitespace
              return t.includes('-') && t.split('|').length >= 2 && /^[\s|:\-]+$/.test(t);
            });

            let html = '<table class="athena-equation-table">';
            const alignments: string[] = [];

            if (separatorIndex >= 1) {
              // Standard markdown table with separator
              // Parse alignment from separator row
              const separatorCells = parseCells(tableLines[separatorIndex]);
              separatorCells.forEach(cell => {
                if (cell.startsWith(':') && cell.endsWith(':')) alignments.push('center');
                else if (cell.endsWith(':')) alignments.push('right');
                else alignments.push('left');
              });

              // Header rows (before separator)
              html += '<thead>';
              for (let k = 0; k < separatorIndex; k++) {
                html += '<tr>';
                const cells = parseCells(tableLines[k]);
                cells.forEach((cell, idx) => {
                  const align = alignments[idx] || 'center';
                  const processedCell = processCellContent(cell);
                  html += `<th style="text-align:${align};padding:8px 12px;font-weight:600;border:1px solid #e5e5e5;">${processedCell}</th>`;
                });
                html += '</tr>';
              }
              html += '</thead>';

              // Body rows (after separator)
              html += '<tbody>';
              for (let k = separatorIndex + 1; k < tableLines.length; k++) {
                if (tableLines[k].trim() === '') continue;
                // Skip if this is another separator row
                if (/^[\s|:\-]+$/.test(tableLines[k].trim())) continue;
                html += '<tr>';
                const cells = parseCells(tableLines[k]);
                cells.forEach((cell, idx) => {
                  const align = alignments[idx] || 'center';
                  const processedCell = processCellContent(cell);
                  html += `<td style="text-align:${align};padding:6px 12px;border:1px solid #e5e5e5;">${processedCell}</td>`;
                });
                html += '</tr>';
              }
              html += '</tbody>';
            } else {
              // Simple table without separator - treat first row as header
              html += '<thead><tr>';
              const headerCells = parseCells(tableLines[0]);
              headerCells.forEach(cell => {
                const processedCell = processCellContent(cell);
                html += `<th style="text-align:center;padding:8px 12px;font-weight:600;border:1px solid #e5e5e5;background:#f7f7f7;">${processedCell}</th>`;
              });
              html += '</tr></thead><tbody>';

              // Data rows
              for (let k = 1; k < tableLines.length; k++) {
                if (tableLines[k].trim() === '') continue;
                html += '<tr>';
                const cells = parseCells(tableLines[k]);
                cells.forEach(cell => {
                  const processedCell = processCellContent(cell);
                  html += `<td style="text-align:center;padding:6px 12px;border:1px solid #e5e5e5;">${processedCell}</td>`;
                });
                html += '</tr>';
              }
              html += '</tbody>';
            }

            html += '</table>';
            console.log('[Athena] Table created successfully:', {
              rowCount: tableLines.length,
              htmlPreview: html.substring(0, 500),
            });
            tablesFound++;
            result.push(html);
            i = j;
            continue;
          } else {
            console.log('[Athena] Table rejected:', {
              tableLineCount: tableLines.length,
              hasSeparator,
              firstLines: tableLines.slice(0, 3),
            });
          }
        }

        result.push(line);
        i++;
      }

      // Convert any remaining widget placeholders to inline markers (for non-table content)
      let finalResult = result.join('\n');
      finalResult = finalResult.replace(/\[\[☃\s+([^\]]+)\]\]/g, (_, widgetId) => {
        return `<span class="athena-widget-inline" data-widget-id="${widgetId.trim()}"></span>`;
      });

      console.log('[Athena] processTable complete:', {
        tablesFound,
        hasWidgetPlaceholders: finalResult.includes('athena-widget-inline'),
        outputPreview: finalResult.substring(0, 500),
      });

      return finalResult;
    };

    // Component to render HTML with inline widget placeholders using portals
    // This preserves table structure by rendering HTML first, then mounting widgets into placeholders
    const HtmlWithInlineWidgets = React.memo(({ html, keyPrefix }: { html: string; keyPrefix: string }) => {
      const containerRef = React.useRef<HTMLDivElement>(null);
      const [widgetMounts, setWidgetMounts] = React.useState<Array<{ el: HTMLElement; widgetId: string }>>([]);
      const [graphieMounts, setGraphieMounts] = React.useState<Array<{ el: HTMLElement; url: string; alt: string }>>([]);

      console.log('[Athena] HtmlWithInlineWidgets rendering:', {
        keyPrefix,
        htmlLength: html.length,
        htmlPreview: html.substring(0, 500),
      });

      // After initial render, find widget and graphie placeholders in the DOM
      React.useEffect(() => {
        if (!containerRef.current) return;

        // Find widget placeholders
        const placeholders = containerRef.current.querySelectorAll('.athena-widget-inline[data-widget-id]');
        const mounts: Array<{ el: HTMLElement; widgetId: string }> = [];

        placeholders.forEach((el) => {
          const widgetId = el.getAttribute('data-widget-id');
          if (widgetId) {
            mounts.push({ el: el as HTMLElement, widgetId });
          }
        });

        console.log('[Athena] Found widget placeholders:', mounts.length);
        if (mounts.length > 0) {
          setWidgetMounts(mounts);
        }

        // Find graphie image placeholders
        const graphiePlaceholders = containerRef.current.querySelectorAll('.athena-graphie-placeholder[data-graphie-url]');
        const gMounts: Array<{ el: HTMLElement; url: string; alt: string }> = [];

        graphiePlaceholders.forEach((el) => {
          const url = el.getAttribute('data-graphie-url');
          const alt = el.getAttribute('data-graphie-alt') || '';
          if (url) {
            gMounts.push({ el: el as HTMLElement, url, alt });
          }
        });

        console.log('[Athena] Found graphie placeholders:', gMounts.length);
        if (gMounts.length > 0) {
          setGraphieMounts(gMounts);
        }
      }, [html]);

      // Render widgets into their placeholders using portals
      const widgetPortals = widgetMounts.map(({ el, widgetId }, idx) => {
        const widget = parsedContent.widgets[widgetId];
        if (!widget) {
          return ReactDOM.createPortal(
            <span className="athena-widget-error">[Widget not found: {widgetId}]</span>,
            el,
            `${keyPrefix}-portal-${idx}`
          );
        }

        const safeWidget = {
          ...widget,
          options: widget.options || {},
          type: widget.type || 'unknown',
        };
        const userValue = state.answers[widgetId];
        const isReadOnly = state.readOnly || (safeWidget.static ?? false);

        return ReactDOM.createPortal(
          <WidgetFactory
            widgetId={widgetId}
            widget={safeWidget as any}
            value={userValue}
            onChange={(value) => !isReadOnly && setAnswer(widgetId, value)}
            readOnly={isReadOnly}
            reviewMode={state.reviewMode}
            theme={state.theme}
          />,
          el,
          `${keyPrefix}-portal-${idx}`
        );
      });

      // Render graphie images into their placeholders using portals
      const graphiePortals = graphieMounts.map(({ el, url, alt }, idx) => {
        return ReactDOM.createPortal(
          <GraphieImage
            url={url}
            alt={alt}
            style={{ maxWidth: '100%' }}
          />,
          el,
          `${keyPrefix}-graphie-portal-${idx}`
        );
      });

      return (
        <>
          <div
            ref={containerRef}
            className="athena-inline-widgets-container"
            dangerouslySetInnerHTML={{ __html: html }}
          />
          {widgetPortals}
          {graphiePortals}
        </>
      );
    });

    // Helper to render HTML that contains inline widget placeholders
    const renderHtmlWithInlineWidgets = (html: string, key: string): React.ReactNode => {
      return <HtmlWithInlineWidgets key={key} html={html} keyPrefix={key} />;
    };

    // Render text content with math/notation support
    const renderTextContent = (text: string, key: string) => {
      // Safety check for null/undefined text
      if (!text || typeof text !== 'string') {
        return null;
      }

      try {
        // First, process tables
        let processedText = processTable(text);

        // Process code fences ```language\ncode\n``` BEFORE math processing
        // This prevents code from being interpreted as math
        // Pattern 1: With language specifier and newline
        processedText = processedText.replace(/```(\w+)\n([\s\S]*?)```/g, (_, lang, code) => {
          const escapedCode = code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
          return `<pre class="athena-code-block" data-language="${lang}"><code>${escapedCode}</code></pre>`;
        });
        // Pattern 2: Without language, just ```\ncode\n```
        processedText = processedText.replace(/```\n([\s\S]*?)```/g, (_, code) => {
          const escapedCode = code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
          return `<pre class="athena-code-block"><code>${escapedCode}</code></pre>`;
        });
        // Pattern 3: Inline code fence ```code``` (no newlines)
        processedText = processedText.replace(/```([^`]+)```/g, (_, code) => {
          const escapedCode = code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
          return `<code class="athena-inline-code">${escapedCode.trim()}</code>`;
        });

        // Also handle inline code `code` (single backticks)
        // But be careful not to process backticks inside code blocks
        processedText = processedText.replace(/`([^`\n]+)`/g, '<code class="athena-inline-code">$1</code>');

        // Clean up stray pipe characters that aren't part of tables
        // Remove standalone || at start of lines
        processedText = processedText.replace(/^\|\|\s*$/gm, '');
        // Remove lines that are just dashes, pipes, colons and spaces (table alignment patterns like "-:|-: | :-")
        processedText = processedText.replace(/^[\s\-:|]+$/gm, '');
        // Remove table alignment pattern lines (e.g., "-:|-:|:-" or "---|---|---")
        processedText = processedText.replace(/^[-:|]+\|[-:|]+$/gm, '');
        // Handle patterns like "|=" at start of lines (from poorly formatted content)
        processedText = processedText.replace(/^\|([^|]*?)$/gm, '$1');
        // Handle inline "|=" patterns that should be "="
        processedText = processedText.replace(/\|=/g, '=');
        // Remove standalone | characters that appear alone on lines
        processedText = processedText.replace(/^\s*\|\s*$/gm, '');
        // Remove trailing || at end of lines (but keep content before)
        processedText = processedText.replace(/\|\|\s*$/gm, '');
        // Remove trailing | at end of lines after content
        processedText = processedText.replace(/\s*\|\s*$/gm, '');
        // Handle "Step N| content" patterns - remove pipe after "Step N"
        processedText = processedText.replace(/(Step\s*\d+)\|\s*/gi, '$1 ');
        // Handle leading pipes before content (like "|28" -> "28")
        processedText = processedText.replace(/^\|(\d)/gm, '$1');
        // Handle "| × " patterns
        processedText = processedText.replace(/\|\s*×/g, '×');

        // Then process math
        processedText = renderMath(processedText);

        // Check for markdown images and render them as React elements
        // FIRST: Pre-process to convert ALL image markdown (including truncated URLs) to a normalized format
        let imageProcessedText = processedText;

        // Debug: Log if content contains image markdown
        if (imageProcessedText.includes('![')) {
          console.log('[Athena] Content contains image markdown:', imageProcessedText.substring(0, 500));
        }

        // Pattern 1: Handle image URLs without closing paren - ![alt](url followed by whitespace/newline/end
        imageProcessedText = imageProcessedText.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)\n]+)(?:\s|$)/g, (_, alt, url) => {
          console.log('[Athena] Pre-process: Image without closing paren:', url);
          return `![${alt}](${url.trim()}) `;
        });

        // Pattern 2: Handle image URLs without closing paren at end of string
        imageProcessedText = imageProcessedText.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)\n]+)$/gm, (_, alt, url) => {
          console.log('[Athena] Pre-process: Image at end of line:', url);
          return `![${alt}](${url.trim()})`;
        });

        // Pattern 3: Handle CDN URLs without closing paren
        imageProcessedText = imageProcessedText.replace(/!\[([^\]]*)\]\(([^)\s]*(?:cdn\.kastatic|ka-perseus)[^\s)\n]*)/g, (_, alt, url) => {
          if (!url.endsWith(')')) {
            console.log('[Athena] Pre-process: CDN image without closing paren:', url);
            return `![${alt}](${url.trim()})`;
          }
          return `![${alt}](${url})`;
        });

        // NUCLEAR OPTION: Direct replacement of ALL image markdown to HTML
        // This runs BEFORE the React element processing and handles ALL cases
        const convertToImgTag = (alt: string, rawUrl: string): string => {
          let imageUrl = rawUrl.trim();
          // Convert web+graphie:// URLs
          if (imageUrl.startsWith('web+graphie://')) {
            imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
          }
          // Handle CDN URLs missing extension
          else if ((imageUrl.includes('cdn.kastatic.org') || imageUrl.includes('ka-perseus')) &&
            !imageUrl.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
            imageUrl = imageUrl + '.png';
          }
          // Handle relative URLs
          else if (imageUrl.startsWith('/')) {
            const ASSETS_BASE_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
            imageUrl = ASSETS_BASE_URL + imageUrl;
          }
          return `<img src="${imageUrl}" alt="${alt}" class="athena-image" style="max-width:100%;height:auto;display:block;margin:1rem 0;" referrerpolicy="no-referrer" />`;
        };

        // Replace ALL image markdown patterns with img tags directly
        // Pattern: ![alt](url) - standard with closing paren
        imageProcessedText = imageProcessedText.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
          console.log('[Athena] Nuclear: Converting image to HTML:', url.substring(0, 80));
          return convertToImgTag(alt, url);
        });

        // Pattern: ![alt](url followed by non-paren (no closing paren)
        imageProcessedText = imageProcessedText.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s<]+)/g, (match, alt, url) => {
          // Only if there's still a ![ pattern (wasn't matched above)
          console.log('[Athena] Nuclear fallback: Converting truncated image:', url.substring(0, 80));
          return convertToImgTag(alt, url);
        });

        // If still has raw markdown, log it
        if (imageProcessedText.includes('![') && imageProcessedText.includes('](')) {
          console.log('[Athena] WARNING: Still has raw image markdown after nuclear processing:',
            imageProcessedText.match(/!\[[^\]]*\]\([^)]{0,100}/)?.[0]);
        }

        // Now use the standard pattern for React element processing (should find nothing since we converted to HTML)
        const imagePattern = /!\[([^\]]*)\]\(([^)]+)\)/g;
        const parts: React.ReactNode[] = [];
        let lastIndex = 0;
        let match;
        let partIndex = 0;

        while ((match = imagePattern.exec(imageProcessedText)) !== null) {
          console.log('[Athena] Image match found:', { alt: match[1], url: match[2] });
          // Add text before the image
          if (match.index > lastIndex) {
            const textBefore = imageProcessedText.slice(lastIndex, match.index);
            const finalText = textBefore
              .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
              .replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>')
              .replace(/`([^`]+)`/g, '<code>$1</code>')
              .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="athena-link">$1</a>');
            parts.push(
              <span
                key={`${key}-text-${partIndex++}`}
                className="athena-text"
                dangerouslySetInnerHTML={{ __html: finalText }}
              />
            );
          }

          // Add the image
          const altText = match[1];
          let imageUrl = match[2];

          // Convert web+graphie:// URLs - use PNG which has labels baked in
          // SVG requires fetching -data.json for labels which faces CORS issues
          if (imageUrl.startsWith('web+graphie://')) {
            imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
          }
          // Handle CDN URLs that might be missing file extension
          else if (imageUrl.includes('cdn.kastatic.org') || imageUrl.includes('ka-perseus')) {
            // Add .png extension if no extension present
            if (!imageUrl.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
              imageUrl = imageUrl + '.png';
            }
          }
          // Handle relative URLs from backend assets
          else if (imageUrl.startsWith('/')) {
            const ASSETS_BASE_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
            imageUrl = ASSETS_BASE_URL + imageUrl;
          }
          // Handle other relative URLs (no protocol)
          else if (!imageUrl.startsWith('http') && !imageUrl.startsWith('data:')) {
            const ASSETS_BASE_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
            imageUrl = ASSETS_BASE_URL + '/' + imageUrl;
          }

          console.log('[Athena] Rendering image:', { alt: altText, url: imageUrl });
          parts.push(
            <div key={`${key}-img-${partIndex++}`} className="athena-inline-image">
              <img
                src={imageUrl}
                alt={altText}
                className="athena-image"
                referrerPolicy="no-referrer"
                style={{ maxWidth: '100%', height: 'auto', display: 'block', margin: '1rem 0' }}
                onLoad={() => console.log('[Athena] Image loaded:', imageUrl)}
                onError={(e) => {
                  console.error('[Athena] Image failed to load:', imageUrl);
                  // Try alternate format as fallback
                  const target = e.target as HTMLImageElement;
                  if (target.src.endsWith('.png')) {
                    target.src = target.src.replace('.png', '.svg');
                  } else if (target.src.endsWith('.svg')) {
                    target.src = target.src.replace('.svg', '.png');
                  }
                }}
              />
            </div>
          );

          lastIndex = match.index + match[0].length;
        }

        // Add remaining text
        if (lastIndex < imageProcessedText.length) {
          const remainingText = imageProcessedText.slice(lastIndex);
          const finalText = remainingText
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="athena-link">$1</a>');
          parts.push(
            <span
              key={`${key}-text-${partIndex++}`}
              className="athena-text"
              dangerouslySetInnerHTML={{ __html: finalText }}
            />
          );
        }

        // If no images found, just process as text with markdown
        if (parts.length === 0) {
          const finalText = imageProcessedText
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="athena-link">$1</a>');

          // Check for inline widget placeholders (from table cells) or graphie image placeholders
          if (finalText.includes('athena-widget-inline') || finalText.includes('athena-graphie-placeholder')) {
            return renderHtmlWithInlineWidgets(finalText, key);
          }

          return (
            <span
              key={key}
              className="athena-text"
              dangerouslySetInnerHTML={{ __html: finalText }}
            />
          );
        }

        // Check if any parts contain inline widgets or graphie images
        const processedParts = parts.map((part, idx) => {
          if (React.isValidElement(part) && part.props.dangerouslySetInnerHTML) {
            const html = part.props.dangerouslySetInnerHTML.__html;
            if (html && (html.includes('athena-widget-inline') || html.includes('athena-graphie-placeholder'))) {
              return renderHtmlWithInlineWidgets(html, `${key}-inline-${idx}`);
            }
          }
          return part;
        });

        return <React.Fragment key={key}>{processedParts}</React.Fragment>;
      } catch (error) {
        console.error(`Error rendering text content:`, error);
        return (
          <span key={key} className="athena-text-error">
            {text}
          </span>
        );
      }
    };

    // Render widget using WidgetFactory
    const renderWidget = (widgetId: string, key: string) => {
      try {
        const widget = parsedContent.widgets[widgetId];
        if (!widget) {
          return (
            <span key={key} className="athena-widget-error">
              [Widget not found: {widgetId}]
            </span>
          );
        }

        // Ensure widget has proper structure
        const safeWidget = {
          ...widget,
          options: widget.options || {},
          type: widget.type || 'unknown',
        };

        const userValue = state.answers[widgetId];
        const isReadOnly = state.readOnly || (safeWidget.static ?? false);

        return (
          <WidgetFactory
            key={key}
            widgetId={widgetId}
            widget={safeWidget as any}
            value={userValue}
            onChange={(value) => !isReadOnly && setAnswer(widgetId, value)}
            readOnly={isReadOnly}
            reviewMode={state.reviewMode}
            theme={state.theme}
          />
        );
      } catch (error) {
        console.error(`Error rendering widget ${widgetId}:`, error);
        return (
          <span key={key} className="athena-widget-error">
            [Error rendering widget: {widgetId}]
          </span>
        );
      }
    };

    return (
      <div
        ref={containerRef}
        className={`athena-content athena-theme-${state.theme}`}
        tabIndex={-1}
        role="region"
        aria-label="Question content"
      >
        <div className="athena-question">
          {parsedContent.parts.map((part, idx) => {
            const key = `part-${idx}`;
            if (part.type === 'text') {
              return renderTextContent(part.content, key);
            } else if (part.type === 'widget' && part.widgetId) {
              return renderWidget(part.widgetId, key);
            }
            return null;
          })}
        </div>

        {/* Hints section */}
        {state.hintsVisible > 0 && Array.isArray(item.hints) && item.hints.length > 0 && (
          <div className="athena-hints">
            <h4 className="athena-hints-title">Hints</h4>
            {item.hints.slice(0, state.hintsVisible).map((hint, idx) => {
              // Process hint content - same processing as question content
              let hintContent = hint?.content || '';

              // Process images in hint content FIRST (before math processing)
              if (hintContent.includes('![')) {
                hintContent = hintContent.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, url) => {
                  let imageUrl = url.trim();
                  if (imageUrl.startsWith('web+graphie://')) {
                    imageUrl = imageUrl.replace('web+graphie://', 'https://') + '.png';
                  } else if ((imageUrl.includes('cdn.kastatic.org') || imageUrl.includes('ka-perseus')) &&
                    !imageUrl.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
                    imageUrl = imageUrl + '.png';
                  }
                  return `<img src="${imageUrl}" alt="${alt}" class="athena-image" style="max-width:100%;height:auto;display:block;margin:1rem 0;" referrerpolicy="no-referrer" />`;
                });
              }

              // Process markdown tables BEFORE math processing
              hintContent = processTable(hintContent);

              // Process math with KaTeX - wrap in try-catch for safety
              try {
                hintContent = renderMath(hintContent);
              } catch (e) {
                console.error('[Athena] Error rendering math in hint:', e);
                // Fallback: try basic LaTeX rendering for inline math
                hintContent = hintContent.replace(/\$([^$]+)\$/g, (_, math) => {
                  try {
                    return katex.renderToString(math.trim(), { throwOnError: false, displayMode: false });
                  } catch {
                    return `<span style="font-style: italic; color: #666;">${math}</span>`;
                  }
                });
              }

              // Process markdown links [text](url) AFTER math (so links aren't inside math)
              hintContent = hintContent.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">$1</a>');

              // Process bold **text** and *text* AFTER math
              hintContent = hintContent.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
              hintContent = hintContent.replace(/\*([^*]+)\*/g, '<em>$1</em>');

              return (
                <div key={`hint-${idx}`} className="athena-hint-item expanded">
                  <div className="athena-hint-header">
                    <span className="athena-hint-label">Hint {idx + 1} of {item.hints?.length || 0}</span>
                  </div>
                  <div
                    className="athena-hint-content"
                    dangerouslySetInnerHTML={{ __html: hintContent }}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }
);

// ============================================================================
// LOADING FALLBACK
// ============================================================================

function LoadingFallback() {
  return (
    <div className="athena-loading">
      <div className="athena-loading-spinner" />
      <span className="athena-loading-text">Loading content...</span>
    </div>
  );
}

// ============================================================================
// ERROR BOUNDARY
// ============================================================================

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class AthenaErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Athena render error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="athena-error">
            <h4>Unable to render content</h4>
            <p>{this.state.error?.message || 'An unexpected error occurred'}</p>
          </div>
        )
      );
    }
    return this.props.children;
  }
}

// ============================================================================
// MAIN RENDERER COMPONENT
// ============================================================================

export const AthenaRenderer = forwardRef<AthenaRendererRef, AthenaRendererProps>(
  function AthenaRenderer(
    {
      item,
      problemNum = 0,
      hintsVisible = 0,
      reviewMode = false,
      showSolutions = 'none',
      initialState,
      onStateChange,
      onAnswerChange,
      readOnly = false,
      theme = 'light',
      ariaLabel,
      apiOptions = {},
      dependencies = {},
    },
    ref
  ) {
    const contentRef = useRef<AthenaRendererRef>(null);

    // Forward ref to content renderer
    useImperativeHandle(ref, () => ({
      getUserInput: () => contentRef.current?.getUserInput() || {},
      getUserInputLegacy: () => contentRef.current?.getUserInputLegacy() || [],
      getSerializedState: () =>
        contentRef.current?.getSerializedState() || { question: {} },
      restoreState: (state) => contentRef.current?.restoreState(state),
      focus: () => contentRef.current?.focus(),
      blur: () => contentRef.current?.blur(),
      score: () =>
        contentRef.current?.score() || {
          correct: false,
          empty: true,
          earned: 0,
          total: 0,
          details: [],
        },
    }));

    // Handle state changes
    const handleEvent = useCallback(
      (event: any) => {
        if (event.type === 'answer-change' && onAnswerChange) {
          onAnswerChange(event.data.widgetId, event.data.value);
        }
        dependencies.onEvent?.(event);
      },
      [onAnswerChange, dependencies]
    );

    return (
      <AthenaErrorBoundary>
        <AthenaProvider
          theme={theme}
          dependencies={{ ...dependencies, onEvent: handleEvent }}
          apiOptions={apiOptions}
          initialAnswers={initialState?.question || {}}
          hintsVisible={hintsVisible}
          reviewMode={reviewMode}
          showSolutions={showSolutions}
          readOnly={readOnly}
        >
          <div
            className="athena-renderer"
            role="application"
            aria-label={ariaLabel || `Question ${problemNum + 1}`}
          >
            <Suspense fallback={<LoadingFallback />}>
              <ContentRenderer ref={contentRef} item={item} problemNum={problemNum} />
            </Suspense>
          </div>
        </AthenaProvider>
      </AthenaErrorBoundary>
    );
  }
);

export default AthenaRenderer;
