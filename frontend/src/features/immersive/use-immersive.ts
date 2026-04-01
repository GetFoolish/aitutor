/**
 * useImmersive — fullscreen immersive mode hook.
 *
 * Inspired by OpenMAIC's immersive mode (#195).
 * Fullscreen API + keyboard shortcut + auto-hide controls support.
 */

import { useCallback, useEffect, useState } from 'react';

export function useImmersive() {
  const [immersive, setImmersive] = useState(false);

  const enter = useCallback(async () => {
    try {
      await document.documentElement.requestFullscreen?.();
    } catch {
      // browser may block or not support fullscreen — fall through to CSS mode
    }
    document.documentElement.setAttribute('data-immersive', 'true');
    setImmersive(true);
  }, []);

  const exit = useCallback(async () => {
    if (document.fullscreenElement) {
      try {
        await document.exitFullscreen?.();
      } catch {
        // ignore
      }
    }
    document.documentElement.removeAttribute('data-immersive');
    setImmersive(false);
  }, []);

  const toggle = useCallback(() => {
    if (immersive) {
      exit();
    } else {
      enter();
    }
  }, [immersive, enter, exit]);

  // Keyboard shortcut: I = toggle, Escape already exits fullscreen natively
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'i' || e.key === 'I') {
        // Ignore if typing in an input
        const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
        if (tag === 'input' || tag === 'textarea') return;
        toggle();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggle]);

  // Sync state when user presses Esc to exit fullscreen natively
  useEffect(() => {
    const onFsChange = () => {
      if (!document.fullscreenElement && immersive) {
        document.documentElement.removeAttribute('data-immersive');
        setImmersive(false);
      }
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, [immersive]);

  return { immersive, toggle, enter, exit };
}
