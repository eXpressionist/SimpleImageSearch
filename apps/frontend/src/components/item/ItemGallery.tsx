import { StatusBadge } from '@/components/common/StatusBadge';
import { CopyableText } from '@/components/common/CopyableText';
import { ThumbnailCard } from '@/components/item/ThumbnailCard';
import { getThumbnails } from '@/utils/images';
import type { ItemWithImageResponse } from '@/types/api';

interface ItemGalleryProps {
  items: ItemWithImageResponse[];
  onItemClick?: (item: ItemWithImageResponse) => void;
}

export function ItemGallery({ items, onItemClick }: ItemGalleryProps) {
  return (
    <div className="item-list">
      {items.map((item) => {
        const image = item.image;
        const thumbnails = getThumbnails(image);
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
                {image && thumbnails.map((thumb) => (
                  <ThumbnailCard key={thumb.position} image={image} thumbnail={thumb} compact />
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
