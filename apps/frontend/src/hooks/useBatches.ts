import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { batchesApi } from '@/api/batches';
import type { BatchCreateRequest } from '@/types/api';

export function useBatches(page = 1, pageSize = 20, status?: string) {
  return useQuery({
    queryKey: ['batches', page, pageSize, status],
    queryFn: () => batchesApi.list({ page, page_size: pageSize, status }),
  });
}

export function useBatch(id: string) {
  return useQuery({
    queryKey: ['batch', id],
    queryFn: () => batchesApi.get(id),
    enabled: !!id,
  });
}

export function useBatchStats(id: string) {
  return useQuery({
    queryKey: ['batchStats', id],
    queryFn: () => batchesApi.getStats(id),
    enabled: !!id,
    refetchInterval: 5000,
  });
}

export function useCreateBatch() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: BatchCreateRequest) => batchesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
    },
  });
}

export function useDeleteBatch() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => batchesApi.delete(id),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      queryClient.invalidateQueries({ queryKey: ['batch'] });
    },
  });
}
