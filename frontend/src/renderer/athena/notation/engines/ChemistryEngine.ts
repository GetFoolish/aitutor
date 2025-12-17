/**
 * Chemistry Engine - KaTeX + mhchem
 *
 * Renders chemical formulas and equations using KaTeX with the mhchem extension.
 * Supports \ce{} for chemical formulas and \pu{} for physical units.
 */

import type { NotationEngine, NotationRenderOptions } from '../../core/types';

interface KaTeXOptions {
  displayMode?: boolean;
  throwOnError?: boolean;
  errorColor?: string;
  macros?: Record<string, string>;
  trust?: boolean;
}

interface KaTeX {
  render(expression: string, element: HTMLElement, options?: KaTeXOptions): void;
  renderToString(expression: string, options?: KaTeXOptions): string;
}

export class ChemistryEngine implements NotationEngine {
  type = 'chemistry' as const;
  private katex: KaTeX | null = null;
  private mhchemLoaded = false;
  private loaded = false;

  private defaultOptions: KaTeXOptions = {
    throwOnError: false,
    errorColor: '#cc0000',
    trust: true, // Required for mhchem
  };

  /**
   * Check if engine is loaded
   */
  isLoaded(): boolean {
    return this.loaded && this.katex !== null && this.mhchemLoaded;
  }

  /**
   * Preload KaTeX and mhchem extension
   */
  async preload(): Promise<void> {
    if (this.loaded) return;

    try {
      // Load KaTeX first
      // @ts-ignore - KaTeX types not installed
      const katexModule = await import('katex');
      this.katex = katexModule.default || katexModule;

      // Load mhchem extension
      try {
        // @ts-ignore - mhchem types not installed
        await import('katex/contrib/mhchem');
        this.mhchemLoaded = true;
      } catch (mhchemError) {
        console.warn('mhchem extension not available, using fallback:', mhchemError);
        // Continue without mhchem - we'll handle it in preprocessing
      }

      // Load KaTeX CSS if not already loaded
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
      console.error('Failed to load Chemistry engine:', error);
      throw new Error(`Failed to load chemistry engine: ${error}`);
    }
  }

  /**
   * Render chemical formula to a DOM element
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
    const displayMode = options?.displayMode ?? true;

    try {
      this.katex.render(expression, container, {
        ...this.defaultOptions,
        displayMode,
      });
      container.classList.add('athena-chemistry', 'athena-math');
    } catch (error) {
      // Render error message instead of throwing
      container.innerHTML = `<span class="athena-chemistry-error" style="color: ${this.defaultOptions.errorColor}">${this.escapeHtml(content)}</span>`;
      console.warn('Chemistry render error:', error);
    }
  }

  /**
   * Render chemical formula to HTML string
   */
  async renderToString(content: string, options?: NotationRenderOptions): Promise<string> {
    await this.preload();

    if (!this.katex) {
      throw new Error('KaTeX not loaded');
    }

    const expression = this.preprocessContent(content);
    const displayMode = options?.displayMode ?? true;

    try {
      return this.katex.renderToString(expression, {
        ...this.defaultOptions,
        displayMode,
      });
    } catch (error) {
      console.warn('Chemistry render error:', error);
      return `<span class="athena-chemistry-error" style="color: ${this.defaultOptions.errorColor}">${this.escapeHtml(content)}</span>`;
    }
  }

  /**
   * Preprocess content to ensure proper mhchem format
   */
  private preprocessContent(content: string): string {
    let processed = content.trim();

    // If mhchem is loaded and content doesn't already use \ce{} or \pu{}
    if (this.mhchemLoaded) {
      // Wrap bare chemical formulas in \ce{}
      if (!processed.includes('\\ce{') && !processed.includes('\\pu{')) {
        // Check if it looks like a chemical formula
        if (this.looksLikeChemicalFormula(processed)) {
          processed = `\\ce{${processed}}`;
        }
      }
    } else {
      // Fallback: convert chemical notation to basic LaTeX
      processed = this.convertToBasicLatex(processed);
    }

    return processed;
  }

  /**
   * Check if content looks like a chemical formula
   */
  private looksLikeChemicalFormula(content: string): boolean {
    // Common patterns for chemical formulas
    const chemicalPatterns = [
      /^[A-Z][a-z]?\d*(\s*[+\-]\s*[A-Z][a-z]?\d*)*$/, // Simple formulas: H2O, NaCl
      /->|<->|<=>/, // Reaction arrows
      /\^\{?\d*[+\-]\}?/, // Ionic charges: Ca^{2+}
      /_\{?\d+\}?/, // Subscripts: H_2O
      /\([A-Z][a-z]?\d*\)\d*/, // Groups: (OH)2
    ];

    return chemicalPatterns.some((pattern) => pattern.test(content));
  }

  /**
   * Convert chemical notation to basic LaTeX when mhchem is not available
   */
  private convertToBasicLatex(content: string): string {
    let latex = content;

    // Remove \ce{} wrapper if present (we'll convert manually)
    latex = latex.replace(/\\ce\{([^}]+)\}/g, '$1');
    latex = latex.replace(/\\pu\{([^}]+)\}/g, '\\text{$1}');

    // Convert element symbols (uppercase followed by optional lowercase)
    // H2O -> H_{2}O
    latex = latex.replace(/([A-Z][a-z]?)(\d+)/g, '$1_{$2}');

    // Convert charges: 2+ -> ^{2+}, + -> ^{+}
    latex = latex.replace(/\^(\d*[+\-])/g, '^{$1}');
    latex = latex.replace(/([A-Z][a-z]?)([+\-])(?!\})/g, '$1^{$2}');

    // Convert reaction arrows
    latex = latex.replace(/->/g, '\\rightarrow');
    latex = latex.replace(/<->/g, '\\leftrightarrow');
    latex = latex.replace(/<=>/g, '\\rightleftharpoons');

    // Wrap in text mode for proper formatting
    return latex;
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

export default ChemistryEngine;
