/**
 * SpotlightOverlay
 *
 * Renders a full-page overlay with two modes:
 * - Spotlight: dims the page with a circular focus area the user can move
 * - Laser pointer: animated red dot that follows the mouse
 *
 * Inspired by OpenMAIC's slide spotlight and laser pointer animations.
 */

import { useCallback, useEffect, useRef } from 'react';
import './spotlight.scss';
import type { SpotlightPosition } from './use-spotlight';

const SPOTLIGHT_RADIUS_PX = 140;

interface SpotlightOverlayProps {
  spotlightActive: boolean;
  laserActive: boolean;
  position: SpotlightPosition;
  onPositionChange: (pos: SpotlightPosition) => void;
}

export default function SpotlightOverlay({
  spotlightActive,
  laserActive,
  position,
  onPositionChange,
}: SpotlightOverlayProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const laserRef = useRef<HTMLDivElement>(null);

  const resolvePosition = useCallback(
    (clientX: number, clientY: number): SpotlightPosition => ({
      x: clientX / window.innerWidth,
      y: clientY / window.innerHeight,
    }),
    [],
  );

  // Update position on mouse/touch move
  const handleMove = useCallback(
    (e: MouseEvent | TouchEvent) => {
      const { clientX, clientY } =
        'touches' in e ? e.touches[0] : (e as MouseEvent);

      if (laserActive && laserRef.current) {
        laserRef.current.style.left = `${clientX}px`;
        laserRef.current.style.top = `${clientY}px`;
      }

      if (spotlightActive) {
        onPositionChange(resolvePosition(clientX, clientY));
      }
    },
    [spotlightActive, laserActive, resolvePosition, onPositionChange],
  );

  // Click to place spotlight
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      if (spotlightActive) {
        onPositionChange(resolvePosition(e.clientX, e.clientY));
      }
    },
    [spotlightActive, resolvePosition, onPositionChange],
  );

  useEffect(() => {
    if (!spotlightActive && !laserActive) return;
    window.addEventListener('mousemove', handleMove as EventListener);
    window.addEventListener('touchmove', handleMove as EventListener, { passive: true });
    return () => {
      window.removeEventListener('mousemove', handleMove as EventListener);
      window.removeEventListener('touchmove', handleMove as EventListener);
    };
  }, [spotlightActive, laserActive, handleMove]);

  if (!spotlightActive && !laserActive) return null;

  const cx = position.x * 100;
  const cy = position.y * 100;
  // Approximate vw-based radius for the CSS gradient
  const rPct = (SPOTLIGHT_RADIUS_PX / Math.min(window.innerWidth, window.innerHeight)) * 100;

  return (
    <div
      ref={overlayRef}
      className={`spotlight-overlay${spotlightActive ? ' spotlight-active' : ''}${laserActive ? ' laser-active' : ''}`}
      onClick={handleClick}
    >
      {spotlightActive && (
        <div
          className="spotlight-mask"
          style={{
            background: `radial-gradient(circle ${SPOTLIGHT_RADIUS_PX}px at ${cx}% ${cy}%, transparent 0%, transparent 60%, rgba(0,0,0,0.65) 100%)`,
          }}
        />
      )}
      {laserActive && (
        <div
          ref={laserRef}
          className="laser-dot"
          style={{
            left: `${position.x * 100}%`,
            top: `${position.y * 100}%`,
          }}
        />
      )}
    </div>
  );
}
