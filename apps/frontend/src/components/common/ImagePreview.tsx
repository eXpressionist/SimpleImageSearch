import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import type { ImageResponse } from '@/types/api';
import { getImageUrl } from '@/api/client';

interface ImagePreviewProps {
  image: ImageResponse | null;
  itemId: string;
  height?: number;
}

export function ImagePreview({ image, itemId, height = 150 }: ImagePreviewProps) {
  if (!image) {
    return (
      <Box
        sx={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: 'grey.100',
          borderRadius: 1,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          No image
        </Typography>
      </Box>
    );
  }
  
  return (
    <Box sx={{ position: 'relative' }}>
      <img
        src={getImageUrl(itemId)}
        alt={image.file_name}
        style={{
          width: '100%',
          height,
          objectFit: 'cover',
          borderRadius: 4,
        }}
        loading="lazy"
      />
      <Typography
        variant="caption"
        sx={{
          position: 'absolute',
          bottom: 4,
          right: 4,
          bgcolor: 'rgba(0,0,0,0.6)',
          color: 'white',
          px: 0.5,
          borderRadius: 0.5,
        }}
      >
        {formatSize(image.file_size)}
      </Typography>
    </Box>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
