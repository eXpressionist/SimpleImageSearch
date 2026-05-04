import { getImageUrl } from '@/api/client';
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
            {item.image ? (
              <img className="detail-image" src={getImageUrl(item.id)} alt={item.image.file_name} />
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

            {item.image && (
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
          {item.image && (
            <a className="button button--ghost" href={item.image.direct_url} target="_blank" rel="noopener noreferrer">
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
