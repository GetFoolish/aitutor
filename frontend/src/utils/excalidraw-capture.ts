import { exportToCanvas } from '@excalidraw/excalidraw';

// Using any type for Excalidraw API since the type exports are complex
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ExcalidrawAPI = any;

// Track if a capture is in progress to prevent concurrent captures
let captureInProgress = false;

/**
 * Validates that the Excalidraw API is in a usable state
 */
function isValidApi(api: ExcalidrawAPI): boolean {
  if (!api) return false;

  try {
    // Check if essential methods exist and are callable
    return (
      typeof api.getSceneElements === 'function' &&
      typeof api.getFiles === 'function' &&
      typeof api.getAppState === 'function'
    );
  } catch {
    return false;
  }
}

/**
 * Captures the current Excalidraw scene to a canvas.
 * Returns null if there are no elements to capture or if capture fails.
 */
export async function captureExcalidrawToCanvas(
  api: ExcalidrawAPI,
  width: number = 1280,
  height: number = 720
): Promise<HTMLCanvasElement | null> {
  // Prevent concurrent captures which can cause crashes
  if (captureInProgress) {
    return null;
  }

  // Validate API before using
  if (!isValidApi(api)) {
    return null;
  }

  captureInProgress = true;

  try {
    const elements = api.getSceneElements();

    if (!elements || !Array.isArray(elements)) {
      return null;
    }

    // Check if there are any visible elements to capture
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const visibleElements = elements.filter((el: any) => el && !el.isDeleted);
    if (visibleElements.length === 0) {
      return null;
    }

    const files = api.getFiles() || {};
    const appState = api.getAppState() || {};

    // Export to canvas using Excalidraw's built-in function
    const canvas = await exportToCanvas({
      elements: visibleElements,
      files,
      appState: {
        ...appState,
        exportWithDarkMode: false,
        exportBackground: true,
      },
      exportPadding: 20,
      maxWidthOrHeight: Math.max(width, height),
    });

    if (!canvas || canvas.width === 0 || canvas.height === 0) {
      return null;
    }

    // Resize to target dimensions while maintaining aspect ratio
    const resizedCanvas = document.createElement('canvas');
    resizedCanvas.width = width;
    resizedCanvas.height = height;
    const ctx = resizedCanvas.getContext('2d');

    if (ctx) {
      // Fill with white background
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, width, height);

      // Calculate aspect-ratio-preserving dimensions
      const scale = Math.min(width / canvas.width, height / canvas.height);
      const scaledWidth = canvas.width * scale;
      const scaledHeight = canvas.height * scale;
      const offsetX = (width - scaledWidth) / 2;
      const offsetY = (height - scaledHeight) / 2;

      // Draw centered and scaled
      ctx.drawImage(canvas, offsetX, offsetY, scaledWidth, scaledHeight);
    }

    return resizedCanvas;
  } catch (error) {
    // Silently fail - don't spam console with errors during rapid state changes
    return null;
  } finally {
    captureInProgress = false;
  }
}

/**
 * Checks if the Excalidraw scene has any drawings
 */
export function hasExcalidrawContent(api: ExcalidrawAPI | null): boolean {
  if (!api) return false;

  try {
    const elements = api.getSceneElements();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return elements.some((el: any) => !el.isDeleted);
  } catch {
    return false;
  }
}
