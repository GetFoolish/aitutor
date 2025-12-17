/**
 * Math Engine - KaTeX Wrapper
 *
 * Provides fast, high-quality math rendering using KaTeX.
 * Significantly faster than MathJax with a smaller bundle size.
 */

import type { NotationEngine, NotationRenderOptions } from '../../core/types';

interface KaTeXOptions {
  displayMode?: boolean;
  output?: 'html' | 'mathml' | 'htmlAndMathml';
  leqno?: boolean;
  fleqn?: boolean;
  throwOnError?: boolean;
  errorColor?: string;
  macros?: Record<string, string>;
  minRuleThickness?: number;
  colorIsTextColor?: boolean;
  maxSize?: number;
  maxExpand?: number;
  strict?: boolean | string | ((errorCode: string, errorMsg: string) => string);
  trust?: boolean | ((context: { command: string; url: string; protocol: string }) => boolean);
  globalGroup?: boolean;
}

interface KaTeX {
  render(expression: string, element: HTMLElement, options?: KaTeXOptions): void;
  renderToString(expression: string, options?: KaTeXOptions): string;
  ParseError: new (message: string) => Error;
}

interface MathEngineOptions {
  macros?: Record<string, string>;
  strict?: boolean;
  throwOnError?: boolean;
}

export class MathEngine implements NotationEngine {
  type = 'math' as const;
  private katex: KaTeX | null = null;
  private loaded = false;
  private defaultOptions: KaTeXOptions;

  constructor(options: MathEngineOptions = {}) {
    this.defaultOptions = {
      throwOnError: options.throwOnError ?? false,
      errorColor: '#cc0000',
      strict: options.strict ?? 'warn',
      trust: false,
      output: 'htmlAndMathml',
      macros: {
        // Common math macros
        '\\R': '\\mathbb{R}',
        '\\N': '\\mathbb{N}',
        '\\Z': '\\mathbb{Z}',
        '\\Q': '\\mathbb{Q}',
        '\\C': '\\mathbb{C}',
        '\\vec': '\\mathbf{#1}',
        '\\norm': '\\left\\|#1\\right\\|',
        '\\abs': '\\left|#1\\right|',
        '\\floor': '\\left\\lfloor#1\\right\\rfloor',
        '\\ceil': '\\left\\lceil#1\\right\\rceil',
        '\\set': '\\left\\{#1\\right\\}',
        '\\ang': '\\left\\langle#1\\right\\rangle',
        // Override with custom macros
        ...(options.macros || {}),
      },
    };
  }

  /**
   * Check if KaTeX is loaded
   */
  isLoaded(): boolean {
    return this.loaded && this.katex !== null;
  }

  /**
   * Preload KaTeX library
   */
  async preload(): Promise<void> {
    if (this.loaded) return;

    try {
      // Dynamic import of KaTeX
      // @ts-ignore - KaTeX types not installed
      const katexModule = await import('katex');
      this.katex = katexModule.default || katexModule;

      // Load KaTeX CSS
      if (typeof document !== 'undefined') {
        const existingLink = document.querySelector('link[href*="katex"]');
        if (!existingLink) {
          const link = document.createElement('link');
          link.rel = 'stylesheet';
          link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';
          link.crossOrigin = 'anonymous';
          document.head.appendChild(link);
        }
      }

      this.loaded = true;
    } catch (error) {
      console.error('Failed to load KaTeX:', error);
      throw new Error(`Failed to load math engine: ${error}`);
    }
  }

  /**
   * Render math expression to a DOM element
   */
  async render(
    content: string,
    container: HTMLElement,
    options?: NotationRenderOptions
  ): Promise<void> {
    await this.preload();

    if (!this.katex) {
      throw new Error('KaTeX not loaded');
    }

    const expression = this.preprocessContent(content);
    const displayMode = options?.displayMode ?? this.isDisplayMode(content);

    try {
      this.katex.render(expression, container, {
        ...this.defaultOptions,
        displayMode,
      });
      container.classList.add('athena-math', displayMode ? 'athena-math-display' : 'athena-math-inline');
    } catch (error) {
      // Render error message instead of throwing
      container.innerHTML = `<span class="athena-math-error" style="color: ${this.defaultOptions.errorColor}">${this.escapeHtml(content)}</span>`;
      console.warn('KaTeX render error:', error);
    }
  }

  /**
   * Render math expression to HTML string
   */
  async renderToString(content: string, options?: NotationRenderOptions): Promise<string> {
    await this.preload();

    if (!this.katex) {
      throw new Error('KaTeX not loaded');
    }

    const expression = this.preprocessContent(content);
    const displayMode = options?.displayMode ?? this.isDisplayMode(content);

    try {
      return this.katex.renderToString(expression, {
        ...this.defaultOptions,
        displayMode,
      });
    } catch (error) {
      console.warn('KaTeX render error:', error);
      return `<span class="athena-math-error" style="color: ${this.defaultOptions.errorColor}">${this.escapeHtml(content)}</span>`;
    }
  }

  /**
   * Preprocess content to handle common formats
   */
  private preprocessContent(content: string): string {
    let processed = content.trim();

    // Remove delimiters if present
    if (processed.startsWith('$$') && processed.endsWith('$$')) {
      processed = processed.slice(2, -2).trim();
    } else if (processed.startsWith('$') && processed.endsWith('$')) {
      processed = processed.slice(1, -1).trim();
    } else if (processed.startsWith('\\[') && processed.endsWith('\\]')) {
      processed = processed.slice(2, -2).trim();
    } else if (processed.startsWith('\\(') && processed.endsWith('\\)')) {
      processed = processed.slice(2, -2).trim();
    }

    // Convert some common patterns that might cause issues
    // Handle \begin{align}...\end{align} -> aligned environment
    processed = processed.replace(
      /\\begin\{align\}([\s\S]*?)\\end\{align\}/g,
      '\\begin{aligned}$1\\end{aligned}'
    );

    // Handle \begin{equation}...\end{equation}
    processed = processed.replace(
      /\\begin\{equation\}([\s\S]*?)\\end\{equation\}/g,
      '$1'
    );

    return processed;
  }

  /**
   * Detect if content should be rendered in display mode
   */
  private isDisplayMode(content: string): boolean {
    const trimmed = content.trim();
    return (
      trimmed.startsWith('$$') ||
      trimmed.startsWith('\\[') ||
      trimmed.includes('\\begin{') ||
      trimmed.includes('\\\\') // Multiline
    );
  }

  /**
   * Escape HTML special characters
   */
  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

export default MathEngine;
