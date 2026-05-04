import { StatusBadge } from '@/components/common/StatusBadge';
import { CopyableText } from '@/components/common/CopyableText';
import type { ItemWithImageResponse, ThumbnailInfo } from '@/types/api';

function getThumbnails(item: ItemWithImageResponse): ThumbnailInfo[] {
  if (!item.image?.direct_url) return [];
  try {
    return JSON.parse(item.image.direct_url) as ThumbnailInfo[];
  } catch {
    return [];
  }
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return '-';
  return `${Math.round(bytes / 1024)} KB`;
}

interface ItemGalleryProps {
  items: ItemWithImageResponse[];
  onItemClick?: (item: ItemWithImageResponse) => void;
}

export function ItemGallery({ items, onItemClick }: ItemGalleryProps) {
  return (
    <div className="item-list">
      {items.map((item) => {
        const thumbnails = getThumbnails(item);
        return (
          <article
            key={item.id}
            className={`item-row ${onItemClick ? 'is-clickable' : ''}`}
            onClick={() => onItemClick?.(item)}
          >
            <div className="item-row__header">
              <strong>{item.position + 1}.</strong>
              <CopyableText text={item.original_query} className="item-query" />
              <StatusBadge status={item.status} />
            </div>

            {thumbnails.length > 0 ? (
              <div className="thumb-strip">
                {thumbnails.map((thumb, index) => (
                  <a
                    key={`${thumb.url}-${index}`}
                    className="thumb-card thumb-card--compact"
                    href={thumb.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <img src={thumb.url} alt={thumb.title || `Thumb ${index + 1}`} loading="lazy" />
                    <span>
                      {thumb.width}x{thumb.height} · {formatFileSize(thumb.file_size)} ·{' '}
                      {thumb.mime_type.split('/')[1]}
                    </span>
                  </a>
                ))}
              </div>
            ) : (
              <p className="caption">No thumbnails</p>
            )}
          </article>
        );
      })}
    </div>
  );
}
