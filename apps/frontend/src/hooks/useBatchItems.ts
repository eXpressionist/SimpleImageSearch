import { useCallback } from 'react';
import { itemsApi } from '@/api/items';
import type { ItemStatus, ItemListResponse } from '@/types/api';
import { useAsyncData, useMutation } from '@/hooks/useAsyncData';

export function useBatchItems(
  batchId: string,
  page = 1,
  pageSize = 50,
  status?: ItemStatus
) {
  const loader = useCallback(
    () => itemsApi.listByBatch(batchId, { page, page_size: pageSize, status }),
    [batchId, page, pageSize, status]
  );

  return useAsyncData(loader, [loader], {
    enabled: !!batchId,
    refetchInterval: (query) => {
      const data = query as ItemListResponse | undefined;
      const hasProcessing = data?.items.some(
        (item) => ['pending', 'searching', 'downloading'].includes(item.status)
      );
      return hasProcessing ? 1000 : false;
    },
  });
}

export function useItem(id: string) {
  const loader = useCallback(() => itemsApi.get(id), [id]);

  return useAsyncData(loader, [loader], { enabled: !!id });
}

export function useRetryItem() {
  return useMutation((id: string) => itemsApi.retry(id));
}

export function useApproveItem() {
  return useMutation((id: string) => itemsApi.approve(id));
}
