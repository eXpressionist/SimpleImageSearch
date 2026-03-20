import Chip from '@mui/material/Chip';
import type { ItemStatus, BatchStatus } from '@/types/api';

const statusColors: Record<string, 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'> = {
  pending: 'default',
  searching: 'info',
  downloading: 'info',
  saved: 'success',
  failed: 'error',
  review_needed: 'warning',
  processing: 'primary',
  completed: 'success',
  partial: 'warning',
};

const statusLabels: Record<string, string> = {
  pending: 'Pending',
  searching: 'Searching',
  downloading: 'Downloading',
  saved: 'Saved',
  failed: 'Failed',
  review_needed: 'Review',
  processing: 'Processing',
  completed: 'Completed',
  partial: 'Partial',
};

interface StatusBadgeProps {
  status: ItemStatus | BatchStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Chip
      label={statusLabels[status] || status}
      color={statusColors[status] || 'default'}
      size="small"
    />
  );
}
