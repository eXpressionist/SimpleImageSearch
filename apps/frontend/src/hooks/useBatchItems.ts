import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { itemsApi } from '@/api/items';
import type { ItemStatus, ItemListResponse } from '@/types/api';

export function useBatchItems(
  batchId: string,
  page = 1,
  pageSize = 50,
  status?: ItemStatus
) {
  return useQuery({
    queryKey: ['batchItems', batchId, page, pageSize, status],
    queryFn: () => itemsApi.listByBatch(batchId, { page, page_size: pageSize, status }),
    enabled: !!batchId,
    refetchInterval: (query) => {
      const data = query.state.data as ItemListResponse | undefined;
      const hasPending = data?.items.some(
        (item) => ['pending', 'searching', 'downloading'].includes(item.status)
      );
      return hasPending ? 3000 : false;
    },
  });
}

export function useItem(id: string) {
  return useQuery({
    queryKey: ['item', id],
    queryFn: () => itemsApi.get(id),
    enabled: !!id,
  });
}

export function useRetryItem() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => itemsApi.retry(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['item', id] });
      queryClient.invalidateQueries({ queryKey: ['batchItems'] });
    },
  });
}

export function useApproveItem() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => itemsApi.approve(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['item', id] });
      queryClient.invalidateQueries({ queryKey: ['batchItems'] });
    },
  });
}
