/**
 * Graphie Image Component
 *
 * Renders Khan Academy graphie images with their labels.
 * Graphie images consist of:
 * - Base SVG image: {hash}.svg
 * - Labels data: {hash}-data.json
 *
 * SVGs are loaded inline to ensure text renders with proper fonts.
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';

interface GraphieLabel {
  content: string;
  coordinates: [number, number];
  alignment?: string;
  typesetAsMath?: boolean;
  style?: Record<string, string>;
}

interface GraphieData {
  labels?: GraphieLabel[];
  range?: [[number, number], [number, number]];
}

interface GraphieImageProps {
  /** The graphie URL (web+graphie:// or https://) */
  url: string;
  /** Alt text for accessibility */
  alt?: string;
  /** Additional CSS class */
  className?: string;
  /** Inline styles */
  style?: React.CSSProperties;
}

// Cache for fetched graphie data and SVG content
const graphieDataCache = new Map<string, GraphieData | null>();
const svgCache = new Map<string, string | null>();

// Load KaTeX for math labels
let katex: any = null;
async function ensureKaTeX() {
  if (katex) return katex;
  try {
    const module = await import('katex');
    katex = module.default || module;
    return katex;
  } catch {
    return null;
  }
}

/**
 * Convert a graphie URL to its base URL (without extension)
 */
function getGraphieBaseUrl(url: string): string {
  let baseUrl = url;

  // Handle web+graphie:// protocol
  if (baseUrl.startsWith('web+graphie://')) {
    baseUrl = 'https://' + baseUrl.replace('web+graphie://', '');
  }

  // Remove any existing extension
  baseUrl = baseUrl.replace(/\.(svg|png)$/, '');

  return baseUrl;
}

export function GraphieImage({ url, alt = '', className = '', style }: GraphieImageProps) {
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [pngFallback, setPngFallback] = useState<string | null>(null);
  const [graphieData, setGraphieData] = useState<GraphieData | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  const [usePngForLabels, setUsePngForLabels] = useState(false);
  const [dataFetchComplete, setDataFetchComplete] = useState(false);
  const [svgFetchComplete, setSvgFetchComplete] = useState(false);
  const [svgHasText, setSvgHasText] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const baseUrl = getGraphieBaseUrl(url);

  // Determine whether to use PNG or SVG based on URL patterns
  // Some images (hundred charts, labeled diagrams) work better with PNG which has text baked in
  useEffect(() => {
    // Check if URL suggests this is a labeled/numbered image that works better with PNG
    const lowerUrl = baseUrl.toLowerCase();
    const preferPng = lowerUrl.includes('hundred') ||
                      lowerUrl.includes('chart') ||
                      lowerUrl.includes('grid') ||
                      lowerUrl.includes('table') ||
                      lowerUrl.includes('labeled');

    if (preferPng) {
      console.log('[GraphieImage] URL suggests labeled image, preferring PNG:', baseUrl);
      setUsePngForLabels(true);
      setSvgFetchComplete(true); // Skip SVG fetch
    } else {
      setUsePngForLabels(false);
    }
    // Note: dataFetchComplete is set by the data.json fetch useEffect
  }, [baseUrl]);

  // Fetch SVG content inline to allow text rendering with proper fonts
  useEffect(() => {
    // Skip if we're already preferring PNG
    if (usePngForLabels && svgFetchComplete) {
      return;
    }

    const svgUrl = baseUrl + '.svg';
    const pngUrl = baseUrl + '.png';
    let timeoutId: NodeJS.Timeout;

    // Check cache first
    if (svgCache.has(svgUrl)) {
      const cached = svgCache.get(svgUrl);
      if (cached) {
        // Check if cached SVG has text elements
        const textCount = (cached.match(/<text/g) || []).length;
        if (textCount === 0) {
          console.log('[GraphieImage] Cached SVG has no text, will render labels from data.json');
        }
        // Always use SVG if available - labels will come from data.json
        setSvgContent(cached);
      } else {
        setPngFallback(pngUrl);
      }
      setSvgFetchComplete(true);
      return;
    }

    // Set a timeout to fall back to PNG if SVG takes too long
    timeoutId = setTimeout(() => {
      console.log('[GraphieImage] SVG fetch timed out, falling back to PNG');
      setPngFallback(pngUrl);
      setSvgFetchComplete(true);
    }, 3000); // 3 second timeout

    // Fetch SVG as text to render inline
    fetch(svgUrl, { mode: 'cors' })
      .then(res => {
        if (!res.ok) throw new Error('Not found');
        return res.text();
      })
      .then(svg => {
        clearTimeout(timeoutId);
        console.log('[GraphieImage] Loaded SVG from', svgUrl, 'length:', svg.length);
        // Check if SVG has text elements
        const textCount = (svg.match(/<text/g) || []).length;
        console.log('[GraphieImage] Found', textCount, 'text elements in SVG');
        setSvgHasText(textCount > 0);
        // Extract dimensions from SVG if available
        const widthMatch = svg.match(/width="(\d+)"/);
        const heightMatch = svg.match(/height="(\d+)"/);

        if (widthMatch && heightMatch) {
          setDimensions({ width: parseInt(widthMatch[1]), height: parseInt(heightMatch[1]) });
        }

        // Add a class to the SVG for styling
        let processedSvg = svg.replace(/<svg/, '<svg class="graphie-svg"');

        // Inject comprehensive CSS style block to ensure ALL text is visible
        // IMPORTANT: Scope all selectors to .graphie-svg to avoid affecting other page elements
        const styleBlock = `<style>
          /* Force all text elements to be visible - scoped to SVG only */
          .graphie-svg text, .graphie-svg tspan, .graphie-svg .label, svg[class*="graphie"] [class*="label"] {
            fill: #333 !important;
            fill-opacity: 1 !important;
            font-family: 'Nunito', -apple-system, sans-serif !important;
            visibility: visible !important;
            display: inline !important;
            opacity: 1 !important;
            stroke: none !important;
          }
          /* Override any hiding attributes */
          text[fill="transparent"], tspan[fill="transparent"],
          text[fill="none"], tspan[fill="none"],
          text[fill="white"], tspan[fill="white"],
          text[fill="#fff"], tspan[fill="#fff"],
          text[fill="#ffffff"], tspan[fill="#ffffff"] {
            fill: #333 !important;
          }
          text[style*="opacity"], tspan[style*="opacity"] {
            opacity: 1 !important;
          }
          text[style*="visibility"], tspan[style*="visibility"] {
            visibility: visible !important;
          }
          text[style*="display: none"], tspan[style*="display: none"] {
            display: inline !important;
          }
          /* Ensure text in defs/use elements is visible */
          defs text, defs tspan, use text, use tspan {
            fill: #333 !important;
            fill-opacity: 1 !important;
            visibility: visible !important;
          }
          /* Fix zero fill-opacity */
          text[fill-opacity="0"], tspan[fill-opacity="0"] {
            fill-opacity: 1 !important;
          }
        </style>`;

        // Insert style block after opening svg tag
        processedSvg = processedSvg.replace(/<svg[^>]*>/, (match) => match + styleBlock);

        // Remove/fix inline styles and attributes that hide text elements
        // Handle opacity in various formats
        processedSvg = processedSvg.replace(/<text([^>]*)style="([^"]*?)opacity:\s*0([^"]*?)"/gi, '<text$1style="$2opacity:1$3"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)style="([^"]*?)opacity:\s*0([^"]*?)"/gi, '<tspan$1style="$2opacity:1$3"');

        // Handle fill="transparent" or fill="none"
        processedSvg = processedSvg.replace(/<text([^>]*)fill="(?:transparent|none)"/gi, '<text$1fill="#333"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)fill="(?:transparent|none)"/gi, '<tspan$1fill="#333"');

        // Handle fill-opacity="0"
        processedSvg = processedSvg.replace(/<text([^>]*)fill-opacity="0"/gi, '<text$1fill-opacity="1"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)fill-opacity="0"/gi, '<tspan$1fill-opacity="1"');

        // Handle visibility="hidden"
        processedSvg = processedSvg.replace(/<text([^>]*)visibility="hidden"/gi, '<text$1visibility="visible"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)visibility="hidden"/gi, '<tspan$1visibility="visible"');

        // Handle display="none"
        processedSvg = processedSvg.replace(/<text([^>]*)display="none"/gi, '<text$1display="inline"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)display="none"/gi, '<tspan$1display="inline"');

        // Handle white/invisible fill colors (commonly used to hide text)
        processedSvg = processedSvg.replace(/<text([^>]*)fill="(?:#fff(?:fff)?|white|rgba?\([^)]*,\s*0\))"/gi, '<text$1fill="#333"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)fill="(?:#fff(?:fff)?|white|rgba?\([^)]*,\s*0\))"/gi, '<tspan$1fill="#333"');

        // Handle stroke-opacity that might hide text outlines
        processedSvg = processedSvg.replace(/<text([^>]*)stroke-opacity="0"/gi, '<text$1stroke-opacity="1"');

        // Ensure text elements without fill get a default fill
        processedSvg = processedSvg.replace(/<text(?![^>]*fill=)/gi, '<text fill="#333" ');

        // Also handle text elements that might have empty or zero-value styling
        processedSvg = processedSvg.replace(/(<text[^>]*style=")([^"]*)(font-size:\s*0[^;]*;?)([^"]*")/gi, '$1$2font-size:14px;$4');

        // Remove any class-based hiding (common in graphie SVGs)
        processedSvg = processedSvg.replace(/class="[^"]*hidden[^"]*"/gi, '');

        // Add explicit styling to make sure text is positioned correctly
        // Some graphie SVGs use transforms that might position text outside viewport
        processedSvg = processedSvg.replace(/<svg([^>]*)>/, (match, attrs) => {
          // Ensure SVG has overflow visible
          if (!attrs.includes('overflow')) {
            return `<svg${attrs} style="overflow:visible">`;
          }
          return match;
        });

        console.log('[GraphieImage] Processed SVG, text elements should now be visible');
        svgCache.set(svgUrl, processedSvg);
        setSvgContent(processedSvg);
        setSvgFetchComplete(true);

        // If SVG has no text elements, labels are in data.json which we fetch separately
        // Don't fall back to PNG - we'll render labels from data.json on top of SVG
        if (textCount === 0) {
          console.log('[GraphieImage] SVG has no text elements, will render labels from data.json');
        }
      })
      .catch((err) => {
        clearTimeout(timeoutId);
        // Fallback to PNG
        console.log('[GraphieImage] Failed to load SVG, falling back to PNG:', err);
        svgCache.set(svgUrl, null);
        setPngFallback(pngUrl);
        setSvgFetchComplete(true);
      });

    // Cleanup timeout on unmount
    return () => {
      clearTimeout(timeoutId);
    };
  }, [baseUrl, usePngForLabels, svgFetchComplete]);

  // Load KaTeX for math rendering
  useEffect(() => {
    ensureKaTeX();
  }, []);

  // Fetch labels data from data.json (JSONP format)
  useEffect(() => {
    const dataUrl = baseUrl + '-data.json';

    // Check cache first
    if (graphieDataCache.has(dataUrl)) {
      const cached = graphieDataCache.get(dataUrl);
      if (cached) {
        setGraphieData(cached);
      }
      setDataFetchComplete(true);
      return;
    }

    // Fetch the data.json file
    fetch(dataUrl, { mode: 'cors' })
      .then(res => {
        if (!res.ok) throw new Error('Not found');
        return res.text();
      })
      .then(text => {
        console.log('[GraphieImage] Loaded data.json from', dataUrl);

        // Parse JSONP format: svgDataHASH({...});
        // Extract JSON from inside the parentheses
        const jsonpMatch = text.match(/^[^(]+\((.+)\);?\s*$/s);
        if (jsonpMatch && jsonpMatch[1]) {
          try {
            const data = JSON.parse(jsonpMatch[1]) as GraphieData;
            console.log('[GraphieImage] Parsed graphie data:', {
              labelCount: data.labels?.length || 0,
              range: data.range
            });
            graphieDataCache.set(dataUrl, data);
            setGraphieData(data);
          } catch (parseErr) {
            console.error('[GraphieImage] Failed to parse JSONP data:', parseErr);
            graphieDataCache.set(dataUrl, null);
          }
        } else {
          // Try parsing as plain JSON
          try {
            const data = JSON.parse(text) as GraphieData;
            console.log('[GraphieImage] Parsed as plain JSON:', {
              labelCount: data.labels?.length || 0,
              range: data.range
            });
            graphieDataCache.set(dataUrl, data);
            setGraphieData(data);
          } catch (parseErr) {
            console.error('[GraphieImage] Not valid JSON or JSONP:', text.substring(0, 100));
            graphieDataCache.set(dataUrl, null);
          }
        }
        setDataFetchComplete(true);
      })
      .catch(err => {
        console.log('[GraphieImage] Failed to load data.json:', err);
        graphieDataCache.set(dataUrl, null);
        setDataFetchComplete(true);
      });
  }, [baseUrl]);

  // Post-render: Force all text elements to be visible via DOM manipulation
  useEffect(() => {
    if (!containerRef.current || !svgContent) return;

    // Wait for DOM to update
    requestAnimationFrame(() => {
      const svgWrapper = containerRef.current?.querySelector('.graphie-svg-wrapper');
      if (!svgWrapper) return;

      // Find all text and tspan elements
      const textElements = svgWrapper.querySelectorAll('text, tspan');
      console.log('[GraphieImage] Post-render: found', textElements.length, 'text elements');

      textElements.forEach((el) => {
        const element = el as SVGElement;
        // Force visibility
        element.style.fill = element.style.fill || '#333';
        element.style.fillOpacity = '1';
        element.style.visibility = 'visible';
        element.style.display = 'inline';
        element.style.opacity = '1';

        // Also set attributes directly
        if (!element.getAttribute('fill') || element.getAttribute('fill') === 'none' || element.getAttribute('fill') === 'transparent') {
          element.setAttribute('fill', '#333');
        }
        element.setAttribute('fill-opacity', '1');
      });
    });
  }, [svgContent]);

  // Process label content - convert LaTeX commands to plain text for SVG display
  const processLabelContent = (content: string): string => {
    if (!content) return '';
    let processed = content;

    // Remove \small{} wrapper - just extract the content
    processed = processed.replace(/\\small\{([^}]*)\}/g, '$1');

    // Remove standalone braces {X} -> X
    processed = processed.replace(/\{([^}]*)\}/g, '$1');

    // Remove \text{} wrapper
    processed = processed.replace(/\\text\{([^}]*)\}/g, '$1');

    // Handle \textbf{} - bold text (just extract content for SVG)
    processed = processed.replace(/\\textbf\{([^}]*)\}/g, '$1');

    // Handle \textit{} - italic text
    processed = processed.replace(/\\textit\{([^}]*)\}/g, '$1');

    // Handle common LaTeX symbols
    processed = processed.replace(/\\times/g, '×');
    processed = processed.replace(/\\div/g, '÷');
    processed = processed.replace(/\\pm/g, '±');
    processed = processed.replace(/\\leq/g, '≤');
    processed = processed.replace(/\\geq/g, '≥');
    processed = processed.replace(/\\neq/g, '≠');
    processed = processed.replace(/\\infty/g, '∞');
    processed = processed.replace(/\\cdot/g, '·');

    // Handle LaTeX spacing commands
    processed = processed.replace(/\\,/g, ' ');  // thin space
    processed = processed.replace(/\\;/g, ' ');  // medium space
    processed = processed.replace(/\\!/g, '');   // negative thin space
    processed = processed.replace(/\\ /g, ' ');  // regular space
    processed = processed.replace(/\\quad/g, '  ');  // quad space
    processed = processed.replace(/\\qquad/g, '    ');  // double quad space

    // Remove any remaining backslashes from simple commands
    processed = processed.replace(/\\([a-zA-Z]+)/g, '');

    // Clean up any double spaces
    processed = processed.replace(/\s+/g, ' ').trim();

    return processed;
  };

  // Inject labels directly into SVG content
  const injectLabelsIntoSvg = useCallback((svg: string, labels: GraphieLabel[], range: [[number, number], [number, number]]): string => {
    if (!labels || labels.length === 0) return svg;

    const [xRange, yRange] = range;
    const xMin = xRange[0], xMax = xRange[1];
    const yMin = yRange[0], yMax = yRange[1];

    // Parse SVG dimensions from viewBox or width/height
    const viewBoxMatch = svg.match(/viewBox="([^"]+)"/);
    const widthMatch = svg.match(/width="([^"]+)"/);
    const heightMatch = svg.match(/height="([^"]+)"/);

    let svgWidth = 400, svgHeight = 400;
    if (viewBoxMatch) {
      const parts = viewBoxMatch[1].split(/\s+/);
      svgWidth = parseFloat(parts[2]) || 400;
      svgHeight = parseFloat(parts[3]) || 400;
    } else if (widthMatch && heightMatch) {
      svgWidth = parseFloat(widthMatch[1]) || 400;
      svgHeight = parseFloat(heightMatch[1]) || 400;
    }

    // The graphie range maps directly to the SVG viewBox
    // xRange maps to [0, svgWidth], yRange maps to [svgHeight, 0] (Y inverted)
    // Generate SVG text elements for labels
    const labelElements = labels.map((label, index) => {
      const [x, y] = label.coordinates;

      // Convert graphie coordinates to SVG coordinates
      // X: xMin -> 0, xMax -> svgWidth
      const svgX = ((x - xMin) / (xMax - xMin)) * svgWidth;
      // Y: yMin -> svgHeight, yMax -> 0 (Y is inverted in SVG)
      const svgY = ((yMax - y) / (yMax - yMin)) * svgHeight;

      // Determine text-anchor based on alignment
      let textAnchor = 'middle';
      let dy = '0.35em'; // Vertical centering
      if (label.alignment === 'left') {
        textAnchor = 'start';
      } else if (label.alignment === 'right') {
        textAnchor = 'end';
      } else if (label.alignment === 'above' || label.alignment === 'top') {
        dy = '-0.5em';
      } else if (label.alignment === 'below' || label.alignment === 'bottom') {
        dy = '1.2em';
      }

      // Build style string
      let styleStr = 'font-family: KaTeX_Main, "Times New Roman", serif; font-size: 16px;';
      if (label.style) {
        if (label.style['font-weight']) styleStr += ` font-weight: ${label.style['font-weight']};`;
        if (label.style.transform) styleStr += ` transform-origin: center; transform: ${label.style.transform};`;
      }

      // Process and escape content for SVG
      const processedContent = processLabelContent(label.content);
      const escapedContent = processedContent
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      return `<text x="${svgX}" y="${svgY}" text-anchor="${textAnchor}" dy="${dy}" fill="#333" style="${styleStr}">${escapedContent}</text>`;
    }).join('\n');

    // Insert labels before closing </svg> tag
    return svg.replace('</svg>', `<g class="graphie-labels">${labelElements}</g></svg>`);
  }, []);

  // Get processed SVG with labels
  const processedSvgWithLabels = useMemo(() => {
    if (!svgContent || !graphieData?.labels || graphieData.labels.length === 0) {
      return svgContent;
    }
    const range = graphieData.range || [[-10, 10], [-10, 10]];
    console.log('[GraphieImage] Injecting', graphieData.labels.length, 'labels into SVG');
    return injectLabelsIntoSvg(svgContent, graphieData.labels, range);
  }, [svgContent, graphieData, injectLabelsIntoSvg]);

  return (
    <div
      ref={containerRef}
      className={`graphie-image-container ${className}`}
      style={{
        position: 'relative',
        display: 'block',
        maxWidth: '100%',
        ...style,
      }}
      role="img"
      aria-label={alt}
    >
      {/*
        Decision tree for rendering:
        1. If preferring PNG (for labeled images) -> use PNG directly
        2. If SVG loaded -> render inline SVG
        3. If PNG fallback set -> use PNG
        4. Default to PNG if nothing else works
      */}
      {usePngForLabels ? (
        // Use PNG because labels couldn't be loaded from data.json
        // PNG has labels baked into the image
        <img
          src={baseUrl + '.png'}
          alt={alt}
          className="graphie-image graphie-png-with-labels"
          style={{
            maxWidth: '100%',
            height: 'auto',
            display: 'block',
          }}
          onError={(e) => {
            // If PNG fails too, show SVG as last resort
            console.log('[GraphieImage] PNG failed, falling back to SVG');
            setUsePngForLabels(false);
          }}
        />
      ) : processedSvgWithLabels ? (
        // Render SVG with labels injected from data.json
        <div
          className="graphie-svg-wrapper"
          style={{
            maxWidth: '100%',
            lineHeight: 0,
          }}
          dangerouslySetInnerHTML={{ __html: processedSvgWithLabels }}
        />
      ) : (
        // Default fallback to PNG (better than showing "Loading..." forever)
        <img
          src={pngFallback || baseUrl + '.png'}
          alt={alt}
          className="graphie-image"
          style={{
            maxWidth: '100%',
            height: 'auto',
            display: 'block',
          }}
          onError={(e) => {
            // If PNG fails, try SVG as last resort
            const img = e.target as HTMLImageElement;
            if (img.src.endsWith('.png')) {
              img.src = baseUrl + '.svg';
            }
          }}
        />
      )}

      {/* Labels are now injected directly into the SVG via processedSvgWithLabels */}
    </div>
  );
}

export default GraphieImage;
