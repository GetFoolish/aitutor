/**
 * Athena Notation Module
 *
 * Provides lazy-loaded notation rendering engines for various content types:
 * - Math (KaTeX)
 * - Chemistry (KaTeX + mhchem)
 * - Music (VexFlow)
 * - Diagrams (Mermaid)
 * - Code (Prism.js)
 */

export { NotationEngineManager, default } from './NotationEngineManager';
export { MathEngine } from './engines/MathEngine';
export { ChemistryEngine } from './engines/ChemistryEngine';
export { MusicEngine } from './engines/MusicEngine';
export { DiagramEngine } from './engines/DiagramEngine';
export { CodeEngine } from './engines/CodeEngine';

// Re-export the hook
export { useNotationEngine } from './useNotationEngine';
