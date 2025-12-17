/**
 * Diagram Engine - Mermaid.js Wrapper
 *
 * Renders flowcharts, sequence diagrams, Gantt charts, and more using Mermaid.
 * Great for historical timelines, process flows, and relationship diagrams.
 */

import type { NotationEngine, NotationRenderOptions } from '../../core/types';

interface MermaidConfig {
  startOnLoad?: boolean;
  theme?: 'default' | 'neutral' | 'dark' | 'forest' | 'base';
  securityLevel?: 'strict' | 'loose' | 'antiscript' | 'sandbox';
  fontFamily?: string;
  logLevel?: 'debug' | 'info' | 'warn' | 'error' | 'fatal';
}

interface Mermaid {
  initialize(config: MermaidConfig): void;
  render(id: string, definition: string): Promise<{ svg: string; bindFunctions?: (element: Element) => void }>;
  parse(definition: string): Promise<boolean>;
}

export class DiagramEngine implements NotationEngine {
  type = 'diagram' as const;
  private mermaid: Mermaid | null = null;
  private loaded = false;
  private initialized = false;
  private renderCounter = 0;

  /**
   * Check if engine is loaded
   */
  isLoaded(): boolean {
    return this.loaded && this.initialized;
  }

  /**
   * Preload Mermaid.js
   */
  async preload(): Promise<void> {
    if (this.loaded) return;

    try {
      // @ts-ignore - Mermaid types may not match
      const mermaidModule = await import('mermaid');
      this.mermaid = (mermaidModule.default || mermaidModule) as unknown as Mermaid;

      // Initialize Mermaid with our configuration
      this.mermaid!.initialize({
        startOnLoad: false, // We handle rendering manually
        theme: 'neutral',
        securityLevel: 'strict',
        fontFamily: 'inherit',
        logLevel: 'error',
      });

      this.initialized = true;
      this.loaded = true;
    } catch (error) {
      console.error('Failed to load Mermaid:', error);
      throw new Error(`Failed to load diagram engine: ${error}`);
    }
  }

  /**
   * Update theme based on current mode
   */
  setTheme(theme: 'light' | 'dark' | 'high-contrast'): void {
    if (!this.mermaid) return;

    const mermaidTheme = theme === 'dark' ? 'dark' : theme === 'high-contrast' ? 'dark' : 'neutral';

    this.mermaid.initialize({
      startOnLoad: false,
      theme: mermaidTheme,
      securityLevel: 'strict',
      fontFamily: 'inherit',
    });
  }

  /**
   * Render diagram to a DOM element
   */
  async render(
    content: string,
    container: HTMLElement,
    options?: NotationRenderOptions
  ): Promise<void> {
    await this.preload();

    if (!this.mermaid) {
      throw new Error('Mermaid not loaded');
    }

    // Update theme if specified
    if (options?.theme) {
      this.setTheme(options.theme);
    }

    const definition = this.preprocessContent(content);
    const id = `athena-mermaid-${++this.renderCounter}-${Date.now()}`;

    try {
      // Validate the diagram first
      const isValid = await this.mermaid.parse(definition);
      if (!isValid) {
        throw new Error('Invalid Mermaid diagram syntax');
      }

      // Render the diagram
      const { svg, bindFunctions } = await this.mermaid.render(id, definition);

      // Set the SVG content
      container.innerHTML = svg;
      container.classList.add('athena-diagram', 'athena-mermaid');

      // Bind any interactive functions
      if (bindFunctions) {
        bindFunctions(container);
      }
    } catch (error) {
      // Render error state
      container.innerHTML = `
        <div class="athena-diagram-error">
          <strong>Diagram Error</strong>
          <pre>${this.escapeHtml(definition)}</pre>
          <p>${this.escapeHtml(String(error))}</p>
        </div>
      `;
      console.warn('Mermaid render error:', error);
    }
  }

  /**
   * Render diagram to SVG string
   */
  async renderToString(content: string, options?: NotationRenderOptions): Promise<string> {
    await this.preload();

    if (!this.mermaid) {
      throw new Error('Mermaid not loaded');
    }

    if (options?.theme) {
      this.setTheme(options.theme);
    }

    const definition = this.preprocessContent(content);
    const id = `athena-mermaid-${++this.renderCounter}-${Date.now()}`;

    try {
      const { svg } = await this.mermaid.render(id, definition);
      return `<div class="athena-diagram athena-mermaid">${svg}</div>`;
    } catch (error) {
      console.warn('Mermaid render error:', error);
      return `
        <div class="athena-diagram-error">
          <strong>Diagram Error</strong>
          <pre>${this.escapeHtml(definition)}</pre>
        </div>
      `;
    }
  }

  /**
   * Preprocess content to clean up common issues
   */
  private preprocessContent(content: string): string {
    let processed = content.trim();

    // Remove markdown code fence if present
    if (processed.startsWith('```mermaid')) {
      processed = processed.slice(10);
    }
    if (processed.startsWith('```')) {
      processed = processed.slice(3);
    }
    if (processed.endsWith('```')) {
      processed = processed.slice(0, -3);
    }

    return processed.trim();
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
   * Static helper to detect if content is a Mermaid diagram
   */
  static isMermaidDiagram(content: string): boolean {
    const trimmed = content.trim();
    const diagramTypes = [
      'graph',
      'flowchart',
      'sequenceDiagram',
      'classDiagram',
      'stateDiagram',
      'erDiagram',
      'gantt',
      'pie',
      'journey',
      'gitGraph',
      'mindmap',
      'timeline',
      'quadrantChart',
      'requirementDiagram',
      'C4Context',
    ];

    return diagramTypes.some(
      (type) => trimmed.startsWith(type) || trimmed.startsWith(`${type} `)
    );
  }
}

export default DiagramEngine;
