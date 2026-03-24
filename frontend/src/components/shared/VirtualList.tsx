"use client";

import { useRef, useState, useEffect, useCallback, type ReactNode } from "react";

/**
 * Lightweight virtual list component that only renders items visible in the
 * viewport plus a small overscan buffer. Avoids adding a dependency on
 * react-window or @tanstack/react-virtual for this single use case.
 *
 * Usage:
 *   <VirtualList
 *     items={tasks}
 *     itemHeight={56}
 *     overscan={5}
 *     renderItem={(task, index) => <TaskRow key={task.id} task={task} />}
 *   />
 */

interface VirtualListProps<T> {
  items: T[];
  /**
   * Fixed height per item in pixels. MUST be a constant value — all items
   * are assumed to have this exact height. Variable-height items (e.g., rows
   * with multi-line text) will overlap or leave gaps. Use a real virtualization
   * library (react-window, @tanstack/react-virtual) if item heights vary.
   */
  itemHeight: number;
  /** Number of extra items to render above/below viewport */
  overscan?: number;
  /** Max height of the scrollable container. Defaults to 600px. */
  maxHeight?: number;
  /** Render a single item */
  renderItem: (item: T, index: number) => ReactNode;
  /** Optional className for the outer container */
  className?: string;
}

export function VirtualList<T>({
  items,
  itemHeight,
  overscan = 5,
  maxHeight = 600,
  renderItem,
  className,
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const totalHeight = items.length * itemHeight;

  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  const visibleCount = Math.ceil(maxHeight / itemHeight);
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(
    items.length,
    Math.floor(scrollTop / itemHeight) + visibleCount + overscan,
  );

  const visibleItems = items.slice(startIndex, endIndex);

  // If list is small enough, don't virtualize
  if (items.length * itemHeight <= maxHeight) {
    return (
      <div className={className}>
        {items.map((item, index) => renderItem(item, index))}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        maxHeight,
        overflow: "auto",
        position: "relative",
      }}
    >
      {/* Spacer to maintain scroll height */}
      <div style={{ height: totalHeight, position: "relative" }}>
        {/* Positioned items */}
        <div
          style={{
            position: "absolute",
            top: startIndex * itemHeight,
            left: 0,
            right: 0,
          }}
        >
          {visibleItems.map((item, i) => renderItem(item, startIndex + i))}
        </div>
      </div>
    </div>
  );
}

/**
 * Pagination hook for large lists — provides "load more" functionality
 * without requiring server-side cursor pagination.
 */
export function useClientPagination<T>(items: T[], pageSize: number = 50) {
  const [visibleCount, setVisibleCount] = useState(pageSize);

  const visibleItems = items.slice(0, visibleCount);
  const hasMore = visibleCount < items.length;
  const remainingCount = items.length - visibleCount;

  const loadMore = useCallback(() => {
    setVisibleCount((prev) => Math.min(prev + pageSize, items.length));
  }, [items.length, pageSize]);

  // Reset when the items array reference changes (e.g., new filter applied).
  // Depending on items.length alone would miss cases where the count stays
  // the same but the contents change (different filter producing same N results).
  useEffect(() => {
    setVisibleCount(pageSize);
  }, [items, pageSize]);

  return { visibleItems, hasMore, remainingCount, loadMore };
}
