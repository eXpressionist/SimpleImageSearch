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
import Skeleton from '@mui/material/Skeleton';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useBatch, useBatchStats } from '@/hooks/useBatches';
import { useBatchItems } from '@/hooks/useBatchItems';
import { BatchProgressBar } from '@/components/batch/BatchProgressBar';
import { ItemTable } from '@/components/item/ItemTable';
import { ItemGallery } from '@/components/item/ItemGallery';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import type { ItemStatus } from '@/types/api';

export function BatchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ItemStatus | ''>('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [viewMode, setViewMode] = useState<'table' | 'gallery'>('gallery');

  const { data: batch, isLoading: batchLoading } = useBatch(id!);
  const { data: stats } = useBatchStats(id!);
  const { data: itemsData, isLoading: itemsLoading, error: itemsError } = useBatchItems(
    id!,
    page + 1,
    rowsPerPage,
    status || undefined
  );

  const isProcessing = stats && (stats.pending > 0 || stats.searching > 0 || stats.downloading > 0);

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
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button 
            variant={viewMode === 'gallery' ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setViewMode('gallery')}
          >
            Gallery
          </Button>
          <Button 
            variant={viewMode === 'table' ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setViewMode('table')}
          >
            Table
          </Button>
        </Box>
      </Box>

      {stats && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <BatchProgressBar stats={stats} total={batch.total_items} />
        </Paper>
      )}

      {isProcessing && itemsData?.items && (
        <ProcessingIndicator items={itemsData.items} />
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

      {itemsLoading && !itemsData ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} variant="rounded" height={80} />
          ))}
        </Box>
      ) : (
        <Paper>
          {viewMode === 'gallery' ? (
            <Box sx={{ p: 1 }}>
              <ItemGallery items={itemsData?.items || []} />
            </Box>
          ) : (
            <ItemTable items={itemsData?.items || []} />
          )}
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

import type { ItemWithImageResponse } from '@/types/api';

function ProcessingIndicator({ items }: { items: ItemWithImageResponse[] }) {
  const processingItems = items.filter(
    item => item.status === 'searching' || item.status === 'downloading'
  );
  
  if (processingItems.length === 0) return null;
  
  return (
    <Paper 
      sx={{ 
        p: 1.5, 
        mb: 2, 
        bgcolor: 'info.lighter',
        border: '1px solid',
        borderColor: 'info.light',
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        flexWrap: 'wrap',
      }}
    >
      <Box 
        sx={{ 
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          animation: 'pulse 1s ease-in-out infinite',
          '@keyframes pulse': {
            '0%, 100%': { opacity: 1 },
            '50%': { opacity: 0.5 },
          },
        }}
      >
        <CircularProgress size={16} />
        <Typography variant="body2" color="info.dark" sx={{ fontWeight: 'medium' }}>
          Now processing:
        </Typography>
      </Box>
      
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {processingItems.slice(0, 5).map(item => (
          <Box 
            key={item.id}
            sx={{ 
              px: 1, 
              py: 0.5, 
              borderRadius: 1, 
              bgcolor: 'white',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
            }}
          >
            <Typography variant="caption" color="text.secondary">
              {item.position + 1}.
            </Typography>
            <Typography variant="caption" sx={{ maxWidth: 150 }} noWrap>
              {item.original_query}
            </Typography>
          </Box>
        ))}
        {processingItems.length > 5 && (
          <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>
            +{processingItems.length - 5} more
          </Typography>
        )}
      </Box>
    </Paper>
  );
}