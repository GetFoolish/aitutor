/**
 * Image URL Migrator
 *
 * Handles migration of Perseus image URLs to modern CDN-based URLs.
 * Perseus uses several image URL formats:
 * - web+graphie://ka-perseus-graphie.s3.amazonaws.com/...
 * - https://ka-perseus-images.s3.amazonaws.com/...
 * - Relative paths
 */

import type { AthenaImage } from '../core/types';

export interface ImageMigrationOptions {
  /** Base URL for the CDN */
  cdnBaseUrl?: string;
  /** Whether to convert HTTP to HTTPS */
  forceHttps?: boolean;
  /** Custom URL transformer */
  customTransformer?: (url: string) => string;
}

/**
 * Migrates Perseus image URLs to modern format
 */
export class ImageURLMigrator {
  private cdnBaseUrl: string;
  private forceHttps: boolean;
  private customTransformer?: (url: string) => string;

  constructor(cdnBaseUrl?: string, options: ImageMigrationOptions = {}) {
    this.cdnBaseUrl = cdnBaseUrl || 'https://ka-perseus-images.s3.amazonaws.com';
    this.forceHttps = options.forceHttps ?? true;
    this.customTransformer = options.customTransformer;
  }

  /**
   * Migrate a single URL
   */
  migrateUrl(url: string): string {
    if (!url || typeof url !== 'string') {
      return url;
    }

    // Apply custom transformer if provided
    if (this.customTransformer) {
      return this.customTransformer(url);
    }

    let result = url;

    // Handle web+graphie:// protocol
    if (result.startsWith('web+graphie://')) {
      result = this.convertWebGraphieUrl(result);
    }

    // Handle relative URLs
    if (result.startsWith('/')) {
      result = this.convertRelativeUrl(result);
    }

    // Handle old S3 URLs
    if (result.includes('.s3.amazonaws.com/')) {
      result = this.modernizeS3Url(result);
    }

    // Force HTTPS if enabled
    if (this.forceHttps && result.startsWith('http://')) {
      result = result.replace('http://', 'https://');
    }

    return result;
  }

  /**
   * Convert web+graphie:// URLs to HTTPS
   * Format: web+graphie://ka-perseus-graphie.s3.amazonaws.com/hash
   *
   * Uses PNG format because PNG images have labels baked in.
   * SVG images require fetching -data.json for labels which faces CORS issues.
   */
  private convertWebGraphieUrl(url: string): string {
    // Remove the web+graphie:// prefix
    let path = url.replace('web+graphie://', '');

    // Build the HTTPS URL
    let result: string;

    // The path is usually a full S3 URL without protocol
    if (path.includes('.s3.amazonaws.com/')) {
      result = 'https://' + path;
    } else if (!path.includes('/')) {
      // If it's just a hash, construct the full URL
      result = `https://ka-perseus-graphie.s3.amazonaws.com/${path}`;
    } else {
      result = 'https://' + path;
    }

    // Add .png extension if no extension present
    // PNG is preferred because it has labels baked into the image
    // SVG requires fetching -data.json for labels which faces CORS issues
    if (!result.match(/\.(png|svg|jpg|jpeg|gif|webp)$/i)) {
      result = result + '.png';
    }

    return result;
  }

  /**
   * Convert relative URLs to absolute
   */
  private convertRelativeUrl(url: string): string {
    // Remove leading slash
    const path = url.replace(/^\/+/, '');

    // Construct full URL
    return `${this.cdnBaseUrl}/${path}`;
  }

  /**
   * Modernize old S3 URLs
   */
  private modernizeS3Url(url: string): string {
    // Already HTTPS
    if (url.startsWith('https://')) {
      return url;
    }

    // Convert HTTP to HTTPS
    if (url.startsWith('http://')) {
      return url.replace('http://', 'https://');
    }

    // Add protocol if missing
    if (url.includes('.s3.amazonaws.com/')) {
      return 'https://' + url;
    }

    return url;
  }

  /**
   * Migrate all URLs in a content string
   * Handles markdown image syntax: ![alt](url)
   * And HTML img tags: <img src="url" />
   */
  migrateContent(content: string): string {
    if (!content || typeof content !== 'string') {
      return content;
    }

    let result = content;

    // Handle markdown images: ![alt](url)
    result = result.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
      const migratedUrl = this.migrateUrl(url);
      return `![${alt}](${migratedUrl})`;
    });

    // Handle HTML img tags: <img src="url" ... />
    result = result.replace(/<img([^>]*)\ssrc=["']([^"']+)["']([^>]*)>/gi, (match, before, url, after) => {
      const migratedUrl = this.migrateUrl(url);
      return `<img${before} src="${migratedUrl}"${after}>`;
    });

    // Handle web+graphie:// URLs in other contexts
    result = result.replace(/web\+graphie:\/\/[^\s)"']+/g, (url) => {
      return this.migrateUrl(url);
    });

    return result;
  }

  /**
   * Migrate image URLs in an object recursively
   */
  migrateObject<T>(obj: T): T {
    if (obj === null || obj === undefined) {
      return obj;
    }

    if (typeof obj === 'string') {
      // Check if it looks like a URL
      if (this.looksLikeImageUrl(obj)) {
        return this.migrateUrl(obj) as unknown as T;
      }
      return obj;
    }

    if (Array.isArray(obj)) {
      return obj.map((item) => this.migrateObject(item)) as unknown as T;
    }

    if (typeof obj === 'object') {
      const result: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
        // Special handling for URL-like keys
        if (this.isUrlKey(key) && typeof value === 'string') {
          result[key] = this.migrateUrl(value);
        } else {
          result[key] = this.migrateObject(value);
        }
      }
      return result as T;
    }

    return obj;
  }

  /**
   * Check if a key name suggests it contains a URL
   */
  private isUrlKey(key: string): boolean {
    const urlKeys = [
      'url',
      'src',
      'href',
      'imageUrl',
      'backgroundUrl',
      'thumbnailUrl',
      'posterUrl',
      'location',
    ];
    return urlKeys.includes(key) || key.toLowerCase().endsWith('url');
  }

  /**
   * Check if a string looks like an image URL
   */
  private looksLikeImageUrl(str: string): boolean {
    if (!str || typeof str !== 'string') {
      return false;
    }

    // Check for web+graphie protocol
    if (str.startsWith('web+graphie://')) {
      return true;
    }

    // Check for image file extensions
    const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'];
    const lowerStr = str.toLowerCase();
    if (imageExtensions.some((ext) => lowerStr.includes(ext))) {
      return true;
    }

    // Check for S3 image URLs
    if (str.includes('ka-perseus-images') || str.includes('ka-perseus-graphie')) {
      return true;
    }

    return false;
  }

  /**
   * Migrate AthenaImage data
   */
  migrateImageData(imageData: AthenaImage): AthenaImage {
    return {
      ...imageData,
      url: this.migrateUrl(imageData.url),
    };
  }

  /**
   * Extract all image URLs from content
   */
  extractImageUrls(content: string): string[] {
    const urls: string[] = [];

    if (!content || typeof content !== 'string') {
      return urls;
    }

    // Extract markdown image URLs
    const markdownPattern = /!\[[^\]]*\]\(([^)]+)\)/g;
    let match;
    while ((match = markdownPattern.exec(content)) !== null) {
      urls.push(match[1]);
    }

    // Extract HTML img src URLs
    const htmlPattern = /<img[^>]*\ssrc=["']([^"']+)["'][^>]*>/gi;
    while ((match = htmlPattern.exec(content)) !== null) {
      urls.push(match[1]);
    }

    // Extract web+graphie URLs
    const graphiePattern = /web\+graphie:\/\/[^\s)"']+/g;
    while ((match = graphiePattern.exec(content)) !== null) {
      urls.push(match[0]);
    }

    return urls;
  }

  /**
   * Generate a migration report for content
   */
  generateMigrationReport(content: string): {
    original: string[];
    migrated: string[];
    changes: Array<{ from: string; to: string }>;
  } {
    const original = this.extractImageUrls(content);
    const changes: Array<{ from: string; to: string }> = [];

    for (const url of original) {
      const migrated = this.migrateUrl(url);
      if (migrated !== url) {
        changes.push({ from: url, to: migrated });
      }
    }

    return {
      original,
      migrated: original.map((url) => this.migrateUrl(url)),
      changes,
    };
  }
}

export default ImageURLMigrator;
