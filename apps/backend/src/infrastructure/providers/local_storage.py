import hashlib
import logging
import re
from pathlib import Path
from typing import Optional
import aiofiles
import imghdr
from PIL import Image
import io

from src.domain.interfaces import StorageProvider, StorageResult

logger = logging.getLogger(__name__)


class LocalFileStorage(StorageProvider):
    def __init__(
        self, 
        base_path: str = "/data/images",
        max_file_size_bytes: int = 10 * 1024 * 1024,
    ):
        self.base_path = Path(base_path)
        self.max_file_size_bytes = max_file_size_bytes
        self._ensure_base_path()
    
    def _ensure_base_path(self) -> None:
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save(
        self, 
        data: bytes, 
        batch_id: str, 
        item_id: str, 
        filename: str,
        content_type: Optional[str] = None,
    ) -> StorageResult:
        logger.info("=" * 40)
        logger.info("LOCAL STORAGE SAVE")
        logger.info(f"Base path: {self.base_path}")
        logger.info(f"Batch ID: {batch_id}")
        logger.info(f"Item ID: {item_id}")
        logger.info(f"Filename: {filename}")
        logger.info(f"Data size: {len(data)} bytes")
        
        if len(data) > self.max_file_size_bytes:
            logger.error(f"File too large: {len(data)} > {self.max_file_size_bytes}")
            raise ValueError(f"File too large: {len(data)} bytes > {self.max_file_size_bytes}")
        
        if len(data) == 0:
            logger.error("Empty file")
            raise ValueError("Empty file")
        
        dir_path = self.base_path / batch_id / item_id
        logger.info(f"Creating directory: {dir_path}")
        dir_path.mkdir(parents=True, exist_ok=True)
        
        safe_filename = self._normalize_filename(filename)
        file_path = dir_path / safe_filename
        logger.info(f"Full file path: {file_path}")
        
        file_hash = hashlib.sha256(data).hexdigest()
        logger.info(f"File hash: {file_hash[:16]}...")
        
        logger.info(f"Writing file...")
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)
        
        # Verify file was written
        if file_path.exists():
            actual_size = file_path.stat().st_size
            logger.info(f"File written successfully, actual size: {actual_size} bytes")
        else:
            logger.error(f"File does not exist after write: {file_path}")
        
        mime_type, width, height = self._analyze_image(data, content_type)
        
        logger.info(f"MIME: {mime_type}, Dimensions: {width}x{height}")
        logger.info("=" * 40)
        
        return StorageResult(
            file_path=str(file_path),
            file_name=safe_filename,
            mime_type=mime_type,
            file_size=len(data),
            file_hash=file_hash,
            width=width,
            height=height,
        )
    
    async def get_file_path(self, batch_id: str, item_id: str) -> Optional[str]:
        dir_path = self.base_path / batch_id / item_id
        if not dir_path.exists():
            return None
        
        files = list(dir_path.iterdir())
        if not files:
            return None
        
        return str(files[0])
    
    async def delete(self, batch_id: str, item_id: str) -> bool:
        dir_path = self.base_path / batch_id / item_id
        if not dir_path.exists():
            return False
        
        import shutil
        shutil.rmtree(dir_path)
        return True
    
    async def exists(self, file_hash: str) -> Optional[str]:
        # TODO: Implement hash-based lookup index for deduplication
        return None
    
    def _normalize_filename(self, filename: str) -> str:
        name = filename.strip()
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        name = re.sub(r'\s+', '_', name)
        name = name.strip('._-')
        
        if len(name) > 200:
            base, ext = name.rsplit('.', 1) if '.' in name else (name, '')
            name = base[:200 - len(ext) - 1] + ('.' + ext if ext else '')
        
        if not name:
            name = "unnamed"
        
        return name
    
    def _analyze_image(self, data: bytes, content_type: Optional[str] = None) -> tuple[str, Optional[int], Optional[int]]:
        detected_format = imghdr.what(None, h=data)
        
        mime_map = {
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp",
        }
        
        if content_type and content_type.startswith("image/"):
            mime_type = content_type
        elif detected_format:
            mime_type = mime_map.get(detected_format, f"image/{detected_format}")
        else:
            mime_type = "application/octet-stream"
        
        width, height = None, None
        try:
            img = Image.open(io.BytesIO(data))
            width, height = img.width, img.height
            img.close()
        except Exception as e:
            logger.debug(f"Could not determine image dimensions: {e}")
        
        return mime_type, width, height
    
    def get_extension_from_mime(self, mime_type: str) -> str:
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
        }
        return mime_to_ext.get(mime_type, ".bin")
