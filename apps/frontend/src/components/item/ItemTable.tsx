import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
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

function formatMime(mime: string): string {
  return mime.split('/')[1]?.toUpperCase() || mime;
}

interface ItemTableProps {
  items: ItemWithImageResponse[];
}

export function ItemTable({ items }: ItemTableProps) {
  return (
    <Table>
      <TableHead>
        <TableRow>
          <TableCell width={50}>#</TableCell>
          <TableCell>Query</TableCell>
          <TableCell width={80}>Status</TableCell>
          <TableCell>Thumbnails (10)</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {items.map((item) => {
          const thumbnails = getThumbnails(item);
          return (
            <TableRow key={item.id} hover>
              <TableCell>{item.position + 1}</TableCell>
              <TableCell>
                <Typography variant="body2">
                  {item.original_query}
                </Typography>
                {item.error_message && (
                  <Typography variant="caption" color="error">
                    {item.error_message}
                  </Typography>
                )}
              </TableCell>
              <TableCell>
                <StatusBadge status={item.status} />
              </TableCell>
              <TableCell>
                {thumbnails.length > 0 ? (
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {thumbnails.map((thumb, idx) => (
                      <Box
                        key={idx}
                        component="a"
                        href={thumb.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{
                          position: 'relative',
                          width: 120,
                          height: 130,
                          borderRadius: 1,
                          overflow: 'hidden',
                          border: '1px solid #ddd',
                          flexShrink: 0,
                          textDecoration: 'none',
                          display: 'block',
                          '&:hover': { opacity: 0.85 },
                        }}
                      >
                        <Box
                          component="img"
                          src={thumb.url}
                          alt={thumb.title || `Thumb ${idx + 1}`}
                          sx={{
                            width: '100%',
                            height: 100,
                            objectFit: 'cover',
                            display: 'block',
                            backgroundColor: '#f5f5f5',
                          }}
                        />
                        <Box
                          sx={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bgcolor: 'rgba(0,0,0,0.7)',
                            color: 'white',
                            fontSize: 9,
                            px: 0.5,
                            py: 0.25,
                            zIndex: 1,
                            pointerEvents: 'none',
                          }}
                        >
                          {thumb.width}x{thumb.height}
                        </Box>
                        <Box
                          sx={{
                            position: 'absolute',
                            bottom: 0,
                            left: 0,
                            right: 0,
                            bgcolor: '#eee',
                            color: '#333',
                            fontSize: 9,
                            px: 0.5,
                            py: 0.25,
                          }}
                        >
                          {formatFileSize(thumb.file_size)} • {formatMime(thumb.mime_type)}
                        </Box>
                      </Box>
                    ))}
                  </Box>
                ) : (
                  <Typography variant="caption" color="text.secondary">
                    No thumbnails
                  </Typography>
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}