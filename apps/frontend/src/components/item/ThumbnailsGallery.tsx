import type { ThumbnailInfo } from '@/types/api';

interface ThumbnailsGalleryProps {
  thumbnails: ThumbnailInfo[];
  selectedIndex: number | null;
  onSelect?: (index: number) => void;
  onOpenOriginal?: (thumbnail: ThumbnailInfo) => void;
}

export function ThumbnailsGallery({
  thumbnails,
  selectedIndex,
  onSelect,
  onOpenOriginal,
}: ThumbnailsGalleryProps) {
  if (!thumbnails || thumbnails.length === 0) {
    return <p className="muted">No thumbnails available</p>;
  }

  return (
    <div className="thumbnail-gallery">
      <p className="muted">{thumbnails.length} thumbnails found</p>

      <div className="thumbnail-grid">
        {thumbnails.map((thumb, index) => (
          <button
            key={`${thumb.url}-${index}`}
            className={`thumbnail-choice ${selectedIndex === index ? 'is-selected' : ''}`}
            type="button"
            onClick={() => onSelect?.(index)}
          >
            <span className="thumbnail-choice__image">
              <img src={thumb.url} alt={thumb.title || `Thumbnail ${index + 1}`} loading="lazy" />
              {selectedIndex === index && <span className="selected-mark">✓</span>}
              <span className="thumbnail-choice__meta">
                <span>{thumb.width}x{thumb.height}</span>
                {onOpenOriginal && (
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(event) => {
                      event.stopPropagation();
                      onOpenOriginal(thumb);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        event.stopPropagation();
                        onOpenOriginal(thumb);
                      }
                    }}
                  >
                    Open
                  </span>
                )}
              </span>
            </span>

            <span className="thumbnail-choice__text">
              {thumb.title && <strong>{thumb.title}</strong>}
              <small>
                {thumb.mime_type} · {thumb.width}x{thumb.height}
              </small>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function parseThumbnails(imageDirectUrl: string | null): ThumbnailInfo[] {
  if (!imageDirectUrl) return [];

  try {
    const parsed = JSON.parse(imageDirectUrl);
    if (Array.isArray(parsed)) {
      return parsed as ThumbnailInfo[];
    }
  } catch (error) {
    console.error('Failed to parse thumbnails:', error);
  }

  return [];
}
