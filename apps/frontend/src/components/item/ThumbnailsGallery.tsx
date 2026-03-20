import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import type { ThumbnailInfo } from '@/types/api';

interface ThumbnailsGalleryProps {
  thumbnails: ThumbnailInfo[];
  selectedIndex: number | null;
  onSelect?: (index: number) => void;
  onOpenOriginal?: (thumbnail: ThumbnailInfo) => void;
}

export function ThumbnailsGallery({
  thumbnails,
  selectedIndex,
  onSelect,
  onOpenOriginal
}: ThumbnailsGalleryProps) {
  if (!thumbnails || thumbnails.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No thumbnails available
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Typography variant="subtitle2" color="text.secondary">
        {thumbnails.length} thumbnails found
      </Typography>

      <Box sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: 1,
        maxHeight: 500,
        overflowY: 'auto'
      }}>
        {thumbnails.map((thumb, index) => (
          <Box
            key={index}
            onClick={() => onSelect?.(index)}
            sx={{
              cursor: onSelect ? 'pointer' : 'default',
              border: selectedIndex === index ? '2px solid #1976d2' : '2px solid transparent',
              borderRadius: 1,
              overflow: 'hidden',
              '&:hover': {
                opacity: 0.8,
              }
            }}
          >
            <Box sx={{ position: 'relative' }}>
              <img
                src={thumb.url}
                alt={thumb.title || `Thumbnail ${index + 1}`}
                style={{
                  width: '100%',
                  height: 80,
                  objectFit: 'cover',
                  display: 'block',
                }}
                loading="lazy"
              />

              {selectedIndex === index && (
                <Box sx={{
                  position: 'absolute',
                  top: 2,
                  right: 2,
                  color: '#1976d2',
                }}>
                  <CheckCircleIcon fontSize="small" />
                </Box>
              )}

              <Box sx={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                background: 'rgba(0,0,0,0.6)',
                color: 'white',
                fontSize: 10,
                px: 0.5,
                py: 0.25,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <span>{thumb.width}x{thumb.height}</span>
                {onOpenOriginal && (
                  <IconButton
                    size="small"
                    sx={{
                      color: 'white',
                      p: 0.25,
                      '&:hover': { color: '#1976d2' }
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenOriginal(thumb);
                    }}
                  >
                    <OpenInNewIcon sx={{ fontSize: 12 }} />
                  </IconButton>
                )}
              </Box>
            </Box>

            <Box sx={{ p: 0.5, background: '#f5f5f5', fontSize: 10 }}>
              {thumb.title && (
                <Typography variant="caption" sx={{ display: 'block', fontWeight: 'bold', lineHeight: 1.2 }} noWrap>
                  {thumb.title}
                </Typography>
              )}
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.2 }} noWrap>
                {thumb.mime_type} • {thumb.width}x{thumb.height}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export function parseThumbnails(imageDirectUrl: string | null): ThumbnailInfo[] {
  if (!imageDirectUrl) return [];

  try {
    const parsed = JSON.parse(imageDirectUrl);
    if (Array.isArray(parsed)) {
      return parsed;
    }
  } catch (e) {
    console.error('Failed to parse thumbnails:', e);
  }

  return [];
}