/**
 * Code Engine - Prism.js Wrapper
 *
 * Provides syntax highlighting for code blocks using Prism.js.
 * Supports 40+ programming languages with lazy loading.
 */

import type { NotationEngine, NotationRenderOptions } from '../../core/types';

interface Prism {
  highlight(code: string, grammar: unknown, language: string): string;
  languages: Record<string, unknown>;
  highlightElement(element: HTMLElement): void;
}

// Map of language aliases to Prism language names
const LANGUAGE_ALIASES: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  rb: 'ruby',
  sh: 'bash',
  shell: 'bash',
  yml: 'yaml',
  md: 'markdown',
  html: 'markup',
  xml: 'markup',
  svg: 'markup',
  'c++': 'cpp',
  'c#': 'csharp',
  cs: 'csharp',
  kt: 'kotlin',
  rs: 'rust',
  ps1: 'powershell',
  dockerfile: 'docker',
  tf: 'hcl',
};

// Languages that are included in Prism core
const CORE_LANGUAGES = ['markup', 'css', 'clike', 'javascript'];

export class CodeEngine implements NotationEngine {
  type = 'code' as const;
  private prism: Prism | null = null;
  private loaded = false;
  private loadedLanguages: Set<string> = new Set(CORE_LANGUAGES);
  private loadingLanguages: Map<string, Promise<void>> = new Map();

  /**
   * Check if engine is loaded
   */
  isLoaded(): boolean {
    return this.loaded && this.prism !== null;
  }

  /**
   * Preload Prism.js
   */
  async preload(): Promise<void> {
    if (this.loaded) return;

    try {
      // Dynamic import of Prism
      const prismModule = await import('prismjs');
      this.prism = prismModule.default || prismModule;

      // Load Prism CSS theme
      if (typeof document !== 'undefined') {
        const existingLink = document.querySelector('link[href*="prism"]');
        if (!existingLink) {
          const link = document.createElement('link');
          link.rel = 'stylesheet';
          // Using a neutral theme that works with light/dark modes
          link.href = 'https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css';
          document.head.appendChild(link);
        }
      }

      this.loaded = true;
    } catch (error) {
      console.error('Failed to load Prism:', error);
      throw new Error(`Failed to load code engine: ${error}`);
    }
  }

  /**
   * Load a specific language grammar
   */
  async loadLanguage(language: string): Promise<void> {
    const normalizedLang = this.normalizeLanguage(language);

    // Already loaded
    if (this.loadedLanguages.has(normalizedLang)) {
      return;
    }

    // Already loading
    if (this.loadingLanguages.has(normalizedLang)) {
      return this.loadingLanguages.get(normalizedLang);
    }

    // Start loading
    const loadPromise = this.doLoadLanguage(normalizedLang);
    this.loadingLanguages.set(normalizedLang, loadPromise);

    try {
      await loadPromise;
      this.loadedLanguages.add(normalizedLang);
    } finally {
      this.loadingLanguages.delete(normalizedLang);
    }
  }

  /**
   * Render code with syntax highlighting to a DOM element
   */
  async render(
    content: string,
    container: HTMLElement,
    options?: NotationRenderOptions & { language?: string; showLineNumbers?: boolean }
  ): Promise<void> {
    await this.preload();

    const language = options?.language || this.detectLanguage(content) || 'plaintext';
    await this.loadLanguage(language);

    const normalizedLang = this.normalizeLanguage(language);
    const highlighted = this.highlightCode(content, normalizedLang);

    // Build the HTML structure
    const wrapper = document.createElement('div');
    wrapper.className = 'athena-code-block';

    // Add language header if specified
    const header = document.createElement('div');
    header.className = 'athena-code-header';
    header.innerHTML = `<span class="athena-code-language">${this.getLanguageDisplayName(normalizedLang)}</span>`;
    wrapper.appendChild(header);

    // Add the code block
    const pre = document.createElement('pre');
    pre.className = `language-${normalizedLang}`;
    if (options?.showLineNumbers) {
      pre.classList.add('line-numbers');
    }

    const code = document.createElement('code');
    code.className = `language-${normalizedLang}`;
    code.innerHTML = highlighted;

    pre.appendChild(code);
    wrapper.appendChild(pre);

    // Clear container and add our content
    container.innerHTML = '';
    container.appendChild(wrapper);
  }

  /**
   * Render code to HTML string
   */
  async renderToString(
    content: string,
    options?: NotationRenderOptions & { language?: string; showLineNumbers?: boolean }
  ): Promise<string> {
    await this.preload();

    const language = options?.language || this.detectLanguage(content) || 'plaintext';
    await this.loadLanguage(language);

    const normalizedLang = this.normalizeLanguage(language);
    const highlighted = this.highlightCode(content, normalizedLang);

    const lineNumbersClass = options?.showLineNumbers ? ' line-numbers' : '';

    return `
      <div class="athena-code-block">
        <div class="athena-code-header">
          <span class="athena-code-language">${this.getLanguageDisplayName(normalizedLang)}</span>
        </div>
        <pre class="language-${normalizedLang}${lineNumbersClass}">
          <code class="language-${normalizedLang}">${highlighted}</code>
        </pre>
      </div>
    `.trim();
  }

  /**
   * Highlight code using Prism
   */
  private highlightCode(code: string, language: string): string {
    if (!this.prism) {
      return this.escapeHtml(code);
    }

    const grammar = this.prism.languages[language];
    if (!grammar) {
      // Fallback to plain text
      return this.escapeHtml(code);
    }

    try {
      return this.prism.highlight(code, grammar, language);
    } catch (error) {
      console.warn(`Failed to highlight ${language}:`, error);
      return this.escapeHtml(code);
    }
  }

  /**
   * Normalize language name using aliases
   */
  private normalizeLanguage(language: string): string {
    const lower = language.toLowerCase();
    return LANGUAGE_ALIASES[lower] || lower;
  }

  /**
   * Get display name for a language
   */
  private getLanguageDisplayName(language: string): string {
    const displayNames: Record<string, string> = {
      javascript: 'JavaScript',
      typescript: 'TypeScript',
      python: 'Python',
      ruby: 'Ruby',
      java: 'Java',
      cpp: 'C++',
      csharp: 'C#',
      go: 'Go',
      rust: 'Rust',
      swift: 'Swift',
      kotlin: 'Kotlin',
      php: 'PHP',
      bash: 'Bash',
      sql: 'SQL',
      json: 'JSON',
      yaml: 'YAML',
      markdown: 'Markdown',
      markup: 'HTML',
      css: 'CSS',
      scss: 'SCSS',
      jsx: 'JSX',
      tsx: 'TSX',
      plaintext: 'Plain Text',
    };
    return displayNames[language] || language.charAt(0).toUpperCase() + language.slice(1);
  }

  /**
   * Detect language from code content
   */
  private detectLanguage(code: string): string | null {
    const firstLine = code.split('\n')[0].trim();

    // Check for shebang
    if (firstLine.startsWith('#!')) {
      if (firstLine.includes('python')) return 'python';
      if (firstLine.includes('node')) return 'javascript';
      if (firstLine.includes('ruby')) return 'ruby';
      if (firstLine.includes('bash') || firstLine.includes('sh')) return 'bash';
    }

    // Check for common patterns
    if (/^import .+ from ['"]/.test(code)) return 'javascript';
    if (/^from .+ import/.test(code)) return 'python';
    if (/^package\s+\w+/.test(code)) return 'java';
    if (/^#include\s*</.test(code)) return 'cpp';
    if (/^fn\s+\w+\s*\(/.test(code)) return 'rust';
    if (/^func\s+\w+\s*\(/.test(code)) return 'go';

    return null;
  }

  /**
   * Load a language grammar dynamically
   */
  private async doLoadLanguage(language: string): Promise<void> {
    if (CORE_LANGUAGES.includes(language)) {
      return; // Core languages are already loaded
    }

    try {
      // Dynamic import of language grammar
      await import(`prismjs/components/prism-${language}`);
    } catch (error) {
      console.warn(`Failed to load Prism language ${language}:`, error);
      // Don't throw - we'll fall back to plain text
    }
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
}

export default CodeEngine;
