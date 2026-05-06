export interface OpenCartMatchSettings {
  use_openrouter: boolean;
  model: string;
  fuzzy_threshold: number;
  low_confidence_threshold: number;
  ignore_service_words: boolean;
}

export interface OpenCartGenerateRequest {
  products_text: string;
  files_text: string;
  image_prefix: string;
  settings: OpenCartMatchSettings;
  openrouter_api_key?: string;
}

export interface OpenRouterModel {
  id: string;
  name: string;
  context_length: number | null;
}

export interface OpenRouterModelList {
  items: OpenRouterModel[];
}

export interface OpenCartProduct {
  product_id: number;
  sku: string;
  line_number: number;
}

export interface OpenCartParseError {
  line_number: number;
  line: string;
  message: string;
}

export interface OpenCartImageMatch {
  product_id: number;
  sku: string;
  filename: string;
  image_path: string;
  method: string;
  confidence: number;
  reason: string;
}

export interface OpenCartMatchConflict {
  product_id: number | null;
  sku: string | null;
  filename: string | null;
  message: string;
}

export interface OpenCartMatchReport {
  matches: OpenCartImageMatch[];
  unmatched_products: OpenCartProduct[];
  unused_files: string[];
  parse_errors: OpenCartParseError[];
  conflicts: OpenCartMatchConflict[];
  low_confidence_matches: OpenCartImageMatch[];
  sql: string;
}

export interface OpenCartGenerateResponse extends OpenCartMatchReport {
  history_id: string;
}

export interface OpenCartHistorySummary {
  id: string;
  created_at: string;
  total_products: number;
  total_files: number;
  matched_count: number;
  unmatched_count: number;
  unused_file_count: number;
  used_openrouter: boolean;
  model: string | null;
}

export interface OpenCartHistoryList {
  items: OpenCartHistorySummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface OpenCartHistoryDetail extends OpenCartHistorySummary {
  products_text: string;
  files_text: string;
  image_prefix: string;
  settings: OpenCartMatchSettings;
  result: OpenCartMatchReport;
  sql: string;
}
