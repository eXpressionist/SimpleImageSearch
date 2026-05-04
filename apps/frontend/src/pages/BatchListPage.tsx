import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BatchCard } from '@/components/batch/BatchCard';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { useBatches, useDeleteBatch } from '@/hooks/useBatches';

export function BatchListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const pageSize = 12;

  const { data, isLoading, error, refetch } = useBatches(page, pageSize);
  const deleteBatch = useDeleteBatch();

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this batch?')) return;

    await deleteBatch.mutateAsync(id);
    await refetch();
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <section className="page-stack">
      <div className="page-title-row">
        <h1>Batches</h1>
        <button className="button button--primary" type="button" onClick={() => navigate('/import')}>
          + Import
        </button>
      </div>

      <ErrorAlert error={error} />
      <ErrorAlert error={deleteBatch.error} />

      {isLoading ? (
        <div className="center-panel">
          <span className="spinner" />
        </div>
      ) : data?.items.length === 0 ? (
        <div className="empty-state">
          <h2>No batches yet</h2>
          <p>Create your first batch to start searching for images.</p>
        </div>
      ) : (
        <>
          <div className="batch-grid">
            {data?.items.map((batch) => (
              <BatchCard key={batch.id} batch={batch} onDelete={handleDelete} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="button button--ghost"
                type="button"
                disabled={page === 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </button>
              <span className="muted">
                Page {page} of {totalPages}
              </span>
              <button
                className="button button--ghost"
                type="button"
                disabled={page === totalPages}
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
