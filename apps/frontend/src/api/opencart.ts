import { api } from './client';
import type {
  OpenCartGenerateRequest,
  OpenCartGenerateResponse,
  OpenCartHistoryDetail,
  OpenCartHistoryList,
} from '@/types/opencart';

export const opencartApi = {
  generateImageSql: (data: OpenCartGenerateRequest) =>
    api.post<OpenCartGenerateResponse>('/opencart/image-matches/generate', data),

  getHistory: (page = 1, pageSize = 20) =>
    api.get<OpenCartHistoryList>(
      `/opencart/image-matches/history?page=${page}&page_size=${pageSize}`
    ),

  getHistoryDetail: (id: string) =>
    api.get<OpenCartHistoryDetail>(`/opencart/image-matches/history/${id}`),
};
