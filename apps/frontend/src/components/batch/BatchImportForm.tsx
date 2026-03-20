import { useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Grid from '@mui/material/Grid';
import { SearchConfig } from '@/types/api';

interface BatchImportFormProps {
  onSubmit: (lines: string[], name?: string, config?: SearchConfig) => void;
  isLoading?: boolean;
}

export function BatchImportForm({ onSubmit, isLoading }: BatchImportFormProps) {
  const [text, setText] = useState('');
  const [name, setName] = useState('');
  const [imagesPerQuery, setImagesPerQuery] = useState(10);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const lines = text
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    
    if (lines.length > 0) {
      const config: SearchConfig = {
        images_per_query: imagesPerQuery,
      };
      onSubmit(lines, name || undefined, config);
    }
  };
  
  const lineCount = text.split('\n').filter((l) => l.trim()).length;
  
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Import Products
      </Typography>
      
      <Box component="form" onSubmit={handleSubmit}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <TextField
              fullWidth
              label="Batch Name (optional)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., January 2024 Products"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="number"
              label="Images per query"
              value={imagesPerQuery}
              onChange={(e) => setImagesPerQuery(Math.min(200, Math.max(1, parseInt(e.target.value) || 1)))}
              inputProps={{ min: 1, max: 200 }}
              helperText="1-200 (Brave limit)"
            />
          </Grid>
        </Grid>
        
        <TextField
          fullWidth
          multiline
          rows={10}
          label="Product List"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter one product per line, e.g.:&#10;Apple iPhone 15 Pro Max 256GB&#10;Samsung Galaxy S24 Ultra 512GB&#10;Logitech MX Master 3S"
          helperText={`${lineCount} items`}
          required
          sx={{ mt: 2 }}
        />
        
        <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
          <Button
            type="submit"
            variant="contained"
            disabled={isLoading || lineCount === 0}
            startIcon={isLoading ? <CircularProgress size={20} /> : null}
          >
            {isLoading ? 'Creating...' : 'Start Search'}
          </Button>
          
          <Button
            variant="outlined"
            component="label"
          >
            Upload File
            <input
              type="file"
              hidden
              accept=".txt,.csv"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  const reader = new FileReader();
                  reader.onload = (event) => {
                    setText(event.target?.result as string || '');
                  };
                  reader.readAsText(file);
                }
              }}
            />
          </Button>
        </Box>
      </Box>
    </Paper>
  );
}
