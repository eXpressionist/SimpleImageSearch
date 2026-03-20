import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import CircularProgress from '@mui/material/CircularProgress';
import TablePagination from '@mui/material/TablePagination';
import MenuItem from '@mui/material/MenuItem';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useBatch, useBatchStats } from '@/hooks/useBatches';
import { useBatchItems } from '@/hooks/useBatchItems';
import { BatchProgressBar } from '@/components/batch/BatchProgressBar';
import { ItemTable } from '@/components/item/ItemTable';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import type { ItemStatus } from '@/types/api';

export function BatchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ItemStatus | ''>('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const { data: batch, isLoading: batchLoading } = useBatch(id!);
  const { data: stats } = useBatchStats(id!);
  const { data: itemsData, isLoading: itemsLoading, error: itemsError } = useBatchItems(
    id!,
    page + 1,
    rowsPerPage,
    status || undefined
  );

  if (batchLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!batch) {
    return (
      <Box>
        <ErrorAlert error={new Error('Batch not found')} />
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/')}>
          Back to batches
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/')}>
            Back
          </Button>
          <Typography variant="h4" sx={{ mt: 1 }}>
            {batch.name}
          </Typography>
        </Box>
      </Box>

      {stats && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <BatchProgressBar stats={stats} total={batch.total_items} />
        </Paper>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            select
            label="Filter by status"
            value={status}
            onChange={(e) => setStatus(e.target.value as ItemStatus | '')}
            size="small"
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="pending">Pending</MenuItem>
            <MenuItem value="searching">Searching</MenuItem>
            <MenuItem value="downloading">Downloading</MenuItem>
            <MenuItem value="saved">Saved</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
            <MenuItem value="review_needed">Review Needed</MenuItem>
          </TextField>
        </Box>
      </Paper>

      <ErrorAlert error={itemsError as Error | null} />

      {itemsLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Paper>
          <ItemTable items={itemsData?.items || []} />
          <TablePagination
            component="div"
            count={itemsData?.total || 0}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => {
              setRowsPerPage(parseInt(e.target.value, 10));
              setPage(0);
            }}
          />
        </Paper>
      )}
    </Box>
  );
}