import { StatusBadge } from '@/components/common/StatusBadge';
import { CopyableText } from '@/components/common/CopyableText';
import { ThumbnailCard } from '@/components/item/ThumbnailCard';
import { getThumbnails } from '@/utils/images';
import type { ItemWithImageResponse } from '@/types/api';

interface ItemTableProps {
  items: ItemWithImageResponse[];
}

export function ItemTable({ items }: ItemTableProps) {
  return (
    <div className="table-scroll">
      <table className="item-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Query</th>
            <th>Status</th>
            <th>Thumbnails</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const image = item.image;
            const thumbnails = getThumbnails(image);
            return (
              <tr key={item.id}>
                <td>{item.position + 1}</td>
                <td>
                  <CopyableText text={item.original_query} />
                  {item.error_message && <p className="caption caption--danger">{item.error_message}</p>}
                </td>
                <td>
                  <StatusBadge status={item.status} />
                </td>
                <td>
                  {thumbnails.length > 0 ? (
                    <div className="thumb-strip">
                      {image && thumbnails.map((thumb) => (
                        <ThumbnailCard key={thumb.position} image={image} thumbnail={thumb} />
                      ))}
                    </div>
                  ) : (
                    <span className="caption">No thumbnails</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
