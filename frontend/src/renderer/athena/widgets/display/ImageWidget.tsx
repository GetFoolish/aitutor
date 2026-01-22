/**
 * Image Widget
 *
 * Display images with:
 * - Responsive sizing
 * - Alt text
 * - Caption
 * - Zoom functionality
 * - Support for web+graphie:// URLs (Khan Academy format)
 */

import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { ImageOptions } from '../../core/types';
import { BaseWidgetWrapper } from '../base/BaseWidget';
import { ImageURLMigrator } from '../../migration/ImageURLMigrator';
import { GraphieImage } from './GraphieImage';
import AthenaContext from '../../AthenaContext';

// Base URL for resolving relative asset URLs (from backend API)
const ASSETS_BASE_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

// Load KaTeX dynamically for rendering math in labels
let katexModule: any = null;
async function ensureKaTeX() {
  if (katexModule) return katexModule;
  try {
    katexModule = await import('katex');
    return katexModule.default || katexModule;
  } catch {
    return null;
  }
}

export interface ImageWidgetProps extends WidgetProps<ImageOptions> { }

// Singleton migrator instance
const imageUrlMigrator = new ImageURLMigrator();

/**
 * Convert image URLs to usable HTTPS URLs
 * Handles web+graphie:// URLs, CDN URLs, relative URLs, and S3 URLs
 * Uses PNG format for graphie images because PNG has labels baked in,
 * while SVG requires separate -data.json for labels (which faces CORS issues)
 */
function convertImageUrl(url: string, usePng: boolean = true): string {
  if (!url) return url;

  let converted = url;

  // Handle frontend assets specifically (served by Vite/Next.js)
  if (url.startsWith('/assets/') || url.startsWith('/fixed_graphs/')) {
    return url;
  }

  // Handle relative URLs (from backend assets)
  if (url.startsWith('/')) {
    converted = ASSETS_BASE_URL + url;
  }
  // Handle web+graphie:// URLs
  else if (url.startsWith('web+graphie://')) {
    converted = imageUrlMigrator.migrateUrl(url);
    // Graphie images need file extension added
    if (!converted.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
      converted = converted + (usePng ? '.png' : '.svg');
    }
  }
  // Handle CDN URLs that might be missing file extension
  else if (url.includes('cdn.kastatic.org') || url.includes('ka-perseus') || url.includes('.s3.amazonaws.com/')) {
    // Add .png extension if no extension present
    if (!url.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
      converted = url + '.png';
    }
  }
  // Handle other relative URLs (no protocol, not starting with /)
  else if (!url.startsWith('http') && !url.startsWith('data:')) {
    converted = ASSETS_BASE_URL + '/' + url;
  }

  return converted;
}

export function ImageWidget({
  widgetId,
  widget,
  theme = 'light',
}: ImageWidgetProps) {
  const options = widget.options || {};
  const [isZoomed, setIsZoomed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [fallbackAttempt, setFallbackAttempt] = useState(0); // 0: original, 1: .png, 2: .svg, 3: give up
  const [katex, setKatex] = useState<any>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const loadTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const backgroundImage = options.backgroundImage;

  // Load KaTeX on mount
  useEffect(() => {
    ensureKaTeX().then(k => setKatex(k));
  }, []);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (loadTimeoutRef.current) {
        clearTimeout(loadTimeoutRef.current);
      }
    };
  }, []);

  // Use Context for robust Dark Mode detection
  const athenaContext = React.useContext(AthenaContext);
  const isDarkMode = athenaContext?.state?.theme
    ? athenaContext.state.theme === 'dark'
    : theme === 'dark'; // Fallback to prop



  // Set a timeout to detect failed loads (images that never fire load or error)
  useEffect(() => {
    if (isLoading && backgroundImage?.url) {
      if (loadTimeoutRef.current) {
        clearTimeout(loadTimeoutRef.current);
      }
      loadTimeoutRef.current = setTimeout(() => {
        if (isLoading) {
          console.log('[ImageWidget] Load timeout, trying fallback');
          if (fallbackAttempt < 3) {
            setFallbackAttempt(prev => prev + 1);
          } else {
            setIsLoading(false);
            setHasError(true);
          }
        }
      }, 5000); // 5 second timeout (reduced for better UX)
    }
    return () => {
      if (loadTimeoutRef.current) {
        clearTimeout(loadTimeoutRef.current);
      }
    };
  }, [isLoading, backgroundImage?.url, fallbackAttempt]);

  // Render label content with math support
  const renderLabelContent = useCallback((content: string): string => {
    if (!content) return '';
    let processed = content;

    // Process inline math $...$
    processed = processed.replace(/\$([^$]+)\$/g, (_, math) => {
      try {
        if (katex) {
          return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false });
        }
        return math;
      } catch {
        return math;
      }
    });

    // Handle \text{} inside math
    processed = processed.replace(/\\text\{([^}]+)\}/g, '<span class="athena-label-text">$1</span>');

    return processed;
  }, [katex]);

  // Convert the URL if needed (handles web+graphie://, relative URLs, etc.)
  const imageUrl = useMemo(() => {
    if (!backgroundImage?.url) return '';

    // --- BROKEN GRAPH FIXES ---
    // 1. Curved Graph (6935f...)
    // Check by Partial Hash OR by Alt Text keywords (very broad fallback)
    const url = backgroundImage.url;
    const alt = options.alt || '';
    const isCurvedGraph = url.includes('e5659') ||
      (alt.includes('Good S') && alt.includes('Good R'));

    if (isCurvedGraph) {
      console.log('[ImageWidget] Fixing Curved Graph (Broad Match)');
      return '/fixed_graphs/curved_graph_6935f1b5.png?v=fixed7';
    }
    // 2. Triangle Graph (69339...)
    if (backgroundImage.url.includes('4d5a7152eb4a9381f6727326fe960fe5c818498b')) {
      console.log('[ImageWidget] Fixing Triangle Graph');
      return '/fixed_graphs/triangle_fix_693396fb.png?v=fixed3';
    }
    // 3. Linear Graph (6936f...)
    const isLinearGraph = url.includes('a73f94') || alt.includes('(1,40)');
    if (isLinearGraph) {
      console.log('[ImageWidget] Fixing Linear Graph (6936f)');
      return '/fixed_graphs/linear_graph_6936fda6.png?v=fixed1';
    }

    let converted = convertImageUrl(backgroundImage.url);

    // Apply fallback attempts - try different extensions
    if (fallbackAttempt > 0) {
      // Remove any existing extension first
      const urlWithoutExt = converted.replace(/\.(png|svg|jpg|jpeg|gif|webp)$/i, '');

      if (fallbackAttempt === 1) {
        // Try .png
        converted = urlWithoutExt + '.png';
      } else if (fallbackAttempt === 2) {
        // Try .svg
        converted = urlWithoutExt + '.svg';
      } else if (fallbackAttempt === 3) {
        // Try without extension (some URLs work without)
        converted = urlWithoutExt;
      }
    }

    console.log('[ImageWidget] URL conversion:', {
      original: backgroundImage.url,
      converted,
      fallbackAttempt
    });

    return converted;
  }, [backgroundImage?.url, fallbackAttempt, options.alt]);

  // Debug log for troubleshooting graph visibility
  // Moved here to be after imageUrl declaration
  useEffect(() => {
    if (widget.options?.backgroundImage?.url?.includes('69334af918bcab85650eed24')) {
      console.log('[ImageWidget] RENDERING TARGET GRAPH 69334af9', {
        themeProp: theme,
        contextTheme: athenaContext?.state?.theme,
        isDarkMode,
        finalUrl: imageUrl
      });
    }
  }, [theme, athenaContext?.state?.theme, isDarkMode, imageUrl]);

  const handleLoad = useCallback(() => {
    setIsLoading(false);
    if (loadTimeoutRef.current) {
      clearTimeout(loadTimeoutRef.current);
    }
  }, []);

  const handleError = useCallback(() => {
    console.log('[ImageWidget] Image load error, attempt:', fallbackAttempt);

    // Try fallback formats before giving up
    if (fallbackAttempt < 3) {
      setFallbackAttempt(prev => prev + 1);
      setIsLoading(true);
      return;
    }

    // All fallbacks failed
    setIsLoading(false);
    setHasError(true);
  }, [fallbackAttempt]);

  const handleZoomToggle = useCallback(() => {
    setIsZoomed((prev) => !prev);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleZoomToggle();
      } else if (e.key === 'Escape' && isZoomed) {
        setIsZoomed(false);
      }
    },
    [handleZoomToggle, isZoomed]
  );

  if (!backgroundImage?.url) {
    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="image">
        {/* CSS "NUCLÉAIRE" pour forcer la correction quoi qu'il arrive */}
        <style>{`
          /* Cible l'image par son URL partielle - fonctionne même si React échoue */
          img[src*="69334af918bcab85650eed24"] {
            /* Par défaut (Light Mode) : pas de filtre */
            filter: none !important;
            mix-blend-mode: normal !important;
          }

          /* Dark Mode : Inversion + Screen */
          /* On utilise :global pour s'assurer que ça tape large */
          :root.dark img[src*="69334af918bcab85650eed24"],
          .dark img[src*="69334af918bcab85650eed24"],
          [data-theme="dark"] img[src*="69334af918bcab85650eed24"] {
             filter: invert(1) hue-rotate(180deg) !important;
             mix-blend-mode: screen !important;
             opacity: 1 !important;
             background-color: transparent !important;
          }
          
          /* Force la transparence des parents directs pour éviter le fond noir */
          .athena-image-container:has(img[src*="69334af918bcab85650eed24"]),
          .athena-image-figure:has(img[src*="69334af918bcab85650eed24"]) {
            background: transparent !important;
            background-color: transparent !important;
          }
        `}</style>
        <div className="athena-image-placeholder">
          No image specified
        </div>
      </BaseWidgetWrapper>
    );
  }

  // Check if this is a graphie image that needs labels from data.json
  // EXCLUDE fixed graphs from this check to ensure they use the standard <img> tag with our override URL
  // Sync detection logic with imageUrl calculation
  const altText = options.alt || '';
  const isCurvedGraphFixed = backgroundImage.url.includes('e5659') ||
    (altText.includes('Good S') && altText.includes('Good R'));

  const isLinearGraphFixed = backgroundImage.url.includes('a73f94') || altText.includes('(1,40)');

  const isBrokenGraph = isCurvedGraphFixed || isLinearGraphFixed ||
    backgroundImage.url.includes('4d5a7152eb4a9381f6727326fe960fe5c818498b');

  const isGraphieImage = !isBrokenGraph && (
    backgroundImage.url.startsWith('web+graphie://') ||
    backgroundImage.url.includes('ka-perseus-graphie') ||
    (backgroundImage.url.includes('kastatic.org') && backgroundImage.url.includes('graphie'))
  );

  // Use GraphieImage component for graphie images to properly render labels from data.json
  if (isGraphieImage) {
    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="image">
        <figure className="athena-image-figure">
          <GraphieImage
            url={backgroundImage.url}
            alt={options.alt || ''}
            style={{
              maxWidth: '100%',
              height: 'auto',
            }}
          />
          {/* Caption */}
          {options.caption && (
            <figcaption className="athena-image-caption">
              {options.caption}
            </figcaption>
          )}
        </figure>
      </BaseWidgetWrapper>
    );
  }

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="image">
      <figure className="athena-image-figure">
        {/* CSS INJECTION FOR STATIC GRAPH FIXES */}
        <style>{`
          /* Dark Mode: Invert colors for fixed graphs (white background -> black) */
          :root.dark .target-graph-fix,
          .dark .target-graph-fix,
          [data-theme="dark"] .target-graph-fix {
            filter: invert(1) hue-rotate(180deg) !important;
            mix-blend-mode: screen !important;
            background-color: transparent !important;
          }
          
          /* Light Mode: No filter */
          .target-graph-fix {
            transition: filter 0.3s ease;
          }

          /* Force White Background for specific diagrams in Dark Mode (e.g. Cell Diagram) */
          .athena-theme-dark .force-white-bg,
          :root.dark .force-white-bg,
          .dark .force-white-bg,
          [data-theme="dark"] .force-white-bg {
             background-color: white !important;
             padding: 8px !important;
             border-radius: 4px !important;
          }
        `}</style>
        {/* Loading state */}
        {isLoading && (
          <div
            className="athena-image-loading"
            style={{
              width: backgroundImage.width,
              height: backgroundImage.height,
            }}
          >
            <div className="athena-image-spinner" />
          </div>
        )}

        {/* Error state */}
        {hasError && (
          <div
            className="athena-image-error"
            style={{
              width: backgroundImage.width,
              height: backgroundImage.height,
            }}
          >
            <ImageBrokenIcon />
            <span>Failed to load image</span>
          </div>
        )}

        {/* Image */}
        <div
          className={`athena-image-container ${isZoomed ? 'zoomed' : ''}`}
          onClick={handleZoomToggle}
          onKeyDown={handleKeyDown}
          role="button"
          tabIndex={0}
          aria-label={`${options.alt || 'Image'}. Click to ${isZoomed ? 'zoom out' : 'zoom in'}`}
          style={{ position: 'relative', display: 'inline-block' }}
        >
          <img
            key={`${widgetId}-img-${fallbackAttempt}`}
            ref={imageRef}
            src={imageUrl}
            alt={options.alt || ''}
            width={backgroundImage.width}
            height={backgroundImage.height}
            onLoad={handleLoad}
            onError={handleError}
            // Logic: Add 'target-graph-fix' class if:
            // 1. URL matches the specific broken graph hash (0b4108...)
            // 2. Alt text contains 'graph' (heuristic)
            className={`athena-image ${isLoading ? 'loading' : ''} ${(imageUrl.includes('0b4108cbcbb425020a161877aa5ead3750ea88d3') ||
              imageUrl.includes('69334af918bcab85650eed24') ||
              imageUrl.toLowerCase().includes('graphie') ||
              imageUrl.toLowerCase().includes('perseus') ||
              imageUrl.includes('fixed_graphs') ||
              imageUrl.toLowerCase().includes('.svg') ||
              (options.alt && (
                options.alt.toLowerCase().includes('graph') ||
                options.alt.toLowerCase().includes('diagram') ||
                options.alt.toLowerCase().includes('drawing') ||
                options.alt.toLowerCase().includes('figure') ||
                options.alt.toLowerCase().includes('axis') ||
                options.alt.toLowerCase().includes('axes') ||
                options.alt.toLowerCase().includes('plot') ||
                options.alt.toLowerCase().includes('coordinate') ||
                options.alt.toLowerCase().includes('illustration')
              ))) &&
              // EXCLUDE photographs and natural images from inversion fix
              !(
                (imageUrl.toLowerCase().match(/\.jpe?g($|\?)/)) ||
                (options.alt && (
                  /\b(beaver|castor|samurai|photograph|photo|forest|star|sky|night|banana|fruit|apple|orange|pear|grape|strawberry|rabbit|bunny|lapin|dog|cat|bird|fish|animal|nature|landscape|pig)s?\b|\bbunnies\b/i.test(options.alt)
                )) ||
                imageUrl.includes('question_69324cd9_forest')
              )
              ? 'target-graph-fix'
              : (imageUrl.includes('90d20d92234515a0ce3d81f731fc210615df78fe'))
                ? 'force-white-bg'
                : ''
              }`}
            referrerPolicy="no-referrer"
            style={{
              display: hasError ? 'none' : 'block',
              maxWidth: '100%',
              height: 'auto',
            }}
          />


          {/* Labels overlaid on image */}
          {Array.isArray(options.labels) && options.labels.length > 0 && !isLoading && !hasError && (
            <div
              className="athena-image-labels"
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
              }}
            >
              {options.labels.map((label, index) => {
                if (!label || !label.coordinates || !Array.isArray(label.coordinates)) return null;
                const [x, y] = label.coordinates;
                const imgWidth = backgroundImage?.width || 400;
                const imgHeight = backgroundImage?.height || 300;

                return (
                  <div
                    key={index}
                    className={`athena-image-label athena-image-label-${label.alignment || 'center'}`}
                    style={{
                      position: 'absolute',
                      left: `${(x / imgWidth) * 100}%`,
                      top: `${(y / imgHeight) * 100}%`,
                      transform: 'translate(-50%, -50%)',
                      backgroundColor: theme === 'dark' ? 'rgba(0,0,0,0.7)' : 'rgba(255,255,255,0.9)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '14px',
                      fontWeight: 500,
                      color: theme === 'dark' ? '#fff' : '#333',
                      whiteSpace: 'nowrap',
                      boxShadow: theme === 'dark' ? '0 1px 3px rgba(255,255,255,0.1)' : '0 1px 3px rgba(0,0,0,0.2)',
                    }}
                    dangerouslySetInnerHTML={{ __html: renderLabelContent(label.content || '') }}
                  />
                );
              })}
            </div>
          )}

          {/* Zoom indicator */}
          {!isZoomed && !hasError && !isLoading && (
            <div className="athena-image-zoom-hint">
              <ZoomIcon />
            </div>
          )}
        </div>

        {/* Caption */}
        {options.caption && (
          <figcaption className="athena-image-caption">
            {options.caption}
          </figcaption>
        )}
      </figure>

      {/* Zoomed overlay */}
      {isZoomed && (
        <div
          className="athena-image-overlay"
          onClick={handleZoomToggle}
          role="dialog"
          aria-modal="true"
          aria-label="Zoomed image"
        >
          <div className="athena-image-overlay-content">
            <img
              src={imageUrl}
              alt={options.alt || ''}
              className="athena-image-zoomed"
            />
            <button
              className="athena-image-close"
              onClick={handleZoomToggle}
              aria-label="Close zoomed image"
            >
              <CloseIcon />
            </button>
          </div>
        </div>
      )}
    </BaseWidgetWrapper>
  );
}

function ZoomIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" />
      <path d="M12 10h-2v2H9v-2H7V9h2V7h1v2h2v1z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
    </svg>
  );
}

function ImageBrokenIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21 5v6.59l-3-3.01-4 4.01-4-4-4 4-3-3.01V5c0-1.1.9-2 2-2h14c1.1 0 2 .9 2 2zm-3 6.42l3 3.01V19c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2v-6.58l3 2.99 4-4 4 4 4-3.99z" />
    </svg>
  );
}

export default ImageWidget;
