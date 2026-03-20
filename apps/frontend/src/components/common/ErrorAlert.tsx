import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Collapse from '@mui/material/Collapse';

interface ErrorAlertProps {
  error: Error | null;
  onClose?: () => void;
}

export function ErrorAlert({ error, onClose }: ErrorAlertProps) {
  return (
    <Collapse in={!!error}>
      <Alert severity="error" onClose={onClose}>
        <AlertTitle>Error</AlertTitle>
        {error?.message || 'An unknown error occurred'}
      </Alert>
    </Collapse>
  );
}
