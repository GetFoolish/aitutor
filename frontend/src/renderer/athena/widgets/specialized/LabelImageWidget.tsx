/**
 * Label Image Widget
 *
 * Interactive image labeling widget.
 * Users click on markers to select labels for regions on an image.
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import { BaseWidgetWrapper } from '../base/BaseWidget';
import { ImageURLMigrator } from '../../migration/ImageURLMigrator';
import { GraphieImage } from '../display/GraphieImage';

// Base URL for resolving relative asset URLs (from backend API)
const ASSETS_BASE_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

// Load KaTeX dynamically
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

export interface LabelImageOptions {
  /** Image URL */
  imageUrl?: string;
  /** Alternative text for the image */
  imageAlt?: string;
  /** Image width */
  imageWidth?: number;
  /** Image height */
  imageHeight?: number;
  /** Available label choices */
  choices?: string[];
  /** Marker positions on the image */
  markers?: Array<{
    /** Marker ID (optional - will be auto-generated if missing) */
    id?: string;
    /** X position (can be 0-1 percentage or 0-100 percentage) */
    x: number;
    /** Y position (can be 0-1 percentage or 0-100 percentage) */
    y: number;
    /** Label for this marker */
    label?: string;
    /** Correct answer for this marker (single string) */
    correctAnswer?: string;
    /** Correct answers for this marker (array format from Perseus data) */
    answers?: string[];
  }>;
  /** Whether choices can be reused */
  multipleAnswers?: boolean;
  /** Hide unused choices */
  hideChoicesUsedElsewhere?: boolean;
}

export interface LabelImageWidgetProps extends WidgetProps<LabelImageOptions> {}

interface MarkerSelection {
  [markerId: string]: string | null;
}

const imageUrlMigrator = new ImageURLMigrator();

export function LabelImageWidget({
  widgetId,
  widget,
  value,
  onChange,
  readOnly,
  disabled,
  reviewMode,
  theme = 'light',
}: LabelImageWidgetProps) {
  const options = widget.options || {};
  const choices = Array.isArray(options.choices) ? options.choices : [];
  const imageWidth = options.imageWidth || 400;
  const imageHeight = options.imageHeight || 300;

  // Filter and normalize markers - handle various data formats from Perseus
  const markers = useMemo(() => {
    if (!Array.isArray(options.markers)) return [];

    return options.markers
      .filter((m: any) =>
        m &&
        typeof m.x === 'number' &&
        typeof m.y === 'number' &&
        !isNaN(m.x) &&
        !isNaN(m.y)
      )
      .map((m: any, index: number) => {
        // Generate ID if not present
        const id = m.id || `marker-${index}`;

        // Detect coordinate format:
        // - 0-1 range: already normalized percentage
        // - 0-100 range: percentage that needs to be divided by 100
        // - > 100: likely pixel coordinates
        let x = m.x;
        let y = m.y;

        // Determine if we're dealing with 0-100 percentages or 0-1
        // Most Perseus data uses 0-100 percentage format
        const maxCoord = Math.max(x, y);
        if (maxCoord > 1 && maxCoord <= 100) {
          // 0-100 percentage format - divide by 100
          x = x / 100;
          y = y / 100;
        } else if (maxCoord > 100) {
          // Pixel coordinates - divide by image dimensions
          x = x / imageWidth;
          y = y / imageHeight;
        }
        // else: already 0-1 format

        // Clamp to valid range
        x = Math.max(0, Math.min(1, x));
        y = Math.max(0, Math.min(1, y));

        // Handle correctAnswer vs answers array
        let correctAnswer = m.correctAnswer;
        if (!correctAnswer && Array.isArray(m.answers) && m.answers.length > 0) {
          correctAnswer = m.answers[0];
        }

        return {
          ...m,
          id,
          x,
          y,
          correctAnswer,
        };
      });
  }, [options.markers, imageWidth, imageHeight]);

  const multipleAnswers = options.multipleAnswers ?? true;

  // Debug: log markers for troubleshooting
  useEffect(() => {
    if (options.markers) {
      console.log('[LabelImageWidget] Markers:', {
        original: options.markers,
        normalized: markers,
        imageUrl: options.imageUrl,
        imageWidth,
        imageHeight
      });
    }
  }, [options.markers, markers, options.imageUrl, imageWidth, imageHeight]);

  // Initialize selections from value
  const getInitialSelections = (): MarkerSelection => {
    if (value && typeof value === 'object') {
      return value as MarkerSelection;
    }
    const initial: MarkerSelection = {};
    markers.forEach((marker) => {
      initial[marker.id] = null;
    });
    return initial;
  };

  const [selections, setSelections] = useState<MarkerSelection>(getInitialSelections);
  const [activeMarker, setActiveMarker] = useState<string | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [fallbackAttempt, setFallbackAttempt] = useState(0); // 0: original, 1: .png, 2: .svg, 3: no extension
  const [katex, setKatex] = useState<any>(null);

  // Load KaTeX on mount
  useEffect(() => {
    ensureKaTeX().then(k => setKatex(k));
  }, []);

  // For graphie images, set imageLoaded immediately so markers appear
  useEffect(() => {
    if (isGraphieUrl && !imageLoaded) {
      // Give GraphieImage a moment to render, then show markers
      const timer = setTimeout(() => {
        setImageLoaded(true);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isGraphieUrl, imageLoaded]);

  // Render math in labels
  const renderLabel = useCallback((label: string): string => {
    if (!label) return '';
    let processed = label;

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

    return processed;
  }, [katex]);

  const isDisabled = readOnly || disabled;

  // Check if this is a graphie URL (needs special handling for labels)
  const isGraphieUrl = useMemo(() => {
    const url = options.imageUrl || '';
    return url.startsWith('web+graphie://') ||
           url.includes('ka-perseus-graphie') ||
           url.includes('kastatic.org') && !url.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i);
  }, [options.imageUrl]);

  // Convert image URL with fallback handling
  const imageUrl = useMemo(() => {
    if (!options.imageUrl) return '';

    let url = options.imageUrl;

    // Handle relative URLs (from backend assets)
    if (url.startsWith('/')) {
      url = ASSETS_BASE_URL + url;
    }
    // Handle web+graphie:// URLs - keep original for GraphieImage component
    else if (url.startsWith('web+graphie://')) {
      // Return the original web+graphie:// URL - GraphieImage will handle it
      return url;
    }
    // Handle other relative URLs (no protocol, not starting with /)
    else if (!url.startsWith('http') && !url.startsWith('data:')) {
      url = ASSETS_BASE_URL + '/' + url;
    }

    // For non-graphie images, apply fallback extensions
    if (!isGraphieUrl) {
      const urlWithoutExt = url.replace(/\.(png|svg|jpg|jpeg|gif|webp)$/i, '');

      if (fallbackAttempt === 0) {
        if (!url.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
          url = url + '.png';
        }
      } else if (fallbackAttempt === 1) {
        url = urlWithoutExt + '.svg';
      } else if (fallbackAttempt === 2) {
        url = urlWithoutExt + '.png';
      } else if (fallbackAttempt === 3) {
        url = urlWithoutExt;
      }
    }

    console.log('[LabelImageWidget] Image URL:', { original: options.imageUrl, resolved: url, isGraphie: isGraphieUrl, fallbackAttempt });
    return url;
  }, [options.imageUrl, fallbackAttempt, isGraphieUrl]);

  // Handle image load error with fallback
  const handleImageError = useCallback(() => {
    console.error('[LabelImageWidget] Image failed to load:', imageUrl, 'attempt:', fallbackAttempt);

    // Try next fallback (up to 4 attempts: original, .png, .svg, no extension)
    if (fallbackAttempt < 3) {
      console.log('[LabelImageWidget] Trying next fallback, attempt:', fallbackAttempt + 1);
      setFallbackAttempt(prev => prev + 1);
      setImageLoaded(false);
    } else {
      // All fallbacks failed
      console.error('[LabelImageWidget] All fallback attempts failed');
      setImageError(true);
    }
  }, [imageUrl, fallbackAttempt]);

  // Get used choices (for hiding when multipleAnswers is false)
  const usedChoices = useMemo(() => {
    if (multipleAnswers) return new Set<string>();
    return new Set(Object.values(selections).filter((v) => v !== null) as string[]);
  }, [selections, multipleAnswers]);

  // Get available choices for a marker
  const getAvailableChoices = useCallback(
    (markerId: string): string[] => {
      if (multipleAnswers) return choices;
      const currentSelection = selections[markerId];
      return choices.filter(
        (choice) => !usedChoices.has(choice) || choice === currentSelection
      );
    },
    [choices, multipleAnswers, selections, usedChoices]
  );

  // Handle marker click
  const handleMarkerClick = useCallback(
    (markerId: string) => {
      if (isDisabled) return;
      setActiveMarker((prev) => (prev === markerId ? null : markerId));
    },
    [isDisabled]
  );

  // Handle choice selection
  const handleChoiceSelect = useCallback(
    (markerId: string, choice: string | null) => {
      const newSelections = { ...selections, [markerId]: choice };
      setSelections(newSelections);
      onChange?.(newSelections);
      setActiveMarker(null);
    },
    [selections, onChange]
  );

  // Check if selection is correct
  const isCorrect = (markerId: string): boolean => {
    const marker = markers.find((m) => m.id === markerId);
    if (!marker) return true;

    const userAnswer = selections[markerId];
    if (!userAnswer) return false;

    // Check against correctAnswer string
    if (marker.correctAnswer) {
      return userAnswer === marker.correctAnswer;
    }

    // Check against answers array
    if (Array.isArray(marker.answers) && marker.answers.length > 0) {
      return marker.answers.includes(userAnswer);
    }

    return true;
  };

  const themeStyles = {
    light: {
      bg: '#fff',
      markerBg: '#2196f3',
      markerText: '#fff',
      dropdownBg: '#fff',
      border: '#e0e0e0',
      text: '#333',
      correct: '#4caf50',
      incorrect: '#f44336',
    },
    dark: {
      bg: '#2d2d2d',
      markerBg: '#64b5f6',
      markerText: '#000',
      dropdownBg: '#3d3d3d',
      border: '#555',
      text: '#fff',
      correct: '#81c784',
      incorrect: '#e57373',
    },
    'high-contrast': {
      bg: '#000',
      markerBg: '#ff0',
      markerText: '#000',
      dropdownBg: '#222',
      border: '#fff',
      text: '#fff',
      correct: '#0f0',
      incorrect: '#f00',
    },
  }[theme];

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="label-image">
      <div className="athena-label-image-container">
        {!isDisabled && (
          <div
            className="athena-label-image-instructions"
            style={{
              marginBottom: '12px',
              fontSize: '14px',
              color: '#666',
            }}
          >
            Click on each marker and select the correct label
          </div>
        )}

        {/* Image with markers */}
        <div
          className="athena-label-image-wrapper"
          style={{
            position: 'relative',
            display: 'inline-block',
            maxWidth: '100%',
          }}
        >
          {/* Loading/error states */}
          {!imageLoaded && !imageError && (
            <div
              style={{
                width: options.imageWidth || 400,
                height: options.imageHeight || 300,
                backgroundColor: '#f5f5f5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '8px',
              }}
            >
              <div className="athena-spinner" />
            </div>
          )}

          {imageError && (
            <div
              style={{
                width: options.imageWidth || 400,
                height: options.imageHeight || 300,
                backgroundColor: '#f5f5f5',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '8px',
                color: '#999',
                padding: '16px',
                boxSizing: 'border-box',
              }}
            >
              <ImageErrorIcon />
              <span style={{ marginTop: '8px', fontWeight: 500 }}>Failed to load image</span>
              {imageUrl && (
                <span style={{ marginTop: '4px', fontSize: '12px', wordBreak: 'break-all', textAlign: 'center', maxWidth: '100%' }}>
                  URL: {imageUrl.substring(0, 80)}{imageUrl.length > 80 ? '...' : ''}
                </span>
              )}
              {!options.imageUrl && (
                <span style={{ marginTop: '4px', fontSize: '12px' }}>
                  (No image URL provided - this may require a graph renderer)
                </span>
              )}
            </div>
          )}

          {/* Image - use GraphieImage for graphie URLs to render labels */}
          {isGraphieUrl ? (
            <div
              style={{
                display: 'block',
                maxWidth: '100%',
              }}
              onLoad={() => setImageLoaded(true)}
            >
              <GraphieImage
                url={imageUrl}
                alt={options.imageAlt || 'Image to label'}
                style={{ maxWidth: '100%', height: 'auto' }}
              />
              {/* Force imageLoaded after a short delay for GraphieImage */}
              {!imageLoaded && (
                <img
                  src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                  onLoad={() => setTimeout(() => setImageLoaded(true), 500)}
                  style={{ display: 'none' }}
                  alt=""
                />
              )}
            </div>
          ) : (
            <img
              key={`${widgetId}-img-${fallbackAttempt}`}
              src={imageUrl}
              alt={options.imageAlt || 'Image to label'}
              onLoad={() => {
                console.log('[LabelImageWidget] Image loaded successfully');
                setImageLoaded(true);
              }}
              onError={handleImageError}
              referrerPolicy="no-referrer"
              style={{
                display: imageLoaded && !imageError ? 'block' : 'none',
                maxWidth: '100%',
                height: 'auto',
                borderRadius: '8px',
              }}
            />
          )}

          {/* Markers */}
          {imageLoaded &&
            markers.map((marker, index) => {
              const selection = selections[marker.id];
              const isActive = activeMarker === marker.id;
              const hasSelection = selection !== null;
              const correct = reviewMode && hasSelection && isCorrect(marker.id);
              const incorrect = reviewMode && hasSelection && !isCorrect(marker.id);

              let markerBg = themeStyles.markerBg;
              if (correct) markerBg = themeStyles.correct;
              if (incorrect) markerBg = themeStyles.incorrect;

              return (
                <div
                  key={marker.id}
                  className="athena-label-marker"
                  style={{
                    position: 'absolute',
                    left: `${marker.x * 100}%`,
                    top: `${marker.y * 100}%`,
                    transform: 'translate(-50%, -50%)',
                    zIndex: isActive ? 100 : 10,
                  }}
                >
                  {/* Marker label (a, b, c, etc.) displayed above the dot */}
                  {marker.label && (
                    <div
                      className="athena-marker-label"
                      style={{
                        position: 'absolute',
                        bottom: '100%',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        marginBottom: '4px',
                        fontSize: '16px',
                        fontWeight: 600,
                        fontStyle: 'italic',
                        color: ['#00bcd4', '#e91e63', '#ffc107', '#4caf50', '#9c27b0', '#ff5722'][index % 6],
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {marker.label}
                    </div>
                  )}

                  {/* Marker button */}
                  <button
                    onClick={() => handleMarkerClick(marker.id)}
                    disabled={isDisabled}
                    aria-label={`Marker ${marker.label || index + 1}${selection ? `: ${selection}` : ''}`}
                    aria-expanded={isActive}
                    style={{
                      width: hasSelection ? 'auto' : '32px',
                      minWidth: '32px',
                      height: '32px',
                      padding: hasSelection ? '0 12px' : '0',
                      backgroundColor: markerBg,
                      color: themeStyles.markerText,
                      border: `2px solid ${isActive ? '#fff' : 'transparent'}`,
                      borderRadius: '16px',
                      cursor: isDisabled ? 'default' : 'pointer',
                      fontSize: '14px',
                      fontWeight: 500,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    {hasSelection ? (
                      <span dangerouslySetInnerHTML={{ __html: renderLabel(selection!) }} />
                    ) : (
                      index + 1
                    )}
                  </button>

                  {/* Dropdown */}
                  {isActive && !isDisabled && (
                    <div
                      className="athena-label-dropdown"
                      style={{
                        position: 'absolute',
                        top: '100%',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        marginTop: '8px',
                        backgroundColor: themeStyles.dropdownBg,
                        border: `1px solid ${themeStyles.border}`,
                        borderRadius: '8px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                        minWidth: '150px',
                        overflow: 'hidden',
                      }}
                    >
                      {/* Clear option */}
                      {hasSelection && (
                        <button
                          onClick={() => handleChoiceSelect(marker.id, null)}
                          style={{
                            width: '100%',
                            padding: '10px 16px',
                            backgroundColor: 'transparent',
                            border: 'none',
                            borderBottom: `1px solid ${themeStyles.border}`,
                            color: '#999',
                            fontSize: '14px',
                            textAlign: 'left',
                            cursor: 'pointer',
                          }}
                        >
                          Clear selection
                        </button>
                      )}

                      {/* Choices */}
                      {getAvailableChoices(marker.id).map((choice) => (
                        <button
                          key={choice}
                          onClick={() => handleChoiceSelect(marker.id, choice)}
                          style={{
                            width: '100%',
                            padding: '10px 16px',
                            backgroundColor:
                              selection === choice ? '#e3f2fd' : 'transparent',
                            border: 'none',
                            borderBottom: `1px solid ${themeStyles.border}`,
                            color: themeStyles.text,
                            fontSize: '14px',
                            textAlign: 'left',
                            cursor: 'pointer',
                          }}
                          dangerouslySetInnerHTML={{ __html: renderLabel(choice) }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
        </div>

        {/* Available choices list */}
        {!isDisabled && choices.length > 0 && (
          <div
            className="athena-label-choices"
            style={{
              marginTop: '16px',
              padding: '12px',
              backgroundColor: '#f5f5f5',
              borderRadius: '8px',
            }}
          >
            <div
              style={{
                marginBottom: '8px',
                fontWeight: 500,
                color: themeStyles.text,
                fontSize: '14px',
              }}
            >
              Available labels:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {choices.map((choice) => {
                const isUsed = usedChoices.has(choice);
                return (
                  <span
                    key={choice}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: isUsed ? '#e0e0e0' : '#fff',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '14px',
                      color: isUsed ? '#999' : themeStyles.text,
                      textDecoration: isUsed && !multipleAnswers ? 'line-through' : 'none',
                    }}
                    dangerouslySetInnerHTML={{ __html: renderLabel(choice) }}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Progress */}
        <div
          style={{
            marginTop: '12px',
            fontSize: '14px',
            color: '#666',
          }}
        >
          {Object.values(selections).filter((v) => v !== null).length} of{' '}
          {markers.length} labeled
        </div>
      </div>
    </BaseWidgetWrapper>
  );
}

function ImageErrorIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21 5v6.59l-3-3.01-4 4.01-4-4-4 4-3-3.01V5c0-1.1.9-2 2-2h14c1.1 0 2 .9 2 2zm-3 6.42l3 3.01V19c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2v-6.58l3 2.99 4-4 4 4 4-3.99z" />
    </svg>
  );
}

export default LabelImageWidget;
