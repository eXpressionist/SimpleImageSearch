export type BatchStatus = 'pending' | 'processing' | 'completed' | 'partial';
export type ItemStatus = 'pending' | 'searching' | 'downloading' | 'saved' | 'failed' | 'review_needed';

export interface SearchConfig {
  images_per_query?: number;
  lr?: string;
  safe?: string;
  img_size?: string | null;
  img_type?: string | null;
  file_type?: string | null;
  rights?: string | null;
  site_search?: string | null;
}

export interface BatchCreateRequest {
  lines: string[];
  name?: string;
  config?: SearchConfig;
}

export interface BatchResponse {
  id: string;
  name: string;
  total_items: number;
  processed_items: number;
  failed_items: number;
  status: BatchStatus;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}

export interface BatchListResponse {
  items: BatchResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface BatchStatsResponse {
  total: number;
  pending: number;
  searching: number;
  downloading: number;
  saved: number;
  failed: number;
  review_needed: number;
}

export interface ThumbnailInfo {
  position: number;
  url: string;
  source_url: string;
  title: string;
  mime_type: string;
  width: number | null;
  height: number | null;
  file_size: number | null;
}

export interface ImageResponse {
  id: string;
  item_id: string;
  source_url: string;
  direct_url: string;
  file_path: string;
  file_name: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  file_hash: string;
  created_at: string;
}

export interface ItemResponse {
  id: string;
  batch_id: string;
  position: number;
  original_query: string;
  normalized_query: string;
  status: ItemStatus;
  error_message: string | null;
  retry_count: number;
  is_approved: boolean;
  created_at: string;
  updated_at: string;
}

export interface ItemWithImageResponse extends ItemResponse {
  image: ImageResponse | null;
}

export interface ItemListResponse {
  items: ItemWithImageResponse[];
  total: number;
  page: number;
  page_size: number;
}