from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class ImageAsset:
    id: UUID
    item_id: UUID
    source_url: str
    direct_url: str
    file_path: str
    file_name: str
    mime_type: str
    file_size: int
    file_hash: str
    width: int | None = None
    height: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def dimensions(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "unknown"
    
    @property
    def file_size_mb(self) -> float:
        return self.file_size / (1024 * 1024)
    
    @property
    def file_extension(self) -> str:
        return self.file_name.rsplit(".", 1)[-1] if "." in self.file_name else ""
