import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import { useCreateBatch } from '@/hooks/useBatches';
import { BatchImportForm } from '@/components/batch/BatchImportForm';
import type { SearchConfig } from '@/types/api';

export function BatchImportPage() {
  const navigate = useNavigate();
  const createBatch = useCreateBatch();
  const [error, setError] = useState<string | null>(null);
  
  const handleSubmit = async (lines: string[], name?: string, config?: SearchConfig) => {
    try {
      const result = await createBatch.mutateAsync({
        lines,
        name,
        config,
      });
      navigate(`/batches/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create batch');
    }
  };
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Import Products
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Enter product names, one per line. The system will search for images
        and download them automatically.
      </Typography>
      
      <BatchImportForm
        onSubmit={handleSubmit}
        isLoading={createBatch.isPending}
      />
      
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
}
