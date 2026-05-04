import type { BatchStatsResponse } from '@/types/api';

interface BatchProgressBarProps {
  stats: BatchStatsResponse;
  total: number;
}

export function BatchProgressBar({ stats, total }: BatchProgressBarProps) {
  const processed = stats.saved + stats.failed + stats.review_needed;
  const progress = total > 0 ? (processed / total) * 100 : 0;
  const isProcessing = stats.pending > 0 || stats.searching > 0 || stats.downloading > 0;

  return (
    <div className="progress-panel">
      <div className="progress-panel__header">
        <div className="progress-panel__title">
          <span>
            {processed} / {total} items processed
          </span>
          {isProcessing && (
            <span className="processing-label">
              <span className="mini-spinner" aria-hidden="true" />
              Processing...
            </span>
          )}
        </div>
        <span className="muted">{progress.toFixed(0)}%</span>
      </div>

      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
        {isProcessing && <div className="progress-shimmer" />}
      </div>

      <div className="status-stats">
        <StatusStat label="Pending" value={stats.pending} tone="muted" active={stats.pending > 0 && stats.searching === 0 && stats.downloading === 0} />
        <StatusStat label="Searching" value={stats.searching} tone="info" active={stats.searching > 0} />
        <StatusStat label="Downloading" value={stats.downloading} tone="info" active={stats.downloading > 0} />
        <StatusStat label="Saved" value={stats.saved} tone="success" />
        <StatusStat label="Failed" value={stats.failed} tone="danger" />
        <StatusStat label="Review" value={stats.review_needed} tone="warning" />
      </div>
    </div>
  );
}

function StatusStat({
  label,
  value,
  tone,
  active = false,
}: {
  label: string;
  value: number;
  tone: 'muted' | 'info' | 'success' | 'danger' | 'warning';
  active?: boolean;
}) {
  if (value === 0 && !active) return null;

  return (
    <span className={`status-stat status-stat--${tone} ${active ? 'is-active' : ''}`}>
      <span className="status-dot" aria-hidden="true" />
      {label}: {value}
    </span>
  );
}
