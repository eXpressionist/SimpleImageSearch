import asyncio
import hashlib
import os
import re
from pathlib import Path
from typing import Optional
from uuid import uuid4

import aiofiles

from src.domain.interfaces import StorageProvider, StorageResult
from src.infrastructure.image_processing import inspect_image


class LocalFileStorage(StorageProvider):
    def __init__(
        self,
        base_path: str = "/data/images",
        max_file_size_bytes: int = 10 * 1024 * 1024,
    ):
        self.base_path = Path(base_path)
        self.max_file_size_bytes = max_file_size_bytes
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        data: bytes,
        batch_id: str,
        item_id: str,
        filename: str,
        content_type: Optional[str] = None,
    ) -> StorageResult:
        return await self._save(data, self.base_path / batch_id / item_id, filename)

    async def save_to_directory(
        self,
        data: bytes,
        target_dir: str,
        filename: str,
        content_type: Optional[str] = None,
    ) -> StorageResult:
        return await self._save(data, self._resolve_target_dir(target_dir), filename)

    async def _save(self, data: bytes, directory: Path, filename: str) -> StorageResult:
        if not data:
            raise ValueError("Empty file")
        if len(data) > self.max_file_size_bytes:
            raise ValueError(f"File too large: {len(data)} bytes > {self.max_file_size_bytes}")

        mime_type, width, height = await asyncio.to_thread(inspect_image, data)
        safe_filename = self._normalize_image_extension(self._normalize_filename(filename), mime_type)
        directory.mkdir(parents=True, exist_ok=True)
        file_path = directory / safe_filename
        temporary_path = directory / f".{uuid4().hex}.tmp"
        try:
            async with aiofiles.open(temporary_path, "wb") as output:
                await output.write(data)
            temporary_path.replace(file_path)
        finally:
            temporary_path.unlink(missing_ok=True)

        return StorageResult(
            file_path=str(file_path),
            file_name=safe_filename,
            mime_type=mime_type,
            file_size=len(data),
            file_hash=hashlib.sha256(data).hexdigest(),
            width=width,
            height=height,
        )

    def _resolve_target_dir(self, target_dir: str) -> Path:
        if os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", target_dir):
            raise ValueError(
                "Windows paths are not available inside this container. "
                "Mount the host folder into Docker and use the container path, for example /exports."
            )
        path = Path(target_dir).expanduser()
        if not path.is_absolute():
            raise ValueError("Target directory must be an absolute path available to the backend")
        return path

    async def get_file_path(self, batch_id: str, item_id: str) -> Optional[str]:
        directory = self.base_path / batch_id / item_id
        if directory.is_dir():
            return next((str(path) for path in directory.iterdir() if path.is_file() and path.suffix != ".tmp"), None)
        return None

    async def delete(self, batch_id: str, item_id: str) -> bool:
        directory = self.base_path / batch_id / item_id
        if not directory.exists():
            return False
        import shutil
        await asyncio.to_thread(shutil.rmtree, directory)
        return True

    async def exists(self, file_hash: str) -> Optional[str]:
        # Hash-based deduplication is not implemented.
        return None

    def _normalize_filename(self, filename: str) -> str:
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename.strip())
        name = re.sub(r'\s+', '_', name).strip('._-')
        if len(name.encode("utf-8")) > 200:
            base, ext = name.rsplit('.', 1) if '.' in name else (name, '')
            suffix = f".{ext}" if ext else ''
            suffix = suffix.encode("utf-8")[:20].decode("utf-8", errors="ignore")
            base = base.encode("utf-8")[:200 - len(suffix.encode("utf-8"))].decode("utf-8", errors="ignore")
            name = base + suffix
        return name or "unnamed"

    def get_extension_from_mime(self, mime_type: str) -> str:
        return {
            "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
            "image/webp": ".webp", "image/bmp": ".bmp", "image/avif": ".avif",
        }.get(mime_type, ".bin")

    def _normalize_image_extension(self, filename: str, mime_type: str) -> str:
        extension = self.get_extension_from_mime(mime_type)
        path = Path(filename)
        if extension == ".bin" or path.suffix.lower() == extension:
            return filename
        return f"{path.stem}{extension}"
