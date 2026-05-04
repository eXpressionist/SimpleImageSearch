interface ErrorAlertProps {
  error: Error | null;
  onClose?: () => void;
}

export function ErrorAlert({ error, onClose }: ErrorAlertProps) {
  if (!error) return null;

  return (
    <div className="alert alert--error" role="alert">
      <div>
        <strong>Error</strong>
        <p>{error.message || 'An unknown error occurred'}</p>
      </div>
      {onClose && (
        <button className="icon-button" type="button" onClick={onClose} aria-label="Close error">
          x
        </button>
      )}
    </div>
  );
}
