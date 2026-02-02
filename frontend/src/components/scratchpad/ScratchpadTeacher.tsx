/**
 * ScratchpadTeacher - A tldraw-based component for progressive teaching animations
 *
 * This component fetches teaching instructions from the backend API and renders
 * them as animated steps using tldraw. Supports multiple instruction types:
 * write, draw_line, draw_arrow, draw_shape, draw_groups, number_line, etc.
 *
 * Features:
 * - Fetches from /api/scratchpad/generate
 * - Handles all instruction types
 * - Play/Pause/Restart controls
 * - Speed adjustment (0.5x, 1x, 1.5x, 2x)
 * - Loading and error states
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Tldraw, Editor, createShapeId, TLShapeId, toRichText } from 'tldraw';
import 'tldraw/tldraw.css';
import { Button } from '@/components/ui/button';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  SkipBack,
  Loader2,
} from 'lucide-react';
import {
  ScratchpadTeacherProps,
  InstructionSet,
  TeachingStep,
  PlaybackSpeed,
  COLOR_MAP,
  SIZE_MAP,
  isWriteAction,
  isDrawLineAction,
  isDrawArrowAction,
  isDrawShapeAction,
  isDrawGroupsAction,
  isNumberLineAction,
  isFractionBarAction,
  isHighlightAction,
  isEraseAction,
} from './types';

const speedLabels: Record<PlaybackSpeed, string> = {
  0.5: '0.5x',
  1: '1x',
  1.5: '1.5x',
  2: '2x',
};

export const ScratchpadTeacher: React.FC<ScratchpadTeacherProps> = ({
  concept,
  gradeLevel,
  context,
  initialSpeed = 1,
  onComplete,
  onPlay,
  onPause,
  onStep,
  className = '',
  showControls = true,
  loop = false,
  autoPlay = false,
  apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001',
}) => {
  const [editor, setEditor] = useState<Editor | null>(null);
  const [instructionSet, setInstructionSet] = useState<InstructionSet | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<PlaybackSpeed>(initialSpeed);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  
  const animationRef = useRef<number | null>(null);
  const stepTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const createdShapesRef = useRef<Set<TLShapeId>>(new Set());

  // Fetch instructions from API on mount
  useEffect(() => {
    const fetchInstructions = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${apiBaseUrl}/api/scratchpad/generate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            concept,
            grade_level: gradeLevel,
            context,
          }),
        });

        if (!response.ok) {
          throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        const data: InstructionSet = await response.json();
        console.log('[ScratchpadTeacher] Fetched instructions:', data);
        setInstructionSet(data);
      } catch (err) {
        console.error('[ScratchpadTeacher] Failed to fetch instructions:', err);
        setError(err instanceof Error ? err.message : 'Failed to load teaching instructions');
      } finally {
        setIsLoading(false);
      }
    };

    fetchInstructions();
  }, [concept, gradeLevel, context, apiBaseUrl]);

  // Helper to get tldraw color from API color string
  const getColor = (colorStr?: string) => {
    if (!colorStr) return 'black';
    return COLOR_MAP[colorStr.toLowerCase()] || 'black';
  };

  // Helper to get tldraw size from API size string
  const getSize = (sizeStr?: string): 's' | 'm' | 'l' | 'xl' => {
    if (!sizeStr) return 'm';
    return SIZE_MAP[sizeStr.toLowerCase()] || 'm';
  };

  // Execute a single teaching step
  const executeStep = useCallback((step: TeachingStep) => {
    if (!editor) {
      console.warn('[ScratchpadTeacher] Cannot execute step: no editor');
      return;
    }

    console.log('[ScratchpadTeacher] Executing step:', step.action, step);

    const shapeId = createShapeId(`step-${step.step_id}`);
    // All action types now have style property (optional)
    const color = getColor('style' in step ? step.style?.color : undefined);
    const size = getSize('style' in step ? step.style?.size : undefined);

    try {
      if (isWriteAction(step)) {
        // Create text shape
        editor.createShape({
          id: shapeId,
          type: 'text',
          x: step.position.x,
          y: step.position.y,
          props: {
            richText: toRichText(step.text),
            color,
            size,
            font: 'draw',
            textAlign: 'start',
            scale: 1,
          },
        });
        createdShapesRef.current.add(shapeId);

      } else if (isDrawLineAction(step)) {
        // Create line (using arrow without arrowheads)
        editor.createShape({
          id: shapeId,
          type: 'arrow',
          x: 0,
          y: 0,
          props: {
            kind: 'arc',
            color,
            size,
            dash: 'draw',
            start: { x: step.from.x, y: step.from.y },
            end: { x: step.to.x, y: step.to.y },
            arrowheadStart: 'none',
            arrowheadEnd: 'none',
            richText: toRichText(''),
          },
        });
        createdShapesRef.current.add(shapeId);

      } else if (isDrawArrowAction(step)) {
        // Create arrow with arrowheads
        editor.createShape({
          id: shapeId,
          type: 'arrow',
          x: 0,
          y: 0,
          props: {
            kind: 'arc',
            color,
            size,
            dash: 'draw',
            start: { x: step.from.x, y: step.from.y },
            end: { x: step.to.x, y: step.to.y },
            arrowheadStart: 'none',
            arrowheadEnd: 'arrow',
            richText: toRichText(''),
          },
        });
        createdShapesRef.current.add(shapeId);

      } else if (isDrawShapeAction(step)) {
        // Create geometric shape
        const geoType = step.shape === 'rectangle' ? 'rectangle' 
                      : step.shape === 'circle' ? 'oval' 
                      : 'ellipse';
        
        editor.createShape({
          id: shapeId,
          type: 'geo',
          x: step.position.x,
          y: step.position.y,
          props: {
            geo: geoType,
            w: step.width,
            h: step.height,
            color,
            size,
            fill: (step.style?.fill ? 'solid' : 'none') as 'none' | 'semi' | 'solid' | 'pattern',
            dash: 'draw',
            font: 'draw',
          },
        });
        createdShapesRef.current.add(shapeId);

      } else if (isDrawGroupsAction(step)) {
        // Draw grid of objects (emojis/symbols)
        const spacing = 40;
        for (let row = 0; row < step.rows; row++) {
          for (let col = 0; col < step.cols; col++) {
            const itemId = createShapeId(`${shapeId}-${row}-${col}`);
            editor.createShape({
              id: itemId,
              type: 'text',
              x: step.position.x + (col * spacing),
              y: step.position.y + (row * spacing),
              props: {
                richText: toRichText(step.object),
                color,
                size: 'l',
                font: 'draw',
                textAlign: 'start',
                scale: 1,
              },
            });
            createdShapesRef.current.add(itemId);
          }
        }

      } else if (isNumberLineAction(step)) {
        // Draw number line
        const lineLength = (step.end - step.start) * 50;
        const lineId = createShapeId(`${shapeId}-line`);
        
        // Main horizontal line
        editor.createShape({
          id: lineId,
          type: 'arrow',
          x: 0,
          y: 0,
          props: {
            kind: 'arc',
            color,
            size,
            dash: 'solid',
            start: { x: step.position.x, y: step.position.y },
            end: { x: step.position.x + lineLength, y: step.position.y },
            arrowheadStart: 'none',
            arrowheadEnd: 'arrow',
            richText: toRichText(''),
          },
        });
        createdShapesRef.current.add(lineId);

        // Add tick marks and labels
        const numTicks = step.ticks || (step.end - step.start);
        for (let i = 0; i <= numTicks; i++) {
          const tickX = step.position.x + (i / numTicks) * lineLength;
          const tickId = createShapeId(`${shapeId}-tick-${i}`);
          
          // Tick mark
          editor.createShape({
            id: tickId,
            type: 'arrow',
            x: 0,
            y: 0,
            props: {
              kind: 'arc',
              color,
              size: 's',
              dash: 'solid',
              start: { x: tickX, y: step.position.y - 10 },
              end: { x: tickX, y: step.position.y + 10 },
              arrowheadStart: 'none',
              arrowheadEnd: 'none',
              richText: toRichText(''),
            },
          });
          createdShapesRef.current.add(tickId);

          // Label
          const labelValue = step.start + (i / numTicks) * (step.end - step.start);
          if (!step.labels || step.labels.includes(labelValue)) {
            const labelId = createShapeId(`${shapeId}-label-${i}`);
            editor.createShape({
              id: labelId,
              type: 'text',
              x: tickX - 10,
              y: step.position.y + 15,
              props: {
                richText: toRichText(labelValue.toString()),
                color,
                size: 's',
                font: 'draw',
                textAlign: 'start',
                scale: 1,
              },
            });
            createdShapesRef.current.add(labelId);
          }
        }

      } else if (isFractionBarAction(step)) {
        // Draw fraction bar
        const barWidth = 200;
        const barHeight = 40;
        const sectionWidth = barWidth / step.denominator;

        // Draw container rectangle
        const containerId = createShapeId(`${shapeId}-container`);
        editor.createShape({
          id: containerId,
          type: 'geo',
          x: step.position.x,
          y: step.position.y,
          props: {
            geo: 'rectangle',
            w: barWidth,
            h: barHeight,
            color,
            size,
            fill: 'none',
            dash: 'solid',
            font: 'draw',
          },
        });
        createdShapesRef.current.add(containerId);

        // Draw section dividers and fill numerator sections
        for (let i = 0; i < step.denominator; i++) {
          if (i < step.numerator) {
            // Filled section
            const fillId = createShapeId(`${shapeId}-fill-${i}`);
            editor.createShape({
              id: fillId,
              type: 'geo',
              x: step.position.x + (i * sectionWidth),
              y: step.position.y,
              props: {
                geo: 'rectangle',
                w: sectionWidth,
                h: barHeight,
                color,
                size: 's',
                fill: 'solid',
                dash: 'solid',
                font: 'draw',
              },
            });
            createdShapesRef.current.add(fillId);
          }
          
          // Divider line (except after last section)
          if (i < step.denominator - 1) {
            const dividerId = createShapeId(`${shapeId}-divider-${i}`);
            editor.createShape({
              id: dividerId,
              type: 'arrow',
              x: 0,
              y: 0,
              props: {
                kind: 'arc',
                color,
                size: 's',
                dash: 'solid',
                start: { 
                  x: step.position.x + ((i + 1) * sectionWidth), 
                  y: step.position.y 
                },
                end: { 
                  x: step.position.x + ((i + 1) * sectionWidth), 
                  y: step.position.y + barHeight 
                },
                arrowheadStart: 'none',
                arrowheadEnd: 'none',
                richText: toRichText(''),
              },
            });
            createdShapesRef.current.add(dividerId);
          }
        }

      } else if (isHighlightAction(step)) {
        // Create semi-transparent highlight rectangle
        editor.createShape({
          id: shapeId,
          type: 'geo',
          x: step.position.x,
          y: step.position.y,
          props: {
            geo: 'rectangle',
            w: step.width,
            h: step.height,
            color: getColor(step.color),
            size: 's',
            fill: 'semi',
            dash: 'solid',
            font: 'draw',
          },
        });
        createdShapesRef.current.add(shapeId);

      } else if (isEraseAction(step)) {
        // Erase shapes by ID or area
        if (step.target_shape_ids) {
          step.target_shape_ids.forEach(id => {
            const targetId = createShapeId(id);
            try {
              editor.deleteShape(targetId);
              createdShapesRef.current.delete(targetId);
            } catch (e) {
              console.warn('[ScratchpadTeacher] Failed to erase shape:', id, e);
            }
          });
        } else if (step.target_area) {
          // Find and delete shapes in area (simplified implementation)
          const shapes = editor.getCurrentPageShapes();
          shapes.forEach(shape => {
            if (
              shape.x >= step.target_area!.x &&
              shape.x <= step.target_area!.x + step.target_area!.width &&
              shape.y >= step.target_area!.y &&
              shape.y <= step.target_area!.y + step.target_area!.height
            ) {
              try {
                editor.deleteShape(shape.id);
                createdShapesRef.current.delete(shape.id);
              } catch (e) {
                console.warn('[ScratchpadTeacher] Failed to erase shape in area:', shape.id, e);
              }
            }
          });
        }
      }

      console.log('[ScratchpadTeacher] Step executed successfully');
    } catch (err) {
      console.error('[ScratchpadTeacher] Error executing step:', err);
    }
  }, [editor]);

  const clearCanvas = useCallback(() => {
    if (!editor) return;
    
    console.log('[ScratchpadTeacher] Clearing canvas:', createdShapesRef.current.size, 'shapes');
    
    createdShapesRef.current.forEach((shapeId) => {
      try {
        editor.deleteShape(shapeId);
      } catch (e) {
        // Shape might already be deleted
      }
    });
    createdShapesRef.current.clear();
  }, [editor]);

  const resetAnimation = useCallback(() => {
    console.log('[ScratchpadTeacher] resetAnimation called');
    
    if (stepTimeoutRef.current) {
      clearTimeout(stepTimeoutRef.current);
      stepTimeoutRef.current = null;
    }
    
    setIsPlaying(false);
    setIsComplete(false);
    setCurrentStepIndex(0);
    setProgress(0);
    
    clearCanvas();
  }, [clearCanvas]);

  // Schedule next step based on delay_ms and speed multiplier
  const scheduleNextStep = useCallback(() => {
    if (!instructionSet || currentStepIndex >= instructionSet.steps.length) {
      setIsComplete(true);
      setIsPlaying(false);
      setProgress(100);
      if (onComplete) onComplete();
      
      if (loop) {
        setTimeout(() => {
          resetAnimation();
          setIsPlaying(true);
        }, 1000);
      }
      return;
    }

    const step = instructionSet.steps[currentStepIndex];
    const delayMs = step.delay_ms / speed; // Adjust for playback speed

    console.log('[ScratchpadTeacher] Scheduling step', currentStepIndex, 'with delay', delayMs);

    stepTimeoutRef.current = setTimeout(() => {
      executeStep(step);
      
      // Call onStep callback if provided
      if (onStep) {
        onStep(step, currentStepIndex);
      }

      // Update progress
      const newProgress = ((currentStepIndex + 1) / instructionSet.steps.length) * 100;
      setProgress(newProgress);
      
      // Move to next step
      setCurrentStepIndex(prev => prev + 1);
    }, delayMs);
  }, [instructionSet, currentStepIndex, speed, executeStep, onStep, onComplete, loop, resetAnimation]);

  // Animation loop - schedule steps when playing
  useEffect(() => {
    if (isPlaying && !isComplete && instructionSet) {
      scheduleNextStep();
    }

    return () => {
      if (stepTimeoutRef.current) {
        clearTimeout(stepTimeoutRef.current);
        stepTimeoutRef.current = null;
      }
    };
  }, [isPlaying, isComplete, instructionSet, currentStepIndex, scheduleNextStep]);

  // Auto-play on mount if enabled and instructions loaded
  useEffect(() => {
    if (autoPlay && instructionSet && editor && !isLoading) {
      setIsPlaying(true);
      if (onPlay) onPlay();
    }
  }, [autoPlay, instructionSet, editor, isLoading, onPlay]);

  const handlePlay = () => {
    if (isComplete) {
      resetAnimation();
    }
    setIsPlaying(true);
    if (onPlay) onPlay();
  };

  const handlePause = () => {
    setIsPlaying(false);
    if (onPause) onPause();
  };

  const handleRestart = () => {
    resetAnimation();
    setIsPlaying(true);
    if (onPlay) onPlay();
  };

  const handleSpeedChange = (newSpeed: PlaybackSpeed) => {
    setSpeed(newSpeed);
  };

  const speeds: PlaybackSpeed[] = [0.5, 1, 1.5, 2];

  // Loading state
  if (isLoading) {
    return (
      <div className={`flex flex-col items-center justify-center gap-4 p-8 ${className}`}>
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading teaching instructions...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`flex flex-col items-center justify-center gap-4 p-8 ${className}`}>
        <div className="text-red-500 text-center">
          <p className="font-semibold mb-2">Failed to load instructions</p>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
        <Button 
          variant="outline" 
          onClick={() => window.location.reload()}
        >
          Retry
        </Button>
      </div>
    );
  }

  // No instructions
  if (!instructionSet) {
    return (
      <div className={`flex flex-col items-center justify-center gap-4 p-8 ${className}`}>
        <p className="text-sm text-muted-foreground">No teaching instructions available</p>
      </div>
    );
  }

  const title = `Teaching: ${concept} (${gradeLevel})`;

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {/* Title Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-card border border-border rounded-lg">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            Step {currentStepIndex}/{instructionSet.steps.length}
          </span>
          <span className="text-sm text-muted-foreground">
            {isComplete ? 'Complete' : isPlaying ? 'Playing' : 'Paused'}
          </span>
          <div 
            className={`w-2 h-2 rounded-full ${
              isComplete ? 'bg-green-500' : isPlaying ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'
            }`} 
          />
        </div>
      </div>

      {/* Canvas Container */}
      <div className="relative w-full h-[500px] border border-border rounded-lg overflow-hidden bg-white">
        <Tldraw
          onMount={(mountedEditor) => {
            console.log('[ScratchpadTeacher] Tldraw mounted');
            setEditor(mountedEditor);
          }}
        />
        
        {/* Progress Overlay */}
        <div className="absolute bottom-4 left-4 right-4 h-1 bg-muted rounded-full overflow-hidden">
          <div 
            className="h-full bg-primary transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Controls Bar */}
      {showControls && (
        <div className="flex items-center justify-between px-4 py-3 bg-card border border-border rounded-lg">
          {/* Playback Controls */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={handleRestart}
              title="Restart"
              className="h-10 w-10"
              disabled={isLoading}
            >
              <SkipBack className="h-4 w-4" />
            </Button>
            
            {isPlaying ? (
              <Button
                variant="default"
                size="icon"
                onClick={handlePause}
                title="Pause"
                className="h-12 w-12"
                disabled={isLoading}
              >
                <Pause className="h-5 w-5" />
              </Button>
            ) : (
              <Button
                variant="default"
                size="icon"
                onClick={handlePlay}
                title={isComplete ? 'Play Again' : 'Play'}
                className="h-12 w-12"
                disabled={isLoading}
              >
                <Play className="h-5 w-5 ml-0.5" />
              </Button>
            )}
            
            <Button
              variant="outline"
              size="icon"
              onClick={() => {
                resetAnimation();
                setIsPlaying(false);
              }}
              title="Reset"
              className="h-10 w-10"
              disabled={isLoading}
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>

          {/* Speed Controls */}
          <div className="flex items-center gap-3">
            <FastForward className="h-4 w-4 text-muted-foreground" />
            <div className="flex items-center gap-1">
              {speeds.map((s) => (
                <Button
                  key={s}
                  variant={speed === s ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => handleSpeedChange(s)}
                  disabled={isLoading}
                  className={`h-8 px-3 text-xs font-medium transition-all ${
                    speed === s 
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {speedLabels[s]}
                </Button>
              ))}
            </div>
          </div>

          {/* Progress Text */}
          <div className="text-sm text-muted-foreground min-w-[80px] text-right">
            {Math.round(progress)}%
          </div>
        </div>
      )}

      {/* Help Text */}
      <p className="text-xs text-muted-foreground text-center px-4">
        Watch as {concept} is explained step-by-step. Use the controls to play, pause, or adjust speed.
      </p>
    </div>
  );
};

export default ScratchpadTeacher;
