from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class ImageResponseDTO(BaseModel):
    id: UUID
    item_id: UUID
    source_url: str
    direct_url: str
    file_path: str
    file_name: str
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    file_hash: str
    created_at: datetime
    
    class Config:
        from_attributes = True
