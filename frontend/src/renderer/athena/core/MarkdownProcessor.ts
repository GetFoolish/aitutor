/**
 * Markdown Processor
 *
 * Processes markdown content with special handling for:
 * - Math notation (preserving LaTeX)
 * - Widget placeholders
 * - Code blocks with syntax highlighting
 * - Diagrams
 */

export interface MarkdownOptions {
  /** Enable math rendering */
  math?: boolean;
  /** Enable code syntax highlighting */
  code?: boolean;
  /** Enable diagrams */
  diagrams?: boolean;
  /** Sanitize HTML */
  sanitize?: boolean;
  /** Base URL for relative links */
  baseUrl?: string;
  /** Custom link target */
  linkTarget?: '_blank' | '_self';
}

export interface ProcessedMarkdown {
  html: string;
  hasMath: boolean;
  hasCode: boolean;
  hasDiagrams: boolean;
  mathExpressions: Array<{ content: string; displayMode: boolean }>;
  codeBlocks: Array<{ language: string; code: string }>;
}

/**
 * Processes markdown content for Athena rendering
 */
export class MarkdownProcessor {
  private options: MarkdownOptions;

  constructor(options: MarkdownOptions = {}) {
    this.options = {
      math: true,
      code: true,
      diagrams: true,
      sanitize: true,
      linkTarget: '_blank',
      ...options,
    };
  }

  /**
   * Process markdown content
   */
  process(content: string): ProcessedMarkdown {
    const mathExpressions: Array<{ content: string; displayMode: boolean }> = [];
    const codeBlocks: Array<{ language: string; code: string }> = [];
    let hasMath = false;
    let hasCode = false;
    let hasDiagrams = false;

    let processed = content;

    // Hardcoded fix for Dino Graph hints showing broken widgets
    if (processed.toLowerCase().includes("plotter 2")) {
      processed = processed.replace(
        /\[\[(?:Widget:\s*|☃\s*)plotter 2.*?\]\]/gi,
        "\n\n![](/fixed_graphs/corr.png)\n\n"
      );
    }

    // Step 1: Protect math expressions from markdown processing
    const mathPlaceholders: Array<{ placeholder: string; content: string; displayMode: boolean }> = [];
    let mathIndex = 0;

    // Protect display math: $$...$$ and \[...\]
    processed = processed.replace(/\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g, (match, content1, content2) => {
      const mathContent = content1 || content2;
      const placeholder = `__MATH_DISPLAY_${mathIndex++}__`;
      mathPlaceholders.push({ placeholder, content: mathContent, displayMode: true });
      mathExpressions.push({ content: mathContent, displayMode: true });
      hasMath = true;
      return placeholder;
    });

    // Protect inline math: $\begin{env}...\end{env}$ (multiline) | $...$ (single line) | \(...\)
    const inlineMathRegex = /\$\\begin\{([^}]+)\}([\s\S]+?)\\end\{\1\}\$|\$([^$\n]+)\$|\\\(([\s\S]+?)\\\)/g;
    processed = processed.replace(inlineMathRegex, (match, envName, envContent, simpleContent, parenContent) => {
      const mathContent = (envName ? `\\begin{${envName}}${envContent}\\end{${envName}}` : null) || simpleContent || parenContent;
      const placeholder = `__MATH_INLINE_${mathIndex++}__`;
      mathPlaceholders.push({ placeholder, content: mathContent, displayMode: false });
      mathExpressions.push({ content: mathContent, displayMode: false });
      hasMath = true;
      return placeholder;
    });

    // Step 2: Protect code blocks
    const codePlaceholders: Array<{ placeholder: string; language: string; code: string }> = [];
    let codeIndex = 0;

    processed = processed.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, language, code) => {
      const placeholder = `__CODE_${codeIndex++}__`;
      const lang = language || 'plaintext';
      codePlaceholders.push({ placeholder, language: lang, code: code.trim() });
      codeBlocks.push({ language: lang, code: code.trim() });

      if (lang === 'mermaid') {
        hasDiagrams = true;
      } else {
        hasCode = true;
      }

      return placeholder;
    });

    // Step 3: Protect widget placeholders
    const widgetPlaceholders: Array<{ placeholder: string; widgetId: string }> = [];
    let widgetIndex = 0;

    processed = processed.replace(/\[\[☃\s+([^\]]+)\]\]/g, (match, widgetId) => {
      const placeholder = `__WIDGET_${widgetIndex++}__`;
      widgetPlaceholders.push({ placeholder, widgetId: widgetId.trim() });
      return placeholder;
    });

    // Support explicit "Widget:" syntax [[Widget: widget-id (type)]]
    processed = processed.replace(/\[\[Widget:\s+([^\]]+)\]\]/g, (match, rawId) => {
      const placeholder = `__WIDGET_${widgetIndex++}__`;
      // rawId might be "plotter 2 (plotter)" -> extract "plotter 2"
      let widgetId = rawId.split('(')[0].trim();
      widgetPlaceholders.push({ placeholder, widgetId });
      return placeholder;
    });

    // Step 4: Process markdown
    processed = this.processMarkdownSyntax(processed);

    // Step 5: Restore placeholders with proper HTML

    // Restore math expressions
    for (const { placeholder, content, displayMode } of mathPlaceholders) {
      const className = displayMode ? 'athena-math athena-math-display' : 'athena-math athena-math-inline';
      const tag = displayMode ? 'div' : 'span';
      const escapedContent = this.escapeHtml(content);
      const html = `<${tag} class="${className}" data-math="${escapedContent}" data-display="${displayMode}">${escapedContent}</${tag}>`;
      processed = processed.replace(placeholder, html);
    }

    // Restore code blocks
    for (const { placeholder, language, code } of codePlaceholders) {
      let html: string;
      if (language === 'mermaid') {
        html = `<div class="athena-diagram athena-mermaid" data-diagram="${this.escapeHtml(code)}">${this.escapeHtml(code)}</div>`;
      } else {
        html = `<pre class="athena-code language-${language}"><code class="language-${language}">${this.escapeHtml(code)}</code></pre>`;
      }
      processed = processed.replace(placeholder, html);
    }

    // Restore widget placeholders
    for (const { placeholder, widgetId } of widgetPlaceholders) {
      const html = `<span class="athena-widget-placeholder" data-widget-id="${this.escapeHtml(widgetId)}"></span>`;
      processed = processed.replace(placeholder, html);
    }

    // Step 6: Sanitize if enabled
    if (this.options.sanitize) {
      processed = this.sanitizeHtml(processed);
    }

    return {
      html: processed,
      hasMath,
      hasCode,
      hasDiagrams,
      mathExpressions,
      codeBlocks,
    };
  }

  /**
   * Process Khan Academy style color commands
   * \purpleD{text}, \blueE{text}, \greenE{text}, \redE{text}, etc.
   */
  private processKhanColors(content: string): string {
    const colorMap: Record<string, string> = {
      // Purple variants
      purpleA: '#9c4dcc',
      purpleB: '#a05acc',
      purpleC: '#aa63d9',
      purpleD: '#b56ccc',
      purpleE: '#c077d9',
      // Blue variants
      blueA: '#1865f2',
      blueB: '#2b73e8',
      blueC: '#4185e8',
      blueD: '#5a9ce8',
      blueE: '#72b3e8',
      // Green variants
      greenA: '#28b463',
      greenB: '#2ecc71',
      greenC: '#52d689',
      greenD: '#6dd8a0',
      greenE: '#87dbb3',
      // Red variants
      redA: '#e74c3c',
      redB: '#ec5050',
      redC: '#f06464',
      redD: '#f47878',
      redE: '#f78c8c',
      // Orange variants
      orangeA: '#e67e22',
      orangeB: '#eb8a33',
      orangeC: '#f09644',
      orangeD: '#f5a256',
      orangeE: '#faae67',
      // Gold/yellow variants
      goldA: '#f1c40f',
      goldB: '#f4ca25',
      goldC: '#f7d03b',
      goldD: '#fad651',
      goldE: '#fddc67',
      // Teal variants
      tealA: '#1abc9c',
      tealB: '#2cc4a4',
      tealC: '#3dccac',
      tealD: '#4dd4b4',
      tealE: '#5edcbc',
      // Pink variants
      pinkA: '#e91e63',
      pinkB: '#ec3575',
      pinkC: '#ef4c87',
      pinkD: '#f26399',
      pinkE: '#f57aab',
      // Gray variants
      grayA: '#333333',
      grayB: '#555555',
      grayC: '#777777',
      grayD: '#999999',
      grayE: '#bbbbbb',
      // Khan accent colors
      kaGreen: '#1fab54',
      kaBlue: '#1865f2',
    };

    let result = content;

    // Match \colorName{text} patterns
    const colorPattern = /\\(purple|blue|green|red|orange|gold|teal|pink|gray|kaGreen|kaBlue)([A-E])?\{([^}]+)\}/gi;
    result = result.replace(colorPattern, (match, colorBase, variant, text) => {
      const colorKey = colorBase.toLowerCase() + (variant || 'D');
      const color = colorMap[colorKey] || colorMap[colorBase.toLowerCase() + 'D'] || '#333';
      return `<span style="color: ${color}; font-weight: 600;">${text}</span>`;
    });

    // Also handle \text{} command (just render the text)
    result = result.replace(/\\text\{([^}]+)\}/g, '$1');

    return result;
  }

  /**
   * Process basic markdown syntax
   */
  private processMarkdownSyntax(content: string): string {
    let result = content;

    // Process Khan Academy color commands first
    result = this.processKhanColors(result);

    // Process tables first (before other transformations)
    result = this.processTables(result);

    // Headers
    result = result.replace(/^#{6}\s+(.*)$/gm, '<h6>$1</h6>');
    result = result.replace(/^#{5}\s+(.*)$/gm, '<h5>$1</h5>');
    result = result.replace(/^#{4}\s+(.*)$/gm, '<h4>$1</h4>');
    result = result.replace(/^#{3}\s+(.*)$/gm, '<h3>$1</h3>');
    result = result.replace(/^#{2}\s+(.*)$/gm, '<h2>$1</h2>');
    result = result.replace(/^#{1}\s+(.*)$/gm, '<h1>$1</h1>');

    // Bold and italic
    result = result.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
    result = result.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    result = result.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    result = result.replace(/___([^_]+)___/g, '<strong><em>$1</em></strong>');
    result = result.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    result = result.replace(/_([^_]+)_/g, '<em>$1</em>');

    // Strikethrough
    result = result.replace(/~~([^~]+)~~/g, '<del>$1</del>');

    // Inline code (but not inside code blocks)
    result = result.replace(/`([^`]+)`/g, '<code class="athena-inline-code">$1</code>');

    // Links - use negative lookbehind to NOT match image syntax (![)
    const linkTarget = this.options.linkTarget === '_blank'
      ? ' target="_blank" rel="noopener noreferrer"'
      : '';
    // The (?<!!) ensures we don't match [text](url) when preceded by ! (which is image syntax)
    result = result.replace(/(?<!!)\[([^\]]+)\]\(([^)]+)\)/g, `<a href="$2"${linkTarget}>$1</a>`);

    // Images - handle web+graphie:// URLs, CDN URLs, and relative URLs
    // Use multiple regex patterns to catch all image markdown variations
    const processImageUrl = (alt: string, url: string): string => {
      let imageUrl = url.trim();

      // Remove any trailing incomplete characters
      imageUrl = imageUrl.replace(/[)\s]+$/, '');

      // Convert web+graphie:// URLs to https:// with PNG extension (PNG has labels baked in)
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
      // Convert relative URLs (starting with /) to absolute URLs using baseUrl
      else if (imageUrl.startsWith('/') && this.options.baseUrl) {
        imageUrl = this.options.baseUrl + imageUrl;
      }
      // Handle relative URLs without leading slash
      else if (!imageUrl.startsWith('http') && !imageUrl.startsWith('data:') && this.options.baseUrl) {
        imageUrl = this.options.baseUrl + '/' + imageUrl;
      }

      return `<img src="${imageUrl}" alt="${alt}" class="athena-image" style="max-width:100%;height:auto;" referrerpolicy="no-referrer" onerror="if(this.src.endsWith('.png')){this.src=this.src.replace('.png','.svg')}else if(this.src.endsWith('.svg')){this.src=this.src.replace('.svg','.png')}" />`;
    };

    // Pattern 1: Standard markdown image with closing paren: ![alt](url)
    result = result.replace(/!\[([^\]]*)\]\(([^)\s\n]+)\)/g, (_, alt, url) => {
      return processImageUrl(alt, url);
    });

    // Pattern 2: Multiline URL - URL split across lines (common with long CDN URLs)
    // This joins URLs that span multiple lines before processing
    result = result.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]*)\n([^\s)]+)/g, (_, alt, urlPart1, urlPart2) => {
      // Join the URL parts and process
      const fullUrl = urlPart1 + urlPart2;
      return processImageUrl(alt, fullUrl);
    });

    // Pattern 3: Image markdown without closing paren (truncated): ![alt](url
    // This matches ![...](... to end of string or next whitespace
    result = result.replace(/!\[([^\]]*)\]\(([^\s\n]+)(?:\s|$)/g, (match, alt, url) => {
      return processImageUrl(alt, url) + ' ';
    });

    // Pattern 4: Catch any remaining ![](url patterns at end of line
    result = result.replace(/!\[([^\]]*)\]\(([^\s\n]+)$/gm, (_, alt, url) => {
      return processImageUrl(alt, url);
    });

    // Pattern 5: Catch any remaining raw image markdown that wasn't processed
    // This is a fallback for unusual formats
    result = result.replace(/!\[\]\(([^)\s]+[^)\s\n]*)/g, (_, url) => {
      if (url.includes('cdn.kastatic') || url.includes('ka-perseus') || url.startsWith('http')) {
        return processImageUrl('', url);
      }
      return `![]($1)`; // Return original if not a valid URL
    });

    // Blockquotes
    result = result.replace(/^>\s+(.*)$/gm, '<blockquote>$1</blockquote>');
    // Merge adjacent blockquotes
    result = result.replace(/<\/blockquote>\n<blockquote>/g, '\n');

    // Horizontal rules
    result = result.replace(/^[-*_]{3,}$/gm, '<hr />');

    // Unordered lists
    result = this.processLists(result);

    // Paragraphs
    result = this.processParagraphs(result);

    return result;
  }

  /**
   * Process markdown tables
   */
  private processTables(content: string): string {
    const lines = content.split('\n');
    const result: string[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Check if this line could be a table row (contains |)
      if (line.includes('|')) {
        // Look for table pattern: header row, separator row, data rows
        const tableLines: string[] = [];
        let j = i;

        // Collect consecutive lines that contain |
        while (j < lines.length && lines[j].includes('|')) {
          tableLines.push(lines[j]);
          j++;
        }

        // Check if we have a valid table (at least 2 rows and one is a separator)
        if (tableLines.length >= 2) {
          const hasAlignmentRow = tableLines.some(l => /^[\s|:-]+$/.test(l));

          if (hasAlignmentRow) {
            // Parse and render as table
            const tableHtml = this.renderTable(tableLines);
            result.push(tableHtml);
            i = j;
            continue;
          }
        }
      }

      result.push(line);
      i++;
    }

    return result.join('\n');
  }

  /**
   * Render a markdown table as HTML
   */
  private renderTable(lines: string[]): string {
    // Find alignment row
    let alignmentRowIndex = lines.findIndex(l => /^[\s|:-]+$/.test(l));

    // Parse alignment
    const alignments: Array<'left' | 'center' | 'right'> = [];
    if (alignmentRowIndex >= 0) {
      const alignLine = lines[alignmentRowIndex];
      const alignCells = alignLine.split('|').filter(c => c.trim());
      alignCells.forEach(cell => {
        const trimmed = cell.trim();
        if (trimmed.startsWith(':') && trimmed.endsWith(':')) {
          alignments.push('center');
        } else if (trimmed.endsWith(':')) {
          alignments.push('right');
        } else {
          alignments.push('left');
        }
      });
    }

    // Parse header (rows before alignment row)
    const headerRows = alignmentRowIndex > 0 ? lines.slice(0, alignmentRowIndex) : [];

    // Parse body (rows after alignment row)
    const bodyRows = alignmentRowIndex >= 0 ? lines.slice(alignmentRowIndex + 1) : lines;

    // Build HTML
    let html = '<table class="athena-table">';

    // Render header
    if (headerRows.length > 0) {
      html += '<thead>';
      headerRows.forEach(row => {
        html += '<tr>';
        const cells = this.parseTableRow(row);
        cells.forEach((cell, idx) => {
          const align = alignments[idx] || 'left';
          html += `<th style="text-align:${align}">${cell}</th>`;
        });
        html += '</tr>';
      });
      html += '</thead>';
    }

    // Render body
    if (bodyRows.length > 0) {
      html += '<tbody>';
      bodyRows.forEach(row => {
        if (row.trim()) {
          html += '<tr>';
          const cells = this.parseTableRow(row);
          cells.forEach((cell, idx) => {
            const align = alignments[idx] || 'left';
            html += `<td style="text-align:${align}">${cell}</td>`;
          });
          html += '</tr>';
        }
      });
      html += '</tbody>';
    }

    html += '</table>';
    return html;
  }

  /**
   * Parse a table row into cells
   */
  private parseTableRow(row: string): string[] {
    // Remove leading/trailing pipes and split
    let cleaned = row.trim();
    if (cleaned.startsWith('|')) cleaned = cleaned.slice(1);
    if (cleaned.endsWith('|')) cleaned = cleaned.slice(0, -1);

    return cleaned.split('|').map(cell => cell.trim());
  }

  /**
   * Process markdown lists
   */
  private processLists(content: string): string {
    let result = content;
    const lines = result.split('\n');
    const processedLines: string[] = [];
    let inList = false;
    let listType: 'ul' | 'ol' | null = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const ulMatch = line.match(/^[-*+]\s+(.*)$/);
      const olMatch = line.match(/^\d+\.\s+(.*)$/);

      if (ulMatch) {
        if (!inList || listType !== 'ul') {
          if (inList) {
            processedLines.push(listType === 'ol' ? '</ol>' : '</ul>');
          }
          processedLines.push('<ul>');
          inList = true;
          listType = 'ul';
        }
        processedLines.push(`<li>${ulMatch[1]}</li>`);
      } else if (olMatch) {
        if (!inList || listType !== 'ol') {
          if (inList) {
            processedLines.push(listType === 'ol' ? '</ol>' : '</ul>');
          }
          processedLines.push('<ol>');
          inList = true;
          listType = 'ol';
        }
        processedLines.push(`<li>${olMatch[1]}</li>`);
      } else {
        if (inList) {
          processedLines.push(listType === 'ol' ? '</ol>' : '</ul>');
          inList = false;
          listType = null;
        }
        processedLines.push(line);
      }
    }

    if (inList) {
      processedLines.push(listType === 'ol' ? '</ol>' : '</ul>');
    }

    return processedLines.join('\n');
  }

  /**
   * Process paragraphs
   */
  private processParagraphs(content: string): string {
    const lines = content.split('\n\n');
    return lines
      .map((block) => {
        const trimmed = block.trim();
        if (!trimmed) return '';

        // Don't wrap if already a block element
        if (
          trimmed.startsWith('<h') ||
          trimmed.startsWith('<ul') ||
          trimmed.startsWith('<ol') ||
          trimmed.startsWith('<blockquote') ||
          trimmed.startsWith('<pre') ||
          trimmed.startsWith('<div') ||
          trimmed.startsWith('<hr') ||
          trimmed.startsWith('<table')
        ) {
          return trimmed;
        }

        return `<p>${trimmed}</p>`;
      })
      .filter((block) => block)
      .join('\n');
  }

  /**
   * Sanitize HTML to prevent XSS
   */
  private sanitizeHtml(html: string): string {
    // Remove script tags
    let result = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');

    // Remove event handlers
    result = result.replace(/\s+on\w+\s*=\s*["'][^"']*["']/gi, '');

    // Remove javascript: URLs
    result = result.replace(/href\s*=\s*["']javascript:[^"']*["']/gi, 'href="#"');

    // Remove data: URLs (except for images)
    result = result.replace(/(?<!img[^>]+)src\s*=\s*["']data:[^"']*["']/gi, 'src=""');

    return result;
  }

  /**
   * Escape HTML special characters
   */
  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * Create a simple markdown processor for basic text
   * @param content The markdown content to process
   * @param baseUrl Optional base URL for resolving relative image URLs (e.g., API server URL)
   */
  static simple(content: string, baseUrl?: string): string {
    const processor = new MarkdownProcessor({
      math: false,
      code: false,
      diagrams: false,
      baseUrl,
    });
    return processor.process(content).html;
  }

  /**
   * Create a full-featured markdown processor
   */
  static full(content: string): ProcessedMarkdown {
    const processor = new MarkdownProcessor();
    return processor.process(content);
  }
}

export default MarkdownProcessor;
