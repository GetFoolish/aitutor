/**
 * Virtual Scroller
 *
 * Virtualized list component for rendering large content efficiently.
 */

import React, {
  useState,
  useCallback,
  useRef,
  useEffect,
  useMemo,
  forwardRef,
  useImperativeHandle,
} from 'react';

export interface VirtualScrollerProps<T> {
  /** Items to render */
  items: T[];
  /** Render function for each item */
  renderItem: (item: T, index: number, style: React.CSSProperties) => React.ReactNode;
  /** Fixed item height (for fixed-size items) */
  itemHeight?: number;
  /** Function to estimate item height (for variable-size items) */
  estimateItemHeight?: (item: T, index: number) => number;
  /** Container height */
  height: number;
  /** Container width */
  width?: number | string;
  /** Overscan count (items to render outside viewport) */
  overscan?: number;
  /** Called when scroll position changes */
  onScroll?: (scrollTop: number, scrollHeight: number) => void;
  /** Called when visible range changes */
  onVisibleRangeChange?: (start: number, end: number) => void;
  /** Custom class name */
  className?: string;
  /** Item key extractor */
  getItemKey?: (item: T, index: number) => string | number;
}

export interface VirtualScrollerRef {
  /** Scroll to specific index */
  scrollToIndex: (index: number, align?: 'start' | 'center' | 'end') => void;
  /** Scroll to specific offset */
  scrollTo: (offset: number) => void;
  /** Get current scroll position */
  getScrollPosition: () => number;
  /** Refresh layout (call after item sizes change) */
  refresh: () => void;
}

/**
 * Virtual scroller component
 */
export const VirtualScroller = forwardRef(function VirtualScroller<T>(
  {
    items,
    renderItem,
    itemHeight,
    estimateItemHeight,
    height,
    width = '100%',
    overscan = 3,
    onScroll,
    onVisibleRangeChange,
    className = '',
    getItemKey,
  }: VirtualScrollerProps<T>,
  ref: React.Ref<VirtualScrollerRef>
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [measuredHeights, setMeasuredHeights] = useState<Map<number, number>>(new Map());

  // Calculate item positions
  const { itemPositions, totalHeight } = useMemo(() => {
    const positions: Array<{ top: number; height: number }> = [];
    let currentTop = 0;

    items.forEach((item, index) => {
      const h = measuredHeights.get(index) ??
        itemHeight ??
        estimateItemHeight?.(item, index) ??
        50;
      positions.push({ top: currentTop, height: h });
      currentTop += h;
    });

    return { itemPositions: positions, totalHeight: currentTop };
  }, [items, itemHeight, estimateItemHeight, measuredHeights]);

  // Calculate visible range
  const { startIndex, endIndex, visibleItems } = useMemo(() => {
    if (items.length === 0) {
      return { startIndex: 0, endIndex: 0, visibleItems: [] };
    }

    // Binary search for start index
    let start = 0;
    let end = itemPositions.length - 1;
    while (start < end) {
      const mid = Math.floor((start + end) / 2);
      if (itemPositions[mid].top + itemPositions[mid].height < scrollTop) {
        start = mid + 1;
      } else {
        end = mid;
      }
    }

    const startIdx = Math.max(0, start - overscan);
    let endIdx = start;

    // Find end index
    const viewportBottom = scrollTop + height;
    while (endIdx < itemPositions.length && itemPositions[endIdx].top < viewportBottom) {
      endIdx++;
    }
    endIdx = Math.min(items.length - 1, endIdx + overscan);

    const visible: Array<{ item: T; index: number; style: React.CSSProperties }> = [];
    for (let i = startIdx; i <= endIdx; i++) {
      visible.push({
        item: items[i],
        index: i,
        style: {
          position: 'absolute',
          top: itemPositions[i].top,
          height: itemPositions[i].height,
          width: '100%',
        },
      });
    }

    return { startIndex: startIdx, endIndex: endIdx, visibleItems: visible };
  }, [items, itemPositions, scrollTop, height, overscan]);

  // Notify visible range change
  useEffect(() => {
    onVisibleRangeChange?.(startIndex, endIndex);
  }, [startIndex, endIndex, onVisibleRangeChange]);

  // Handle scroll
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const newScrollTop = target.scrollTop;
    setScrollTop(newScrollTop);
    onScroll?.(newScrollTop, target.scrollHeight);
  }, [onScroll]);

  // Measure item height
  const measureItem = useCallback((index: number, height: number) => {
    setMeasuredHeights((prev) => {
      const next = new Map(prev);
      next.set(index, height);
      return next;
    });
  }, []);

  // Expose ref methods
  useImperativeHandle(ref, () => ({
    scrollToIndex: (index: number, align = 'start') => {
      if (!containerRef.current || index < 0 || index >= items.length) return;

      const position = itemPositions[index];
      if (!position) return;

      let targetScroll = position.top;
      if (align === 'center') {
        targetScroll = position.top - (height - position.height) / 2;
      } else if (align === 'end') {
        targetScroll = position.top - height + position.height;
      }

      containerRef.current.scrollTop = Math.max(0, targetScroll);
    },
    scrollTo: (offset: number) => {
      if (containerRef.current) {
        containerRef.current.scrollTop = offset;
      }
    },
    getScrollPosition: () => scrollTop,
    refresh: () => {
      setMeasuredHeights(new Map());
    },
  }), [items.length, itemPositions, height, scrollTop]);

  return (
    <div
      ref={containerRef}
      className={`athena-virtual-scroller ${className}`}
      style={{
        height,
        width,
        overflow: 'auto',
        position: 'relative',
      }}
      onScroll={handleScroll}
    >
      <div
        style={{
          height: totalHeight,
          position: 'relative',
          width: '100%',
        }}
      >
        {visibleItems.map(({ item, index, style }) => (
          <VirtualItem
            key={getItemKey?.(item, index) ?? index}
            index={index}
            style={style}
            onMeasure={measureItem}
          >
            {renderItem(item, index, style)}
          </VirtualItem>
        ))}
      </div>
    </div>
  );
}) as <T>(
  props: VirtualScrollerProps<T> & { ref?: React.Ref<VirtualScrollerRef> }
) => React.ReactElement;

/**
 * Virtual item wrapper for measuring
 */
function VirtualItem({
  index,
  style,
  onMeasure,
  children,
}: {
  index: number;
  style: React.CSSProperties;
  onMeasure: (index: number, height: number) => void;
  children: React.ReactNode;
}) {
  const itemRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (itemRef.current) {
      const observer = new ResizeObserver((entries) => {
        const entry = entries[0];
        if (entry) {
          onMeasure(index, entry.contentRect.height);
        }
      });

      observer.observe(itemRef.current);
      return () => observer.disconnect();
    }
  }, [index, onMeasure]);

  return (
    <div ref={itemRef} style={style}>
      {children}
    </div>
  );
}

/**
 * Hook for virtual scrolling with items
 */
export function useVirtualScroller<T>(
  items: T[],
  options: {
    itemHeight?: number;
    estimateItemHeight?: (item: T, index: number) => number;
    containerHeight: number;
    overscan?: number;
  }
) {
  const {
    itemHeight,
    estimateItemHeight,
    containerHeight,
    overscan = 3,
  } = options;

  const [scrollTop, setScrollTop] = useState(0);

  // Calculate positions
  const { positions, totalHeight, visibleRange } = useMemo(() => {
    const pos: Array<{ top: number; height: number }> = [];
    let currentTop = 0;

    items.forEach((item, index) => {
      const h = itemHeight ?? estimateItemHeight?.(item, index) ?? 50;
      pos.push({ top: currentTop, height: h });
      currentTop += h;
    });

    // Calculate visible range
    let startIdx = 0;
    while (startIdx < pos.length && pos[startIdx].top + pos[startIdx].height < scrollTop) {
      startIdx++;
    }
    startIdx = Math.max(0, startIdx - overscan);

    let endIdx = startIdx;
    const viewportBottom = scrollTop + containerHeight;
    while (endIdx < pos.length && pos[endIdx].top < viewportBottom) {
      endIdx++;
    }
    endIdx = Math.min(items.length - 1, endIdx + overscan);

    return {
      positions: pos,
      totalHeight: currentTop,
      visibleRange: { start: startIdx, end: endIdx },
    };
  }, [items, itemHeight, estimateItemHeight, scrollTop, containerHeight, overscan]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const getItemProps = useCallback((index: number) => ({
    style: {
      position: 'absolute' as const,
      top: positions[index]?.top ?? 0,
      height: positions[index]?.height ?? itemHeight ?? 50,
      width: '100%',
    },
  }), [positions, itemHeight]);

  return {
    scrollTop,
    totalHeight,
    visibleRange,
    handleScroll,
    getItemProps,
    visibleItems: items.slice(visibleRange.start, visibleRange.end + 1),
  };
}

export default VirtualScroller;
