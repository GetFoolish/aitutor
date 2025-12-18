/**
 * Interactive Graph Widget
 *
 * A coordinate plane for interactive math problems.
 * Supports:
 * - Point placement
 * - Line drawing
 * - Polygon creation
 * - Circle drawing
 * - Function graphing
 * - Angle measurement
 * - Background images
 */

import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { InteractiveGraphOptions } from '../../core/types';
import { BaseWidgetWrapper } from '../base/BaseWidget';
import { ImageURLMigrator } from '../../migration/ImageURLMigrator';

export interface InteractiveGraphWidgetProps extends WidgetProps<InteractiveGraphOptions> {}

interface Point {
  x: number;
  y: number;
}

interface GraphState {
  points: Point[];
  lines: Array<{ start: Point; end: Point }>;
  selectedPointIndex: number | null;
}

const imageUrlMigrator = new ImageURLMigrator();

export function InteractiveGraphWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: InteractiveGraphWidgetProps) {
  const options = widget.options || {};
  const svgRef = useRef<SVGSVGElement>(null);

  // Graph configuration
  const range = options.range || [[-10, 10], [-10, 10]];
  const [[xMin, xMax], [yMin, yMax]] = range;
  const step = options.step || [1, 1];
  const gridStep = options.gridStep || step;
  const snapStep = options.snapStep || step;
  const graphType = options.graph?.type || 'point';
  const numPoints = options.graph?.numPoints || 1;
  const backgroundImage = options.backgroundImage;

  // Canvas dimensions
  const width = 400;
  const height = 400;
  const padding = 40;

  // Calculate scale
  const xScale = (width - 2 * padding) / (xMax - xMin);
  const yScale = (height - 2 * padding) / (yMax - yMin);

  // Convert graph coordinates to SVG coordinates
  const toSVG = useCallback(
    (point: Point): Point => ({
      x: padding + (point.x - xMin) * xScale,
      y: height - padding - (point.y - yMin) * yScale,
    }),
    [xMin, yMin, xScale, yScale]
  );

  // Convert SVG coordinates to graph coordinates
  const toGraph = useCallback(
    (svgX: number, svgY: number): Point => {
      const x = (svgX - padding) / xScale + xMin;
      const y = (height - padding - svgY) / yScale + yMin;
      return {
        x: Math.round(x / snapStep[0]) * snapStep[0],
        y: Math.round(y / snapStep[1]) * snapStep[1],
      };
    },
    [xMin, yMin, xScale, yScale, snapStep]
  );

  // Initialize state from value
  const getInitialState = (): GraphState => {
    if (value && typeof value === 'object') {
      return value as GraphState;
    }
    return {
      points: [],
      lines: [],
      selectedPointIndex: null,
    };
  };

  const [state, setState] = useState<GraphState>(getInitialState);
  const [isDragging, setIsDragging] = useState(false);

  const isDisabled = readOnly || disabled;

  // Handle click on graph
  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (isDisabled || isDragging) return;

      const svg = svgRef.current;
      if (!svg) return;

      const rect = svg.getBoundingClientRect();
      const svgX = e.clientX - rect.left;
      const svgY = e.clientY - rect.top;
      const graphPoint = toGraph(svgX, svgY);

      // Check if within bounds
      if (graphPoint.x < xMin || graphPoint.x > xMax || graphPoint.y < yMin || graphPoint.y > yMax) {
        return;
      }

      if (graphType === 'point' || graphType === 'polygon') {
        // Add point up to max allowed
        if (state.points.length < numPoints) {
          const newPoints = [...state.points, graphPoint];
          const newState = { ...state, points: newPoints };
          setState(newState);
          onChange?.(newState);
        }
      } else if (graphType === 'linear' || graphType === 'segment') {
        // For lines, we need exactly 2 points
        if (state.points.length < 2) {
          const newPoints = [...state.points, graphPoint];
          const newState = { ...state, points: newPoints };
          setState(newState);
          onChange?.(newState);
        }
      }
    },
    [isDisabled, isDragging, toGraph, graphType, numPoints, state, onChange, xMin, xMax, yMin, yMax]
  );

  // Handle point drag
  const handlePointMouseDown = useCallback(
    (index: number, e: React.MouseEvent) => {
      if (isDisabled) return;
      e.stopPropagation();
      setState((prev) => ({ ...prev, selectedPointIndex: index }));
      setIsDragging(true);
    },
    [isDisabled]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!isDragging || state.selectedPointIndex === null) return;

      const svg = svgRef.current;
      if (!svg) return;

      const rect = svg.getBoundingClientRect();
      const svgX = e.clientX - rect.left;
      const svgY = e.clientY - rect.top;
      const graphPoint = toGraph(svgX, svgY);

      // Clamp to bounds
      const clampedPoint = {
        x: Math.max(xMin, Math.min(xMax, graphPoint.x)),
        y: Math.max(yMin, Math.min(yMax, graphPoint.y)),
      };

      const newPoints = [...state.points];
      newPoints[state.selectedPointIndex] = clampedPoint;
      const newState = { ...state, points: newPoints };
      setState(newState);
      onChange?.(newState);
    },
    [isDragging, state, toGraph, onChange, xMin, xMax, yMin, yMax]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setState((prev) => ({ ...prev, selectedPointIndex: null }));
  }, []);

  // Remove point on right-click or double-click
  const handlePointRemove = useCallback(
    (index: number, e: React.MouseEvent) => {
      if (isDisabled) return;
      e.preventDefault();
      e.stopPropagation();
      const newPoints = state.points.filter((_, i) => i !== index);
      const newState = { ...state, points: newPoints };
      setState(newState);
      onChange?.(newState);
    },
    [isDisabled, state, onChange]
  );

  // Generate grid lines
  const gridLines = useMemo(() => {
    const lines = [];

    // Vertical grid lines
    for (let x = Math.ceil(xMin / gridStep[0]) * gridStep[0]; x <= xMax; x += gridStep[0]) {
      const svgStart = toSVG({ x, y: yMin });
      const svgEnd = toSVG({ x, y: yMax });
      lines.push({
        key: `v-${x}`,
        x1: svgStart.x,
        y1: svgStart.y,
        x2: svgEnd.x,
        y2: svgEnd.y,
        isAxis: x === 0,
      });
    }

    // Horizontal grid lines
    for (let y = Math.ceil(yMin / gridStep[1]) * gridStep[1]; y <= yMax; y += gridStep[1]) {
      const svgStart = toSVG({ x: xMin, y });
      const svgEnd = toSVG({ x: xMax, y });
      lines.push({
        key: `h-${y}`,
        x1: svgStart.x,
        y1: svgStart.y,
        x2: svgEnd.x,
        y2: svgEnd.y,
        isAxis: y === 0,
      });
    }

    return lines;
  }, [xMin, xMax, yMin, yMax, gridStep, toSVG]);

  // Generate axis labels
  const axisLabels = useMemo(() => {
    const labels = [];

    // X-axis labels
    for (let x = Math.ceil(xMin / step[0]) * step[0]; x <= xMax; x += step[0]) {
      if (x !== 0) {
        const pos = toSVG({ x, y: 0 });
        labels.push({ key: `x-${x}`, x: pos.x, y: height - padding + 20, text: x.toString() });
      }
    }

    // Y-axis labels
    for (let y = Math.ceil(yMin / step[1]) * step[1]; y <= yMax; y += step[1]) {
      if (y !== 0) {
        const pos = toSVG({ x: 0, y });
        labels.push({ key: `y-${y}`, x: padding - 20, y: pos.y + 4, text: y.toString() });
      }
    }

    return labels;
  }, [xMin, xMax, yMin, yMax, step, toSVG]);

  // Compute line for linear graph
  const linearLine = useMemo(() => {
    if ((graphType !== 'linear' && graphType !== 'segment') || state.points.length < 2) {
      return null;
    }

    const [p1, p2] = state.points;

    if (graphType === 'segment') {
      return { start: toSVG(p1), end: toSVG(p2) };
    }

    // Extend line to graph edges for linear
    const slope = (p2.y - p1.y) / (p2.x - p1.x);
    const yIntercept = p1.y - slope * p1.x;

    // Find intersection with graph boundaries
    const xAtYMin = (yMin - yIntercept) / slope;
    const xAtYMax = (yMax - yIntercept) / slope;
    const yAtXMin = slope * xMin + yIntercept;
    const yAtXMax = slope * xMax + yIntercept;

    const intersections: Point[] = [];
    if (xAtYMin >= xMin && xAtYMin <= xMax) intersections.push({ x: xAtYMin, y: yMin });
    if (xAtYMax >= xMin && xAtYMax <= xMax) intersections.push({ x: xAtYMax, y: yMax });
    if (yAtXMin >= yMin && yAtXMin <= yMax) intersections.push({ x: xMin, y: yAtXMin });
    if (yAtXMax >= yMin && yAtXMax <= yMax) intersections.push({ x: xMax, y: yAtXMax });

    if (intersections.length >= 2) {
      return { start: toSVG(intersections[0]), end: toSVG(intersections[1]) };
    }

    return { start: toSVG(p1), end: toSVG(p2) };
  }, [graphType, state.points, toSVG, xMin, xMax, yMin, yMax]);

  // Background image URL - apply same URL handling as ImageWidget
  const bgImageUrl = useMemo(() => {
    if (!backgroundImage?.url) return null;

    let url = backgroundImage.url;

    // Handle web+graphie:// URLs
    if (url.startsWith('web+graphie://')) {
      url = imageUrlMigrator.migrateUrl(url);
      // Add .png extension if missing (PNG has labels baked in)
      if (!url.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
        url = url + '.png';
      }
    }
    // Handle CDN URLs without extension
    else if (url.includes('cdn.kastatic.org') || url.includes('ka-perseus') || url.includes('.s3.amazonaws.com/')) {
      if (!url.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
        url = url + '.png';
      }
    }
    // Handle relative URLs
    else if (url.startsWith('/')) {
      const baseUrl = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';
      url = baseUrl + url;
    }

    return url;
  }, [backgroundImage?.url]);

  const themeStyles = {
    light: {
      bg: '#fff',
      grid: '#e0e0e0',
      axis: '#333',
      point: '#2196f3',
      line: '#2196f3',
      text: '#333',
    },
    dark: {
      bg: '#2d2d2d',
      grid: '#4d4d4d',
      axis: '#fff',
      point: '#64b5f6',
      line: '#64b5f6',
      text: '#fff',
    },
    'high-contrast': {
      bg: '#000',
      grid: '#444',
      axis: '#fff',
      point: '#ff0',
      line: '#ff0',
      text: '#fff',
    },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="interactive-graph">
      <div className="athena-graph-container">
        {options.title && (
          <div
            className="athena-graph-title"
            style={{
              marginBottom: '12px',
              fontWeight: 600,
              color: themeStyles.text,
            }}
          >
            {options.title}
          </div>
        )}

        {!isDisabled && (
          <div
            className="athena-graph-instructions"
            style={{
              marginBottom: '12px',
              fontSize: '14px',
              color: '#666',
            }}
          >
            {graphType === 'point' &&
              `Click to place ${numPoints > 1 ? `up to ${numPoints} points` : 'a point'}. Drag to move. Right-click to remove.`}
            {(graphType === 'linear' || graphType === 'segment') &&
              'Click to place two points to define the line.'}
            {graphType === 'polygon' &&
              `Click to place ${numPoints} points to form a polygon.`}
          </div>
        )}

        <svg
          ref={svgRef}
          width={width}
          height={height}
          onClick={handleClick}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{
            backgroundColor: themeStyles.bg,
            border: `1px solid ${themeStyles.grid}`,
            borderRadius: '8px',
            cursor: isDisabled ? 'default' : 'crosshair',
          }}
          aria-label={`Interactive graph. ${state.points.length} points placed.`}
          role="img"
        >
          {/* Background image */}
          {bgImageUrl && (
            <image
              href={bgImageUrl}
              x={padding}
              y={padding}
              width={width - 2 * padding}
              height={height - 2 * padding}
              preserveAspectRatio="xMidYMid meet"
              opacity={0.5}
              crossOrigin="anonymous"
              onError={(e) => {
                // Try fallback: swap .png to .svg or vice versa
                const target = e.currentTarget;
                const currentHref = target.getAttribute('href') || '';
                if (currentHref.endsWith('.png')) {
                  target.setAttribute('href', currentHref.replace('.png', '.svg'));
                } else if (currentHref.endsWith('.svg')) {
                  target.setAttribute('href', currentHref.replace('.svg', '.png'));
                }
              }}
            />
          )}

          {/* Grid lines */}
          {gridLines.map((line) => (
            <line
              key={line.key}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={line.isAxis ? themeStyles.axis : themeStyles.grid}
              strokeWidth={line.isAxis ? 2 : 1}
            />
          ))}

          {/* Axis labels */}
          {axisLabels.map((label) => (
            <text
              key={label.key}
              x={label.x}
              y={label.y}
              textAnchor="middle"
              fontSize="12"
              fill={themeStyles.text}
            >
              {label.text}
            </text>
          ))}

          {/* Linear/segment line */}
          {linearLine && (
            <line
              x1={linearLine.start.x}
              y1={linearLine.start.y}
              x2={linearLine.end.x}
              y2={linearLine.end.y}
              stroke={themeStyles.line}
              strokeWidth={2}
            />
          )}

          {/* Polygon */}
          {graphType === 'polygon' && state.points.length >= 3 && (
            <polygon
              points={state.points.map((p) => `${toSVG(p).x},${toSVG(p).y}`).join(' ')}
              fill={`${themeStyles.line}33`}
              stroke={themeStyles.line}
              strokeWidth={2}
            />
          )}

          {/* Points */}
          {state.points.map((point, index) => {
            const svgPoint = toSVG(point);
            const isSelected = state.selectedPointIndex === index;
            // Get label from options or use alphabet (A, B, C, ...)
            const optionLabels = options.graph?.coords?.map((c: any) => c.label) || [];
            const alphabetLabel = String.fromCharCode(65 + index); // A, B, C...
            const label = optionLabels[index] || alphabetLabel;

            return (
              <g key={index}>
                {/* Larger hit area */}
                <circle
                  cx={svgPoint.x}
                  cy={svgPoint.y}
                  r={15}
                  fill="transparent"
                  cursor={isDisabled ? 'default' : 'move'}
                  onMouseDown={(e) => handlePointMouseDown(index, e)}
                  onContextMenu={(e) => handlePointRemove(index, e)}
                  onDoubleClick={(e) => handlePointRemove(index, e)}
                />
                {/* Visible point */}
                <circle
                  cx={svgPoint.x}
                  cy={svgPoint.y}
                  r={isSelected ? 10 : 8}
                  fill={themeStyles.point}
                  stroke="#fff"
                  strokeWidth={2}
                  style={{ transition: 'r 0.1s ease' }}
                />
                {/* Point label - alphabet (A, B, C...) below the point */}
                <text
                  x={svgPoint.x}
                  y={svgPoint.y + 24}
                  textAnchor="middle"
                  fontSize="14"
                  fontWeight="bold"
                  fill={themeStyles.text}
                >
                  {label}
                </text>
                {/* Coordinate tooltip shown on hover or if showCoordinates option is set */}
                {options.showCoordinates && (
                  <text
                    x={svgPoint.x + 14}
                    y={svgPoint.y - 14}
                    fontSize="11"
                    fill={themeStyles.text}
                    opacity={0.7}
                  >
                    ({point.x}, {point.y})
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Point count */}
        {!isDisabled && (
          <div
            style={{
              marginTop: '8px',
              fontSize: '14px',
              color: '#666',
            }}
          >
            Points: {state.points.length}
            {numPoints > 1 && ` / ${numPoints}`}
          </div>
        )}
      </div>
    </BaseWidgetWrapper>
  );
}

export default InteractiveGraphWidget;
