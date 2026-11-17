import { getImageFileUrl, getImagePreviewUrl } from '@/api/client';
import type { ImageResponse, ThumbnailInfo } from '@/types/api';

export function httpImageUrl(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  try {
    const url = new URL(value);
    if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) return url.href;
  } catch {
    // Older assets can contain a JSON list instead of a URL.
  }
  return undefined;
}

function positiveNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
}

export function parseThumbnails(payload: string | null): ThumbnailInfo[] {
  if (!payload) return [];
  try {
    const parsed: unknown = JSON.parse(payload);
    if (!Array.isArray(parsed)) return [];
    return parsed.flatMap((entry: unknown, index): ThumbnailInfo[] => {
      if (!entry || typeof entry !== 'object') return [];
      const value = entry as Record<string, unknown>;
      const url = httpImageUrl(value.url);
      if (!url) return [];
      return [{
        position: index,
        url,
        thumbnail_url: httpImageUrl(value.thumbnail_url),
        source_url: httpImageUrl(value.source_url) || '',
        title: typeof value.title === 'string' ? value.title : '',
        mime_type: typeof value.mime_type === 'string' ? value.mime_type : 'image/jpeg',
        width: positiveNumber(value.width),
        height: positiveNumber(value.height),
        file_size: positiveNumber(value.file_size),
      }];
    });
  } catch {
    return [];
  }
}

export function getThumbnails(image: ImageResponse | null): ThumbnailInfo[] {
  if (!image) return [];
  if (image.mime_type === 'application/json') return parseThumbnails(image.direct_url);
  return [{
    position: 0,
    url: httpImageUrl(image.direct_url) || getImageFileUrl(image.id),
    source_url: image.source_url,
    title: image.file_name,
    mime_type: image.mime_type,
    width: image.width,
    height: image.height,
    file_size: image.file_size,
  }];
}

export function getPreviewSources(image: ImageResponse, thumbnail: ThumbnailInfo): string[] {
  return [
    ...(image.file_path ? [getImageFileUrl(image.id)] : []),
    ...(thumbnail.thumbnail_url ? [thumbnail.thumbnail_url] : []),
    getImagePreviewUrl(image.id, thumbnail.position),
    thumbnail.url,
  ];
}

export function formatFileSize(bytes: number | null): string {
  if (bytes === null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatDimensions(thumbnail: ThumbnailInfo): string {
  return thumbnail.width && thumbnail.height ? `${thumbnail.width}x${thumbnail.height}` : 'Unknown size';
}

export function formatMime(mime: string): string {
  return mime.split('/')[1]?.toUpperCase() || mime;
}
