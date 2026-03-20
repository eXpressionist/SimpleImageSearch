import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import ReplayIcon from '@mui/icons-material/Replay';
import type { ItemWithImageResponse } from '@/types/api';
import { StatusBadge } from '@/components/common/StatusBadge';
import { getImageUrl } from '@/api/client';

interface ItemDetailModalProps {
  item: ItemWithImageResponse | null;
  open: boolean;
  onClose: () => void;
  onRetry?: (id: string) => void;
}

export function ItemDetailModal({ item, open, onClose, onRetry }: ItemDetailModalProps) {
  if (!item) return null;
  
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h6">Item #{item.position + 1}</Typography>
            <StatusBadge status={item.status} />
          </Box>
          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ display: 'flex', gap: 3 }}>
          <Box sx={{ flex: 1 }}>
            {item.image ? (
              <Box
                component="img"
                src={getImageUrl(item.id)}
                alt={item.image.file_name}
                sx={{
                  width: '100%',
                  maxHeight: 400,
                  objectFit: 'contain',
                  borderRadius: 1,
                  bgcolor: 'grey.100',
                }}
              />
            ) : (
              <Box
                sx={{
                  width: '100%',
                  height: 300,
                  bgcolor: 'grey.200',
                  borderRadius: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Typography color="text.secondary">No image</Typography>
              </Box>
            )}
          </Box>
          
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Original Query
            </Typography>
            <Typography variant="body1" gutterBottom>
              {item.original_query}
            </Typography>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="subtitle2" color="text.secondary">
              Normalized Query
            </Typography>
            <Typography variant="body2" gutterBottom>
              {item.normalized_query}
            </Typography>
            
            {item.error_message && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" color="error">
                  Error
                </Typography>
                <Typography variant="body2" color="error">
                  {item.error_message}
                </Typography>
              </>
            )}
            
            {item.image && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  File Info
                </Typography>
                <Typography variant="body2">
                  Name: {item.image.file_name}
                </Typography>
                <Typography variant="body2">
                  Size: {(item.image.file_size / 1024).toFixed(1)} KB
                </Typography>
                {item.image.width && item.image.height && (
                  <Typography variant="body2">
                    Dimensions: {item.image.width} x {item.image.height}
                  </Typography>
                )}
                <Typography variant="body2">
                  Type: {item.image.mime_type}
                </Typography>
              </>
            )}
          </Box>
        </Box>
      </DialogContent>
      
      <DialogActions>
        {item.image && (
          <Button
            href={item.image.direct_url}
            target="_blank"
          >
            Open Original
          </Button>
        )}
        {['failed', 'review_needed'].includes(item.status) && onRetry && (
          <Button
            variant="contained"
            startIcon={<ReplayIcon />}
            onClick={() => {
              onRetry(item.id);
              onClose();
            }}
          >
            Retry
          </Button>
        )}
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
