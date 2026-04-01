/**
 * useSpotlight — state hook for spotlight and laser pointer modes.
 *
 * Inspired by OpenMAIC's slide spotlight and laser pointer animations.
 */

import { useCallback, useState } from 'react';

export interface SpotlightPosition {
  x: number; // 0..1 relative to container width
  y: number; // 0..1 relative to container height
}

export function useSpotlight() {
  const [spotlightActive, setSpotlightActive] = useState(false);
  const [laserActive, setLaserActive] = useState(false);
  const [position, setPosition] = useState<SpotlightPosition>({ x: 0.5, y: 0.5 });

  const toggleSpotlight = useCallback(() => {
    setSpotlightActive((prev) => {
      if (!prev) setLaserActive(false); // mutually exclusive
      return !prev;
    });
  }, []);

  const toggleLaser = useCallback(() => {
    setLaserActive((prev) => {
      if (!prev) setSpotlightActive(false); // mutually exclusive
      return !prev;
    });
  }, []);

  const deactivate = useCallback(() => {
    setSpotlightActive(false);
    setLaserActive(false);
  }, []);

  return {
    spotlightActive,
    laserActive,
    position,
    setPosition,
    toggleSpotlight,
    toggleLaser,
    deactivate,
  };
}
