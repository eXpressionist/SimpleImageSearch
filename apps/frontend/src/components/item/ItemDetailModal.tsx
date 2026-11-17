import { ResilientImage } from '@/components/common/ResilientImage';
import { getPreviewSources, getThumbnails } from '@/utils/images';
import { StatusBadge } from '@/components/common/StatusBadge';
import type { ItemWithImageResponse } from '@/types/api';

interface ItemDetailModalProps {
  item: ItemWithImageResponse | null;
  open: boolean;
  onClose: () => void;
  onRetry?: (id: string) => void;
}

export function ItemDetailModal({ item, open, onClose, onRetry }: ItemDetailModalProps) {
  if (!open || !item) return null;
  const thumbnail = getThumbnails(item.image)[0];

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="item-modal-title" onClick={(event) => event.stopPropagation()}>
        <header className="modal__header">
          <div>
            <h2 id="item-modal-title">Item #{item.position + 1}</h2>
            <StatusBadge status={item.status} />
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close item details">
            x
          </button>
        </header>

        <div className="modal__body item-detail-grid">
          <div>
            {item.image && thumbnail ? (
              <ResilientImage className="detail-image" sources={getPreviewSources(item.image, thumbnail)} alt={thumbnail.title || item.image.file_name} loading="eager" />
            ) : (
              <div className="image-placeholder image-placeholder--large">No image</div>
            )}
          </div>

          <dl className="detail-list">
            <dt>Original Query</dt>
            <dd>{item.original_query}</dd>

            <dt>Normalized Query</dt>
            <dd>{item.normalized_query}</dd>

            {item.error_message && (
              <>
                <dt>Error</dt>
                <dd className="danger-text">{item.error_message}</dd>
              </>
            )}

            {item.image && item.image.mime_type !== 'application/json' && (
              <>
                <dt>File Info</dt>
                <dd>
                  <div>Name: {item.image.file_name}</div>
                  <div>Size: {(item.image.file_size / 1024).toFixed(1)} KB</div>
                  {item.image.width && item.image.height && (
                    <div>
                      Dimensions: {item.image.width} x {item.image.height}
                    </div>
                  )}
                  <div>Type: {item.image.mime_type}</div>
                </dd>
              </>
            )}
          </dl>
        </div>

        <footer className="modal__actions">
          {thumbnail && (
            <a className="button button--ghost" href={thumbnail.url} target="_blank" rel="noopener noreferrer">
              Open Original
            </a>
          )}
          {['failed', 'review_needed'].includes(item.status) && onRetry && (
            <button
              className="button button--primary"
              type="button"
              onClick={() => {
                onRetry(item.id);
                onClose();
              }}
            >
              Retry
            </button>
          )}
          <button className="button button--ghost" type="button" onClick={onClose}>
            Close
          </button>
        </footer>
      </section>
    </div>
  );
}
