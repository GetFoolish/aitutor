/**
 * Grapher Widget
 *
 * Graph mathematical functions on a coordinate plane.
 * Users drag control points to define the function.
 * Supports: linear, quadratic, absolute_value, exponential, logarithmic, sinusoid
 */

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';

type FunctionType = 'linear' | 'quadratic' | 'absolute_value' | 'exponential' | 'logarithmic' | 'sinusoid' | 'tangent' | 'square_root';

interface GrapherOptions {
  range?: [[number, number], [number, number]];
  step?: [number, number];
  snapStep?: [number, number];
  graph?: { type: FunctionType };
  correct?: { type: FunctionType; coords: [number, number][] };
  availableTypes?: FunctionType[];
  backgroundImage?: { url: string; width?: number; height?: number };
}

interface Point {
  x: number;
  y: number;
}

// Function model definitions
const functionModels: Record<FunctionType, {
  numPoints: number;
  defaultCoords: (range: [[number, number], [number, number]]) => Point[];
  getPath: (coords: Point[], xMin: number, xMax: number, xScale: (x: number) => number, yScale: (y: number) => number) => string;
  label: string;
}> = {
  linear: {
    numPoints: 2,
    defaultCoords: (range) => [
      { x: range[0][0] + 2, y: 0 },
      { x: range[0][1] - 2, y: 0 }
    ],
    getPath: (coords, xMin, xMax, xScale, yScale) => {
      if (coords.length < 2) return '';
      const [p1, p2] = coords;
      // y = mx + b
      const m = (p2.y - p1.y) / (p2.x - p1.x);
      const b = p1.y - m * p1.x;
      const y1 = m * xMin + b;
      const y2 = m * xMax + b;
      return `M ${xScale(xMin)} ${yScale(y1)} L ${xScale(xMax)} ${yScale(y2)}`;
    },
    label: 'Linear'
  },
  quadratic: {
    numPoints: 3,
    defaultCoords: (range) => [
      { x: 0, y: 0 }, // vertex
      { x: -2, y: 4 },
      { x: 2, y: 4 }
    ],
    getPath: (coords, xMin, xMax, xScale, yScale) => {
      if (coords.length < 3) return '';
      // Use vertex form: y = a(x-h)² + k
      const [vertex, p1, p2] = coords;
      const h = vertex.x;
      const k = vertex.y;
      // Calculate 'a' from one of the other points
      const dx = p1.x - h;
      const dy = p1.y - k;
      const a = dx !== 0 ? dy / (dx * dx) : 1;

      // Generate path points
      const points: string[] = [];
      const step = (xMax - xMin) / 100;
      for (let x = xMin; x <= xMax; x += step) {
        const y = a * Math.pow(x - h, 2) + k;
        if (points.length === 0) {
          points.push(`M ${xScale(x)} ${yScale(y)}`);
        } else {
          points.push(`L ${xScale(x)} ${yScale(y)}`);
        }
      }
      return points.join(' ');
    },
    label: 'Quadratic'
  },
  absolute_value: {
    numPoints: 3,
    defaultCoords: (range) => [
      { x: 0, y: 0 }, // vertex
      { x: -2, y: 2 },
      { x: 2, y: 2 }
    ],
    getPath: (coords, xMin, xMax, xScale, yScale) => {
      if (coords.length < 3) return '';
      const [vertex, p1] = coords;
      const h = vertex.x;
      const k = vertex.y;
      const dx = p1.x - h;
      const dy = p1.y - k;
      const a = dx !== 0 ? dy / Math.abs(dx) : 1;

      const points: string[] = [];
      const step = (xMax - xMin) / 100;
      for (let x = xMin; x <= xMax; x += step) {
        const y = a * Math.abs(x - h) + k;
        if (points.length === 0) {
          points.push(`M ${xScale(x)} ${yScale(y)}`);
        } else {
          points.push(`L ${xScale(x)} ${yScale(y)}`);
        }
      }
      return points.join(' ');
    },
    label: 'Absolute Value'
  },
  exponential: {
    numPoints: 2,
    defaultCoords: (range) => [
      { x: 0, y: 1 },
      { x: 2, y: 4 }
    ],
    getPath: (coords, xMin, xMax, xScale, yScale) => {
      if (coords.length < 2) return '';
      const [p1, p2] = coords;
      // y = a * b^x
      // Use two points to solve for a and b
      const b = Math.pow(p2.y / p1.y, 1 / (p2.x - p1.x));
      const a = p1.y / Math.pow(b, p1.x);

      const points: string[] = [];
      const step = (xMax - xMin) / 100;
      for (let x = xMin; x <= xMax; x += step) {
        const y = a * Math.pow(b, x);
        if (y > -1000 && y < 1000) { // Avoid extreme values
          if (points.length === 0) {
            points.push(`M ${xScale(x)} ${yScale(y)}`);
          } else {
            points.push(`L ${xScale(x)} ${yScale(y)}`);
          }
        }
      }
      return points.join(' ');
    },
    label: 'Exponential'
  },
  logarithmic: {
    numPoints: 2,
    defaultCoords: (range) => [
      { x: 1, y: 0 },
      { x: 3, y: 2 }
    ],
    getPath: (coords, xMin, xMax, xScale, yScale) => {
      if (coords.length < 2) return '';
      const [p1, p2] = coords;
      // y = a * log(x) + b
      const a = (p2.y - p1.y) / (Math.log(p2.x) - Math.log(p1.x));
      const b = p1.y - a * Math.log(p1.x);

      const points: string[] = [];
      const step = (xMax - xMin) / 100;
      for (let x = Math.max(0.01, xMin); x <= xMax; x += step) {
        const y = a * Math.log(x) + b;
        if (y > -1000 && y < 1000) {
          if (points.length === 0) {
            points.push(`M ${xScale(x)} ${yScale(y)}`);
          } else {
            points.push(`L ${xScale(x)} ${yScale(y)}`);
          }
        }
      }
      return points.join(' ');
    },
    label: 'Logarithmic'
  },
  sinusoid: {
    numPoints: 4,
    defaultCoords: (range) => [
      { x: 0, y: 0 }, // midline point
      { x: Math.PI / 2, y: 1 }, // max
      { x: Math.PI, y: 0 }, // midline
      { x: 3 * Math.PI / 2, y: -1 } // min
    ],
    getPath: (coords, xMin, xMax, xScale, yScale) => {
      if (coords.length < 4) return '';
      const [mid1, max, mid2, min] = coords;
      // y = A * sin(B(x - C)) + D
      const D = (max.y + min.y) / 2; // vertical shift
      const A = max.y - D; // amplitude
      const period = 2 * (mid2.x - mid1.x);
      const B = (2 * Math.PI) / period;
      const C = mid1.x;

      const points: string[] = [];
      const step = (xMax - xMin) / 200;
      for (let x = xMin; x <= xMax; x += step) {
        const y = A * Math.sin(B * (x - C)) + D;
        if (points.length === 0) {
          points.push(`M ${xScale(x)} ${yScale(y)}`);
        } else {
          points.push(`L ${xScale(x)} ${yScale(y)}`);
        }
      }
      return points.join(' ');
    },
    label: 'Sinusoid'
  },
  tangent: {
    numPoints: 2,
    defaultCoords: (range) => [
      { x: 0, y: 0 },
      { x: Math.PI / 4, y: 1 }
    ],
    getPath: (coords, xMin, xMax, xScale, yScale) => {
      if (coords.length < 2) return '';
      const [p1, p2] = coords;
      const a = (p2.y - p1.y) / (Math.tan(p2.x) - Math.tan(p1.x));

      const points: string[] = [];
      const step = (xMax - xMin) / 200;
      let lastY: number | null = null;
      for (let x = xMin; x <= xMax; x += step) {
        const y = a * Math.tan(x);
        // Skip asymptotes (large jumps)
        if (lastY !== null && Math.abs(y - lastY) > 20) {
          points.push('');
          lastY = null;
        } else if (y > -50 && y < 50) {
          if (lastY === null || points[points.length - 1] === '') {
            points.push(`M ${xScale(x)} ${yScale(y)}`);
          } else {
            points.push(`L ${xScale(x)} ${yScale(y)}`);
          }
          lastY = y;
        }
      }
      return points.filter(p => p).join(' ');
    },
    label: 'Tangent'
  },
  square_root: {
    numPoints: 2,
    defaultCoords: (range) => [
      { x: 0, y: 0 },
      { x: 4, y: 2 }
    ],
    getPath: (coords, xMin, xMax, xScale, yScale) => {
      if (coords.length < 2) return '';
      const [p1, p2] = coords;
      // y = a * sqrt(x - h) + k
      const h = p1.x;
      const k = p1.y;
      const a = (p2.y - k) / Math.sqrt(p2.x - h);

      const points: string[] = [];
      const step = (xMax - xMin) / 100;
      for (let x = Math.max(h, xMin); x <= xMax; x += step) {
        const y = a * Math.sqrt(x - h) + k;
        if (points.length === 0) {
          points.push(`M ${xScale(x)} ${yScale(y)}`);
        } else {
          points.push(`L ${xScale(x)} ${yScale(y)}`);
        }
      }
      return points.join(' ');
    },
    label: 'Square Root'
  }
};

export interface GrapherWidgetProps extends WidgetProps<GrapherOptions> {}

export function GrapherWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: GrapherWidgetProps) {
  const options = widget.options || {};
  const range = options.range || [[-10, 10], [-10, 10]];
  const [[xMin, xMax], [yMin, yMax]] = range;
  const step = options.step || [1, 1];
  const snapStep = options.snapStep || step;
  const availableTypes = options.availableTypes || [options.graph?.type || 'linear'] as FunctionType[];
  const correctAnswer = options.correct;

  const svgRef = useRef<SVGSVGElement>(null);

  // Initialize state
  const getInitialState = () => {
    if (value && typeof value === 'object' && 'type' in value && 'coords' in value) {
      return value as { type: FunctionType; coords: Point[] };
    }
    const type = availableTypes[0];
    return {
      type,
      coords: functionModels[type]?.defaultCoords(range) || []
    };
  };

  const [graphState, setGraphState] = useState(getInitialState);
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const currentModel = functionModels[graphState.type];
  const isDisabled = readOnly || disabled;

  const themeStyles = {
    light: { bg: '#fff', grid: '#e5e7eb', axis: '#374151', line: '#3b82f6', point: '#2563eb', pointHover: '#1d4ed8', text: '#6b7280', correct: '#22c55e' },
    dark: { bg: '#1f2937', grid: '#374151', axis: '#e5e7eb', line: '#60a5fa', point: '#3b82f6', pointHover: '#2563eb', text: '#9ca3af', correct: '#4ade80' },
    'high-contrast': { bg: '#000', grid: '#333', axis: '#fff', line: '#ff0', point: '#ff0', pointHover: '#ff8c00', text: '#fff', correct: '#0f0' },
  }[theme];

  // SVG dimensions
  const width = 400;
  const height = 400;
  const padding = 40;
  const graphWidth = width - 2 * padding;
  const graphHeight = height - 2 * padding;

  // Scale functions
  const xScale = useCallback((x: number) => padding + ((x - xMin) / (xMax - xMin)) * graphWidth, [xMin, xMax, graphWidth]);
  const yScale = useCallback((y: number) => height - padding - ((y - yMin) / (yMax - yMin)) * graphHeight, [yMin, yMax, graphHeight]);

  // Inverse scale (SVG to graph coordinates)
  const toGraphCoords = useCallback((svgX: number, svgY: number): Point => {
    const x = ((svgX - padding) / graphWidth) * (xMax - xMin) + xMin;
    const y = ((height - padding - svgY) / graphHeight) * (yMax - yMin) + yMin;
    // Snap to grid
    return {
      x: Math.round(x / snapStep[0]) * snapStep[0],
      y: Math.round(y / snapStep[1]) * snapStep[1]
    };
  }, [xMin, xMax, yMin, yMax, graphWidth, graphHeight, snapStep]);

  // Generate grid lines
  const gridLines = useMemo(() => {
    const lines: { key: string; x1: number; y1: number; x2: number; y2: number; isAxis: boolean }[] = [];
    for (let x = Math.ceil(xMin); x <= Math.floor(xMax); x++) {
      lines.push({
        key: `v-${x}`,
        x1: xScale(x), y1: padding,
        x2: xScale(x), y2: height - padding,
        isAxis: x === 0
      });
    }
    for (let y = Math.ceil(yMin); y <= Math.floor(yMax); y++) {
      lines.push({
        key: `h-${y}`,
        x1: padding, y1: yScale(y),
        x2: width - padding, y2: yScale(y),
        isAxis: y === 0
      });
    }
    return lines;
  }, [xMin, xMax, yMin, yMax, xScale, yScale]);

  // Generate axis labels
  const axisLabels = useMemo(() => {
    const labels: { key: string; x: number; y: number; text: string }[] = [];
    for (let x = Math.ceil(xMin); x <= Math.floor(xMax); x++) {
      if (x !== 0) {
        labels.push({ key: `lx-${x}`, x: xScale(x), y: yScale(0) + 16, text: String(x) });
      }
    }
    for (let y = Math.ceil(yMin); y <= Math.floor(yMax); y++) {
      if (y !== 0) {
        labels.push({ key: `ly-${y}`, x: xScale(0) - 8, y: yScale(y) + 4, text: String(y) });
      }
    }
    return labels;
  }, [xMin, xMax, yMin, yMax, xScale, yScale]);

  // Generate function path
  const functionPath = useMemo(() => {
    if (!currentModel || graphState.coords.length < currentModel.numPoints) return '';
    return currentModel.getPath(graphState.coords, xMin, xMax, xScale, yScale);
  }, [currentModel, graphState.coords, xMin, xMax, xScale, yScale]);

  // Generate correct answer path (for review mode)
  const correctPath = useMemo(() => {
    if (!reviewMode || !correctAnswer) return '';
    const model = functionModels[correctAnswer.type];
    if (!model) return '';
    const coords = correctAnswer.coords.map(c => ({ x: c[0], y: c[1] }));
    return model.getPath(coords, xMin, xMax, xScale, yScale);
  }, [reviewMode, correctAnswer, xMin, xMax, xScale, yScale]);

  // Handle point drag
  const handleMouseDown = useCallback((index: number, e: React.MouseEvent) => {
    if (isDisabled) return;
    e.preventDefault();
    setDraggingIndex(index);
  }, [isDisabled]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (draggingIndex === null || !svgRef.current) return;

    const svg = svgRef.current;
    const rect = svg.getBoundingClientRect();
    const svgX = e.clientX - rect.left;
    const svgY = e.clientY - rect.top;
    const newPoint = toGraphCoords(svgX, svgY);

    // Clamp to bounds
    newPoint.x = Math.max(xMin, Math.min(xMax, newPoint.x));
    newPoint.y = Math.max(yMin, Math.min(yMax, newPoint.y));

    const newCoords = [...graphState.coords];
    newCoords[draggingIndex] = newPoint;

    const newState = { ...graphState, coords: newCoords };
    setGraphState(newState);
    onChange?.(newState);
  }, [draggingIndex, toGraphCoords, graphState, xMin, xMax, yMin, yMax, onChange]);

  const handleMouseUp = useCallback(() => {
    setDraggingIndex(null);
  }, []);

  // Handle type change
  const handleTypeChange = useCallback((newType: FunctionType) => {
    if (isDisabled) return;
    const model = functionModels[newType];
    const newState = {
      type: newType,
      coords: model.defaultCoords(range)
    };
    setGraphState(newState);
    onChange?.(newState);
  }, [isDisabled, range, onChange]);

  // Add global mouse handlers
  useEffect(() => {
    if (draggingIndex !== null) {
      const handleGlobalMouseUp = () => setDraggingIndex(null);
      window.addEventListener('mouseup', handleGlobalMouseUp);
      return () => window.removeEventListener('mouseup', handleGlobalMouseUp);
    }
  }, [draggingIndex]);

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="grapher">
      <div
        className="athena-grapher"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '16px',
          backgroundColor: themeStyles.bg,
          borderRadius: '8px',
        }}
      >
        {/* Type selector */}
        {availableTypes.length > 1 && !isDisabled && (
          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
            {availableTypes.map((type) => (
              <button
                key={type}
                onClick={() => handleTypeChange(type)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '4px',
                  border: graphState.type === type ? `2px solid ${themeStyles.line}` : '1px solid #ccc',
                  backgroundColor: graphState.type === type ? themeStyles.line : 'transparent',
                  color: graphState.type === type ? '#fff' : themeStyles.text,
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                {functionModels[type]?.label || type}
              </button>
            ))}
          </div>
        )}

        {/* Graph SVG */}
        <svg
          ref={svgRef}
          width={width}
          height={height}
          style={{
            border: `1px solid ${themeStyles.grid}`,
            borderRadius: '4px',
            cursor: draggingIndex !== null ? 'grabbing' : 'default'
          }}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {/* Background */}
          <rect x={0} y={0} width={width} height={height} fill={themeStyles.bg} />

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
              textAnchor={label.key.startsWith('ly') ? 'end' : 'middle'}
              fontSize="10"
              fill={themeStyles.text}
            >
              {label.text}
            </text>
          ))}

          {/* Correct answer (review mode) */}
          {correctPath && (
            <path
              d={correctPath}
              fill="none"
              stroke={themeStyles.correct}
              strokeWidth={2}
              strokeDasharray="5,5"
              opacity={0.7}
            />
          )}

          {/* Function curve */}
          {functionPath && (
            <path
              d={functionPath}
              fill="none"
              stroke={themeStyles.line}
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Control points */}
          {graphState.coords.map((point, index) => {
            const svgPoint = { x: xScale(point.x), y: yScale(point.y) };
            const isHovered = hoverIndex === index;
            const isDragging = draggingIndex === index;

            return (
              <g key={index}>
                {/* Larger hit area for easier grabbing */}
                <circle
                  cx={svgPoint.x}
                  cy={svgPoint.y}
                  r={20}
                  fill="transparent"
                  style={{ cursor: isDisabled ? 'default' : 'grab' }}
                  onMouseDown={(e) => handleMouseDown(index, e)}
                  onMouseEnter={() => setHoverIndex(index)}
                  onMouseLeave={() => setHoverIndex(null)}
                />
                {/* Visible point */}
                <circle
                  cx={svgPoint.x}
                  cy={svgPoint.y}
                  r={isHovered || isDragging ? 10 : 8}
                  fill={isHovered || isDragging ? themeStyles.pointHover : themeStyles.point}
                  stroke="#fff"
                  strokeWidth={2}
                  style={{
                    transition: 'r 0.1s, fill 0.1s',
                    cursor: isDisabled ? 'default' : 'grab'
                  }}
                />
                {/* Coordinate label */}
                {(isHovered || isDragging) && (
                  <text
                    x={svgPoint.x}
                    y={svgPoint.y - 15}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight="600"
                    fill={themeStyles.text}
                  >
                    ({point.x.toFixed(1)}, {point.y.toFixed(1)})
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Instructions */}
        <div
          style={{
            marginTop: '12px',
            fontSize: '13px',
            color: themeStyles.text,
            textAlign: 'center',
          }}
        >
          {isDisabled
            ? `${currentModel?.label || 'Function'} graph`
            : `Drag the blue points to adjust the ${currentModel?.label?.toLowerCase() || 'function'}`}
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

export default GrapherWidget;
