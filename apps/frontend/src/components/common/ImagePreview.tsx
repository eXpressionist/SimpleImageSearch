import { getImageUrl } from '@/api/client';
import type { ImageResponse } from '@/types/api';

interface ImagePreviewProps {
  image: ImageResponse | null;
  itemId: string;
  height?: number;
}

export function ImagePreview({ image, itemId, height = 150 }: ImagePreviewProps) {
  if (!image) {
    return (
      <div className="image-placeholder" style={{ height }}>
        No image
      </div>
    );
  }

  return (
    <div className="image-preview">
      <img
        src={getImageUrl(itemId)}
        alt={image.file_name}
        style={{ height }}
        loading="lazy"
      />
      <span className="image-preview__meta">{formatSize(image.file_size)}</span>
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
