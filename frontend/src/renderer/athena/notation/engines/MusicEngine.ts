/**
 * Music Engine - VexFlow Wrapper
 *
 * Renders musical notation including notes, staff, chords, and rhythms.
 * Uses VexFlow for high-quality music engraving.
 */

import type { NotationEngine, NotationRenderOptions } from '../../core/types';

// Note: VexFlow types are complex, so we'll use a simplified interface
interface VexFlow {
  Renderer: new (element: HTMLElement, backend: number) => VexFlowRenderer;
  Stave: new (x: number, y: number, width: number) => VexFlowStave;
  StaveNote: new (options: VexFlowNoteOptions) => VexFlowNote;
  Voice: new (options: VexFlowVoiceOptions) => VexFlowVoice;
  Formatter: new () => VexFlowFormatter;
  Factory: new (options: VexFlowFactoryOptions) => VexFlowFactory;
}

interface VexFlowRenderer {
  resize(width: number, height: number): void;
  getContext(): VexFlowContext;
  backends: { SVG: number; CANVAS: number };
}

interface VexFlowContext {
  setFont(family: string, size: number, weight: string): VexFlowContext;
  setFillStyle(style: string): VexFlowContext;
}

interface VexFlowStave {
  addClef(clef: string): VexFlowStave;
  addTimeSignature(signature: string): VexFlowStave;
  addKeySignature(key: string): VexFlowStave;
  setContext(context: VexFlowContext): VexFlowStave;
  draw(): void;
}

interface VexFlowNoteOptions {
  keys: string[];
  duration: string;
  clef?: string;
  stem_direction?: number;
}

interface VexFlowNote {
  addAccidental(index: number, accidental: unknown): VexFlowNote;
  addDot(index: number): VexFlowNote;
}

interface VexFlowVoiceOptions {
  num_beats: number;
  beat_value: number;
}

interface VexFlowVoice {
  addTickables(notes: VexFlowNote[]): VexFlowVoice;
  draw(context: VexFlowContext, stave: VexFlowStave): void;
}

interface VexFlowFormatter {
  joinVoices(voices: VexFlowVoice[]): VexFlowFormatter;
  format(voices: VexFlowVoice[], width: number): void;
}

interface VexFlowFactoryOptions {
  renderer: { elementId: string; width: number; height: number };
}

interface VexFlowFactory {
  Stave(options: unknown): VexFlowStave;
  StaveNote(options: VexFlowNoteOptions): VexFlowNote;
  Voice(options: VexFlowVoiceOptions): VexFlowVoice;
  draw(): void;
}

export class MusicEngine implements NotationEngine {
  type = 'music' as const;
  private vexflow: VexFlow | null = null;
  private loaded = false;

  /**
   * Check if engine is loaded
   */
  isLoaded(): boolean {
    return this.loaded && this.vexflow !== null;
  }

  /**
   * Preload VexFlow
   */
  async preload(): Promise<void> {
    if (this.loaded) return;

    try {
      // @ts-ignore - VexFlow types are complex
      const vexflowModule = await import('vexflow');
      this.vexflow = vexflowModule as unknown as VexFlow;
      this.loaded = true;
    } catch (error) {
      console.error('Failed to load VexFlow:', error);
      throw new Error(`Failed to load music engine: ${error}`);
    }
  }

  /**
   * Render music notation to a DOM element
   */
  async render(
    content: string,
    container: HTMLElement,
    options?: NotationRenderOptions
  ): Promise<void> {
    await this.preload();

    if (!this.vexflow) {
      throw new Error('VexFlow not loaded');
    }

    try {
      const parsed = this.parseNotation(content);

      // Clear the container
      container.innerHTML = '';
      container.classList.add('athena-music', 'athena-vexflow');

      // Create renderer
      const { Renderer, Stave, StaveNote, Voice, Formatter } = this.vexflow;
      const renderer = new Renderer(container, Renderer.prototype.backends?.SVG || 3);

      // Set dimensions
      const width = parsed.width || 500;
      const height = parsed.height || 150;
      renderer.resize(width, height);

      const context = renderer.getContext();
      context.setFont('Arial', 10, 'normal').setFillStyle('#000');

      // Create stave
      const stave = new Stave(10, 40, width - 20);

      if (parsed.clef) {
        stave.addClef(parsed.clef);
      } else {
        stave.addClef('treble');
      }

      if (parsed.timeSignature) {
        stave.addTimeSignature(parsed.timeSignature);
      }

      if (parsed.keySignature) {
        stave.addKeySignature(parsed.keySignature);
      }

      stave.setContext(context).draw();

      // Create notes
      const notes = parsed.notes.map((note) => {
        const staveNote = new StaveNote({
          keys: note.keys,
          duration: note.duration,
          clef: parsed.clef || 'treble',
        });

        // Add accidentals
        note.accidentals?.forEach((acc, idx) => {
          if (acc && this.vexflow) {
            // Would need Accidental class from VexFlow
          }
        });

        // Add dots
        note.dots?.forEach((_, idx) => {
          staveNote.addDot(idx);
        });

        return staveNote;
      });

      // Create voice and add notes
      const voice = new Voice({
        num_beats: parsed.beats || 4,
        beat_value: parsed.beatValue || 4,
      });
      voice.addTickables(notes);

      // Format and justify notes
      new Formatter().joinVoices([voice]).format([voice], width - 60);

      // Draw the voice
      voice.draw(context, stave);
    } catch (error) {
      container.innerHTML = `
        <div class="athena-music-error">
          <strong>Music Notation Error</strong>
          <pre>${this.escapeHtml(content)}</pre>
          <p>${this.escapeHtml(String(error))}</p>
        </div>
      `;
      console.warn('VexFlow render error:', error);
    }
  }

  /**
   * Render music notation to SVG string
   */
  async renderToString(content: string, options?: NotationRenderOptions): Promise<string> {
    // Create a temporary container
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    document.body.appendChild(tempContainer);

    try {
      await this.render(content, tempContainer, options);
      const svg = tempContainer.innerHTML;
      return `<div class="athena-music athena-vexflow">${svg}</div>`;
    } finally {
      document.body.removeChild(tempContainer);
    }
  }

  /**
   * Parse notation string into structured data
   */
  private parseNotation(content: string): ParsedNotation {
    const trimmed = content.trim();

    // Check if it's ABC notation
    if (this.isABCNotation(trimmed)) {
      return this.parseABCNotation(trimmed);
    }

    // Check if it's simple space-separated notes
    if (/^[A-Ga-g][#b]?\d?\s/.test(trimmed)) {
      return this.parseSimpleNotation(trimmed);
    }

    // Default: treat as simple notation
    return this.parseSimpleNotation(trimmed);
  }

  /**
   * Check if content is ABC notation
   */
  private isABCNotation(content: string): boolean {
    return /^X:\s*\d/m.test(content) || /^K:\s*[A-G]/m.test(content);
  }

  /**
   * Parse ABC notation format
   */
  private parseABCNotation(content: string): ParsedNotation {
    const result: ParsedNotation = {
      clef: 'treble',
      notes: [],
      beats: 4,
      beatValue: 4,
    };

    // Parse header fields
    const keyMatch = content.match(/K:\s*([A-G][#b]?)(m)?/);
    if (keyMatch) {
      result.keySignature = keyMatch[1] + (keyMatch[2] || '');
    }

    const meterMatch = content.match(/M:\s*(\d+)\/(\d+)/);
    if (meterMatch) {
      result.beats = parseInt(meterMatch[1], 10);
      result.beatValue = parseInt(meterMatch[2], 10);
      result.timeSignature = `${result.beats}/${result.beatValue}`;
    }

    // Parse notes (simplified - full ABC parsing is complex)
    const notePattern = /([A-Ga-g][',]*)(\d*)/g;
    const noteSection = content.split('\n').filter((line) => !/^[A-Z]:/.test(line)).join('');
    let match;

    while ((match = notePattern.exec(noteSection)) !== null) {
      const noteName = match[1];
      const duration = match[2] || '1';

      const keys = [this.abcNoteToVexFlow(noteName)];
      const durationMap: Record<string, string> = {
        '1': 'q',
        '2': 'h',
        '4': 'w',
        '/2': '8',
        '/4': '16',
      };

      result.notes.push({
        keys,
        duration: durationMap[duration] || 'q',
      });
    }

    return result;
  }

  /**
   * Parse simple notation format (e.g., "C4 D4 E4 F4")
   */
  private parseSimpleNotation(content: string): ParsedNotation {
    const result: ParsedNotation = {
      clef: 'treble',
      notes: [],
      beats: 4,
      beatValue: 4,
    };

    const tokens = content.split(/\s+/);

    for (const token of tokens) {
      const parsed = this.parseNoteToken(token);
      if (parsed) {
        result.notes.push(parsed);
      }
    }

    return result;
  }

  /**
   * Parse a single note token
   */
  private parseNoteToken(token: string): NoteData | null {
    // Format: NoteName[Accidental][Octave][/Duration]
    // Examples: C4, D#4, Eb4/2, F4/4
    const match = token.match(/^([A-Ga-g])([#b]?)(\d)?(?:\/(\d+))?$/);
    if (!match) return null;

    const [, noteName, accidental, octave = '4', duration] = match;
    const pitch = noteName.toUpperCase() + accidental;
    const key = `${pitch}/${octave}`;

    // Duration mapping: /1 = whole, /2 = half, /4 = quarter (default), /8 = eighth
    const durationMap: Record<string, string> = {
      '1': 'w',
      '2': 'h',
      '4': 'q',
      '8': '8',
      '16': '16',
    };

    return {
      keys: [key],
      duration: durationMap[duration || '4'] || 'q',
      accidentals: accidental ? [accidental] : undefined,
    };
  }

  /**
   * Convert ABC note to VexFlow format
   */
  private abcNoteToVexFlow(abcNote: string): string {
    // ABC notation: CDEFGABcdefgab
    // Uppercase = lower octave, lowercase = higher octave
    // ' = up one octave, , = down one octave
    const isLower = abcNote[0] === abcNote[0].toLowerCase();
    const baseNote = abcNote[0].toUpperCase();
    let octave = isLower ? 5 : 4;

    // Count octave modifiers
    for (const char of abcNote.slice(1)) {
      if (char === "'") octave++;
      else if (char === ',') octave--;
    }

    return `${baseNote}/${octave}`;
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

interface NoteData {
  keys: string[];
  duration: string;
  accidentals?: string[];
  dots?: boolean[];
}

interface ParsedNotation {
  clef: string;
  timeSignature?: string;
  keySignature?: string;
  notes: NoteData[];
  beats: number;
  beatValue: number;
  width?: number;
  height?: number;
}

export default MusicEngine;
