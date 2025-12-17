/**
 * Athena Performance Module
 *
 * Performance utilities and optimizations.
 */

export {
  createLazyLoader,
  loadModule,
  preloadModules,
  createLazyComponent,
  ModuleRegistry,
  moduleRegistry,
  dynamicImport,
  prefetchModule,
  preloadModule,
} from './LazyLoader';
export type { LazyModule, LazyLoaderOptions } from './LazyLoader';

export {
  LRUCache,
  RenderCache,
  memoize,
  memoizeAsync,
  renderCache,
} from './RenderCache';
export type { CacheEntry, CacheOptions } from './RenderCache';

export { VirtualScroller, useVirtualScroller } from './VirtualScroller';
export type { VirtualScrollerProps, VirtualScrollerRef } from './VirtualScroller';
