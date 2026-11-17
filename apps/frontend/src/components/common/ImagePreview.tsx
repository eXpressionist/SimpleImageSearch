import { ResilientImage } from '@/components/common/ResilientImage';
import { formatFileSize, getPreviewSources, getThumbnails } from '@/utils/images';
import type { ImageResponse } from '@/types/api';

interface ImagePreviewProps {
  image: ImageResponse | null;
  height?: number;
}

export function ImagePreview({ image, height = 150 }: ImagePreviewProps) {
  const thumbnail = getThumbnails(image)[0];
  if (!image || !thumbnail) {
    return (
      <div className="image-placeholder" style={{ height }}>
        No image
      </div>
    );
  }

  return (
    <div className="image-preview">
      <ResilientImage
        sources={getPreviewSources(image, thumbnail)}
        alt={thumbnail.title || image.file_name}
        style={{ height }}
        loading="lazy"
      />
      <span className="image-preview__meta">{formatFileSize(thumbnail.file_size)}</span>
    </div>
  );
}
