import { api } from './client';
import type {
  BatchCreateRequest,
  BatchResponse,
  BatchListResponse,
  BatchStatsResponse,
} from '@/types/api';

export const batchesApi = {
  create: (data: BatchCreateRequest) =>
    api.post<BatchResponse>('/batches', data),
  
  list: (params?: { page?: number; page_size?: number; status?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));
    if (params?.status) searchParams.set('status', params.status);
    
    const query = searchParams.toString();
    return api.get<BatchListResponse>(`/batches${query ? `?${query}` : ''}`);
  },
  
  get: (id: string) =>
    api.get<BatchResponse>(`/batches/${id}`),
  
  getStats: (id: string) =>
    api.get<BatchStatsResponse>(`/batches/${id}/stats`),
  
  delete: (id: string) =>
    api.delete<void>(`/batches/${id}`),
};
