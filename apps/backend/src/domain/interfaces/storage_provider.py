from typing import Protocol
from dataclasses import dataclass


@dataclass
class StorageResult:
    file_path: str
    file_name: str
    mime_type: str
    file_size: int
    file_hash: str
    width: int | None = None
    height: int | None = None


class StorageProvider(Protocol):
    async def save(
        self, 
        data: bytes, 
        batch_id: str, 
        item_id: str, 
        filename: str,
        content_type: str | None = None,
    ) -> StorageResult:
        """
        Save file and return metadata.
        
        Should handle:
        - Directory creation
        - Filename normalization
        - Hash calculation
        - MIME type detection
        """
        ...
    
    async def get_file_path(self, batch_id: str, item_id: str) -> str | None:
        """Get absolute file path for serving, or None if not found."""
        ...
    
    async def delete(self, batch_id: str, item_id: str) -> bool:
        """Delete stored file. Returns True if deleted, False if not found."""
        ...
    
    async def exists(self, file_hash: str) -> str | None:
        """Check if file with this hash already exists. Returns path if found."""
        ...
