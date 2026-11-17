import asyncio
import json
import logging
from pathlib import Path
from uuid import UUID
from weakref import WeakValueDictionary

import httpx

from src.domain.entities import ImageAsset
from src.infrastructure.config import Settings
from src.infrastructure.image_processing import create_preview
from src.infrastructure.providers import LocalFileStorage

from .image_downloader import ImageDownloader

logger = logging.getLogger(__name__)


class ImagePreviewService:
    def __init__(self, storage: LocalFileStorage, settings: Settings):
        self.storage = storage
        preview_settings = settings.model_copy(update={
            "download_timeout": min(settings.download_timeout, 10), "max_retries": 2,
        })
        self.downloader = ImageDownloader(storage, preview_settings)
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        self._locks: WeakValueDictionary[tuple[UUID, int], asyncio.Lock] = WeakValueDictionary()

    async def get_preview(self, image: ImageAsset, index: int) -> Path:
        # Concurrent viewers share one download; completed requests do not retain locks.
        lock = self._locks.setdefault((image.id, index), asyncio.Lock())
        async with lock:
            return await self._get_preview(image, index)

    async def _get_preview(self, image: ImageAsset, index: int) -> Path:
        if image.mime_type != "application/json":
            if index != 0:
                raise IndexError("Preview not found")
            candidates = [image.direct_url]
        else:
            try:
                thumbnails = json.loads(image.direct_url)
            except (ValueError, TypeError) as error:
                raise IndexError("Invalid thumbnail list") from error
            if not isinstance(thumbnails, list) or not 0 <= index < len(thumbnails):
                raise IndexError("Preview not found")
            thumbnail = thumbnails[index]
            if not isinstance(thumbnail, dict):
                raise IndexError("Invalid thumbnail")
            candidates = [thumbnail.get("thumbnail_url"), thumbnail.get("url")]

        cached_path = self.storage.base_path / "previews" / str(image.id) / f"{index}.png"
        if cached_path.is_file():
            return cached_path

        for url in dict.fromkeys(url for url in candidates if isinstance(url, str) and url):
            try:
                async with self._semaphore:
                    data, _ = await self.downloader.fetch_image(url)
                    preview = await asyncio.to_thread(create_preview, data)
            except (ValueError, OSError, httpx.HTTPError) as error:
                logger.debug("Preview source failed for image %s: %s", image.id, error)
                continue
            result = await self.storage.save(
                preview, "previews", str(image.id), f"{index}.png", "image/png"
            )
            return Path(result.file_path)
        raise ValueError("No image source is available")
