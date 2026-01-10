/**
 * Canny Edge Detection Web Worker
 * Pure JavaScript implementation of Canny edge detection
 * No external dependencies - optimized for performance
 */

/**
 * Convert RGBA ImageData to grayscale
 */
function toGrayscale(imageData: ImageData): Uint8ClampedArray {
  const data = imageData.data;
  const grayscale = new Uint8ClampedArray(imageData.width * imageData.height);

  for (let i = 0; i < data.length; i += 4) {
    // Standard luminosity formula: 0.299*R + 0.587*G + 0.114*B
    grayscale[i / 4] = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
  }

  return grayscale;
}

/**
 * Apply Gaussian blur to reduce noise
 */
function gaussianBlur(data: Uint8ClampedArray, width: number, height: number): Uint8ClampedArray {
  const kernel = [
    [1, 4, 6, 4, 1],
    [4, 16, 24, 16, 4],
    [6, 24, 36, 24, 6],
    [4, 16, 24, 16, 4],
    [1, 4, 6, 4, 1]
  ];
  const factor = 256;
  const result = new Uint8ClampedArray(data.length);

  for (let y = 2; y < height - 2; y++) {
    for (let x = 2; x < width - 2; x++) {
      let sum = 0;
      for (let ky = 0; ky < 5; ky++) {
        for (let kx = 0; kx < 5; kx++) {
          sum += data[(y - 2 + ky) * width + (x - 2 + kx)] * kernel[ky][kx];
        }
      }
      result[y * width + x] = Math.round(sum / factor);
    }
  }

  return result;
}

/**
 * Compute Sobel edges (gradient magnitude and direction)
 */
function sobelEdges(data: Uint8ClampedArray, width: number, height: number) {
  const magnitude = new Float32Array(data.length);
  const direction = new Float32Array(data.length);

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = y * width + x;

      // Sobel kernels
      const gx = -data[(y - 1) * width + (x - 1)] - 2 * data[y * width + (x - 1)] - data[(y + 1) * width + (x - 1)]
                 + data[(y - 1) * width + (x + 1)] + 2 * data[y * width + (x + 1)] + data[(y + 1) * width + (x + 1)];

      const gy = -data[(y - 1) * width + (x - 1)] - 2 * data[(y - 1) * width + x] - data[(y - 1) * width + (x + 1)]
                 + data[(y + 1) * width + (x - 1)] + 2 * data[(y + 1) * width + x] + data[(y + 1) * width + (x + 1)];

      magnitude[idx] = Math.sqrt(gx * gx + gy * gy);
      direction[idx] = Math.atan2(gy, gx);
    }
  }

  return { magnitude, direction };
}

/**
 * Non-maximum suppression
 */
function nonMaxSuppression(magnitude: Float32Array, direction: Float32Array, width: number, height: number): Uint8ClampedArray {
  const result = new Uint8ClampedArray(magnitude.length);

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = y * width + x;
      const angle = direction[idx] * 180 / Math.PI;
      const normalizedAngle = angle < 0 ? angle + 180 : angle;

      let q = 0, r = 0;

      if ((normalizedAngle >= 0 && normalizedAngle < 22.5) || (normalizedAngle >= 157.5 && normalizedAngle <= 180)) {
        q = magnitude[(y) * width + (x + 1)];
        r = magnitude[(y) * width + (x - 1)];
      } else if (normalizedAngle >= 22.5 && normalizedAngle < 67.5) {
        q = magnitude[(y + 1) * width + (x - 1)];
        r = magnitude[(y - 1) * width + (x + 1)];
      } else if (normalizedAngle >= 67.5 && normalizedAngle < 112.5) {
        q = magnitude[(y + 1) * width + (x)];
        r = magnitude[(y - 1) * width + (x)];
      } else {
        q = magnitude[(y - 1) * width + (x - 1)];
        r = magnitude[(y + 1) * width + (x + 1)];
      }

      result[idx] = (magnitude[idx] >= q && magnitude[idx] >= r) ? Math.round(magnitude[idx]) : 0;
    }
  }

  return result;
}

/**
 * Double thresholding and edge tracking
 */
function doubleThreshold(edges: Uint8ClampedArray, lowThreshold: number, highThreshold: number, width: number, height: number): Uint8ClampedArray {
  const result = new Uint8ClampedArray(edges.length);
  const strong = 255;
  const weak = 100;

  // First pass: classify pixels
  for (let i = 0; i < edges.length; i++) {
    if (edges[i] >= highThreshold) {
      result[i] = strong;
    } else if (edges[i] >= lowThreshold) {
      result[i] = weak;
    }
  }

  // Edge tracking by hysteresis
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = y * width + x;
      if (result[idx] === weak) {
        let isConnected = false;
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            if (result[(y + dy) * width + (x + dx)] === strong) {
              isConnected = true;
              break;
            }
          }
          if (isConnected) break;
        }
        result[idx] = isConnected ? strong : 0;
      }
    }
  }

  return result;
}

/**
 * Main Canny edge detection algorithm
 */
function cannyEdgeDetection(imageData: ImageData, lowThreshold: number, highThreshold: number): ImageData {
  const width = imageData.width;
  const height = imageData.height;

  // Step 1: Convert to grayscale
  let gray = toGrayscale(imageData);

  // Step 2: Gaussian blur
  gray = gaussianBlur(gray, width, height);

  // Step 3: Sobel edges
  const { magnitude, direction } = sobelEdges(gray, width, height);

  // Step 4: Non-maximum suppression
  let edges = nonMaxSuppression(magnitude, direction, width, height);

  // Step 5: Double thresholding and edge tracking
  edges = doubleThreshold(edges, lowThreshold, highThreshold, width, height);

  // Convert grayscale edges to RGBA ImageData (white edges on black background)
  const output = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < edges.length; i++) {
    const val = edges[i];
    const idx = i * 4;
    output[idx] = val;     // R
    output[idx + 1] = val; // G
    output[idx + 2] = val; // B
    output[idx + 3] = 255; // A
  }

  return new ImageData(output, width, height);
}

// Web Worker message handler
self.onmessage = (e: MessageEvent) => {
  const { width, height, data, lowThreshold, highThreshold } = e.data;

  try {
    if (!width || !height || !data) {
      throw new Error(`Invalid image data received: width=${width}, height=${height}, data=${!!data}`);
    }

    // Reconstruct ImageData from width, height, and data
    let imageDataArray: Uint8ClampedArray;
    if (data instanceof ArrayBuffer) {
      imageDataArray = new Uint8ClampedArray(data);
    } else if (Array.isArray(data)) {
      imageDataArray = new Uint8ClampedArray(data);
    } else if (data instanceof Uint8ClampedArray) {
      imageDataArray = data;
    } else {
      throw new Error(`Invalid data type: ${typeof data}`);
    }

    const imageData = new ImageData(imageDataArray, width, height);

    // Apply Canny edge detection
    const resultImageData = cannyEdgeDetection(
      imageData,
      lowThreshold || 50,
      highThreshold || 100
    );

    // Use ArrayBuffer for efficient zero-copy transfer
    const resultBuffer = resultImageData.data.buffer.slice(0);

    // Send result with transferable ArrayBuffer for optimal performance
    self.postMessage({
      success: true,
      width: resultImageData.width,
      height: resultImageData.height,
      data: resultBuffer
    }, [resultBuffer]);

  } catch (error: any) {
    console.error('[Canny Worker] Error:', error);
    self.postMessage({
      error: error?.message || 'Unknown error in Canny edge detection',
      success: false
    });
  }
};

