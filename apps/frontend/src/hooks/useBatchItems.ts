import { useCallback } from 'react';
import { itemsApi } from '@/api/items';
import type { ItemStatus } from '@/types/api';
import { useAsyncData, useMutation } from '@/hooks/useAsyncData';

export function useBatchItems(
  batchId: string,
  page = 1,
  pageSize = 50,
  status?: ItemStatus,
  batchIsProcessing = false
) {
  const loader = useCallback(
    () => itemsApi.listByBatch(batchId, { page, page_size: pageSize, status }),
    [batchId, page, pageSize, status]
  );

  return useAsyncData(loader, {
    enabled: !!batchId,
    refetchInterval: (data) => {
      const hasProcessing = data?.items.some(
        (item) => ['pending', 'searching', 'downloading'].includes(item.status)
      );
      return batchIsProcessing || hasProcessing ? 1000 : 5000;
    },
  });
}

export function useItem(id: string) {
  const loader = useCallback(() => itemsApi.get(id), [id]);

  return useAsyncData(loader, { enabled: !!id });
}

export function useRetryItem() {
  return useMutation((id: string) => itemsApi.retry(id));
}

export function useApproveItem() {
  return useMutation((id: string) => itemsApi.approve(id));
}
