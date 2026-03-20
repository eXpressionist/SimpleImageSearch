import logging
from pathlib import Path
from typing import Optional

from src.infrastructure.config import get_settings

logger = logging.getLogger(__name__)


class FileStorageService:
    def __init__(self):
        self.settings = get_settings()
        self.base_path = Path(self.settings.storage_path)
    
    def get_file_path(self, batch_id: str, item_id: str) -> Optional[Path]:
        dir_path = self.base_path / batch_id / item_id
        if not dir_path.exists():
            return None
        
        files = list(dir_path.iterdir())
        if not files:
            return None
        
        return files[0]
    
    def file_exists(self, file_path: str) -> bool:
        return Path(file_path).exists()
    
    def get_content_type(self, filename: str) -> str:
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp",
        }
        return mime_map.get(ext, "application/octet-stream")
