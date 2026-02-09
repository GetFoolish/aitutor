/**
 * DrawingAnimator - Progressive stroke/shape rendering engine
 *
 * Accepts batches of drawing commands and renders them progressively
 * using requestAnimationFrame for smooth 60fps animation.
 *
 * This is the critical piece that enables the "Sal Khan" experience:
 * lines draw point-by-point, circles sweep arc-by-arc, and text
 * types character-by-character — all while Gemini continues speaking.
 */

// ──────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────

export interface ShapeDef {
  type: "line" | "rect" | "circle" | "arrow" | "text_label" | "number_line" | "freehand";
  // line / arrow
  x1?: number; y1?: number; x2?: number; y2?: number;
  // rect
  x?: number; y?: number; w?: number; h?: number;
  // circle
  cx?: number; cy?: number; r?: number;
  // text_label
  text?: string; size?: number; font?: string;
  // number_line
  length?: number; min?: number; max?: number; marks?: number[];
  // freehand (raw points)
  points?: Array<{ x: number; y: number }>;
  // common
  color?: string;
  width?: number;
}

export interface DrawBatch {
  shapes: ShapeDef[];
  clearFirst?: boolean;
  /** Duration in ms for the entire batch animation. Default 1500 */
  durationMs?: number;
}

interface AnimatingShape {
  shape: ShapeDef;
  startTime: number;
  durationMs: number;
}

type RenderCallback = () => void;

// ──────────────────────────────────────────────────────────
// DrawingAnimator
// ────────────────────────────────────────────────────────────

export class DrawingAnimator {
  private queue: AnimatingShape[] = [];
  private rafId: number | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private onRedrawNeeded: RenderCallback | null = null;
  private _isAnimating = false;

  /** Completed shapes that should be persisted in the canvas state */
  private completedShapes: Array<{ shape: ShapeDef; progress: number }> = [];

  get isAnimating(): boolean {
    return this._isAnimating;
  }

  /**
   * Bind to a canvas context and a redraw callback.
   * The redraw callback is invoked on each animation frame so the
   * host component can composite static + animated content.
   */
  attach(ctx: CanvasRenderingContext2D, onRedrawNeeded: RenderCallback) {
    this.ctx = ctx;
    this.onRedrawNeeded = onRedrawNeeded;
  }

  detach() {
    this.stop();
    this.ctx = null;
    this.onRedrawNeeded = null;
  }

  /**
   * Enqueue a batch of shapes for progressive rendering.
   * Returns immediately — animation happens async.
   */
  enqueue(batch: DrawBatch): void {
    const now = performance.now();
    const totalDuration = batch.durationMs ?? 1500;
    const perShape = batch.shapes.length > 0 ? totalDuration / batch.shapes.length : totalDuration;

    let offset = 0;
    for (const shape of batch.shapes) {
      this.queue.push({
        shape,
        startTime: now + offset,
        durationMs: perShape,
      });
      offset += perShape;
    }

    if (!this._isAnimating) {
      this._isAnimating = true;
      this.tick();
    }
  }

  /** Stop all animations and clear the queue */
  stop() {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.queue = [];
    this.completedShapes = [];
    this._isAnimating = false;
  }

  /** Cancel pending animations but keep already-completed shapes */
  cancelPending() {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    // Move any partially animated shapes to completed at their current progress
    this.queue = [];
    this._isAnimating = false;
  }

  // ──────────────────────────────────────────────────────────
  // Animation loop
  // ──────────────────────────────────────────────────────────

  private tick = () => {
    const now = performance.now();
    const ctx = this.ctx;
    if (!ctx) {
      this._isAnimating = false;
      return;
    }

    // Process queue: render each shape at its current progress
    const stillAnimating: AnimatingShape[] = [];

    for (const item of this.queue) {
      const elapsed = now - item.startTime;
      const progress = Math.min(elapsed / item.durationMs, 1);

      if (progress < 0) {
        // Not started yet
        stillAnimating.push(item);
        continue;
      }

      // Render at current progress
      this.renderShape(ctx, item.shape, progress);

      if (progress < 1) {
        stillAnimating.push(item);
      } else {
        // Shape completed — store for persistence
        this.completedShapes.push({ shape: item.shape, progress: 1 });
      }
    }

    this.queue = stillAnimating;

    // Notify host to redraw (host composites static + animated layers)
    this.onRedrawNeeded?.();

    if (this.queue.length > 0) {
      this.rafId = requestAnimationFrame(this.tick);
    } else {
      this._isAnimating = false;
      this.rafId = null;
    }
  };

  // ──────────────────────────────────────────────────────────
  // Shape renderers (progressive)
  // ──────────────────────────────────────────────────────────

  renderShape(ctx: CanvasRenderingContext2D, shape: ShapeDef, progress: number) {
    ctx.save();
    const color = shape.color || "#1e1e1e";
    const lineWidth = shape.width || 3;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    switch (shape.type) {
      case "line":
        this.renderLine(ctx, shape, progress);
        break;
      case "rect":
        this.renderRect(ctx, shape, progress);
        break;
      case "circle":
        this.renderCircle(ctx, shape, progress);
        break;
      case "arrow":
        this.renderArrow(ctx, shape, progress);
        break;
      case "text_label":
        this.renderTextLabel(ctx, shape, progress);
        break;
      case "number_line":
        this.renderNumberLine(ctx, shape, progress);
        break;
      case "freehand":
        this.renderFreehand(ctx, shape, progress);
        break;
    }

    ctx.restore();
  }

  private renderLine(ctx: CanvasRenderingContext2D, s: ShapeDef, progress: number) {
    const x1 = s.x1 ?? 0, y1 = s.y1 ?? 0;
    const x2 = s.x2 ?? 0, y2 = s.y2 ?? 0;
    const endX = x1 + (x2 - x1) * progress;
    const endY = y1 + (y2 - y1) * progress;

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(endX, endY);
    ctx.stroke();
  }

  private renderRect(ctx: CanvasRenderingContext2D, s: ShapeDef, progress: number) {
    const x = s.x ?? 0, y = s.y ?? 0;
    const w = s.w ?? 100, h = s.h ?? 100;
    // Draw rect as 4 line segments progressively
    const perimeter = 2 * w + 2 * h;
    const drawn = perimeter * progress;

    ctx.beginPath();
    ctx.moveTo(x, y);

    // Side 1: top
    const s1 = Math.min(drawn, w);
    ctx.lineTo(x + s1, y);
    if (drawn <= w) { ctx.stroke(); return; }

    // Side 2: right
    const s2 = Math.min(drawn - w, h);
    ctx.lineTo(x + w, y + s2);
    if (drawn <= w + h) { ctx.stroke(); return; }

    // Side 3: bottom
    const s3 = Math.min(drawn - w - h, w);
    ctx.lineTo(x + w - s3, y + h);
    if (drawn <= 2 * w + h) { ctx.stroke(); return; }

    // Side 4: left
    const s4 = Math.min(drawn - 2 * w - h, h);
    ctx.lineTo(x, y + h - s4);
    ctx.stroke();
  }

  private renderCircle(ctx: CanvasRenderingContext2D, s: ShapeDef, progress: number) {
    const cx = s.cx ?? 0, cy = s.cy ?? 0, r = s.r ?? 50;
    const endAngle = 2 * Math.PI * progress;

    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + endAngle);
    ctx.stroke();
  }

  private renderArrow(ctx: CanvasRenderingContext2D, s: ShapeDef, progress: number) {
    const x1 = s.x1 ?? 0, y1 = s.y1 ?? 0;
    const x2 = s.x2 ?? 0, y2 = s.y2 ?? 0;

    // Shaft takes 70% of animation, arrowhead takes 30%
    const shaftProgress = Math.min(progress / 0.7, 1);
    const headProgress = Math.max((progress - 0.7) / 0.3, 0);

    // Draw shaft
    const endX = x1 + (x2 - x1) * shaftProgress;
    const endY = y1 + (y2 - y1) * shaftProgress;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(endX, endY);
    ctx.stroke();

    // Draw arrowhead when shaft is complete
    if (headProgress > 0) {
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const headLength = Math.min(20, Math.hypot(x2 - x1, y2 - y1) * 0.25);
      const leftX = x2 - headLength * Math.cos(angle - Math.PI / 6);
      const leftY = y2 - headLength * Math.sin(angle - Math.PI / 6);
      const rightX = x2 - headLength * Math.cos(angle + Math.PI / 6);
      const rightY = y2 - headLength * Math.sin(angle + Math.PI / 6);

      const lx = x2 + (leftX - x2) * headProgress;
      const ly = y2 + (leftY - y2) * headProgress;
      const rx = x2 + (rightX - x2) * headProgress;
      const ry = y2 + (rightY - y2) * headProgress;

      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(lx, ly);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(rx, ry);
      ctx.stroke();
    }
  }

  private renderTextLabel(ctx: CanvasRenderingContext2D, s: ShapeDef, progress: number) {
    const x = s.x ?? 0, y = s.y ?? 0;
    const text = s.text ?? "";
    const fontSize = s.size ?? 20;
    const fontFamily = s.font ?? "'Space Grotesk', sans-serif";

    ctx.font = `bold ${fontSize}px ${fontFamily}`;
    ctx.textBaseline = "top";

    // Typewriter effect: reveal characters progressively
    const charsToShow = Math.ceil(text.length * progress);
    const visibleText = text.substring(0, charsToShow);

    ctx.fillText(visibleText, x, y);
  }

  private renderNumberLine(ctx: CanvasRenderingContext2D, s: ShapeDef, progress: number) {
    const x = s.x ?? 50, y = s.y ?? 300;
    const length = s.length ?? 700;
    const min = s.min ?? 0, max = s.max ?? 10;
    const marks = s.marks ?? [];
    const range = max - min;
    if (range <= 0) return;

    const tickHeight = 12;
    const fontSize = 14;
    const fontFamily = "'Space Grotesk', sans-serif";

    // Phase 1 (0-40%): Draw the main axis line
    const axisProgress = Math.min(progress / 0.4, 1);
    const axisEndX = x + length * axisProgress;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(axisEndX, y);
    ctx.stroke();

    if (progress <= 0.4) return;

    // Phase 2 (40-70%): Draw tick marks and labels
    const tickProgress = Math.min((progress - 0.4) / 0.3, 1);
    const step = range <= 30 ? 1 : Math.ceil(range / 20);
    const totalTicks = Math.floor(range / step) + 1;
    const ticksToShow = Math.ceil(totalTicks * tickProgress);

    ctx.font = `${fontSize}px ${fontFamily}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    let tickIdx = 0;
    for (let v = min; v <= max; v += step) {
      if (tickIdx >= ticksToShow) break;
      const px = x + ((v - min) / range) * length;

      ctx.beginPath();
      ctx.moveTo(px, y - tickHeight);
      ctx.lineTo(px, y + tickHeight);
      ctx.stroke();

      // Label
      ctx.fillText(String(v), px, y + tickHeight + 4);
      tickIdx++;
    }

    if (progress <= 0.7) return;

    // Phase 3 (70-100%): Highlight marks
    const markProgress = Math.min((progress - 0.7) / 0.3, 1);
    const marksToShow = Math.ceil(marks.length * markProgress);

    ctx.save();
    ctx.strokeStyle = "#e03131";
    ctx.fillStyle = "#e03131";
    ctx.lineWidth = (s.width ?? 2) + 1;

    for (let i = 0; i < marksToShow; i++) {
      const m = marks[i];
      if (m >= min && m <= max) {
        const px = x + ((m - min) / range) * length;

        ctx.beginPath();
        ctx.arc(px, y, 8, 0, 2 * Math.PI);
        ctx.stroke();

        ctx.font = `bold ${fontSize}px ${fontFamily}`;
        ctx.fillText(String(m), px, y - tickHeight - fontSize - 4);
      }
    }
    ctx.restore();
  }

  private renderFreehand(ctx: CanvasRenderingContext2D, s: ShapeDef, progress: number) {
    const points = s.points ?? [];
    if (points.length < 2) return;

    const pointsToShow = Math.ceil(points.length * progress);

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < pointsToShow; i++) {
      ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.stroke();
  }

  // ──────────────────────────────────────────────────────────
  // Render all completed shapes (for static redraw)
  // ──────────────────────────────────────────────────────────

  renderCompleted(ctx: CanvasRenderingContext2D) {
    for (const { shape } of this.completedShapes) {
      this.renderShape(ctx, shape, 1);
    }
  }

  /** Get count of completed shapes */
  get completedCount(): number {
    return this.completedShapes.length;
  }

  /** Move all currently-animating shapes to completed (render at 100%) */
  finishAll() {
    for (const item of this.queue) {
      this.completedShapes.push({ shape: item.shape, progress: 1 });
    }
    this.queue = [];
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this._isAnimating = false;
    this.onRedrawNeeded?.();
  }

  /** Clear all completed shapes */
  clearCompleted() {
    this.completedShapes = [];
  }
}

