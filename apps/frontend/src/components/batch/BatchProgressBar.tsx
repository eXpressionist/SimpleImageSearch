import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';
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
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2">
            {processed} / {total} items processed
          </Typography>
          {isProcessing && (
            <Box 
              sx={{ 
                display: 'inline-flex',
                alignItems: 'center',
                gap: 0.5,
                px: 1,
                py: 0.25,
                borderRadius: 1,
                bgcolor: 'info.light',
                color: 'info.dark',
                animation: 'pulse 1.5s ease-in-out infinite',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 1 },
                  '50%': { opacity: 0.6 },
                },
              }}
            >
              <ProcessingSpinner />
              <Typography variant="caption" sx={{ fontWeight: 'medium' }}>
                Processing...
              </Typography>
            </Box>
          )}
        </Box>
        <Typography variant="body2" color="text.secondary">
          {progress.toFixed(0)}%
        </Typography>
      </Box>
      
      <Box sx={{ position: 'relative', mb: 2 }}>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{ 
            height: 10, 
            borderRadius: 5,
            bgcolor: 'grey.200',
            '& .MuiLinearProgress-bar': {
              borderRadius: 5,
            }
          }}
        />
        {isProcessing && (
          <LinearProgress
            variant="indeterminate"
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: 10,
              borderRadius: 5,
              opacity: 0.3,
              '& .MuiLinearProgress-bar': {
                borderRadius: 5,
              }
            }}
          />
        )}
      </Box>
      
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <StatusStat label="Pending" value={stats.pending} color="grey.500" isProcessing={stats.pending > 0 && stats.searching === 0 && stats.downloading === 0} />
        <StatusStat label="Searching" value={stats.searching} color="info.main" isProcessing={stats.searching > 0} />
        <StatusStat label="Downloading" value={stats.downloading} color="info.main" isProcessing={stats.downloading > 0} />
        <StatusStat label="Saved" value={stats.saved} color="success.main" />
        <StatusStat label="Failed" value={stats.failed} color="error.main" />
        <StatusStat label="Review" value={stats.review_needed} color="warning.main" />
      </Box>
    </Box>
  );
}

function ProcessingSpinner() {
  return (
    <Box
      sx={{
        width: 14,
        height: 14,
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
  );
}

function StatusStat({ 
  label, 
  value, 
  color, 
  isProcessing = false 
}: { 
  label: string; 
  value: number; 
  color: string;
  isProcessing?: boolean;
}) {
  if (value === 0 && !isProcessing) return null;
  
  return (
    <Box sx={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: 0.5,
      animation: isProcessing ? 'pulse 1s ease-in-out infinite' : 'none',
      '@keyframes pulse': {
        '0%, 100%': { opacity: 1 },
        '50%': { opacity: 0.5 },
      },
    }}>
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          bgcolor: color,
          ...(isProcessing && {
            animation: 'fadeInOut 1s ease-in-out infinite',
            '@keyframes fadeInOut': {
              '0%, 100%': { transform: 'scale(1)', opacity: 1 },
              '50%': { transform: 'scale(1.3)', opacity: 0.7 },
            },
          }),
        }}
      />
      <Typography variant="caption" sx={{ fontWeight: isProcessing ? 'bold' : 'normal' }}>
        {label}: {value}
      </Typography>
    </Box>
  );
}
