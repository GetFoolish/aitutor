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
import AthenaContext from '../../AthenaContext';

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

/**
 * Restructures the SVG for the voting graph to move legend squares to a side-by-side layout
 * and adds padding to prevent overlaps.
 */
function restructureSvgForVotingGraph(svg: string): string {
  try {
    console.log('[GraphieImage] restructureSvgForVotingGraph CALLED for SVG length:', svg.length);
    const parser = new DOMParser();
    const doc = parser.parseFromString(svg, 'image/svg+xml');
    const svgEl = doc.querySelector('svg');
    if (!svgEl) {
      console.error('[GraphieImage] RESTRUCTURE FAILED: No SVG element found');
      return svg;
    }

    const viewBox = svgEl.getAttribute('viewBox');
    console.log('[GraphieImage] Original ViewBox:', viewBox);
    let svgWidth = 400;
    let svgHeight = 400;

    if (viewBox) {
      const parts = viewBox.split(/[\s,]+/);
      svgWidth = parseFloat(parts[2]) || 400;
      svgHeight = parseFloat(parts[3]) || 400;
    }

    // --- EXPAND CANVAS ---
    const topPadding = 180;    // Area for title (increased for clearance)
    const bottomPadding = 200; // Room for X-axis label and legend footer
    const leftPadding = 60;    // Add left padding for Y-axis label

    const newHeight = svgHeight + topPadding + bottomPadding;
    const newWidth = svgWidth + leftPadding;

    // Update SVG attributes
    svgEl.setAttribute('viewBox', `0 0 ${newWidth} ${newHeight}`);
    svgEl.setAttribute('data-original-height', svgHeight.toString());
    svgEl.setAttribute('data-restructured', 'true');
    // Ensure it takes full width
    svgEl.setAttribute('width', '100%');
    svgEl.removeAttribute('height');

    // --- MOVE GRAPH CONTENT ---
    // Wrap EVERYTHING that was in the SVG into a translation group
    const g = doc.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('transform', `translate(${leftPadding}, ${topPadding})`);
    g.setAttribute('class', 'graph-content-transformed');

    while (svgEl.firstChild) {
      g.appendChild(svgEl.firstChild);
    }
    svgEl.appendChild(g);

    // --- REPOSITION LEGEND BOXES (RECTS AND PATHS) ---
    const boxes = Array.from(g.querySelectorAll('rect, path'));
    const barCenter = svgWidth / 2;
    // legendTopY relative to the transformed group
    const legendTopY = svgHeight + 68; // Aligned with the text labels

    boxes.forEach(box => {
      const fill = box.getAttribute('fill') || '';
      const isGrey = fill === '#b3b3b3' || fill.includes('ccc') || fill === 'gray';
      const isBlack = fill === '#1a1a1a' || fill === 'black' || fill === '#000';

      if (isGrey || isBlack) {
        let bbox = { x: 0, y: 0, width: 0, height: 0 };
        if (box.tagName.toLowerCase() === 'rect') {
          bbox = {
            x: parseFloat(box.getAttribute('x') || '0'),
            y: parseFloat(box.getAttribute('y') || '0'),
            width: parseFloat(box.getAttribute('width') || '0'),
            height: parseFloat(box.getAttribute('height') || '0')
          };
        } else {
          // For paths, extract typical legend y from the path data or use known ones
          const d = box.getAttribute('d') || '';
          const match = d.match(/M\s*([\d.]+)\s+([\d.]+)/);
          if (match) {
            bbox = { x: parseFloat(match[1]), y: parseFloat(match[2]), width: 15, height: 15 };
          }
        }

        // CRITICAL: Only move it if it's below the main graph area (y > svgHeight - 50)
        // This prevents moving the actual data bars!
        if (bbox.y > svgHeight - 80) {
          // Vertical Stack: Grey on top, Black below
          // Align very close to the text (text is at barCenter + 15)
          let newX = barCenter - 5;
          let newY = legendTopY;

          if (isBlack) {
            newY += 25; // Stack below grey
          }

          const dx = newX - bbox.x;
          const dy = newY - bbox.y;

          if (box.tagName.toLowerCase() === 'rect') {
            box.setAttribute('x', newX.toString());
            box.setAttribute('y', newY.toString());
          } else {
            box.setAttribute('transform', `translate(${dx}, ${dy})`);
          }
        }
      }
    });

    console.log('[GraphieImage] RESTRUCTURE SUCCESS! New dimensions:', newWidth, newHeight);
    return new XMLSerializer().serializeToString(doc);
  } catch (err) {
    console.error('[GraphieImage] Error restructuring SVG:', err);
    return svg;
  }
}

export function GraphieImage({ url, alt = '', className = '', style }: GraphieImageProps) {
  // Get global context safely (returns null if not in provider)
  const athenaContext = React.useContext(AthenaContext);
  // Safe access to viewMode
  const viewMode = athenaContext?.state?.viewMode || 'athena';

  // STANDALONE Dark Mode Detection (works without ThemeProvider)
  // We use state only for the standalone detection fallback
  const [standaloneIsDarkMode, setStandaloneIsDarkMode] = useState(false);

  // EFFECT: Handle standalone detection (listeners)
  // Only runs once on mount to set up listeners for fallback cases
  useEffect(() => {
    const checkStandaloneDarkMode = () => {
      // 1. Check localStorage first (user preference)
      const storedTheme = localStorage.getItem('ai-tutor-theme');

      // 2. Check if HTML has dark class (ThemeProvider active)
      const htmlHasDark = document.documentElement.classList.contains('dark');

      // 3. Check system preference
      const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

      // 4. Determine if dark mode should be active
      let isDark = false;

      if (storedTheme === 'dark') {
        isDark = true;
      } else if (storedTheme === 'light') {
        isDark = false;
      } else if (storedTheme === 'system' || !storedTheme) {
        // Use system preference if theme is 'system' or not set
        isDark = systemPrefersDark;
      }

      // Override with HTML class if ThemeProvider is active
      if (htmlHasDark) {
        isDark = true;
      }

      setStandaloneIsDarkMode(isDark);
    };

    // Initial check
    checkStandaloneDarkMode();

    // Listen for localStorage changes
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'ai-tutor-theme') {
        checkStandaloneDarkMode();
      }
    };
    window.addEventListener('storage', handleStorageChange);

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleMediaChange = () => checkStandaloneDarkMode();
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleMediaChange);
    }

    // Observer for HTML class changes
    const observer = new MutationObserver(checkStandaloneDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleMediaChange);
      }
      observer.disconnect();
    };
  }, []);

  // DERIVED STATE: Determine final dark mode status
  // If context is available, use it (INSTANT). Otherwise, use standalone state.
  const isDarkMode = athenaContext?.state?.theme
    ? athenaContext.state.theme === 'dark'
    : standaloneIsDarkMode;

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

  // DEBUG: Check if we are capturing the right ID
  const isTargetID = url.toLowerCase().includes('6933b3176cf86fa761d0a255') || baseUrl.toLowerCase().includes('6933b3176cf86fa761d0a255') || baseUrl.includes('6ba2c9076404d0c5e704a2071bec7597bb3dc011');

  useEffect(() => {
    if (isTargetID) {
      console.log('[[DEBUG TARGET]] Found target voting graph ID!');
      console.log('[[DEBUG TARGET]] URL:', url);
      console.log('[[DEBUG TARGET]] BaseURL:', baseUrl);
    }
  }, [isTargetID, url, baseUrl]);

  // Determine whether to use PNG or SVG based on URL patterns
  // Some images (hundred charts, labeled diagrams) work better with PNG which has text baked in
  // Hardcoded data for the problematic voting graph (Hash: 6ba2c9076404d0c5e704a2071bec7597bb3dc011)
  const VOTING_GRAPH_DATA = {
    "range": [[-1.5086666666666666, 7.3], [-70, 130]],
    "labels": [
      { "content": "0", "coordinates": [0, 0], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "10", "coordinates": [0, 10], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "20", "coordinates": [0, 20], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "30", "coordinates": [0, 30], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "40", "coordinates": [0, 40], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "50", "coordinates": [0, 50], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "60", "coordinates": [0, 60], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "70", "coordinates": [0, 70], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "80", "coordinates": [0, 80], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "90", "coordinates": [0, 90], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "100", "coordinates": [0, 100], "alignment": "left", "typesetAsMath": true, "style": {} },
      { "content": "<center>1</center>", "coordinates": [0.65, 0], "alignment": "below", "typesetAsMath": false, "style": {} },
      { "content": "<center>2</center>", "coordinates": [1.65, 0], "alignment": "below", "typesetAsMath": false, "style": {} },
      { "content": "<center>3</center>", "coordinates": [2.65, 0], "alignment": "below", "typesetAsMath": false, "style": {} },
      { "content": "<center>4</center>", "coordinates": [3.65, 0], "alignment": "below", "typesetAsMath": false, "style": {} },
      { "content": "<center>5</center>", "coordinates": [4.65, 0], "alignment": "below", "typesetAsMath": false, "style": {} },
      { "content": "<center>6</center>", "coordinates": [5.65, 0], "alignment": "below", "typesetAsMath": false, "style": {} },
      { "content": "<center>7</center>", "coordinates": [6.65, 0], "alignment": "below", "typesetAsMath": false, "style": {} },
      { "content": "<center>Voters' Political Orientation, Level of<br>Political Information, and Probability<br>of Voting</center>", "coordinates": [2.25, 130], "alignment": "below", "typesetAsMath": false, "style": { "font-weight": "bold", "font-size": "16px" } },
      { "content": "<center>Voters' political orientation<br>(1 = strong Democrat/liberal;<br>4 = independent;<br>7 = strong Republican/conservative)</center>", "coordinates": [2.8499999999999996, -10.416666666666668], "alignment": "below", "typesetAsMath": false, "style": {} },
      { "content": "<center>Probability of voting (%)</center>", "coordinates": [-1.3383333333333332, 50], "alignment": "center", "typesetAsMath": false, "style": { "font-weight": "bold", "transform": "rotate(-90deg)" } },
      { "content": "high information", "coordinates": [2.3649999999999998, -61.66666666666667], "alignment": "right", "typesetAsMath": false, "style": {} },
      { "content": "low information", "coordinates": [2.3649999999999998, -50.66666666666667], "alignment": "right", "typesetAsMath": false, "style": {} }
    ]
  };

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

    // FORCE CACHE CLEAR for the problematic voting graph to ensure restructuring applies
    if (baseUrl.toLowerCase().includes('6933b3176cf86fa761d0a255') || baseUrl.includes('6ba2c9076404d0c5e704a2071bec7597bb3dc011')) {
      const svgUrl = baseUrl + '.svg';
      if (svgCache.has(svgUrl)) {
        console.log('[GraphieImage] Force clearing cache for 6933b... to ensure restructure');
        svgCache.delete(svgUrl);
      }
      // Force SVG usage
      setUsePngForLabels(false);
    }
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
    // Add cache buster to prevent stale SVG loading
    const fetchUrl = svgUrl + '?t=' + new Date().getTime();
    fetch(fetchUrl, { mode: 'cors' })
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

        // Detect voting graph based on URL
        const isVotingUrl = baseUrl.toLowerCase().includes('voting') ||
          baseUrl.toLowerCase().includes('political') ||
          baseUrl.toLowerCase().includes('6ba2c9076404d0c5e704a2071bec7597bb3dc011') ||
          baseUrl.toLowerCase().includes('6933b3176cf86fa761d0a255');

        if (isVotingUrl) {
          console.log('[GraphieImage] Voting graph detected by URL, restructuring SVG');
          processedSvg = restructureSvgForVotingGraph(processedSvg);
        }

        // Inject comprehensive CSS style block to ensure ALL text is visible
        // IMPORTANT: Scope all selectors to .graphie-svg to avoid affecting other page elements
        const styleBlock = `<style>
          /* Force all text elements to be visible - scoped to SVG only */
          .graphie-svg text, .graphie-svg tspan, .graphie-svg .label, svg[class*="graphie"] [class*="label"] {
            fill: #000 !important; /* Force high contrast black ALWAYS */
            fill-opacity: 1 !important;
            font-family: 'Arial', 'Helvetica', sans-serif !important; /* Academic, crisp font */
            font-weight: 500 !important; /* Slightly clearer */
            visibility: visible !important;
            display: inline !important;
            opacity: 1 !important;
            stroke: none !important;
            text-rendering: optimizeLegibility !important; /* Better text rendering */
          }
          /* Enhance sharpness of geometric elements */
          .graphie-svg line, .graphie-svg rect, .graphie-svg polyline {
            shape-rendering: crispEdges !important; /* Sharp lines for axes and bars */
          }
          .graphie-svg path {
            shape-rendering: geometricPrecision !important; /* Smooth curves, but precise */
          }
          /* Override any hiding attributes */
          text[fill="transparent"], tspan[fill="transparent"],
          text[fill="none"], tspan[fill="none"],
          text[fill="white"], tspan[fill="white"],
          text[fill="#fff"], tspan[fill="#fff"],
          text[fill="white"], tspan[fill="white"],
          text[fill="#fff"], tspan[fill="#fff"],
          text[fill="#ffffff"], tspan[fill="#ffffff"] {
            fill: #000 !important; /* Force even white text to black in high contrast mode */
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
            fill: currentColor !important;
            fill-opacity: 1 !important;
            visibility: visible !important;
          }
          /* Fix zero fill-opacity */
          text[fill-opacity="0"], tspan[fill-opacity="0"] {
            fill-opacity: 1 !important;
          }
          /* Force SVG background transparency */
          svg {
            background: transparent !important;
            background-color: transparent !important;
          }
          /* Make white background-like shapes transparent */
          ellipse[fill="white"], ellipse[fill="#fff"], ellipse[fill="#ffffff"],
          polygon[fill="white"], polygon[fill="#fff"], polygon[fill="#ffffff"],
          rect[style*="fill: white"], rect[style*="fill:#fff"], rect[style*="fill:#ffffff"],
          path[style*="fill: white"], path[style*="fill:#fff"], path[style*="fill:#ffffff"],
          rect[fill*="rgb(255"], path[fill*="rgb(255"] {
            fill: transparent !important;
            fill-opacity: 0 !important;
          }
          /* Reset strokes that might have been forced to white incorrectly */
          path[stroke="white"], path[stroke="#fff"], path[stroke="#ffffff"] {
            stroke: currentColor !important;
          }
          /* Ensure specific colors (like cyan boxes) are preserved and not forced to currentColor by high-level rules */
          path[stroke*="#"], path[stroke*="rgb"], rect[stroke*="#"], rect[stroke*="rgb"] {
            /* stroke: inherit; -- allow specific strokes */
          }
        </style>`;

        // Insert style block after opening svg tag
        processedSvg = processedSvg.replace(/<svg[^>]*>/, (match) => match + styleBlock);

        // Remove/fix inline styles and attributes that hide text elements
        // Handle opacity in various formats
        processedSvg = processedSvg.replace(/<text([^>]*)style="([^"]*?)opacity:\s*0([^"]*?)"/gi, '<text$1style="$2opacity:1$3"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)style="([^"]*?)opacity:\s*0([^"]*?)"/gi, '<tspan$1style="$2opacity:1$3"');

        // Handle fill="transparent" or fill="none"
        processedSvg = processedSvg.replace(/<text([^>]*)fill="(?:transparent|none)"/gi, '<text$1fill="currentColor"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)fill="(?:transparent|none)"/gi, '<tspan$1fill="currentColor"');

        // Handle fill-opacity="0"
        processedSvg = processedSvg.replace(/<text([^>]*)fill-opacity="0"/gi, '<text$1fill-opacity="1"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)fill-opacity="0"/gi, '<tspan$1fill-opacity="1"');

        // Handle visibility="hidden"
        processedSvg = processedSvg.replace(/<text([^>]*)visibility="hidden"/gi, '<text$1visibility="visible"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)visibility="hidden"/gi, '<tspan$1visibility="visible"');

        // Handle display="none"
        processedSvg = processedSvg.replace(/<text([^>]*)display="none"/gi, '<text$1display="inline"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)display="none"/gi, '<tspan$1display="inline"');

        // Handle white/invisible fill colors (commonly used to hide text or as backgrounds)
        // For text, we definitely want currentColor
        processedSvg = processedSvg.replace(/<text([^>]*)fill="(?:#fff(?:fff)?|white|rgba?\([^)]*,\s*0\))"/gi, '<text$1fill="currentColor"');
        processedSvg = processedSvg.replace(/<tspan([^>]*)fill="(?:#fff(?:fff)?|white|rgba?\([^)]*,\s*0\))"/gi, '<tspan$1fill="currentColor"');

        // For shapes, if it's pure white, it's likely a background or container that should be transparent
        processedSvg = processedSvg.replace(/<(path|rect|circle|ellipse|polygon|polyline)([^>]*)fill="(?:#fff(?:fff)?|white)"/gi, '<$1$2fill="none"');
        processedSvg = processedSvg.replace(/<(path|rect|circle|ellipse|polygon|polyline)([^>]*)stroke="(?:#fff(?:fff)?|white)"/gi, '<$1$2stroke="currentColor"');

        // Handle inline style white fills/strokes for all shapes
        processedSvg = processedSvg.replace(/<(path|rect|circle|ellipse|polygon|polyline)([^>]*)style="([^"]*?)fill:\s*(?:#fff(?:fff)?|white)([^"]*?)"/gi, '<$1$2style="$3fill:none$4"');
        processedSvg = processedSvg.replace(/<(path|rect|circle|ellipse|polygon|polyline)([^>]*)style="([^"]*?)stroke:\s*(?:#fff(?:fff)?|white)([^"]*?)"/gi, '<$1$2style="$3stroke:currentColor$4"');

        // Handle black/dark fills that should be dynamic (only if they are pure black or very dark gray)
        processedSvg = processedSvg.replace(/<(path|rect|circle|ellipse|line|polyline|polygon)([^>]*)fill="(?:#000(?:000)?|#333(?:333)?|black)"/gi, '<$1$2fill="currentColor"');
        processedSvg = processedSvg.replace(/<(path|rect|circle|ellipse|line|polyline|polygon)([^>]*)stroke="(?:#000(?:000)?|#333(?:333)?|black)"/gi, '<$1$2stroke="currentColor"');

        // Handle inline style dark fills/strokes
        processedSvg = processedSvg.replace(/<(path|rect|circle|ellipse|line|polyline|polygon)([^>]*)style="([^"]*?)fill:\s*(?:#000(?:000)?|#333(?:333)?|black)([^"]*?)"/gi, '<$1$2style="$3fill:currentColor$4"');
        processedSvg = processedSvg.replace(/<(path|rect|circle|ellipse|line|polyline|polygon)([^>]*)style="([^"]*?)stroke:\s*(?:#000(?:000)?|#333(?:333)?|black)([^"]*?)"/gi, '<$1$2style="$3stroke:currentColor$4"');

        // Handle stroke-opacity that might hide text outlines
        processedSvg = processedSvg.replace(/<text([^>]*)stroke-opacity="0"/gi, '<text$1stroke-opacity="1"');

        // Ensure text elements without fill get a default fill
        processedSvg = processedSvg.replace(/<text(?![^>]*fill=)/gi, '<text fill="currentColor" ');

        // Also handle text elements that might have empty or zero-value styling
        processedSvg = processedSvg.replace(/(<text[^>]*style=")([^"]*)(font-size:\s*0[^;]*;?)([^"]*")/gi, '$1$2font-size:14px;$4');

        // Remove any class-based hiding (common in graphie SVGs)
        processedSvg = processedSvg.replace(/class="[^"]*hidden[^"]*"/gi, '');

        // Handle <image> tags (pictograms/icons)
        // Convert schemeless URLs (//) to https://
        processedSvg = processedSvg.replace(/<image([^>]*)(?:xlink:)?href="\/\/([^"]*)"/gi, '<image$1href="https://$2"');
        // Ensure images are visible
        processedSvg = processedSvg.replace(/<image(?![^>]*style=)/gi, '<image style="visibility:visible;opacity:1" ');

        // Add explicit styling to make sure text is positioned correctly and background is transparent
        // Some graphie SVGs use transforms that might position text outside viewport
        processedSvg = processedSvg.replace(/<svg([^>]*)>/, (match, attrs) => {
          let newAttrs = attrs;
          // Ensure SVG has overflow visible and transparent background
          if (!attrs.includes('overflow')) {
            newAttrs += ' style="overflow:visible;background:transparent !important"';
          } else if (!attrs.includes('background')) {
            newAttrs = attrs.replace(/style="([^"]*)"/, 'style="$1;background:transparent !important"');
          }
          return `<svg${newAttrs}>`;
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

    // FORCE HARDCODED DATA for Voting Graph
    // This bypasses fetch failures and guarantees labels exist for our fix
    if (baseUrl.toLowerCase().includes('6933b3176cf86fa761d0a255') || baseUrl.includes('6ba2c9076404d0c5e704a2071bec7597bb3dc011')) {
      console.log('[GraphieImage] Using HARDCODED data for voting graph');
      // We already defined VOTING_GRAPH_DATA constant at component scope (lines 220+)
      // But since it's defined inside the component, we can access it here.
      // Wait, scope is fine.
      setGraphieData(VOTING_GRAPH_DATA);
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



  // Trigger restructuring based on graphie data (labels) if URL detection missed it
  useEffect(() => {
    if (graphieData && svgContent && !svgContent.includes('data-restructured')) {
      const isVotingGraph = graphieData.labels?.some(l => {
        const c = processLabelContent(l.content).toLowerCase();
        return c.includes('voting') || c.includes('voter') || c.includes('polit') || c.includes('democrat') || c.includes('republic') || c.includes('high information');
      }) || baseUrl.toLowerCase().includes('6933b3176cf86fa761d0a255');

      if (isVotingGraph) {
        console.log('[GraphieImage] Voting graph detected by labels or ID, restructuring SVG now');
        setSvgContent(prev => prev ? restructureSvgForVotingGraph(prev) : null);
      }
    }
  }, [graphieData, svgContent, baseUrl]);

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
        element.style.fill = element.style.fill || 'currentColor';
        element.style.fillOpacity = '1';
        element.style.visibility = 'visible';
        element.style.display = 'inline';
        element.style.opacity = '1';

        // Also set attributes directly
        if (!element.getAttribute('fill') || element.getAttribute('fill') === 'none' || element.getAttribute('fill') === 'transparent') {
          element.setAttribute('fill', 'currentColor');
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

    // Remove <center> tags (often found in Perseus labels but not supported by SVG text)
    processed = processed.replace(/<center>/gi, '');
    processed = processed.replace(/<\/center>/gi, '');

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

    // Parse SVG dimensions and check for restructuring
    const viewBoxMatch = svg.match(/viewBox="([^"]+)"/);
    // Robust detection: check for the data attribute in the SVG string
    // OR if we know it's our target graph (force it)
    const isTargetGraph = baseUrl.toLowerCase().includes('6933b3176cf86fa761d0a255') || baseUrl.includes('6ba2c9076404d0c5e704a2071bec7597bb3dc011');
    const isRestructured = svg.includes('data-restructured') || isTargetGraph;
    const origHeightMatch = svg.match(/data-original-height="([^"]+)"/);

    let svgWidth = 400, svgHeight = 400;
    let coordinateHeight = 400; // The height used for mapping coordinates [yMin, yMax]

    if (viewBoxMatch) {
      const parts = viewBoxMatch[1].split(/\s+/);
      svgWidth = parseFloat(parts[2]) || 400;
      svgHeight = parseFloat(parts[3]) || 400;
      coordinateHeight = svgHeight;
    }

    if (isRestructured && origHeightMatch) {
      // If expanded, the coordinates [yMin, yMax] mapping should still use the ORIGINAL height scale
      coordinateHeight = parseFloat(origHeightMatch[1]) || 400;
    }

    // Generate SVG text elements for labels
    const labelElements = labels.map((label, index) => {
      const [x, y] = label.coordinates;
      let svgX = ((x - xMin) / (xMax - xMin)) * svgWidth;
      let svgY = ((yMax - y) / (yMax - yMin)) * coordinateHeight;

      let textAnchor = 'middle';
      let dy = '0.35em';
      let transformAttr = '';
      let styleStr = 'font-family: Arial, Helvetica, sans-serif; font-size: 16px;';

      // --- LAYOUT RESTRUCTURING SPECIAL FIXES ---
      // Robust detection of the voting graph
      const isVotingGraph = labels.some(l => {
        const c = processLabelContent(l.content).toLowerCase();
        return c.includes('voting') || c.includes('voter') || c.includes('polit') || c.includes('democrat') || c.includes('republic') || c.includes('information');
      }) || baseUrl.toLowerCase().includes('6933b3176cf86fa761d0a255') || baseUrl.includes('6ba2c9076404d0c5e704a2071bec7597bb3dc011');
      const topPadding = 90; // Match the value used in restructureSvgForVotingGraph
      const barCenter = svgWidth / 2;

      // The "baseline" (y=0 in math coords) is at a specific Y in our coordinateHeight
      const graphBaselineY = (yMax / (yMax - yMin)) * coordinateHeight;

      // Process content for matching and display
      let processedContent = processLabelContent(label.content);

      if (index === 0) {
        console.log('[GraphieImage] Checking voting graph:', isVotingGraph, 'isRestructured:', isRestructured, 'isTargetGraph:', isTargetGraph);
        console.log('[GraphieImage] Label contents examples:', labels.slice(0, 3).map(l => processLabelContent(l.content)));
      }

      if (isVotingGraph && isRestructured) {
        const lowerContent = processedContent.toLowerCase();

        // DEBUG: Log every label processed in this block
        if (index === 0 || index === labels.length - 1) { // Log first and last to avoid spamming too much, or log all if needed
          console.log(`[GraphieImage] Processing label: "${lowerContent}"`);
        }

        // SUPER ROBUST MATCHING
        // Strip common HTML tags for checking
        const cleanContent = lowerContent.replace(/<[^>]*>/g, ' ');

        // 1. LEGEND (Bottom Right)
        if (cleanContent.includes('high information') || cleanContent.includes('low information')) {
          // Revert to using the calculated svgX/svgY so it matches the boxes (which are drawn at math coords)
          // Original alignment was 'right', but visual is Box [Text], so we want 'start' (left align) 
          // to place text to the right of the coordinate (assuming coordinate is the box position)
          textAnchor = 'start';

          // Small nudge if needed. 
          // Original X (math) ~ 175. Visual box might be there.
          // Adding a small margin to separate text from box.
          svgX += 15;

          // Y adjustment: The math Y makes them float too high above the boxes.
          // We push them down significantly to align "center-ish" with the boxes.
          // User said "boxes ascend", implying gap. We close it by moving text down.
          svgY += 35;

          styleStr += ' font-weight: bold; font-size: 14px;';
        }
        // 2. MAIN TITLE (Top)
        // Match specific words known to be in the title
        else if (cleanContent.includes('level of') || cleanContent.includes('political information') || (cleanContent.includes('probability') && cleanContent.includes('voting') && !cleanContent.includes('%'))) {
          svgX = barCenter;
          textAnchor = 'middle';
          svgY = -115;
          if (cleanContent.includes('orientation')) svgY = -140; // Top line
          if (cleanContent.includes('voting')) svgY = -90; // Bottom line

          styleStr += ' font-weight: bold; font-size: 18px !important;';
        }
        // 3. Y-AXIS LABEL (Left)
        else if (cleanContent.includes('%') || (cleanContent.includes('probability') && cleanContent.includes('voting'))) {
          svgX = 155;
          svgY = coordinateHeight / 2.6;
          textAnchor = 'middle';
          dy = '0.35em';
          transformAttr = `rotate(-90 ${svgX} ${svgY})`;

          styleStr += ' font-weight: bold;';
        }
        // 4. X-AXIS LABEL (Bottom)
        else if (cleanContent.includes('1 =') || cleanContent.includes('strong') || cleanContent.includes('independent')) {
          svgX = barCenter;
          textAnchor = 'middle';
          svgY = graphBaselineY + 65;
          if (cleanContent.includes('democrat')) svgY = graphBaselineY + 12;
          if (cleanContent.includes('independent')) svgY = graphBaselineY + 22;
          if (cleanContent.includes('republican')) svgY = graphBaselineY + 32;
        }
        // 5. EVERYTHING ELSE (Ticks integers)
        else {
          // Standard positioning logic...
          if (label.alignment === 'below') svgY += 6;
          if (label.alignment === 'left') { textAnchor = 'end'; svgX -= 10; }

          // Only mark as RED if it contains text characters (not just numbers)
          // This helps identify "missed" labels
          if (/[a-z]/.test(cleanContent)) {
            // Missed text labels - ensure they are visible
            styleStr += ' font-weight: bold;';
          }
        }
      } else {
        // Standard non-voting graph logic
        if (label.alignment === 'left') {
          textAnchor = 'end';
          svgX -= 10;
        } else if (label.alignment === 'right') {
          textAnchor = 'start';
          svgX += 3;
        } else if (label.alignment === 'above' || label.alignment === 'top') {
          dy = '-0.8em';
        } else if (label.alignment === 'below' || label.alignment === 'bottom') {
          svgY += 25;
          dy = '1.2em';
        }
      }

      if (label.style) {
        if (label.style['font-weight']) styleStr += ` font-weight: ${label.style['font-weight']};`;
        if (label.style['font-size']) styleStr += ` font-size: ${label.style['font-size']};`;

        // Extract transform for SVG attribute (CSS transform doesn't work on SVG text elements reliably)
        if (label.style.transform) {
          // Convert CSS rotate(-90deg) to SVG rotate(-90 x y)
          const rotateMatch = label.style.transform.match(/rotate\((-?\d+)deg\)/);
          if (rotateMatch) {
            const angle = rotateMatch[1];
            // Rotate around the precise text position
            transformAttr = `rotate(${angle} ${svgX} ${svgY})`;

            // We want to push it closer to the Y-axis or just keep it centered.
            dy = '0.35em';
          } else {
            // Fallback: strip 'deg' if present, as SVG doesn't use units in rotate()
            transformAttr = label.style.transform.replace('deg', '');
          }
        }
      }

      // Processed content is already available from matching logic

      // Split by <br> tags to support multiline labels in SVG
      const lines = processedContent.split(/<br\s*\/?>/i);

      const tspanElements = lines.map((line, lineIdx) => {
        // Escape content as it will be inside <tspan>
        const escapedLine = line
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');

        const lineDy = lineIdx === 0 ? dy : '1.2em';

        // IMPORTANT: Apply the accumulated styles (including debugging colors) here!
        return `<tspan x="${svgX}" dy="${lineDy}" style="${styleStr}">${escapedLine}</tspan>`;
      }).join('');

      return `<text x="${svgX}" y="${svgY}" text-anchor="${textAnchor}" dy="${dy}" fill="currentColor" style="${styleStr}" ${transformAttr ? `transform="${transformAttr}"` : ''}>${tspanElements}</text>`;
    }).join('\n');

    // Insert labels into the transformed group if it exists, otherwise at the end
    // Insert labels into the transformed group if it exists, otherwise at the end
    // Use robust regex to find the closing tag of the transformed group
    if (svg.includes('class="graph-content-transformed"')) {
      // Find the last closing </g> which closes the transformed group
      // We look for the last </g> before </svg>
      const lastGroupCloseIndex = svg.lastIndexOf('</g>');
      if (lastGroupCloseIndex !== -1) {
        return svg.slice(0, lastGroupCloseIndex) + `<g class="graphie-labels">${labelElements}</g>` + svg.slice(lastGroupCloseIndex);
      }
    }

    // Fallback: If we couldn't insert into the group, or if the group wasn't found but we know it should be restructured
    if (isRestructured) {
      // If the SVG is restructured (expanded), the main content is shifted by (60, 180).
      // If we are appending labels to the root, we MUST apply the same shift so the relative coordinates (like -140) work.
      // This handles cases where regex failed or the group structure is slightly different.
      return svg.replace('</svg>', `<g transform="translate(60, 180)" class="graphie-labels">${labelElements}</g></svg>`);
    }

    return svg.replace('</svg>', `<g class="graphie-labels">${labelElements}</g></svg>`);
  }, [baseUrl]);

  // Get processed SVG with labels
  const processedSvgWithLabels = useMemo(() => {
    if (!svgContent || !graphieData?.labels || graphieData.labels.length === 0) {
      return svgContent;
    }
    const range = graphieData.range || [[-10, 10], [-10, 10]];
    console.log('[GraphieImage] Injecting', graphieData.labels.length, 'labels into SVG');
    return injectLabelsIntoSvg(svgContent, graphieData.labels, range);
  }, [svgContent, graphieData, injectLabelsIntoSvg]);

  // FORCE STATIC IMAGE FOR BROKEN VOTING GRAPH (ID: 6933b3176cf86fa761d0a255)
  // This bypasses all complex SVG restructuring logic as requested by user.
  // Placed HERE to allow all hooks to run first, avoiding "Rendered fewer hooks than expected" error.
  if (baseUrl.includes('6933b3176cf86fa761d0a255') || baseUrl.includes('6ba2c9076404d0c5e704a2071bec7597bb3dc011')) {
    return (
      <div className={`graphie-container ${className}`} style={{ ...style, width: '100%', maxWidth: '400px', margin: '0 auto', background: 'transparent', padding: 0, border: 'none' }}>
        {/* CSS pour dark mode - ULTRA-SPÉCIFIQUE pour éviter d'affecter d'autres éléments */}
        <style>{`
          /* Cible UNIQUEMENT l'image avec la classe voting-graph-fix */
            /* Mode Clair: Multiply pour détourer le blanc (le rend transparent) */
          /* Mode Clair: Multiply pour détourer le blanc (le rend transparent) */
          img.voting-graph-fix {
            filter: none !important;
            mix-blend-mode: multiply !important;
          }
          /* Mode Sombre: Screen pour détourer le noir (le rend transparent) après inversion */
          /* On cible via la classe .force-dark injectée par JS, plus fiable que html.dark */
          img.voting-graph-fix.force-dark {
            filter: invert(1) hue-rotate(180deg) !important;
            mix-blend-mode: screen !important;
          }
        `}</style>
        <img
          src="/fixed_graphs/voting_graph.png"
          alt={alt || "Graph showing voters' political orientation"}
          className={`voting-graph-fix ${isDarkMode ? 'force-dark' : ''}`}
          style={{
            width: '100%',
            height: 'auto',
            display: 'block',
            margin: 0,
            padding: 0,
            border: 'none',
            background: 'transparent',
            transition: 'filter 0.3s ease, opacity 0.3s ease',
            // Transparence en mode comparaison (géré par JS)
            opacity: viewMode === 'comparison' ? 0.8 : 1
          }}
        />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`graphie-image-container ${className}`}
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        maxWidth: '100%',
        margin: '2rem auto',
        textAlign: 'center',
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
          style={{
            display: 'flex',
            justifyContent: 'center',
            textAlign: 'center', // Ensure text/inline elements are centered
            width: '100%',
            marginTop: '1rem',
            marginBottom: '1rem'
          }}
        >
          <div
            className="graphie-svg-wrapper"
            dangerouslySetInnerHTML={{ __html: processedSvgWithLabels }}
            style={{
              display: 'block',
              margin: '0 auto',
              maxWidth: '100%',
              lineHeight: 0,
            }}
          />
        </div>
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
