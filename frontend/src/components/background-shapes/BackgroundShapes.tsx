/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useEffect, useState } from 'react';
import './BackgroundShapes.scss';

interface ShapeConfig {
  type: 'circle' | 'square' | 'rectangle' | 'triangle';
  color: string;
  size: number;
  x: number;
  y: number;
  width?: number;
  height?: number;
}

// EXTREME NEO-BRUTALISM color palette - BOLD primary colors only
const WEB1_COLORS = [
  '#FF6B6B', // Coral Red
  '#FCD34D', // Bold Yellow
  '#22C55E', // Bold Green
  '#000000', // Pure Black for contrast
];

interface BackgroundShapesProps {
  count?: number; // Number of shapes to generate (default: 15 for login, 45 for landing)
}

const generateRandomShapes = (count: number): ShapeConfig[] => {
  const shapes: ShapeConfig[] = [];
  // EXTREME: Only squares and triangles - no circles for brutal aesthetic
  const shapeTypes: ('circle' | 'square' | 'triangle')[] = [
    'square', 'square', 'triangle' // More squares for brutalism
  ];

  for (let i = 0; i < count; i++) {
    const type = shapeTypes[Math.floor(Math.random() * shapeTypes.length)];
    const color = WEB1_COLORS[Math.floor(Math.random() * WEB1_COLORS.length)];
    // EXTREME: 2-3x LARGER shapes (60-120px)
    const size = Math.floor(Math.random() * 60) + 60;

    // Generate positions that can be partially off-screen for visual interest
    const x = Math.floor(Math.random() * 120) - 10; // -10% to 110%
    const y = Math.floor(Math.random() * 120) - 10; // -10% to 110%

    shapes.push({
      type,
      color,
      size,
      x,
      y,
    });
  }

  return shapes;
};

export default function BackgroundShapes({ count = 15 }: BackgroundShapesProps) {
  const [shapes, setShapes] = useState<ShapeConfig[]>([]);

  useEffect(() => {
    setShapes(generateRandomShapes(count));
  }, [count]);

  const renderShape = (shape: ShapeConfig, index: number) => {
    const strokeColor = '#000000'; // EXTREME: Always black stroke
    const strokeWidth = 5; // EXTREME: Thicker strokes
    const shadowOffset = 4; // Offset shadow

    switch (shape.type) {
      case 'circle':
        // EXTREME: Circles become squares
        return (
          <svg
            key={index}
            width={shape.size + shadowOffset}
            height={shape.size + shadowOffset}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
            }}
          >
            {/* Shadow */}
            <rect
              x={strokeWidth + shadowOffset}
              y={strokeWidth + shadowOffset}
              width={shape.size - strokeWidth * 2}
              height={shape.size - strokeWidth * 2}
              fill="#000"
            />
            {/* Main shape */}
            <rect
              x={strokeWidth}
              y={strokeWidth}
              width={shape.size - strokeWidth * 2}
              height={shape.size - strokeWidth * 2}
              fill={shape.color}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
            />
          </svg>
        );

      case 'square':
        return (
          <svg
            key={index}
            width={shape.size + shadowOffset}
            height={shape.size + shadowOffset}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
            }}
          >
            {/* Shadow */}
            <rect
              x={strokeWidth + shadowOffset}
              y={strokeWidth + shadowOffset}
              width={shape.size - strokeWidth * 2}
              height={shape.size - strokeWidth * 2}
              fill="#000"
            />
            {/* Main shape */}
            <rect
              x={strokeWidth}
              y={strokeWidth}
              width={shape.size - strokeWidth * 2}
              height={shape.size - strokeWidth * 2}
              fill={shape.color}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
            />
          </svg>
        );

      case 'rectangle':
        return (
          <svg
            key={index}
            width={(shape.width || shape.size) + shadowOffset}
            height={(shape.height || shape.size) + shadowOffset}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
            }}
          >
            {/* Shadow */}
            <rect
              x={strokeWidth + shadowOffset}
              y={strokeWidth + shadowOffset}
              width={(shape.width || shape.size) - strokeWidth * 2}
              height={(shape.height || shape.size) - strokeWidth * 2}
              fill="#000"
            />
            {/* Main shape */}
            <rect
              x={strokeWidth}
              y={strokeWidth}
              width={(shape.width || shape.size) - strokeWidth * 2}
              height={(shape.height || shape.size) - strokeWidth * 2}
              fill={shape.color}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
            />
          </svg>
        );

      case 'triangle':
        const triangleSize = shape.size;
        const padding = strokeWidth + 2;
        const points = `
          ${triangleSize / 2},${padding}
          ${triangleSize - padding},${triangleSize - padding}
          ${padding},${triangleSize - padding}
        `;
        const shadowPoints = `
          ${triangleSize / 2 + shadowOffset},${padding + shadowOffset}
          ${triangleSize - padding + shadowOffset},${triangleSize - padding + shadowOffset}
          ${padding + shadowOffset},${triangleSize - padding + shadowOffset}
        `;
        return (
          <svg
            key={index}
            width={shape.size + shadowOffset}
            height={shape.size + shadowOffset}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
            }}
          >
            {/* Shadow */}
            <polygon
              points={shadowPoints}
              fill="#000"
            />
            {/* Main shape */}
            <polygon
              points={points}
              fill={shape.color}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
            />
          </svg>
        );

      default:
        return null;
    }
  };

  return (
    <div className="background-shapes">
      {shapes.map((shape, index) => renderShape(shape, index))}
    </div>
  );
}
