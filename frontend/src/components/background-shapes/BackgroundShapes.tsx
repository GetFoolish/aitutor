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

// Web 1.0 Neo-brutalist color palette - high saturation primary colors
const WEB1_COLORS = [
  '#FF6B6B', // Hot Red - like unmixed paint
  '#FFD93D', // Vivid Yellow - like highlighter markers
  '#C4B5FD', // Soft Violet - gentle yet vibrant
];

interface BackgroundShapesProps {
  count?: number; // Number of shapes to generate (default: 15 for login, 45 for landing)
}

const generateRandomShapes = (count: number): ShapeConfig[] => {
  const shapes: ShapeConfig[] = [];
  const shapeTypes: ('circle' | 'square' | 'triangle')[] = [
    'circle', 'square', 'triangle'
  ];

  for (let i = 0; i < count; i++) {
    const type = shapeTypes[Math.floor(Math.random() * shapeTypes.length)];
    const color = WEB1_COLORS[Math.floor(Math.random() * WEB1_COLORS.length)];
    const size = Math.floor(Math.random() * 29) + 29; // 29-58px (20% bigger than before)

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
    const strokeColor = 'currentColor'; // Will inherit from parent (black in light mode, white in dark)
    const strokeWidth = 3;

    switch (shape.type) {
      case 'circle':
        return (
          <svg
            key={index}
            width={shape.size}
            height={shape.size}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
            }}
          >
            <circle
              cx={shape.size / 2}
              cy={shape.size / 2}
              r={(shape.size / 2) - (strokeWidth + 2)}
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
            width={shape.size}
            height={shape.size}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
            }}
          >
            <rect
              x={strokeWidth + 2}
              y={strokeWidth + 2}
              width={shape.size - (strokeWidth + 2) * 2}
              height={shape.size - (strokeWidth + 2) * 2}
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
            width={shape.width}
            height={shape.height}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
            }}
          >
            <rect
              x={strokeWidth + 2}
              y={strokeWidth + 2}
              width={(shape.width || shape.size) - (strokeWidth + 2) * 2}
              height={(shape.height || shape.size) - (strokeWidth + 2) * 2}
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
        return (
          <svg
            key={index}
            width={shape.size}
            height={shape.size}
            style={{
              position: 'absolute',
              left: `${shape.x}%`,
              top: `${shape.y}%`,
            }}
          >
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
