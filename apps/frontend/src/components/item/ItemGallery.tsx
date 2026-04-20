import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import type { ItemWithImageResponse, ThumbnailInfo } from '@/types/api';
import { StatusBadge } from '@/components/common/StatusBadge';

function getThumbnails(item: ItemWithImageResponse): ThumbnailInfo[] {
  if (!item.image?.direct_url) return [];
  try {
    return JSON.parse(item.image.direct_url);
  } catch {
    return [];
  }
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return '-';
  const kb = Math.round(bytes / 1024);
  return `${kb} KB`;
}

interface ItemGalleryProps {
  items: ItemWithImageResponse[];
  onItemClick?: (item: ItemWithImageResponse) => void;
}

export function ItemGallery({ items, onItemClick }: ItemGalleryProps) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {items.map((item) => {
        const thumbnails = getThumbnails(item);
        return (
          <Box
            key={item.id}
            onClick={() => onItemClick?.(item)}
            sx={{
              p: 1,
              border: '1px solid #ddd',
              borderRadius: 1,
              cursor: onItemClick ? 'pointer' : 'default',
              '&:hover': { bgcolor: 'action.hover' },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, gap: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold', minWidth: 30 }}>
                {item.position + 1}.
              </Typography>
              <Typography variant="body2" noWrap sx={{ flex: 1, maxWidth: 200 }}>
                {item.original_query}
              </Typography>
              <StatusBadge status={item.status} />
            </Box>

            {thumbnails.length > 0 ? (
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {thumbnails.map((thumb, idx) => (
                  <Box
                    key={idx}
                    sx={{
                      position: 'relative',
                      width: 102,
                      height: 90,
                      borderRadius: 0.5,
                      overflow: 'hidden',
                      border: '1px solid #ddd',
                      flexShrink: 0,
                    }}
                  >
                    <Box
                      component="img"
                      src={thumb.url}
                      alt={thumb.title || `Thumb ${idx + 1}`}
                      sx={{
                        width: '100%',
                        height: 75,
                        objectFit: 'cover',
                        display: 'block',
                      }}
                    />
                    <IconButton
                      size="small"
                      href={thumb.url}
                      target="_blank"
                      onClick={(e) => e.stopPropagation()}
                      sx={{
                        position: 'absolute',
                        top: 2,
                        right: 2,
                        p: '2px',
                        minHeight: 18,
                        minWidth: 18,
                        bgcolor: 'rgba(0,0,0,0.7)',
                        color: 'white',
                        borderRadius: 0.5,
                        '&:hover': { bgcolor: 'rgba(0,0,0,0.9)' },
                      }}
                    >
                      <OpenInNewIcon sx={{ fontSize: 12 }} />
                    </IconButton>
                    <Typography
                      variant="caption"
                      sx={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        bgcolor: 'rgba(0,0,0,0.7)',
                        color: 'white',
                        fontSize: 8,
                        px: 0.25,
                        lineHeight: 1,
                      }}
                    >
                      {thumb.width}x{thumb.height} • {formatFileSize(thumb.file_size)} • {thumb.mime_type.split('/')[1]}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography variant="caption" color="text.secondary">
                No thumbnails
              </Typography>
            )}
          </Box>
        );
      })}
    </Box>
  );
}