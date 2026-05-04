import type { BatchStatus, ItemStatus } from '@/types/api';

const statusLabels: Record<string, string> = {
  pending: 'Pending',
  searching: 'Searching...',
  downloading: 'Downloading...',
  saved: 'Saved',
  failed: 'Failed',
  review_needed: 'Review',
  processing: 'Processing',
  completed: 'Completed',
  partial: 'Partial',
};

const processingStatuses = ['searching', 'downloading', 'pending', 'processing'];

interface StatusBadgeProps {
  status: ItemStatus | BatchStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const isProcessing = processingStatuses.includes(status);

  return (
    <span className={`status-badge status-badge--${status} ${isProcessing ? 'is-pulsing' : ''}`}>
      {isProcessing && <span className="mini-spinner" aria-hidden="true" />}
      {statusLabels[status] || status}
    </span>
  );
}
