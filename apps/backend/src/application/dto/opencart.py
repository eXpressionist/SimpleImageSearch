from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OpenCartMatchSettingsDTO(BaseModel):
    use_openrouter: bool = False
    model: str = "openai/gpt-4.1-nano"
    fuzzy_threshold: float = Field(default=0.78, ge=0.0, le=1.0)
    low_confidence_threshold: float = Field(default=0.86, ge=0.0, le=1.0)
    ignore_service_words: bool = True


class OpenCartGenerateRequestDTO(BaseModel):
    products_text: str = Field(min_length=1)
    files_text: str = Field(min_length=1)
    image_prefix: str = ""
    settings: OpenCartMatchSettingsDTO = Field(default_factory=OpenCartMatchSettingsDTO)
    openrouter_api_key: str | None = None


class OpenCartProductDTO(BaseModel):
    product_id: int
    sku: str
    line_number: int


class OpenCartParseErrorDTO(BaseModel):
    line_number: int
    line: str
    message: str


class OpenCartImageMatchDTO(BaseModel):
    product_id: int
    sku: str
    filename: str
    image_path: str
    method: str
    confidence: float
    reason: str


class OpenCartMatchConflictDTO(BaseModel):
    product_id: int | None = None
    sku: str | None = None
    filename: str | None = None
    message: str


class OpenCartGenerateResponseDTO(BaseModel):
    history_id: UUID
    matches: list[OpenCartImageMatchDTO]
    unmatched_products: list[OpenCartProductDTO]
    unused_files: list[str]
    parse_errors: list[OpenCartParseErrorDTO]
    conflicts: list[OpenCartMatchConflictDTO]
    low_confidence_matches: list[OpenCartImageMatchDTO]
    sql: str


class OpenCartHistorySummaryDTO(BaseModel):
    id: UUID
    created_at: datetime
    total_products: int
    total_files: int
    matched_count: int
    unmatched_count: int
    unused_file_count: int
    used_openrouter: bool
    model: str | None = None


class OpenCartHistoryListDTO(BaseModel):
    items: list[OpenCartHistorySummaryDTO]
    total: int
    page: int
    page_size: int


class OpenCartHistoryDetailDTO(OpenCartHistorySummaryDTO):
    products_text: str
    files_text: str
    image_prefix: str
    settings: dict[str, Any]
    result: dict[str, Any]
    sql: str
