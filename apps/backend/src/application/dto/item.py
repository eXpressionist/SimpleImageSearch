from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID


class ItemResponseDTO(BaseModel):
    id: UUID
    batch_id: UUID
    position: int
    original_query: str
    normalized_query: str
    status: str
    error_message: Optional[str] = None
    retry_count: int
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ItemWithImageDTO(BaseModel):
    id: UUID
    batch_id: UUID
    position: int
    original_query: str
    normalized_query: str
    status: str
    error_message: Optional[str] = None
    retry_count: int
    is_approved: bool
    image: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ItemListDTO(BaseModel):
    items: List[ItemWithImageDTO]
    total: int
    page: int
    page_size: int
