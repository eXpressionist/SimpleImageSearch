import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BatchImportForm } from '@/components/batch/BatchImportForm';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { useCreateBatch } from '@/hooks/useBatches';
import type { SearchConfig } from '@/types/api';

export function BatchImportPage() {
  const navigate = useNavigate();
  const createBatch = useCreateBatch();
  const [error, setError] = useState<Error | null>(null);

  const handleSubmit = async (lines: string[], name?: string, config?: SearchConfig) => {
    try {
      setError(null);
      const result = await createBatch.mutateAsync({ lines, name, config });
      navigate(`/batches/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to create batch'));
    }
  };

  return (
    <section className="page-stack">
      <div>
        <h1>Import Products</h1>
        <p className="lede">
          Enter product names, one per line. The system will search for images and download them
          automatically.
        </p>
      </div>

      <BatchImportForm onSubmit={handleSubmit} isLoading={createBatch.isPending} />
      <ErrorAlert error={error} onClose={() => setError(null)} />
    </section>
  );
}
