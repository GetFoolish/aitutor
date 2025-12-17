/**
 * Notation Engine Manager
 *
 * Orchestrates lazy-loading and caching of notation rendering engines.
 * Supports math (KaTeX), chemistry (mhchem), music (VexFlow),
 * diagrams (Mermaid), and code (Prism.js).
 */

import type { NotationType, NotationEngine, NotationRenderOptions } from '../core/types';

type EngineStatus = 'idle' | 'loading' | 'loaded' | 'error';

interface EngineState {
  status: EngineStatus;
  engine: NotationEngine | null;
  error: Error | null;
  loadPromise: Promise<NotationEngine> | null;
}

/**
 * Manages lazy-loading and caching of notation engines.
 * Uses singleton pattern for global engine management.
 */
class NotationEngineManagerClass {
  private engines: Map<NotationType, EngineState> = new Map();
  private listeners: Set<(type: NotationType, status: EngineStatus) => void> = new Set();

  constructor() {
    // Initialize all engine states as idle
    const engineTypes: NotationType[] = [
      'math',
      'chemistry',
      'music',
      'diagram',
      'code',
      'physics',
      'economics',
      'geography',
    ];

    engineTypes.forEach((type) => {
      this.engines.set(type, {
        status: 'idle',
        engine: null,
        error: null,
        loadPromise: null,
      });
    });
  }

  /**
   * Get the current status of an engine
   */
  getStatus(type: NotationType): EngineStatus {
    return this.engines.get(type)?.status || 'idle';
  }

  /**
   * Check if an engine is loaded and ready
   */
  isLoaded(type: NotationType): boolean {
    return this.getStatus(type) === 'loaded';
  }

  /**
   * Check if an engine is currently loading
   */
  isLoading(type: NotationType): boolean {
    return this.getStatus(type) === 'loading';
  }

  /**
   * Get a loaded engine (throws if not loaded)
   */
  getEngine(type: NotationType): NotationEngine {
    const state = this.engines.get(type);
    if (!state?.engine) {
      throw new Error(`Engine ${type} is not loaded. Call loadEngine first.`);
    }
    return state.engine;
  }

  /**
   * Load an engine lazily. Returns cached engine if already loaded.
   */
  async loadEngine(type: NotationType): Promise<NotationEngine> {
    const state = this.engines.get(type);
    if (!state) {
      throw new Error(`Unknown engine type: ${type}`);
    }

    // Return cached engine if loaded
    if (state.status === 'loaded' && state.engine) {
      return state.engine;
    }

    // Return existing promise if loading
    if (state.status === 'loading' && state.loadPromise) {
      return state.loadPromise;
    }

    // Start loading
    this.updateEngineState(type, { status: 'loading', loadPromise: null, error: null });

    const loadPromise = this.doLoadEngine(type);
    this.updateEngineState(type, { loadPromise });

    try {
      const engine = await loadPromise;
      this.updateEngineState(type, {
        status: 'loaded',
        engine,
        loadPromise: null,
      });
      return engine;
    } catch (error) {
      this.updateEngineState(type, {
        status: 'error',
        error: error instanceof Error ? error : new Error(String(error)),
        loadPromise: null,
      });
      throw error;
    }
  }

  /**
   * Preload multiple engines without waiting
   */
  preloadEngines(types: NotationType[]): void {
    types.forEach((type) => {
      if (!this.isLoaded(type) && !this.isLoading(type)) {
        this.loadEngine(type).catch(() => {
          // Silently fail preload - will retry on actual use
        });
      }
    });
  }

  /**
   * Detect which notation types are present in content
   */
  static detectNotationTypes(content: string): NotationType[] {
    const types: NotationType[] = [];

    // Math detection: $...$, $$...$$, \[...\], \(...\), or common LaTeX commands
    if (/\$[^$]+\$|\\\[|\\\(|\\frac|\\sqrt|\\int|\\sum|\\lim|\\prod/.test(content)) {
      types.push('math');
    }

    // Chemistry detection: \ce{...}, \pu{...}, or common chemistry notation
    if (/\\ce\{|\\pu\{|\\rightarrow|\\leftrightarrow|->|<->/.test(content)) {
      types.push('chemistry');
    }

    // Music detection: ABC notation or VexFlow markers
    if (/```abc|X:\s*\d|K:\s*[A-G]|```vexflow/.test(content)) {
      types.push('music');
    }

    // Diagram detection: Mermaid syntax
    if (/```mermaid|graph\s+(TD|LR|TB|BT)|sequenceDiagram|gantt|classDiagram|stateDiagram/.test(content)) {
      types.push('diagram');
    }

    // Code detection: Fenced code blocks with language
    if (/```(js|javascript|python|py|java|cpp|c\+\+|rust|go|ruby|php|swift|kotlin|typescript|ts)\b/.test(content)) {
      types.push('code');
    }

    // Physics detection: SI units, vectors
    if (/\\SI\{|\\si\{|\\vec\{|\\hat\{|\\unit\{/.test(content)) {
      types.push('physics');
    }

    return types;
  }

  /**
   * Render content using the appropriate engine
   */
  async render(
    type: NotationType,
    content: string,
    container: HTMLElement,
    options?: NotationRenderOptions
  ): Promise<void> {
    const engine = await this.loadEngine(type);
    return engine.render(content, container, options);
  }

  /**
   * Render content to string using the appropriate engine
   */
  async renderToString(
    type: NotationType,
    content: string,
    options?: NotationRenderOptions
  ): Promise<string> {
    const engine = await this.loadEngine(type);
    return engine.renderToString(content, options);
  }

  /**
   * Subscribe to engine status changes
   */
  subscribe(callback: (type: NotationType, status: EngineStatus) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  /**
   * Clear a cached engine (useful for testing or memory management)
   */
  clearEngine(type: NotationType): void {
    this.engines.set(type, {
      status: 'idle',
      engine: null,
      error: null,
      loadPromise: null,
    });
    this.notifyListeners(type, 'idle');
  }

  /**
   * Clear all cached engines
   */
  clearAll(): void {
    this.engines.forEach((_, type) => this.clearEngine(type));
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  private updateEngineState(type: NotationType, updates: Partial<EngineState>): void {
    const current = this.engines.get(type);
    if (current) {
      this.engines.set(type, { ...current, ...updates });
      if (updates.status) {
        this.notifyListeners(type, updates.status);
      }
    }
  }

  private notifyListeners(type: NotationType, status: EngineStatus): void {
    this.listeners.forEach((callback) => callback(type, status));
  }

  private async doLoadEngine(type: NotationType): Promise<NotationEngine> {
    switch (type) {
      case 'math':
        return this.loadMathEngine();
      case 'chemistry':
        return this.loadChemistryEngine();
      case 'music':
        return this.loadMusicEngine();
      case 'diagram':
        return this.loadDiagramEngine();
      case 'code':
        return this.loadCodeEngine();
      case 'physics':
        // Physics uses math engine with additional macros
        return this.loadPhysicsEngine();
      case 'economics':
        return this.loadEconomicsEngine();
      case 'geography':
        return this.loadGeographyEngine();
      default:
        throw new Error(`Unknown engine type: ${type}`);
    }
  }

  private async loadMathEngine(): Promise<NotationEngine> {
    const { MathEngine } = await import('./engines/MathEngine');
    const engine = new MathEngine();
    await engine.preload();
    return engine;
  }

  private async loadChemistryEngine(): Promise<NotationEngine> {
    const { ChemistryEngine } = await import('./engines/ChemistryEngine');
    const engine = new ChemistryEngine();
    await engine.preload();
    return engine;
  }

  private async loadMusicEngine(): Promise<NotationEngine> {
    const { MusicEngine } = await import('./engines/MusicEngine');
    const engine = new MusicEngine();
    await engine.preload();
    return engine;
  }

  private async loadDiagramEngine(): Promise<NotationEngine> {
    const { DiagramEngine } = await import('./engines/DiagramEngine');
    const engine = new DiagramEngine();
    await engine.preload();
    return engine;
  }

  private async loadCodeEngine(): Promise<NotationEngine> {
    const { CodeEngine } = await import('./engines/CodeEngine');
    const engine = new CodeEngine();
    await engine.preload();
    return engine;
  }

  private async loadPhysicsEngine(): Promise<NotationEngine> {
    // Physics engine extends math engine with SI units support
    const { MathEngine } = await import('./engines/MathEngine');
    const engine = new MathEngine({
      macros: {
        '\\SI': '\\text{#1}\\,\\text{#2}',
        '\\si': '\\text{#1}',
        '\\unit': '\\text{#1}',
        '\\vec': '\\mathbf{#1}',
        '\\hat': '\\mathbf{\\hat{#1}}',
      },
    });
    await engine.preload();
    return engine;
  }

  private async loadEconomicsEngine(): Promise<NotationEngine> {
    // Economics engine will use Chart.js for graphs
    // For now, return a placeholder that forwards to diagram engine
    const { DiagramEngine } = await import('./engines/DiagramEngine');
    const engine = new DiagramEngine();
    await engine.preload();
    return engine;
  }

  private async loadGeographyEngine(): Promise<NotationEngine> {
    // Geography engine will use Leaflet for maps
    // For now, return a placeholder
    const { DiagramEngine } = await import('./engines/DiagramEngine');
    const engine = new DiagramEngine();
    await engine.preload();
    return engine;
  }
}

// Export singleton instance and class (for static methods)
export const NotationEngineManager = new NotationEngineManagerClass();
export { NotationEngineManagerClass };
export default NotationEngineManager;
