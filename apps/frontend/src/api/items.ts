import { api } from './client';
import type { ItemResponse, ItemWithImageResponse, ItemListResponse } from '@/types/api';

export const itemsApi = {
  get: (id: string) =>
    api.get<ItemWithImageResponse>(`/items/${id}`),
  
  listByBatch: (
    batchId: string,
    params?: { page?: number; page_size?: number; status?: string }
  ) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));
    if (params?.status) searchParams.set('status', params.status);
    
    const query = searchParams.toString();
    return api.get<ItemListResponse>(`/batches/${batchId}/items${query ? `?${query}` : ''}`);
  },
  
  retry: (id: string) =>
    api.post<ItemResponse>(`/items/${id}/retry`),
  
  approve: (id: string) =>
    api.post<ItemResponse>(`/items/${id}/approve`),
  
  recoverStuck: (batchId?: string, stuckMinutes: number = 5) => {
    const searchParams = new URLSearchParams();
    if (batchId) searchParams.set('batch_id', batchId);
    searchParams.set('stuck_minutes', String(stuckMinutes));
    return api.post<{ recovered_count: number; message: string }>(`/items/recover-stuck?${searchParams.toString()}`);
  },
};
