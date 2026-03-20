import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import LinearProgress from '@mui/material/LinearProgress';
import Box from '@mui/material/Box';
import { useNavigate } from 'react-router-dom';
import type { BatchResponse } from '@/types/api';
import { StatusBadge } from '@/components/common/StatusBadge';

interface BatchCardProps {
  batch: BatchResponse;
  onDelete?: (id: string) => void;
}

export function BatchCard({ batch, onDelete }: BatchCardProps) {
  const navigate = useNavigate();
  
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="h6" noWrap sx={{ maxWidth: '60%' }}>
            {batch.name}
          </Typography>
          <StatusBadge status={batch.status} />
        </Box>
        
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {batch.total_items} items • {batch.processed_items} processed
          {batch.failed_items > 0 && ` • ${batch.failed_items} failed`}
        </Typography>
        
        <Box sx={{ mt: 2 }}>
          <LinearProgress
            variant="determinate"
            value={batch.progress_percent}
            sx={{ height: 8, borderRadius: 4 }}
          />
          <Typography variant="caption" color="text.secondary">
            {batch.progress_percent.toFixed(0)}% complete
          </Typography>
        </Box>
        
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          Created: {new Date(batch.created_at).toLocaleString()}
        </Typography>
      </CardContent>
      
      <CardActions>
        <Button
          size="small"
          onClick={() => navigate(`/batches/${batch.id}`)}
        >
          View Details
        </Button>
        {onDelete && batch.status !== 'processing' && (
          <Button
            size="small"
            color="error"
            onClick={() => onDelete(batch.id)}
          >
            Delete
          </Button>
        )}
      </CardActions>
    </Card>
  );
}
