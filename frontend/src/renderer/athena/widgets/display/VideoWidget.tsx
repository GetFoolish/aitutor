/**
 * Video Widget
 *
 * Embed videos from YouTube, Vimeo, and other sources.
 * Supports:
 * - YouTube videos (including YouTube Shorts)
 * - Khan Academy videos
 * - Custom video URLs
 */

import React, { useState, useCallback, useMemo } from 'react';
import type { WidgetProps } from '../WidgetRegistry';
import type { VideoOptions } from '../../core/types';
import { BaseWidgetWrapper } from '../base/BaseWidget';

export interface VideoWidgetProps extends WidgetProps<VideoOptions> {}

/**
 * Extract YouTube video ID from various URL formats
 */
function extractYouTubeId(url: string): string | null {
  if (!url) return null;

  // Handle youtube.com/watch?v=ID
  const watchMatch = url.match(/(?:youtube\.com\/watch\?v=|youtube\.com\/watch\?.*&v=)([a-zA-Z0-9_-]{11})/);
  if (watchMatch) return watchMatch[1];

  // Handle youtu.be/ID
  const shortMatch = url.match(/youtu\.be\/([a-zA-Z0-9_-]{11})/);
  if (shortMatch) return shortMatch[1];

  // Handle youtube.com/embed/ID
  const embedMatch = url.match(/youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/);
  if (embedMatch) return embedMatch[1];

  // Handle youtube.com/v/ID
  const vMatch = url.match(/youtube\.com\/v\/([a-zA-Z0-9_-]{11})/);
  if (vMatch) return vMatch[1];

  // Handle shorts
  const shortsMatch = url.match(/youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/);
  if (shortsMatch) return shortsMatch[1];

  return null;
}

/**
 * Extract Khan Academy video slug
 */
function extractKhanAcademySlug(url: string): string | null {
  if (!url) return null;

  const match = url.match(/khanacademy\.org\/.*\/v\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];

  return null;
}

/**
 * Get embed URL for various video providers
 */
function getEmbedUrl(location: string): { url: string; provider: string } | null {
  if (!location) return null;

  // YouTube
  const youtubeId = extractYouTubeId(location);
  if (youtubeId) {
    return {
      url: `https://www.youtube.com/embed/${youtubeId}?rel=0&modestbranding=1`,
      provider: 'youtube',
    };
  }

  // Khan Academy
  const kaSlug = extractKhanAcademySlug(location);
  if (kaSlug) {
    return {
      url: `https://www.khanacademy.org/embed_video?v=${kaSlug}`,
      provider: 'khan-academy',
    };
  }

  // Vimeo
  const vimeoMatch = location.match(/vimeo\.com\/(\d+)/);
  if (vimeoMatch) {
    return {
      url: `https://player.vimeo.com/video/${vimeoMatch[1]}`,
      provider: 'vimeo',
    };
  }

  // Direct video URL (mp4, webm, etc.)
  if (/\.(mp4|webm|ogg|mov)(\?.*)?$/i.test(location)) {
    return {
      url: location,
      provider: 'direct',
    };
  }

  // Assume it's a direct embed URL
  if (location.startsWith('http')) {
    return {
      url: location,
      provider: 'unknown',
    };
  }

  return null;
}

export function VideoWidget({
  widgetId,
  widget,
  theme = 'light',
}: VideoWidgetProps) {
  const options = widget.options || {};
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const embedInfo = useMemo(() => {
    return getEmbedUrl(options.location || '');
  }, [options.location]);

  const handleLoad = useCallback(() => {
    setIsLoading(false);
  }, []);

  const handleError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  if (!embedInfo) {
    return (
      <BaseWidgetWrapper widgetId={widgetId} widgetType="video">
        <div className="athena-video-placeholder" style={{
          padding: '40px 20px',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px',
          textAlign: 'center',
          color: '#666',
        }}>
          <VideoIcon />
          <p style={{ marginTop: '12px' }}>No video specified</p>
        </div>
      </BaseWidgetWrapper>
    );
  }

  const aspectRatio = options.aspectRatio || '16:9';
  const [w, h] = aspectRatio.split(':').map(Number);
  const paddingBottom = `${(h / w) * 100}%`;

  return (
    <BaseWidgetWrapper widgetId={widgetId} widgetType="video">
      <div className="athena-video-container">
        {/* Video wrapper with aspect ratio */}
        <div
          className="athena-video-wrapper"
          style={{
            position: 'relative',
            width: '100%',
            paddingBottom,
            backgroundColor: '#000',
            borderRadius: '8px',
            overflow: 'hidden',
          }}
        >
          {/* Loading state */}
          {isLoading && (
            <div
              className="athena-video-loading"
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#1a1a1a',
              }}
            >
              <div className="athena-video-spinner" style={{
                width: '40px',
                height: '40px',
                border: '3px solid rgba(255,255,255,0.2)',
                borderTopColor: '#fff',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }} />
            </div>
          )}

          {/* Error state */}
          {hasError && (
            <div
              className="athena-video-error"
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#1a1a1a',
                color: '#999',
              }}
            >
              <VideoErrorIcon />
              <span style={{ marginTop: '12px' }}>Failed to load video</span>
            </div>
          )}

          {/* Video iframe or native video */}
          {embedInfo.provider === 'direct' ? (
            <video
              src={embedInfo.url}
              controls
              onLoadedData={handleLoad}
              onError={handleError}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
              }}
              aria-label={options.caption || 'Video'}
            >
              Your browser does not support the video tag.
            </video>
          ) : (
            <iframe
              src={embedInfo.url}
              title={options.caption || 'Video'}
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              onLoad={handleLoad}
              onError={handleError}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                display: hasError ? 'none' : 'block',
              }}
            />
          )}
        </div>

        {/* Caption */}
        {options.caption && (
          <div className="athena-video-caption" style={{
            marginTop: '8px',
            padding: '8px 12px',
            fontSize: '14px',
            color: '#666',
            backgroundColor: '#f9f9f9',
            borderRadius: '4px',
          }}>
            {options.caption}
          </div>
        )}

        {/* Provider badge */}
        {embedInfo.provider !== 'unknown' && embedInfo.provider !== 'direct' && (
          <div className="athena-video-provider" style={{
            marginTop: '4px',
            fontSize: '12px',
            color: '#999',
            textTransform: 'capitalize',
          }}>
            via {embedInfo.provider.replace('-', ' ')}
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </BaseWidgetWrapper>
  );
}

function VideoIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
    </svg>
  );
}

function VideoErrorIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21 6.5l-4 4V7c0-.55-.45-1-1-1H9.82L21 17.18V6.5zM3.27 2L2 3.27 4.73 6H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.21 0 .39-.08.55-.18L19.73 21 21 19.73 3.27 2z"/>
    </svg>
  );
}

export default VideoWidget;
