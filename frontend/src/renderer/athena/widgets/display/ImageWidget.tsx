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

export interface ImageWidgetProps extends WidgetProps<ImageOptions> {}

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
  }, [backgroundImage?.url, fallbackAttempt]);

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
        <div className="athena-image-placeholder">
          No image specified
        </div>
      </BaseWidgetWrapper>
    );
  }

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="image">
      <figure className="athena-image-figure">
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
            className={`athena-image ${isLoading ? 'loading' : ''}`}
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
                      backgroundColor: 'rgba(255,255,255,0.9)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '14px',
                      fontWeight: 500,
                      color: '#333',
                      whiteSpace: 'nowrap',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
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
      <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
      <path d="M12 10h-2v2H9v-2H7V9h2V7h1v2h2v1z"/>
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
    </svg>
  );
}

function ImageBrokenIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21 5v6.59l-3-3.01-4 4.01-4-4-4 4-3-3.01V5c0-1.1.9-2 2-2h14c1.1 0 2 .9 2 2zm-3 6.42l3 3.01V19c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2v-6.58l3 2.99 4-4 4 4 4-3.99z"/>
    </svg>
  );
}

export default ImageWidget;
