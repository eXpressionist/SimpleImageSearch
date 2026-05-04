import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { BatchProgressBar } from '@/components/batch/BatchProgressBar';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { ItemGallery } from '@/components/item/ItemGallery';
import { ItemTable } from '@/components/item/ItemTable';
import { itemsApi } from '@/api/items';
import { useBatch, useBatchStats } from '@/hooks/useBatches';
import { useBatchItems } from '@/hooks/useBatchItems';
import type { ItemStatus, ItemWithImageResponse } from '@/types/api';

export function BatchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ItemStatus | ''>('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [viewMode, setViewMode] = useState<'table' | 'gallery'>('gallery');
  const [recovering, setRecovering] = useState(false);
  const [recoverError, setRecoverError] = useState<Error | null>(null);

  const { data: batch, isLoading: batchLoading } = useBatch(id || '');
  const { data: stats, refetch: refetchStats } = useBatchStats(id || '');
  const {
    data: itemsData,
    isLoading: itemsLoading,
    error: itemsError,
    refetch: refetchItems,
  } = useBatchItems(id || '', page + 1, rowsPerPage, status || undefined);

  const isProcessing = stats && (stats.pending > 0 || stats.searching > 0 || stats.downloading > 0);
  const hasStuckItems = stats && (stats.searching > 0 || stats.downloading > 0);
  const totalPages = itemsData ? Math.max(1, Math.ceil(itemsData.total / rowsPerPage)) : 1;

  const handleRecoverStuck = async () => {
    if (!id) return;
    setRecovering(true);
    setRecoverError(null);
    try {
      await itemsApi.recoverStuck(id, 2);
      await Promise.all([refetchItems(), refetchStats()]);
    } catch (error) {
      setRecoverError(error instanceof Error ? error : new Error('Failed to recover stuck items'));
    } finally {
      setRecovering(false);
    }
  };

  if (batchLoading) {
    return (
      <div className="center-panel">
        <span className="spinner" />
      </div>
    );
  }

  if (!batch) {
    return (
      <section className="page-stack">
        <ErrorAlert error={new Error('Batch not found')} />
        <button className="button button--ghost" type="button" onClick={() => navigate('/')}>
          Back to batches
        </button>
      </section>
    );
  }

  return (
    <section className="page-stack">
      <div className="detail-header">
        <div className="detail-header__title">
          <button className="button button--ghost" type="button" onClick={() => navigate('/')}>
            Back
          </button>
          <h1>{batch.name}</h1>
        </div>

        <div className="toolbar">
          {hasStuckItems && (
            <button
              className="button button--warning"
              type="button"
              onClick={handleRecoverStuck}
              disabled={recovering}
            >
              {recovering ? 'Recovering...' : 'Recover Stuck'}
            </button>
          )}
          <button
            className={`button ${viewMode === 'gallery' ? 'button--primary' : 'button--ghost'}`}
            type="button"
            onClick={() => setViewMode('gallery')}
          >
            Gallery
          </button>
          <button
            className={`button ${viewMode === 'table' ? 'button--primary' : 'button--ghost'}`}
            type="button"
            onClick={() => setViewMode('table')}
          >
            Table
          </button>
        </div>
      </div>

      {stats && (
        <div className="card">
          <BatchProgressBar stats={stats} total={batch.total_items} />
        </div>
      )}

      {isProcessing && itemsData?.items && <ProcessingIndicator items={itemsData.items} />}

      <div className="card filter-card">
        <label className="field field--inline">
          <span>Filter by status</span>
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as ItemStatus | '');
              setPage(0);
            }}
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="searching">Searching</option>
            <option value="downloading">Downloading</option>
            <option value="saved">Saved</option>
            <option value="failed">Failed</option>
            <option value="review_needed">Review Needed</option>
          </select>
        </label>
      </div>

      <ErrorAlert error={itemsError} />
      <ErrorAlert error={recoverError} onClose={() => setRecoverError(null)} />

      {itemsLoading && !itemsData ? (
        <div className="skeleton-stack">
          {[0, 1, 2, 3, 4].map((item) => (
            <div className="skeleton-row" key={item} />
          ))}
        </div>
      ) : (
        <div className="card result-card">
          {viewMode === 'gallery' ? (
            <ItemGallery items={itemsData?.items || []} />
          ) : (
            <ItemTable items={itemsData?.items || []} />
          )}

          <div className="pagination pagination--right">
            <label className="field field--inline">
              <span>Rows</span>
              <select
                value={rowsPerPage}
                onChange={(event) => {
                  setRowsPerPage(parseInt(event.target.value, 10));
                  setPage(0);
                }}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </label>
            <button
              className="button button--ghost"
              type="button"
              disabled={page === 0}
              onClick={() => setPage((current) => Math.max(0, current - 1))}
            >
              Previous
            </button>
            <span className="muted">
              Page {page + 1} of {totalPages}
            </span>
            <button
              className="button button--ghost"
              type="button"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function ProcessingIndicator({ items }: { items: ItemWithImageResponse[] }) {
  const processingItems = items.filter(
    (item) => item.status === 'searching' || item.status === 'downloading'
  );

  if (processingItems.length === 0) return null;

  return (
    <div className="processing-panel">
      <div className="processing-panel__label">
        <span className="spinner spinner--small" />
        <strong>Now processing:</strong>
      </div>

      <div className="processing-chip-list">
        {processingItems.slice(0, 5).map((item) => (
          <span className="processing-chip" key={item.id}>
            <span>{item.position + 1}.</span>
            <span>{item.original_query}</span>
          </span>
        ))}
        {processingItems.length > 5 && (
          <span className="caption">+{processingItems.length - 5} more</span>
        )}
      </div>
    </div>
  );
}
