from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class SearchConfigDTO(BaseModel):
    images_per_query: int = Field(default=10, ge=1, le=200)
    lr: str = Field(default="lang_ru")
    safe: str = Field(default="active")
    img_size: Optional[str] = Field(default="large")
    img_type: Optional[str] = None
    file_type: Optional[str] = None
    rights: Optional[str] = None
    site_search: Optional[str] = None


class BatchCreateDTO(BaseModel):
    lines: List[str] = Field(..., min_length=1, max_length=1000)
    name: Optional[str] = None
    config: Optional[SearchConfigDTO] = None
    
    @field_validator("lines")
    @classmethod
    def validate_lines(cls, v: List[str]) -> List[str]:
        cleaned = [line.strip() for line in v if line.strip()]
        if not cleaned:
            raise ValueError("At least one non-empty line required")
        return cleaned


class BatchResponseDTO(BaseModel):
    id: UUID
    name: str
    total_items: int
    processed_items: int
    failed_items: int
    status: str
    progress_percent: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BatchListDTO(BaseModel):
    items: List[BatchResponseDTO]
    total: int
    page: int
    page_size: int


class BatchStatsDTO(BaseModel):
    total: int
    pending: int
    searching: int
    downloading: int
    saved: int
    failed: int
    review_needed: int


class BatchOriginalDownloadRequestDTO(BaseModel):
    count_per_item: int = Field(..., ge=1, le=200)
    target_dir: str = Field(..., min_length=1, max_length=1000)


class BatchOriginalDownloadResponseDTO(BaseModel):
    total: int
    downloaded: int
    failed_downloads: int
    skipped_items: int


class BatchOriginalDownloadJobDTO(BaseModel):
    job_id: str
    status: str


class BatchOriginalDownloadProgressDTO(BaseModel):
    job_id: str
    status: str
    total: int = 0
    completed: int = 0
    downloaded: int = 0
    failed_downloads: int = 0
    skipped_items: int = 0
    current_item: Optional[str] = None
    current_url: Optional[str] = None
    error: Optional[str] = None
