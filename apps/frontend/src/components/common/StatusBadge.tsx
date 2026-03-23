import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
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
  searching: 'Searching...',
  downloading: 'Downloading...',
  saved: 'Saved',
  failed: 'Failed',
  review_needed: 'Review',
  processing: 'Processing',
  completed: 'Completed',
  partial: 'Partial',
};

const processingStatuses = ['searching', 'downloading', 'pending'];

interface StatusBadgeProps {
  status: ItemStatus | BatchStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const isProcessing = processingStatuses.includes(status);
  
  return (
    <Chip
      label={
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {isProcessing && (
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                border: '2px solid currentColor',
                borderTopColor: 'transparent',
                animation: 'spin 1s linear infinite',
                '@keyframes spin': {
                  '0%': { transform: 'rotate(0deg)' },
                  '100%': { transform: 'rotate(360deg)' },
                },
              }}
            />
          )}
          {statusLabels[status] || status}
        </Box>
      }
      color={statusColors[status] || 'default'}
      size="small"
      sx={isProcessing ? {
        animation: 'pulse 1.5s ease-in-out infinite',
        '@keyframes pulse': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.7 },
        },
      } : {}}
    />
  );
}
