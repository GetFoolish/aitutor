/**
 * Performance Benchmark
 *
 * Tools for measuring and comparing Athena performance.
 */

export interface BenchmarkResult {
  name: string;
  iterations: number;
  totalTime: number;
  avgTime: number;
  minTime: number;
  maxTime: number;
  stdDev: number;
  p95: number;
  p99: number;
  opsPerSecond: number;
}

export interface BenchmarkOptions {
  /** Number of iterations */
  iterations?: number;
  /** Warmup iterations */
  warmup?: number;
  /** Timeout per iteration in ms */
  timeout?: number;
  /** Setup function before each iteration */
  setup?: () => void | Promise<void>;
  /** Teardown function after each iteration */
  teardown?: () => void | Promise<void>;
}

export interface BenchmarkSuite {
  name: string;
  benchmarks: Map<string, () => void | Promise<void>>;
  results: Map<string, BenchmarkResult>;
}

/**
 * Run a single benchmark
 */
export async function runBenchmark(
  name: string,
  fn: () => void | Promise<void>,
  options: BenchmarkOptions = {}
): Promise<BenchmarkResult> {
  const {
    iterations = 100,
    warmup = 10,
    timeout = 30000,
    setup,
    teardown,
  } = options;

  const times: number[] = [];

  // Warmup
  for (let i = 0; i < warmup; i++) {
    await setup?.();
    await fn();
    await teardown?.();
  }

  // Run iterations
  for (let i = 0; i < iterations; i++) {
    await setup?.();

    const start = performance.now();
    await fn();
    const end = performance.now();

    await teardown?.();

    times.push(end - start);
  }

  // Calculate statistics
  const totalTime = times.reduce((a, b) => a + b, 0);
  const avgTime = totalTime / times.length;
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);

  const variance = times.reduce((sum, t) => sum + Math.pow(t - avgTime, 2), 0) / times.length;
  const stdDev = Math.sqrt(variance);

  const sorted = [...times].sort((a, b) => a - b);
  const p95 = sorted[Math.floor(times.length * 0.95)];
  const p99 = sorted[Math.floor(times.length * 0.99)];

  const opsPerSecond = 1000 / avgTime;

  return {
    name,
    iterations,
    totalTime,
    avgTime,
    minTime,
    maxTime,
    stdDev,
    p95,
    p99,
    opsPerSecond,
  };
}

/**
 * Create a benchmark suite
 */
export function createBenchmarkSuite(name: string): BenchmarkSuite {
  return {
    name,
    benchmarks: new Map(),
    results: new Map(),
  };
}

/**
 * Add benchmark to suite
 */
export function addBenchmark(
  suite: BenchmarkSuite,
  name: string,
  fn: () => void | Promise<void>
): void {
  suite.benchmarks.set(name, fn);
}

/**
 * Run all benchmarks in suite
 */
export async function runBenchmarkSuite(
  suite: BenchmarkSuite,
  options: BenchmarkOptions = {}
): Promise<Map<string, BenchmarkResult>> {
  for (const [name, fn] of suite.benchmarks) {
    const result = await runBenchmark(name, fn, options);
    suite.results.set(name, result);
  }
  return suite.results;
}

/**
 * Format benchmark results as table
 */
export function formatBenchmarkResults(results: Map<string, BenchmarkResult> | BenchmarkResult[]): string {
  const resultArray = Array.isArray(results)
    ? results
    : Array.from(results.values());

  const lines: string[] = [];
  lines.push('| Benchmark | Avg (ms) | Min (ms) | Max (ms) | Std Dev | p95 | p99 | ops/sec |');
  lines.push('|-----------|----------|----------|----------|---------|-----|-----|---------|');

  for (const result of resultArray) {
    lines.push(
      `| ${result.name} | ${result.avgTime.toFixed(2)} | ${result.minTime.toFixed(2)} | ${result.maxTime.toFixed(2)} | ${result.stdDev.toFixed(2)} | ${result.p95.toFixed(2)} | ${result.p99.toFixed(2)} | ${result.opsPerSecond.toFixed(0)} |`
    );
  }

  return lines.join('\n');
}

/**
 * Compare two benchmark results
 */
export function compareBenchmarks(
  baseline: BenchmarkResult,
  comparison: BenchmarkResult
): {
  name: string;
  baselineName: string;
  comparisonName: string;
  avgDiff: number;
  avgDiffPercent: number;
  faster: boolean;
  speedup: number;
} {
  const avgDiff = comparison.avgTime - baseline.avgTime;
  const avgDiffPercent = (avgDiff / baseline.avgTime) * 100;
  const faster = avgDiff < 0;
  const speedup = faster ? baseline.avgTime / comparison.avgTime : comparison.avgTime / baseline.avgTime;

  return {
    name: `${baseline.name} vs ${comparison.name}`,
    baselineName: baseline.name,
    comparisonName: comparison.name,
    avgDiff,
    avgDiffPercent,
    faster,
    speedup,
  };
}

/**
 * Memory usage tracker
 */
export class MemoryTracker {
  private snapshots: Array<{ label: string; heapUsed: number; timestamp: number }> = [];

  /**
   * Take a memory snapshot
   */
  snapshot(label: string): void {
    if (typeof performance !== 'undefined' && 'memory' in performance) {
      const memory = (performance as any).memory;
      this.snapshots.push({
        label,
        heapUsed: memory.usedJSHeapSize,
        timestamp: Date.now(),
      });
    }
  }

  /**
   * Get memory diff between two snapshots
   */
  diff(startLabel: string, endLabel: string): number | null {
    const start = this.snapshots.find(s => s.label === startLabel);
    const end = this.snapshots.find(s => s.label === endLabel);

    if (!start || !end) return null;
    return end.heapUsed - start.heapUsed;
  }

  /**
   * Get all snapshots
   */
  getSnapshots() {
    return [...this.snapshots];
  }

  /**
   * Clear snapshots
   */
  clear(): void {
    this.snapshots = [];
  }

  /**
   * Format as table
   */
  format(): string {
    const lines: string[] = [];
    lines.push('| Snapshot | Heap Used (MB) | Diff (MB) |');
    lines.push('|----------|----------------|-----------|');

    let prevHeap = 0;
    for (const snapshot of this.snapshots) {
      const heapMB = snapshot.heapUsed / (1024 * 1024);
      const diffMB = (snapshot.heapUsed - prevHeap) / (1024 * 1024);
      lines.push(
        `| ${snapshot.label} | ${heapMB.toFixed(2)} | ${prevHeap ? (diffMB > 0 ? '+' : '') + diffMB.toFixed(2) : '-'} |`
      );
      prevHeap = snapshot.heapUsed;
    }

    return lines.join('\n');
  }
}

/**
 * Render time profiler
 */
export class RenderProfiler {
  private renders: Array<{
    component: string;
    phase: 'mount' | 'update';
    actualDuration: number;
    baseDuration: number;
    startTime: number;
    commitTime: number;
  }> = [];

  /**
   * Record a render
   */
  record(
    component: string,
    phase: 'mount' | 'update',
    actualDuration: number,
    baseDuration: number,
    startTime: number,
    commitTime: number
  ): void {
    this.renders.push({
      component,
      phase,
      actualDuration,
      baseDuration,
      startTime,
      commitTime,
    });
  }

  /**
   * Get render summary
   */
  getSummary(): Map<string, {
    component: string;
    mountCount: number;
    updateCount: number;
    totalActualTime: number;
    avgActualTime: number;
    totalBaseTime: number;
  }> {
    const summary = new Map<string, {
      component: string;
      mountCount: number;
      updateCount: number;
      totalActualTime: number;
      avgActualTime: number;
      totalBaseTime: number;
    }>();

    for (const render of this.renders) {
      if (!summary.has(render.component)) {
        summary.set(render.component, {
          component: render.component,
          mountCount: 0,
          updateCount: 0,
          totalActualTime: 0,
          avgActualTime: 0,
          totalBaseTime: 0,
        });
      }

      const stats = summary.get(render.component)!;
      if (render.phase === 'mount') {
        stats.mountCount++;
      } else {
        stats.updateCount++;
      }
      stats.totalActualTime += render.actualDuration;
      stats.totalBaseTime += render.baseDuration;
    }

    // Calculate averages
    for (const [, stats] of summary) {
      const totalRenders = stats.mountCount + stats.updateCount;
      stats.avgActualTime = totalRenders > 0 ? stats.totalActualTime / totalRenders : 0;
    }

    return summary;
  }

  /**
   * Clear records
   */
  clear(): void {
    this.renders = [];
  }

  /**
   * Format as table
   */
  format(): string {
    const summary = this.getSummary();
    const lines: string[] = [];
    lines.push('| Component | Mounts | Updates | Total Time (ms) | Avg Time (ms) |');
    lines.push('|-----------|--------|---------|-----------------|---------------|');

    for (const [, stats] of summary) {
      lines.push(
        `| ${stats.component} | ${stats.mountCount} | ${stats.updateCount} | ${stats.totalActualTime.toFixed(2)} | ${stats.avgActualTime.toFixed(2)} |`
      );
    }

    return lines.join('\n');
  }
}

// Global instances
export const memoryTracker = new MemoryTracker();
export const renderProfiler = new RenderProfiler();

/**
 * Athena performance targets
 */
export const PERFORMANCE_TARGETS = {
  // Bundle sizes (KB)
  bundleSize: {
    initial: 200,  // Target: <200KB initial (vs ~1MB Perseus)
    katex: 100,    // KaTeX lazy loaded
    vexflow: 300,  // VexFlow lazy loaded
    mermaid: 250,  // Mermaid lazy loaded
  },

  // Render times (ms)
  renderTime: {
    firstContentfulPaint: 500,  // Target: <500ms
    mathRender: 50,             // Target: <50ms per equation
    widgetRender: 100,          // Target: <100ms per widget
    interactiveReady: 1000,     // Target: <1s to interactive
  },

  // Memory (MB)
  memory: {
    idle: 30,      // Target: <30MB idle
    rendering: 50, // Target: <50MB while rendering
  },
};

export default {
  runBenchmark,
  createBenchmarkSuite,
  addBenchmark,
  runBenchmarkSuite,
  formatBenchmarkResults,
  compareBenchmarks,
  MemoryTracker,
  RenderProfiler,
  memoryTracker,
  renderProfiler,
  PERFORMANCE_TARGETS,
};
