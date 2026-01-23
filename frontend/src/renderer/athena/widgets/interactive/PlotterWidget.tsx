/**
 * Plotter Widget
 *
 * Plot scatter points on a coordinate plane.
 */

import React, { useState, useCallback } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

// Helper to convert LaTeX to plain text for SVG text rendering
// SVG <text> elements can't render HTML/KaTeX, so we convert to readable text
const stripMathDelimiters = (text: string): string => {
  if (!text) return '';
  let result = text.trim();

  // Handle empty math delimiters first (used as spacing markers)
  // $$ alone or $ $ becomes empty string
  if (result === '$$' || result === '$' || result === '$ $') return '';

  // Remove $$...$$ delimiters (display math), keeping the content
  result = result.replace(/\$\$([\s\S]*?)\$\$/g, '$1');
  // Remove $...$ delimiters (inline math), keeping the content
  result = result.replace(/\$([^$]*)\$/g, '$1');

  // If result is now empty or just whitespace, return empty string
  if (!result.trim()) return '';

  // Convert fractions \frac{a}{b} or \dfrac{a}{b} to a/b or mixed number format
  result = result.replace(/\\d?frac\{(\d+)\}\{(\d+)\}/g, (_, num, den) => {
    // For simple fractions, use fraction symbol or slash
    return `${num}/${den}`;
  });

  // Handle mixed numbers like 80\frac{1}{2} -> 80½
  // Common fractions to Unicode
  const fractionMap: Record<string, string> = {
    '1/2': '½', '1/3': '⅓', '2/3': '⅔', '1/4': '¼', '3/4': '¾',
    '1/5': '⅕', '2/5': '⅖', '3/5': '⅗', '4/5': '⅘',
    '1/6': '⅙', '5/6': '⅚', '1/8': '⅛', '3/8': '⅜', '5/8': '⅝', '7/8': '⅞'
  };

  // Replace common fractions with Unicode equivalents
  for (const [frac, unicode] of Object.entries(fractionMap)) {
    result = result.replace(new RegExp(frac.replace('/', '\\/'), 'g'), unicode);
  }

  // Remove common LaTeX commands but keep their arguments
  result = result.replace(/\\text\{([^}]+)\}/g, '$1');
  result = result.replace(/\\textbf\{([^}]+)\}/g, '$1');
  result = result.replace(/\\mathrm\{([^}]+)\}/g, '$1');
  result = result.replace(/\\textit\{([^}]+)\}/g, '$1');

  // Remove remaining backslashes from LaTeX commands
  result = result.replace(/\\[a-zA-Z]+/g, '');

  // Clean up extra spaces and braces
  result = result.replace(/[{}]/g, '');
  result = result.replace(/\s+/g, ' ');

  return result.trim();
};

// Helper to split text for multiline SVG rendering (handles <br> tags)
const splitMultilineLabel = (text: string): string[] => {
  if (!text) return [''];
  // First strip math delimiters
  const cleaned = stripMathDelimiters(text);
  // Split by <br>, <br/>, or <br /> tags
  const lines = cleaned.split(/<br\s*\/?>/gi);
  return lines.map(line => line.trim()).filter(line => line.length > 0);
};

// Helper to extract label from category (handles string or object formats)
const getCategoryLabel = (cat: unknown): string => {
  if (!cat) return '';
  if (typeof cat === 'string') return cat;
  if (typeof cat === 'object') {
    const obj = cat as Record<string, unknown>;
    // Try common property names for labels
    if (typeof obj.content === 'string') return obj.content;
    if (typeof obj.label === 'string') return obj.label;
    if (typeof obj.text === 'string') return obj.text;
    if (typeof obj.name === 'string') return obj.name;
    if (typeof obj.value === 'string') return obj.value;
  }
  return String(cat);
};

interface PlotterOptions {
  range?: [[number, number], [number, number]];
  step?: [number, number];
  starting?: [number, number][] | number[];
  correct?: [number, number][] | number[];
  categories?: string[];
  type?: 'scatter' | 'bar' | 'pic' | 'dotplot';
  picUrl?: string;
  picSize?: number;
  labelInterval?: number;
  scaleY?: number;
  maxY?: number;
  snapsPerLine?: number;
  labels?: string[];  // Axis labels [x-axis label, y-axis label]
  labelText?: string; // Alternate axis label property
  labelX?: string;
  labelY?: string;
}

export interface PlotterWidgetProps extends WidgetProps<PlotterOptions> { }

export function PlotterWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: PlotterWidgetProps) {
  const options = widget.options || {};
  console.log(`[PlotterWidget] Render: ${widgetId}`, { type: options.type, labelX: options.labelX, labelY: options.labelY, range: options.range });

  // Safely extract range with proper validation
  const defaultRange: [[number, number], [number, number]] = [[0, 5], [0, 8]];
  const rawRange = options.range;
  const range: [[number, number], [number, number]] = (
    Array.isArray(rawRange) &&
    rawRange.length >= 2 &&
    Array.isArray(rawRange[0]) &&
    rawRange[0].length >= 2 &&
    Array.isArray(rawRange[1]) &&
    rawRange[1].length >= 2 &&
    typeof rawRange[0][0] === 'number' &&
    typeof rawRange[0][1] === 'number' &&
    typeof rawRange[1][0] === 'number' &&
    typeof rawRange[1][1] === 'number'
  ) ? rawRange as [[number, number], [number, number]] : defaultRange;

  // Determine plot type - dotplot and pictograph take precedence over categories
  const plotType = options.type || 'scatter';
  const isDotPlot = plotType === 'dotplot';
  const isPictograph = plotType === 'pic';
  const isPictogram = isDotPlot || isPictograph;

  // Check if this is a bar chart (categories mode, but NOT dotplot or pictograph)
  // Keep all categories for positioning, but may render some labels as empty
  const categories = options.categories || [];
  // Check if there are any non-empty categories (to determine if it's a bar chart)
  const hasValidCategories = categories.some(cat => {
    if (!cat) return false;
    const label = getCategoryLabel(cat);
    const stripped = stripMathDelimiters(label);
    return stripped.length > 0;
  });
  const isBarChart = categories.length > 0 && !isPictogram;

  // For bar charts, starting values are an array of Y values (one per category)
  const getStartingBarValues = (): number[] => {
    if (!isBarChart) return [];
    if (Array.isArray(value)) return value as number[];
    if (Array.isArray(options.starting)) {
      // Starting could be array of numbers or array of [x,y] points
      if (options.starting.length > 0 && typeof options.starting[0] === 'number') {
        return options.starting as number[];
      }
      // Convert [x, y] points to just y values
      return (options.starting as [number, number][]).map(p => Array.isArray(p) ? p[1] : 0);
    }
    return categories.map(() => 0);
  };

  const [barValues, setBarValues] = useState<number[]>(getStartingBarValues);

  const correctBarValues = isBarChart && Array.isArray(options.correct)
    ? (typeof options.correct[0] === 'number'
      ? options.correct as number[]
      : (options.correct as [number, number][]).map(p => Array.isArray(p) ? p[1] : 0))
    : [];

  // For scatter plots
  const correctPoints = !isBarChart && Array.isArray(options.correct) ? (options.correct as unknown[]).filter(
    (p): p is [number, number] => Array.isArray(p) && p.length >= 2 && typeof p[0] === 'number' && typeof p[1] === 'number'
  ) : [];

  const [points, setPoints] = useState<[number, number][]>(() => {
    if (isBarChart) return [];
    if (Array.isArray(value)) {
      return (value as unknown[]).filter(
        (p): p is [number, number] => Array.isArray(p) && p.length >= 2 && typeof p[0] === 'number' && typeof p[1] === 'number'
      );
    }
    if (Array.isArray(options.starting)) {
      return (options.starting as unknown[]).filter(
        (p): p is [number, number] => Array.isArray(p) && p.length >= 2 && typeof p[0] === 'number' && typeof p[1] === 'number'
      );
    }
    return [];
  });

  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null);
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  const themeStyles = {
    light: { bg: '#fff', grid: '#e5e7eb', axis: '#374151', point: '#3b82f6', correct: '#22c55e', text: '#6b7280' },
    dark: { bg: '#000000', grid: '#374151', axis: '#e5e7eb', point: '#60a5fa', correct: '#4ade80', text: '#9ca3af' },
    'high-contrast': { bg: '#000', grid: '#333', axis: '#fff', point: '#ff0', correct: '#0f0', text: '#fff' },
  }[theme];

  const isDisabled = readOnly || disabled;

  // SVG dimensions
  const width = 500; // Increased width for better title spacing
  const height = 350; // Increased height
  const padding = 60; // Increased padding for titles
  const graphWidth = width - 2 * padding;
  const graphHeight = height - 2 * padding;

  // Scale functions
  const xScale = (x: number) => padding + ((x - range[0][0]) / (range[0][1] - range[0][0])) * graphWidth;
  const yScale = (y: number) => height - padding - ((y - range[1][0]) / (range[1][1] - range[1][0])) * graphHeight;

  // Inverse scale
  const xInverse = (px: number) => range[0][0] + ((px - padding) / graphWidth) * (range[0][1] - range[0][0]);
  const yInverse = (py: number) => range[1][0] + ((height - padding - py) / graphHeight) * (range[1][1] - range[1][0]);

  // Generate grid lines
  const xTicks: number[] = [];
  const yTicks: number[] = [];
  const xStep = options.step?.[0] || 1;
  const yStep = options.step?.[1] || options.scaleY || 1;

  for (let x = range[0][0]; x <= range[0][1]; x = Number((x + xStep).toFixed(10))) xTicks.push(x);
  for (let y = range[1][0]; y <= range[1][1]; y = Number((y + yStep).toFixed(10))) yTicks.push(y);

  const handleClick = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (isDisabled) return;

    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Convert to graph coordinates and snap to grid
    const graphX = Math.round(xInverse(x));
    const graphY = Math.round(yInverse(y));

    // Check if within bounds
    if (graphX < range[0][0] || graphX > range[0][1] || graphY < range[1][0] || graphY > range[1][1]) {
      return;
    }

    // Check if point already exists (toggle off)
    const existingIdx = points.findIndex(p => p[0] === graphX && p[1] === graphY);
    let newPoints: [number, number][];

    if (existingIdx >= 0) {
      newPoints = points.filter((_, i) => i !== existingIdx);
    } else {
      newPoints = [...points, [graphX, graphY]];
    }

    setPoints(newPoints);
    onChange?.(newPoints);
  }, [isDisabled, points, onChange, range]);

  // Bar chart click handler
  const handleBarClick = useCallback((categoryIndex: number, newY: number) => {
    if (isDisabled) return;
    const newValues = [...barValues];
    newValues[categoryIndex] = Math.max(range[1][0], Math.min(range[1][1], newY));
    setBarValues(newValues);
    onChange?.(newValues);
  }, [isDisabled, barValues, onChange, range]);

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!isDragging || dragIndex === null || isDisabled) return;

    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const clickY = e.clientY - rect.top;
    const newY = Math.round(yInverse(clickY));

    handleBarClick(dragIndex, newY);
  }, [isDragging, dragIndex, isDisabled, yInverse, handleBarClick]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragIndex(null);
  }, []);

  // Render bar chart
  if (isBarChart) {
    const barWidth = (graphWidth / categories.length) * 0.6;
    const barGap = (graphWidth / categories.length) * 0.4;
    const maxY = options.maxY || range[1][1];

    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="plotter">
        <div className="athena-plotter" style={{ padding: '16px', backgroundColor: themeStyles.bg, borderRadius: '8px' }}>
          <svg
            width={width}
            height={height + 30}
            style={{ border: `1px solid ${themeStyles.grid}`, borderRadius: '4px' }}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <rect x={0} y={0} width={width} height={height + 30} fill={themeStyles.bg} />

            {/* Y-axis grid lines and labels */}
            {yTicks.map((y) => (
              <g key={`y-${y}`}>
                <line x1={padding} y1={yScale(y)} x2={width - padding} y2={yScale(y)} stroke={themeStyles.grid} strokeWidth={1} />
                <text x={padding - 8} y={yScale(y) + 4} textAnchor="end" fontSize="11" fill={themeStyles.text}>{y}</text>
              </g>
            ))}

            {/* Axes */}
            <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke={themeStyles.axis} strokeWidth={2} />
            <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke={themeStyles.axis} strokeWidth={2} />

            {/* Bars */}
            {categories.map((cat, i) => {
              const barX = padding + i * (graphWidth / categories.length) + barGap / 2;
              const barY = barValues[i] || 0;
              const barHeight = ((barY - range[1][0]) / (maxY - range[1][0])) * graphHeight;
              const isHovered = hoveredBar === i;

              return (
                <g key={`bar-${i}`}>
                  {/* Click area (full height for easier interaction) */}
                  <rect
                    x={barX}
                    y={padding}
                    width={barWidth}
                    height={graphHeight}
                    fill="transparent"
                    style={{ cursor: isDisabled ? 'default' : 'ns-resize' }}
                    onMouseEnter={() => !isDisabled && setHoveredBar(i)}
                    onMouseLeave={() => setHoveredBar(null)}
                    onMouseDown={(e) => {
                      if (isDisabled) return;
                      setIsDragging(true);
                      setDragIndex(i);

                      const rect = e.currentTarget.ownerSVGElement?.getBoundingClientRect();
                      if (rect) {
                        const clickY = e.clientY - rect.top;
                        const newY = Math.round(yInverse(clickY));
                        handleBarClick(i, newY);
                      }
                    }}
                  />
                  {/* Bar */}
                  <rect
                    x={barX}
                    y={height - padding - barHeight}
                    width={barWidth}
                    height={Math.max(barHeight, 0)}
                    fill={isHovered ? '#4ade80' : '#28ae7b'}
                    stroke={isHovered ? '#22c55e' : '#1a7a56'}
                    strokeWidth={isHovered ? 2 : 1}
                    style={{
                      cursor: isDisabled ? 'default' : 'ns-resize',
                      transition: 'all 0.15s ease',
                    }}
                    pointerEvents="none"
                  />
                  {/* Category label (supports multiline with <br>) */}
                  <text
                    x={barX + barWidth / 2}
                    y={height - padding + 16}
                    textAnchor="middle"
                    fontSize="11"
                    fill={isHovered ? themeStyles.axis : themeStyles.text}
                    fontWeight={isHovered ? 600 : 400}
                  >
                    {splitMultilineLabel(getCategoryLabel(cat)).map((line, lineIndex) => (
                      <tspan
                        key={lineIndex}
                        x={barX + barWidth / 2}
                        dy={lineIndex === 0 ? 0 : 12}
                      >
                        {line}
                      </tspan>
                    ))}
                  </text>
                  {/* Value label on bar */}
                  {barY > 0 && (
                    <text
                      x={barX + barWidth / 2}
                      y={height - padding - barHeight - 5}
                      textAnchor="middle"
                      fontSize="11"
                      fontWeight="600"
                      fill={themeStyles.axis}
                    >
                      {barY}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Correct values (review mode) */}
            {reviewMode && correctBarValues.map((correctY, i) => {
              const barX = padding + i * (graphWidth / categories.length) + barGap / 2;
              const correctHeight = ((correctY - range[1][0]) / (maxY - range[1][0])) * graphHeight;
              return (
                <rect
                  key={`correct-${i}`}
                  x={barX}
                  y={height - padding - correctHeight}
                  width={barWidth}
                  height={2}
                  fill="#ef4444"
                />
              );
            })}

            {options.labelX && (
              <text
                x={padding + graphWidth / 2}
                y={height - 5}
                textAnchor="middle"
                fontSize="14"
                fontWeight="700"
                fill={themeStyles.axis}
              >
                {options.labelX}
              </text>
            )}
            {options.labelY && (
              <text
                x={20}
                y={padding + graphHeight / 2}
                textAnchor="middle"
                fontSize="14"
                fontWeight="700"
                fill={themeStyles.axis}
                transform={`rotate(-90, 20, ${padding + graphHeight / 2})`}
              >
                {options.labelY}
              </text>
            )}
          </svg>

          <div style={{ marginTop: '12px', fontSize: '13px', color: themeStyles.text, textAlign: 'center' }}>
            {isDisabled ? 'View the bar chart above' : 'Click on bars to adjust values'}
          </div>
        </div>
      </BaseWidgetWrapper>
    );
  }

  // Render dot plot or pictograph (number line with stackable dots or icons)
  if (isPictogram) {
    const dotRadius = isPictograph ? (options.picSize || 30) / 2 : 10;
    const dotSpacing = isPictograph ? (options.picSize || 34) + 4 : 24;
    const xAxisY = height - padding - 20;

    // For pictogram plots, track how many elements are at each x position
    const dotCounts: Record<number, number> = {};
    points.forEach(([x]) => {
      dotCounts[x] = (dotCounts[x] || 0) + 1;
    });

    // Handle clicking on the number line to add/remove dots
    const handleDotPlotClick = (e: React.MouseEvent<SVGSVGElement>) => {
      if (isDisabled) return;

      const svg = e.currentTarget;
      const rect = svg.getBoundingClientRect();
      const clickX = e.clientX - rect.left;

      // Convert to graph X coordinate and snap to nearest integer
      const graphX = Math.round(xInverse(clickX));

      // Check if within bounds
      if (graphX < range[0][0] || graphX > range[0][1]) return;

      // Add a dot at this x position (y is determined by count)
      const currentCount = dotCounts[graphX] || 0;
      const newPoints: [number, number][] = [...points, [graphX, currentCount + 1]];
      setPoints(newPoints);
      onChange?.(newPoints);
    };

    // Handle clicking on existing dot to remove it
    const handleDotClick = (e: React.MouseEvent, x: number) => {
      if (isDisabled) return;
      e.stopPropagation();

      // Remove the topmost dot at this x position
      const newPoints = [...points];
      for (let i = newPoints.length - 1; i >= 0; i--) {
        if (newPoints[i][0] === x) {
          newPoints.splice(i, 1);
          break;
        }
      }
      setPoints(newPoints);
      onChange?.(newPoints);
    };

    // Calculate x positions for categories or range
    const xPositions = categories.length > 0
      ? categories.map((_, i) => range[0][0] + i)
      : xTicks;

    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="plotter">
        <div className={`athena-plotter ${isDotPlot ? 'athena-dotplot' : 'athena-pictograph'}`} style={{ padding: '16px', backgroundColor: themeStyles.bg, borderRadius: '8px' }}>
          <svg
            width={width}
            height={height}
            style={{ border: `1px solid ${themeStyles.grid}`, borderRadius: '4px', cursor: isDisabled ? 'default' : 'pointer' }}
            onClick={handleDotPlotClick}
          >
            <rect x={0} y={0} width={width} height={height} fill={themeStyles.bg} />

            {/* Number line */}
            <line
              x1={padding}
              y1={xAxisY}
              x2={width - padding}
              y2={xAxisY}
              stroke={themeStyles.axis}
              strokeWidth={2}
            />

            {/* Tick marks and labels */}
            {xPositions.map((x, i) => (
              <g key={`tick-${i}`}>
                <line
                  x1={xScale(x)}
                  y1={xAxisY - 6}
                  x2={xScale(x)}
                  y2={xAxisY + 6}
                  stroke={themeStyles.axis}
                  strokeWidth={2}
                />
                <text
                  x={xScale(x)}
                  y={xAxisY + 22}
                  textAnchor="middle"
                  fontSize="12"
                  fill={themeStyles.text}
                >
                  {categories.length > 0 ? stripMathDelimiters(getCategoryLabel(categories[i])) : x}
                </text>
              </g>
            ))}

            {/* Axis label (from labels array or labelText) */}
            {(options.labels?.[0] || options.labelText) && (
              <text
                x={width / 2}
                y={xAxisY + 45}
                textAnchor="middle"
                fontSize="12"
                fontWeight="500"
                fill={themeStyles.text}
              >
                {stripMathDelimiters(options.labels?.[0] || options.labelText || '')}
              </text>
            )}

            {/* Elements stacked at each x position */}
            {xPositions.map((x) => {
              const count = dotCounts[x] || 0;
              return Array.from({ length: count }).map((_, dotIndex) => {
                const cx = xScale(x);
                const cy = xAxisY - dotSpacing - dotIndex * dotSpacing;

                if (isPictograph && options.picUrl) {
                  return (
                    <image
                      key={`pic-${x}-${dotIndex}`}
                      x={cx - dotRadius}
                      y={cy - dotRadius}
                      width={dotRadius * 2}
                      height={dotRadius * 2}
                      href={options.picUrl}
                      style={{
                        cursor: isDisabled ? 'default' : 'pointer',
                        filter: theme === 'dark' ? 'invert(1) hue-rotate(180deg)' : 'none'
                      }}
                      onClick={(e) => handleDotClick(e, x)}
                    />
                  );
                }

                return (
                  <circle
                    key={`dot-${x}-${dotIndex}`}
                    cx={cx}
                    cy={cy}
                    r={dotRadius}
                    fill={themeStyles.point}
                    stroke="white"
                    strokeWidth={2}
                    style={{ cursor: isDisabled ? 'default' : 'pointer' }}
                    onClick={(e) => handleDotClick(e, x)}
                  />
                );
              });
            })}

            {/* Correct answer indicators (review mode) */}
            {reviewMode && correctPoints.map(([x], i) => {
              const correctCount = correctPoints.filter(p => p[0] === x).length;
              const userCount = dotCounts[x] || 0;
              if (userCount < correctCount) {
                if (isPictograph && options.picUrl) {
                  return (
                    <image
                      key={`correct-${i}`}
                      x={xScale(x) - dotRadius}
                      y={xAxisY - dotSpacing - userCount * dotSpacing - dotRadius}
                      width={dotRadius * 2}
                      height={dotRadius * 2}
                      href={options.picUrl}
                      opacity={0.5}
                      style={{
                        filter: theme === 'dark'
                          ? 'invert(1) hue-rotate(180deg) opacity(0.5) sepia(1) saturate(5) hue-rotate(90deg)'
                          : 'sepia(1) saturate(5) hue-rotate(90deg)'
                      }} // Greenish tint for correct
                    />
                  );
                } else {
                  return (
                    <circle
                      key={`correct-${i}`}
                      cx={xScale(x)}
                      cy={xAxisY - dotSpacing - userCount * dotSpacing}
                      r={dotRadius}
                      fill={themeStyles.correct}
                      opacity={0.5}
                    />
                  );
                }
              }
              return null;
            })}
          </svg>

          <div style={{ marginTop: '12px', fontSize: '13px', color: themeStyles.text, textAlign: 'center' }}>
            {isDisabled ? 'View the dot plot above' : 'Click on the number line to add dots, click a dot to remove it'}
          </div>
        </div>
      </BaseWidgetWrapper>
    );
  }

  // Render scatter plot (original)
  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="plotter">
      <div
        className="athena-plotter"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '16px',
          backgroundColor: themeStyles.bg,
          borderRadius: '8px',
        }}
      >
        <svg
          width={width}
          height={height}
          style={{
            border: `1px solid ${themeStyles.grid}`,
            borderRadius: '4px',
            cursor: isDisabled ? 'default' : 'crosshair',
          }}
          onClick={handleClick}
        >
          {/* Background */}
          <rect x={0} y={0} width={width} height={height} fill={themeStyles.bg} />

          {/* Grid lines */}
          {xTicks.map((x) => (
            <line
              key={`vgrid-${x}`}
              x1={xScale(x)}
              y1={padding}
              x2={xScale(x)}
              y2={height - padding}
              stroke={x === 0 ? themeStyles.axis : themeStyles.grid}
              strokeWidth={x === 0 ? 2 : 1}
            />
          ))}
          {yTicks.map((y) => (
            <line
              key={`hgrid-${y}`}
              x1={padding}
              y1={yScale(y)}
              x2={width - padding}
              y2={yScale(y)}
              stroke={y === 0 ? themeStyles.axis : themeStyles.grid}
              strokeWidth={y === 0 ? 2 : 1}
            />
          ))}

          {/* X-axis labels */}
          {xTicks.map((x) => (
            <text
              key={`xlabel-${x}`}
              x={xScale(x)}
              y={height - padding + 16}
              textAnchor="middle"
              fontSize="10"
              fill={themeStyles.text}
            >
              {x}
            </text>
          ))}

          {/* Y-axis labels */}
          {yTicks.map((y) => (
            <text
              key={`ylabel-${y}`}
              x={padding - 8}
              y={yScale(y) + 4}
              textAnchor="end"
              fontSize="10"
              fill={themeStyles.text}
            >
              {y}
            </text>
          ))}

          {/* Correct points (shown in review mode) */}
          {reviewMode && correctPoints.map(([x, y], i) => (
            <circle
              key={`correct-${i}`}
              cx={xScale(x)}
              cy={yScale(y)}
              r={8}
              fill={themeStyles.correct}
              opacity={0.5}
            />
          ))}

          {/* User points */}
          {points.map(([x, y], i) => {
            const isHovered = hoveredPoint === i;
            return (
              <g key={`point-${i}`}>
                <circle
                  cx={xScale(x)}
                  cy={yScale(y)}
                  r={isHovered ? 12 : 8}
                  fill={isHovered ? '#ef4444' : themeStyles.point}
                  stroke="white"
                  strokeWidth={2}
                  style={{
                    cursor: isDisabled ? 'default' : 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={() => !isDisabled && setHoveredPoint(i)}
                  onMouseLeave={() => setHoveredPoint(null)}
                />
                {/* Tooltip showing coordinates when hovered */}
                {isHovered && (
                  <text
                    x={xScale(x)}
                    y={yScale(y) - 16}
                    textAnchor="middle"
                    fontSize="10"
                    fontWeight="600"
                    fill={themeStyles.axis}
                  >
                    ({x}, {y}) - click to remove
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        <div
          style={{
            marginTop: '12px',
            fontSize: '13px',
            color: themeStyles.text,
            textAlign: 'center',
          }}
        >
          {isDisabled
            ? `${points.length} point(s) plotted`
            : `Click to plot points (${points.length} placed)`}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

export default PlotterWidget;
