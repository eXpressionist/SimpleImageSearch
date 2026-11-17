import { useCallback } from 'react';
import { batchesApi } from '@/api/batches';
import type { BatchCreateRequest } from '@/types/api';
import { useAsyncData, useMutation } from '@/hooks/useAsyncData';

export function useBatches(page = 1, pageSize = 20, status?: string) {
  const loader = useCallback(
    () => batchesApi.list({ page, page_size: pageSize, status }),
    [page, pageSize, status]
  );

  return useAsyncData(loader);
}

export function useBatch(id: string) {
  const loader = useCallback(() => batchesApi.get(id), [id]);

  return useAsyncData(loader, { enabled: !!id });
}

export function useBatchStats(id: string) {
  const loader = useCallback(() => batchesApi.getStats(id), [id]);

  return useAsyncData(loader, {
    enabled: !!id,
    refetchInterval: (data) => {
      const isProcessing =
        data && (data.pending > 0 || data.searching > 0 || data.downloading > 0);
      return isProcessing ? 1000 : 5000;
    },
  });
}

export function useCreateBatch() {
  return useMutation((data: BatchCreateRequest) => batchesApi.create(data));
}

export function useDeleteBatch() {
  return useMutation((id: string) => batchesApi.delete(id));
}
