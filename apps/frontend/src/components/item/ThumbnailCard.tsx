import { ResilientImage } from '@/components/common/ResilientImage';
import type { ImageResponse, ThumbnailInfo } from '@/types/api';
import { formatDimensions, formatFileSize, formatMime, getPreviewSources } from '@/utils/images';

interface ThumbnailCardProps {
  image: ImageResponse;
  thumbnail: ThumbnailInfo;
  compact?: boolean;
}

export function ThumbnailCard({ image, thumbnail, compact = false }: ThumbnailCardProps) {
  return (
    <a
      className={`thumb-card ${compact ? 'thumb-card--compact' : ''}`}
      href={thumbnail.url}
      target="_blank"
      rel="noopener noreferrer"
      title={thumbnail.title || 'Open original image'}
      onClick={(event) => event.stopPropagation()}
    >
      <ResilientImage
        sources={getPreviewSources(image, thumbnail)}
        alt={thumbnail.title || `Image ${thumbnail.position + 1}`}
      />
      {!compact && <span className="thumb-card__top">{formatDimensions(thumbnail)}</span>}
      <span className={compact ? 'thumb-card__meta' : 'thumb-card__bottom'}>
        <span>{compact && `${formatDimensions(thumbnail)} · `}{formatFileSize(thumbnail.file_size)}</span>
        <span>{formatMime(thumbnail.mime_type)}</span>
      </span>
    </a>
  );
}
