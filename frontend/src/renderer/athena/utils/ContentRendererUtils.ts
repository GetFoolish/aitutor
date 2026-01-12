// @ts-ignore
import katex from 'katex';
import { marked } from 'marked';

// KaTeX macros for Khan Academy color commands
// Note: In KaTeX macros, # is used for arguments, so hex colors need ## to escape the #
export const katexMacros = {
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
  output: 'html' as const, // Force only HTML output to avoid MathML duplication issues
};

// Helper function to render math with KaTeX
export const renderMath = (text: string): string => {
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

  // STEP 1.5: Convert unsupported 'eqnarray' to 'aligned' (KaTeX doesn't support eqnarray)
  // Handle qquad wrapper: \qquad { \begin{eqnarray} ... \end{eqnarray} }
  processed = processed.replace(/\\qquad\s*\{\s*\\begin\{eqnarray\}/g, '\\qquad \\begin{aligned}');
  processed = processed.replace(/\\end\{eqnarray\}\s*\}/g, '\\end{aligned}');
  processed = processed.replace(/\\begin\{eqnarray\}/g, '\\begin{aligned}');
  processed = processed.replace(/\\end\{eqnarray\}/g, '\\end{aligned}');

  // Normalize eqnarray alignment markers (&=&) to aligned markers (&=)
  if (processed.includes('aligned') || processed.includes('eqnarray')) {
    processed = processed.replace(/&=&/g, '&=');
  }

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

  // Process regex-based math wrapping for common bare LaTeX patterns
  // This handles cases like "kx^\textcolor{...}" which are math but miss $ delimiters

  // CRITICAL FIX: We must temporarily protect EXISTING inline math ($...$) before running matches for bare math.
  // Otherwise, the bare math regex (which looks for patterns like [0-9]+\^[...]) might falsely match content 
  // INSIDE valid latex (e.g., matching "6^{-}" inside "$\lim_{x\to 6^{-}}$").
  // This causes the regex to wrap the inner part in new $ signs, breaking the outer math block.
  const inlineMathBlocks: string[] = [];
  processed = processed.replace(/\$([^$]+)\$/g, (match) => {
    // Skip if it looks like $$ (should be protected already but safety check)
    if (match.startsWith('$$')) return match;
    const idx = inlineMathBlocks.length;
    inlineMathBlocks.push(match);
    return `__ATHENA_TEMP_INLINE_MATH_${idx}__`;
  });

  const bareMathPatterns = [
    // Pattern: something^something (exponent) - Supports simple chars, {groups}, or \textcolor{...}{...}
    new RegExp("(?<!\\$)(?<!\\\\)\\b([a-zA-Z0-9]+)\\^(\\{[^}]+\\}|\\\\textcolor\\{[^}]+\\}\\{[^}]+\\}|[a-zA-Z0-9\\\\]+)(?!\\$)", "g"),
    // Pattern: \frac{...}{...} without $
    new RegExp("(?<!\\$)\\\\frac\\{[^}]+\\}\\{[^}]+\\}(?!\\$)", "g"),
    // Pattern: \sqrt{...} without $
    // Pattern: complex polynomial with color (e.g. \textcolor{...}{7}x^...)
    // Matches sequences of digits, vars, ^, +, -, and textcolor blocks
    new RegExp("(?<!\\$)(?<!\\\\)((?:\\\\textcolor\\{#[a-fA-F0-9]{3,6}\\}\\{[^}]+\\}|[0-9a-z]+)[\\^x+\\-=]+(?:\\\\textcolor\\{#[a-fA-F0-9]{3,6}\\}\\{[^}]+\\}|[0-9a-z\\^+\\-=]+)+)(?!\\$)", "g"),
  ];

  bareMathPatterns.forEach(pattern => {
    processed = processed.replace(pattern, (match) => {
      // Safety check: strictly ignore matches that look like CSS classes or simple hyphenated text.
      // We only want to wrap distinctively "math-y" expressions (containing ^, \, +, =, etc.)
      // This prevents breaking HTML attributes like class="athena-equation-table"
      if (/^[a-zA-Z0-9\-\s]+$/.test(match)) return match;

      return `$${match}$`;
    });
  });

  // Restore protected inline math blocks
  processed = processed.replace(/__ATHENA_TEMP_INLINE_MATH_(\d+)__/g, (_, idx) => {
    return inlineMathBlocks[parseInt(idx, 10)];
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
export const processTable = (text: string): string => {
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
    if (/^[\s|:-]+$/.test(trimmed) && trimmed.includes('-')) return false;
    return true;
  };

  // Helper to parse cells accounting for escaped pipes
  const parseCells = (line: string): string[] => {
    // Split by | but ignore \|
    const cells: string[] = [];
    let currentCell = '';
    let isEscaped = false;

    for (let k = 0; k < line.length; k++) {
      const char = line[k];
      if (isEscaped) {
        currentCell += char;
        isEscaped = false;
      } else if (char === '\\') {
        currentCell += char;
        isEscaped = true;
      } else if (char === '|') {
        cells.push(currentCell.trim());
        currentCell = '';
      } else {
        currentCell += char;
      }
    }
    cells.push(currentCell.trim());

    // Remove empty first/last cells if they are empty (common in markdown tables | a | b |)
    if (cells.length > 0 && cells[0] === '') cells.shift();
    if (cells.length > 0 && cells[cells.length - 1] === '') cells.pop();

    return cells;
  };

  // Helper to process cell content (basic markdown only, math handled later)
  const processCellContent = (cell: string): string => {
    let content = cell.trim();
    // Convert widget placeholders from [[☃ widget-id]] to inline markers
    // This allows widgets to be rendered inside table cells
    content = content.replace(/\[\[☃\s+([^\]]+)\]\]/g, (_, widgetId) => {
      return `<span class="athena-widget-inline" data-widget-id="${widgetId.trim()}"></span>`;
    });
    return content;
  };

  // Helper to check if a line has meaningful content (not just empty cells)
  const hasMeaningfulContent = (cells: string[]): boolean => {
    return cells.some(cell => cell.trim().length > 0 && !/^[\s:-]+$/.test(cell));
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmedLine = line.trim();

    // Check if this line looks like a table row
    const hasPipes = trimmedLine.includes('|');
    const isValid = isValidTableRow(line);

    // Only process as table if it looks valid
    const cells = hasPipes ? parseCells(line) : [];
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
  // IMPORTANT: Ensure table is followed by a blank line to avoid merging with subsequent blocks (like headers)
  let finalResult = result.join('\n') + '\n\n';
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

// Helper to process image markdown
export const processImageMarkdown = (text: string): string => {
  if (!text || !text.includes('![')) return text || '';

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

    // For graphie images, check if it's a statistical graph that needs PNG
    if (isGraphieUrl(imageUrl)) {
      console.log('[Athena] Processing graphie URL:', imageUrl);
      const lowerUrl = imageUrl.toLowerCase();

      // Refined heuristic: check for statistical keywords
      // Ensure "graph" is matched as more than just a substring of "graphie" 
      // by checking for common statistical terms or specific URL patterns
      const isStatisticalGraph =
        lowerUrl.includes('voting') ||
        lowerUrl.includes('political') ||
        lowerUrl.includes('probability') ||
        lowerUrl.includes('bar-') ||
        lowerUrl.includes('axis') ||
        lowerUrl.includes('chart') ||
        (/\bgraph\b/.test(lowerUrl.replace('graphie', ' '))); // Match "graph" but not in "graphie"

      console.log('[Athena] Is statistical graph?', isStatisticalGraph, 'URL:', lowerUrl.substring(0, 100));
      // For statistical graphs, use PNG directly (has rotated axis labels already rendered)
      if (isStatisticalGraph) {
        console.log('[Athena] Statistical graph detected, using PNG directly:', imageUrl);
        let pngUrl = imageUrl;
        if (pngUrl.startsWith('web+graphie://')) {
          pngUrl = pngUrl.replace('web+graphie://', 'https://').replace(/\.(png|svg)$/, '') + '.png';
        } else {
          pngUrl = pngUrl.replace(/\.(png|svg)$/, '') + '.png';
        }
        return `<img src="${pngUrl}" alt="${alt}" class="graphie-image" style="max-width:500px;width:auto;height:auto;display:block;margin:1rem auto;" referrerpolicy="no-referrer" />`;
      }

      // For other graphie images, create a placeholder that will be replaced with GraphieImage component
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
    } else if (imageUrl.startsWith('/')) {
      const ASSETS_BASE_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
      imageUrl = ASSETS_BASE_URL + imageUrl;
    }

    return `<img src="${imageUrl}" alt="${alt}" class="athena-image" style="max-width:100%;height:auto;display:block;margin:1rem 0;" referrerpolicy="no-referrer" />`;
  };

  // Pattern 1: Standard ![alt] (url) with optional whitespace and closing paren
  processed = processed.replace(/!\[([\s\S]*?)\]\s*\(\s*([\s\S]*?)\s*\)/g, (_, alt, url) => {
    console.log('[Athena] Early processing: Standard image:', url.substring(0, 80));
    return toImgTag(alt, url.trim());
  });

  // Pattern 2: Truncated URL without closing paren, allowing whitespace
  processed = processed.replace(/!\[([^\]]*)\]\s*\((https?:\/\/[^\s\n<]+)/g, (_, alt, url) => {
    console.log('[Athena] Early processing: Truncated image:', url.substring(0, 80));
    return toImgTag(alt, url.replace(/[)\s]+$/, ''));
  });

  return processed;
};

// Helper to clean up legacy content artifacts (stray pipes, etc.)
export const cleanLegacyContent = (text: string): string => {
  let processedText = text;

  // 1. Remove stray blockquote markers ">" that appear at the start of table cells or lines
  // MUST happen before header normalization so we see the # characters correctly
  processedText = processedText.replace(/([\|\n]|^)\s*>+\s*/gm, '$1');
  // Also handle stray ">" immediately before headers or images within a line
  processedText = processedText.replace(/(\s+)>+(#{1,6}|!\[)/g, '$1$2');

  // 2. Handle headers with trailing hashes (e.g., "##Which Pet?##" -> "## Which Pet?")
  // Ensure they are surrounded by blank lines so marked.parse() recognizes them as block elements
  // We use a broader regex that handles both cases with and without trailing hashes
  processedText = processedText.replace(/(^|[\n|])\s*(#{1,6})\s*([^#|\n]+?)\s*#*\s*(?=[\|\n]|$)/g, '$1\n\n$2 $3\n\n');

  // 3. Unescape escaped dollar signs (e.g., "\$212" -> "$212")
  // Use HTML entity &dollar; to avoid accidentally triggering KaTeX math rendering later
  // MUST happen before math protection in Phase 2
  processedText = processedText.replace(/\\(\$)/g, '&dollar;');

  // 4. Normalize legacy double-pipe delimiters "||"
  // Try to break them into newlines to separate sections or rows
  processedText = processedText.replace(/\s*\|\|\s*/g, '\n\n');

  // 4.5. Detect mangled table rows joined on one line (e.g. "Col1 | Col2 | - | - | Row2_1 | Row2_2")
  // If we see a separator pattern followed by more pipes on the same line, break it
  processedText = processedText.replace(/(\|\s*[:\-]{2,}\s*\|\s*[:\-]{2,}\s*\|)\s*/g, '$1\n');

  // 4.6. Normalize ordered lists to ensure they're recognized as block elements
  // Ensure ordered lists (1., 2., etc.) are preceded by blank lines
  // Handle both start of content (^) and after newlines (\n)
  processedText = processedText.replace(/(^|\n)([0-9]+\.\s+)/gm, '$1\n$2');

  // 5. Clean up stray pipe characters that aren't part of tables
  // Remove standalone | at start of lines
  processedText = processedText.replace(/^\|\s*$/gm, '');
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
  // Remove trailing | at end of lines after content
  processedText = processedText.replace(/\s*\|\s*$/gm, '');

  // 6. Handle "Step N| content" patterns - remove pipe after "Step N"
  processedText = processedText.replace(/(Step\s*\d+)\|\s*/gi, '$1 ');
  // Handle leading pipes before content (like "|28" -> "28")
  processedText = processedText.replace(/^\|(\d)/gm, '$1');
  // Handle "| × " patterns
  processedText = processedText.replace(/\|\s*×/g, '×');

  return processedText;
};

// Helper to process code blocks
export const preprocessCodeBlocks = (text: string): string => {
  let processedText = text;
  // Process code fences ```language\ncode\n``` BEFORE math processing
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
  processedText = processedText.replace(/`([^`\n]+)`/g, '<code class="athena-inline-code">$1</code>');
  return processedText;
};

// Helper to preprocess basic Markdown formatting
// This ensures **bold** and # headers are properly handled
const preprocessMarkdown = (text: string): string => {
  if (!text) return '';

  let processed = text;

  // Convert **text** to <strong>text</strong> if not already in HTML
  // But preserve it inside code blocks (already protected)
  processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Convert # headers at start of line
  // # Header → <h1>Header</h1>
  // ## Header → <h2>Header</h2>
  // ### Header → <h3>Header</h3>
  processed = processed.replace(/^#{1,3}\s+(.+)$/gm, (match, headerText, offset) => {
    const level = match.indexOf(' ');
    return `<h${level}>${headerText}</h${level}>`;
  });

  return processed;
};


// Orchestrator for full content processing
export const processContent = (content: string): string => {
  if (!content) return '';

  // Phase 1: Clean legacy content (IMPORTANT: must happen first to unescape \$ and fix mangled structure)
  let processed = cleanLegacyContent(content);

  // Phase 2: Protect raw math from table parser
  const mathBlocks: string[] = [];
  processed = processed.replace(/\$\$([\s\S]+?)\$\$|\$([^$]+)\$/g, (match) => {
    const placeholder = `__ATHENA_MATH_RAW_${mathBlocks.length}__`;
    mathBlocks.push(match);
    return placeholder;
  });

  // Phase 3: Process tables (now safe from || in math and clean from legacy artifacts)
  processed = processTable(processed);

  // Phase 3.5: Decode problematic HTML entities in plain text (safe after math protection)
  // This must happen BEFORE any other protection that might catch them
  if (processed.includes('&dollar;') || processed.includes('{,}')) {
    console.log('[Athena] Decoding HTML entities:', {
      before: processed.substring(0, 200),
      hasDollar: processed.includes('&dollar;'),
      hasComma: processed.includes('{,}')
    });
    // &dollar; → $
    processed = processed.replace(/&dollar;/g, '$');
    // {,} → ,
    processed = processed.replace(/\{,\}/g, ',');
  }

  // Phase 4: Pre-process code blocks
  processed = preprocessCodeBlocks(processed);

  // Phase 5: Process images
  processed = processImageMarkdown(processed);

  // Phase 6: Render math and protect the HTML output
  const htmlProtected: string[] = [];
  const addProtection = (html: string): string => {
    const placeholder = `ATHENAHTMLSAFE${htmlProtected.length}ENDMARKER`;
    htmlProtected.push(html);
    return placeholder;
  };

  // Render each math block and protect the resulting HTML
  mathBlocks.forEach((math, idx) => {
    const renderedMath = renderMath(math);
    const protectedPlaceholder = addProtection(renderedMath);
    console.log(`[Athena] Math ${idx}: ${math} -> ${protectedPlaceholder}`);
    processed = processed.replace(`__ATHENA_MATH_RAW_${idx}__`, protectedPlaceholder);
  });

  // Phase 7: Protect other HTML elements from Markdown
  processed = processed.replace(/<table[\s\S]*?<\/table>/g, (match) => addProtection(match));
  processed = processed.replace(/<(pre|code)[\s\S]*?<\/\1>/g, (match) => addProtection(match));
  processed = processed.replace(/<img[^>]+>/g, (match) => addProtection(match));
  processed = processed.replace(/<span[^>]*class="athena-graphie-placeholder"[^>]*>[\s\S]*?<\/span>/g, (match) => addProtection(match));

  // Phase 8: Convert widget placeholders to HTML and protect them
  processed = processed.replace(/\[\[☃\s+([^\]]+)\]\]/g, (_, widgetId) => {
    const html = `<span class="athena-widget-inline" data-widget-id="${widgetId.trim()}"></span>`;
    return addProtection(html);
  });

  // Phase 8.5: Preprocess basic Markdown formatting (before marked parser)
  // This ensures **bold** and # headers are converted
  processed = preprocessMarkdown(processed);

  // Phase 9: Run Markdown parser on simplified text
  // Enable gfm (GitHub Flavored Markdown) and pedantic for better list handling
  let finalHtml = marked.parse(processed, {
    breaks: true,
    gfm: true,
    pedantic: false
  }) as string;

  // Phase 10: Restore all protected HTML
  // Phase 10: Restore all protected HTML
  // IMPORTANT: Restore in REVERSE order (Last-In, First-Out)
  // This is critical because outer blocks (like tables) are protected AFTER inner blocks (like math).
  // Restoring the outer block first (higher index) exposes the inner placeholders (lower index) to be caught by subsequent iterations.
  console.log(`[Athena] Restoring ${htmlProtected.length} protected HTML blocks`);
  for (let idx = htmlProtected.length - 1; idx >= 0; idx--) {
    const html = htmlProtected[idx];
    const placeholder = `ATHENAHTMLSAFE${idx}ENDMARKER`;
    finalHtml = finalHtml.split(placeholder).join(html);
  }

  return finalHtml;
};
