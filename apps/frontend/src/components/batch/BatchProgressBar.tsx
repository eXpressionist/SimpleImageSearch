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
  
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body2">
          {processed} / {total} items processed
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {progress.toFixed(0)}%
        </Typography>
      </Box>
      
      <LinearProgress
        variant="determinate"
        value={progress}
        sx={{ height: 10, borderRadius: 5, mb: 2 }}
      />
      
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <StatusStat label="Pending" value={stats.pending} color="grey.500" />
        <StatusStat label="Searching" value={stats.searching} color="info.main" />
        <StatusStat label="Downloading" value={stats.downloading} color="info.main" />
        <StatusStat label="Saved" value={stats.saved} color="success.main" />
        <StatusStat label="Failed" value={stats.failed} color="error.main" />
        <StatusStat label="Review" value={stats.review_needed} color="warning.main" />
      </Box>
    </Box>
  );
}

function StatusStat({ label, value, color }: { label: string; value: number; color: string }) {
  if (value === 0) return null;
  
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          bgcolor: color,
        }}
      />
      <Typography variant="caption">
        {label}: {value}
      </Typography>
    </Box>
  );
}
