/**
 * Content Parser
 *
 * Parses Perseus/Athena content strings to extract:
 * - Widget placeholders [[☃ widget-id]]
 * - Math notation (LaTeX)
 * - Chemical notation
 * - Other special syntax
 */

import type { AthenaWidget, NotationType } from './types';
import { NotationEngineManagerClass } from '../notation/NotationEngineManager';

export interface ParsedSegment {
  type: 'text' | 'widget' | 'math' | 'code' | 'diagram' | 'chemistry' | 'music';
  content: string;
  widgetId?: string;
  raw?: string;
  displayMode?: boolean;
  language?: string;
}

export interface ParseResult {
  segments: ParsedSegment[];
  widgetIds: string[];
  notationTypes: NotationType[];
}

/**
 * Parses content strings into renderable segments
 */
export class ContentParser {
  // Widget placeholder pattern: [[☃ widget-id]]
  private static readonly WIDGET_PATTERN = /\[\[☃\s+([^\]]+)\]\]/g;

  // Display math pattern: $$...$$ or \[...\]
  private static readonly DISPLAY_MATH_PATTERN = /\$\$([^$]+)\$\$|\\\[([^\]]+)\\\]/g;

  // Inline math pattern: $...$ or \(...\)
  private static readonly INLINE_MATH_PATTERN = /\$([^$\n]+)\$|\\\(([^)]+)\\\)/g;

  // Code block pattern: ```language\n...\n```
  private static readonly CODE_BLOCK_PATTERN = /```(\w*)\n?([\s\S]*?)```/g;

  // Mermaid diagram pattern
  private static readonly MERMAID_PATTERN = /```mermaid\n?([\s\S]*?)```/g;

  // Chemistry notation patterns
  private static readonly CHEMISTRY_PATTERNS = [
    /\\ce\{([^}]+)\}/g, // \ce{H2O}
    /\\pu\{([^}]+)\}/g, // \pu{kg.m/s^2}
  ];

  /**
   * Parse content into segments
   */
  static parse(content: string, widgets?: Record<string, AthenaWidget>): ParseResult {
    const segments: ParsedSegment[] = [];
    const widgetIds: string[] = [];
    const notationTypesSet = new Set<NotationType>();

    if (!content) {
      return { segments: [], widgetIds: [], notationTypes: [] };
    }

    // First pass: Extract code blocks and mermaid diagrams (they shouldn't be processed for other patterns)
    const codeBlocks: Array<{ placeholder: string; segment: ParsedSegment }> = [];
    let processedContent = content;

    // Extract mermaid diagrams
    processedContent = processedContent.replace(this.MERMAID_PATTERN, (match, code) => {
      const placeholder = `__MERMAID_${codeBlocks.length}__`;
      codeBlocks.push({
        placeholder,
        segment: {
          type: 'diagram',
          content: code.trim(),
          raw: match,
        },
      });
      notationTypesSet.add('diagram');
      return placeholder;
    });

    // Extract code blocks
    processedContent = processedContent.replace(this.CODE_BLOCK_PATTERN, (match, language, code) => {
      if (language === 'mermaid') {
        // Already handled above
        return match;
      }
      const placeholder = `__CODE_${codeBlocks.length}__`;
      codeBlocks.push({
        placeholder,
        segment: {
          type: 'code',
          content: code.trim(),
          language: language || 'plaintext',
          raw: match,
        },
      });
      notationTypesSet.add('code');
      return placeholder;
    });

    // Second pass: Process remaining content
    let lastIndex = 0;
    const allMatches: Array<{
      index: number;
      length: number;
      segment: ParsedSegment;
    }> = [];

    // Find widget placeholders
    let widgetMatch;
    const widgetPattern = new RegExp(this.WIDGET_PATTERN.source, 'g');
    while ((widgetMatch = widgetPattern.exec(processedContent)) !== null) {
      const widgetId = widgetMatch[1].trim();
      widgetIds.push(widgetId);
      allMatches.push({
        index: widgetMatch.index,
        length: widgetMatch[0].length,
        segment: {
          type: 'widget',
          content: '',
          widgetId,
          raw: widgetMatch[0],
        },
      });
    }

    // Find display math
    let displayMatch;
    const displayPattern = new RegExp(this.DISPLAY_MATH_PATTERN.source, 'g');
    while ((displayMatch = displayPattern.exec(processedContent)) !== null) {
      const mathContent = displayMatch[1] || displayMatch[2];
      // Check if this is chemistry notation
      const isChemistry = this.isChemistryNotation(mathContent);
      allMatches.push({
        index: displayMatch.index,
        length: displayMatch[0].length,
        segment: {
          type: isChemistry ? 'chemistry' : 'math',
          content: mathContent.trim(),
          displayMode: true,
          raw: displayMatch[0],
        },
      });
      notationTypesSet.add(isChemistry ? 'chemistry' : 'math');
    }

    // Find inline math
    let inlineMatch;
    const inlinePattern = new RegExp(this.INLINE_MATH_PATTERN.source, 'g');
    while ((inlineMatch = inlinePattern.exec(processedContent)) !== null) {
      // Skip if this overlaps with a display math match
      const overlaps = allMatches.some(
        (m) =>
          inlineMatch!.index >= m.index &&
          inlineMatch!.index < m.index + m.length
      );
      if (overlaps) continue;

      const mathContent = inlineMatch[1] || inlineMatch[2];
      const isChemistry = this.isChemistryNotation(mathContent);
      allMatches.push({
        index: inlineMatch.index,
        length: inlineMatch[0].length,
        segment: {
          type: isChemistry ? 'chemistry' : 'math',
          content: mathContent.trim(),
          displayMode: false,
          raw: inlineMatch[0],
        },
      });
      notationTypesSet.add(isChemistry ? 'chemistry' : 'math');
    }

    // Sort matches by index
    allMatches.sort((a, b) => a.index - b.index);

    // Build segments array
    for (const match of allMatches) {
      // Add text before this match
      if (match.index > lastIndex) {
        const textContent = processedContent.slice(lastIndex, match.index);
        if (textContent.trim()) {
          segments.push({
            type: 'text',
            content: textContent,
          });
        }
      }

      // Add the matched segment
      segments.push(match.segment);
      lastIndex = match.index + match.length;
    }

    // Add remaining text
    if (lastIndex < processedContent.length) {
      const textContent = processedContent.slice(lastIndex);
      if (textContent.trim()) {
        segments.push({
          type: 'text',
          content: textContent,
        });
      }
    }

    // Replace code block placeholders back
    for (const block of codeBlocks) {
      const placeholderIndex = segments.findIndex(
        (s) => s.type === 'text' && s.content.includes(block.placeholder)
      );
      if (placeholderIndex !== -1) {
        const textSegment = segments[placeholderIndex];
        const parts = textSegment.content.split(block.placeholder);

        const newSegments: ParsedSegment[] = [];
        if (parts[0].trim()) {
          newSegments.push({ type: 'text', content: parts[0] });
        }
        newSegments.push(block.segment);
        if (parts[1]?.trim()) {
          newSegments.push({ type: 'text', content: parts[1] });
        }

        segments.splice(placeholderIndex, 1, ...newSegments);
      }
    }

    return {
      segments,
      widgetIds,
      notationTypes: Array.from(notationTypesSet),
    };
  }

  /**
   * Check if content contains chemistry notation
   */
  private static isChemistryNotation(content: string): boolean {
    return (
      content.includes('\\ce{') ||
      content.includes('\\pu{') ||
      // Check for chemical formulas without \ce
      /[A-Z][a-z]?\d*(?:[+-]\d*)?/.test(content) && /[→⇌↔]/.test(content)
    );
  }

  /**
   * Detect all notation types in content
   */
  static detectNotationTypes(content: string): NotationType[] {
    return NotationEngineManagerClass.detectNotationTypes(content);
  }

  /**
   * Extract widget IDs from content
   */
  static extractWidgetIds(content: string): string[] {
    const ids: string[] = [];
    let match;
    const pattern = new RegExp(this.WIDGET_PATTERN.source, 'g');
    while ((match = pattern.exec(content)) !== null) {
      ids.push(match[1].trim());
    }
    return ids;
  }

  /**
   * Replace widget placeholders with custom content
   */
  static replaceWidgetPlaceholders(
    content: string,
    replacer: (widgetId: string) => string
  ): string {
    return content.replace(this.WIDGET_PATTERN, (match, widgetId) => {
      return replacer(widgetId.trim());
    });
  }

  /**
   * Check if content has any widgets
   */
  static hasWidgets(content: string): boolean {
    return this.WIDGET_PATTERN.test(content);
  }

  /**
   * Check if content has math notation
   */
  static hasMath(content: string): boolean {
    return (
      this.DISPLAY_MATH_PATTERN.test(content) ||
      this.INLINE_MATH_PATTERN.test(content)
    );
  }

  /**
   * Check if content has code blocks
   */
  static hasCode(content: string): boolean {
    return this.CODE_BLOCK_PATTERN.test(content);
  }

  /**
   * Check if content has diagrams
   */
  static hasDiagrams(content: string): boolean {
    return this.MERMAID_PATTERN.test(content);
  }

  /**
   * Count widgets in content
   */
  static countWidgets(content: string): number {
    return this.extractWidgetIds(content).length;
  }

  /**
   * Validate that all widget references exist
   */
  static validateWidgetReferences(
    content: string,
    widgets: Record<string, unknown>
  ): { valid: boolean; missing: string[]; unused: string[] } {
    const referenced = this.extractWidgetIds(content);
    const defined = Object.keys(widgets);

    const missing = referenced.filter((id) => !defined.includes(id));
    const unused = defined.filter((id) => !referenced.includes(id));

    return {
      valid: missing.length === 0,
      missing,
      unused,
    };
  }

  /**
   * Convert content to plain text (strip all special syntax)
   */
  static toPlainText(content: string): string {
    let result = content;

    // Remove widget placeholders
    result = result.replace(this.WIDGET_PATTERN, '[widget]');

    // Remove math delimiters but keep content
    result = result.replace(this.DISPLAY_MATH_PATTERN, (match, content1, content2) => {
      return content1 || content2 || '';
    });
    result = result.replace(this.INLINE_MATH_PATTERN, (match, content1, content2) => {
      return content1 || content2 || '';
    });

    // Remove code blocks
    result = result.replace(this.CODE_BLOCK_PATTERN, '[code]');

    // Remove mermaid diagrams
    result = result.replace(this.MERMAID_PATTERN, '[diagram]');

    return result.trim();
  }

  /**
   * Estimate reading time for content
   */
  static estimateReadingTime(content: string): number {
    const plainText = this.toPlainText(content);
    const wordCount = plainText.split(/\s+/).filter((w) => w.length > 0).length;
    const wordsPerMinute = 200;
    return Math.ceil(wordCount / wordsPerMinute);
  }
}

export default ContentParser;
