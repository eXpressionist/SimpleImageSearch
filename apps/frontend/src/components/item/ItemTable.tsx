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

function formatMime(mime: string): string {
  return mime.split('/')[1]?.toUpperCase() || mime;
}

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
            <th>Thumbnails (10)</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const thumbnails = getThumbnails(item);
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
                      {thumbnails.map((thumb, index) => (
                        <a
                          key={`${thumb.url}-${index}`}
                          className="thumb-card"
                          href={thumb.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <img src={thumb.url} alt={thumb.title || `Thumb ${index + 1}`} loading="lazy" />
                          <span className="thumb-card__top">{thumb.width}x{thumb.height}</span>
                          <span className="thumb-card__bottom">
                            {formatFileSize(thumb.file_size)} · {formatMime(thumb.mime_type)}
                          </span>
                        </a>
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
