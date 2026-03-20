import { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import Pagination from '@mui/material/Pagination';
import CircularProgress from '@mui/material/CircularProgress';
import Fab from '@mui/material/Fab';
import AddIcon from '@mui/icons-material/Add';
import { useNavigate } from 'react-router-dom';
import { useBatches, useDeleteBatch } from '@/hooks/useBatches';
import { BatchCard } from '@/components/batch/BatchCard';
import { ErrorAlert } from '@/components/common/ErrorAlert';

export function BatchListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const pageSize = 12;
  
  const { data, isLoading, error } = useBatches(page, pageSize);
  const deleteBatch = useDeleteBatch();
  
  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this batch?')) {
      deleteBatch.mutate(id);
    }
  };
  
  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;
  
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Batches</Typography>
      </Box>
      
      <ErrorAlert error={error as Error | null} />
      
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : data?.items.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary">
            No batches yet
          </Typography>
          <Typography color="text.secondary">
            Create your first batch to start searching for images
          </Typography>
        </Box>
      ) : (
        <>
          <Grid container spacing={3}>
            {data?.items.map((batch) => (
              <Grid item key={batch.id} xs={12} sm={6} md={4}>
                <BatchCard batch={batch} onDelete={handleDelete} />
              </Grid>
            ))}
          </Grid>
          
          {totalPages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Pagination
                count={totalPages}
                page={page}
                onChange={(_, newPage) => setPage(newPage)}
                color="primary"
              />
            </Box>
          )}
        </>
      )}
      
      <Fab
        color="primary"
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
        onClick={() => navigate('/import')}
      >
        <AddIcon />
      </Fab>
    </Box>
  );
}
