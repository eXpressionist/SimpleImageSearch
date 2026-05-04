import { useNavigate } from 'react-router-dom';
import { StatusBadge } from '@/components/common/StatusBadge';
import type { BatchResponse } from '@/types/api';

interface BatchCardProps {
  batch: BatchResponse;
  onDelete?: (id: string) => void;
}

export function BatchCard({ batch, onDelete }: BatchCardProps) {
  const navigate = useNavigate();

  return (
    <article className="card batch-card">
      <div className="batch-card__header">
        <h2 title={batch.name}>{batch.name}</h2>
        <StatusBadge status={batch.status} />
      </div>

      <p className="muted">
        {batch.total_items} items · {batch.processed_items} processed
        {batch.failed_items > 0 && ` · ${batch.failed_items} failed`}
      </p>

      <div className="compact-progress" aria-label={`${batch.progress_percent.toFixed(0)}% complete`}>
        <div style={{ width: `${batch.progress_percent}%` }} />
      </div>
      <p className="caption">{batch.progress_percent.toFixed(0)}% complete</p>
      <p className="caption">Created: {new Date(batch.created_at).toLocaleString()}</p>

      <div className="actions">
        <button className="button button--ghost" type="button" onClick={() => navigate(`/batches/${batch.id}`)}>
          View Details
        </button>
        {onDelete && batch.status !== 'processing' && (
          <button className="button button--danger" type="button" onClick={() => onDelete(batch.id)}>
            Delete
          </button>
        )}
      </div>
    </article>
  );
}
