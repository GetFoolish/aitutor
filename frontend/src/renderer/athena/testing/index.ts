/**
 * Athena Testing Module
 *
 * Testing utilities, benchmarks, and fixtures.
 */

export {
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
} from './PerformanceBenchmark';
export type { BenchmarkResult, BenchmarkOptions, BenchmarkSuite } from './PerformanceBenchmark';

export {
  runAccessibilityAudit,
  formatAuditReport,
  WCAG_CRITERIA,
  ATHENA_CHECKS,
} from './AccessibilityAudit';
export type { AccessibilityIssue, AuditResult, AuditOptions } from './AccessibilityAudit';

// Test fixtures
export { default as mathQuestions } from './fixtures/math-questions.json';
export { default as chemistryQuestions } from './fixtures/chemistry-questions.json';
export { default as multiSubjectQuestions } from './fixtures/multi-subject-questions.json';
