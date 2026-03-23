import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
from uuid import uuid4, UUID
from collections import OrderedDict

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Batch, BatchItem, ProcessingLog, ImageAsset
from src.domain.value_objects import BatchStatus, ItemStatus, Query
from src.domain.interfaces import SearchConfig, SearchProvider
from src.infrastructure.database import (
    BatchRepository, ItemRepository, LogRepository, ImageRepository, async_session_factory
)
from src.infrastructure.providers import LocalFileStorage
from src.infrastructure.config import get_settings

from .image_downloader import ImageDownloader

logger = logging.getLogger(__name__)


async def get_file_size_from_url(url: str) -> int | None:
    """Get file size from URL using HEAD request."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.head(url)
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
    except Exception as e:
        logger.warning(f"Failed to get file size for {url[:50]}...: {e}")
    return None


async def process_batch_background(batch_id: UUID) -> None:
    """
    Background task that processes a batch with its own database session.
    This is called from BackgroundTasks and creates a fresh session.
    """
    logger.info(f"BACKGROUND TASK START: Processing batch {batch_id}")

    settings = get_settings()

    async with async_session_factory() as session:
        try:
            from src.api.dependencies import get_search_provider, get_storage

            search_provider = get_search_provider()
            storage = get_storage()

            processor = BatchProcessor(
                session=session,
                search_provider=search_provider,
                storage=storage,
            )

            await processor.process_batch(batch_id)

            logger.info(f"BACKGROUND TASK COMPLETE: Batch {batch_id}")
        except Exception as e:
            logger.error(f"BACKGROUND TASK ERROR: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await session.rollback()
            raise


class BatchProcessor:
    def __init__(
        self,
        session: AsyncSession,
        search_provider: SearchProvider,
        storage: LocalFileStorage,
    ):
        self.session = session
        self.settings = get_settings()
        self.search_provider = search_provider
        self.storage = storage
        self.downloader = ImageDownloader(storage, self.settings)

        self.batch_repo = BatchRepository(session)
        self.item_repo = ItemRepository(session)
        self.log_repo = LogRepository(session)
        self.image_repo = ImageRepository(session)

        self._semaphore = asyncio.Semaphore(self.settings.max_concurrent_downloads)

    async def create_batch(
        self,
        lines: List[str],
        name: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> Batch:
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        seen: Dict[str, int] = OrderedDict()
        for i, line in enumerate(cleaned_lines):
            query = Query.from_raw(line)
            if query.normalized not in seen:
                seen[query.normalized] = i

        unique_lines = [cleaned_lines[i] for i in seen.values()]

        batch = Batch(
            id=uuid4(),
            name=name or f"Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            total_items=len(unique_lines),
            config=config or {},
        )

        batch = await self.batch_repo.create(batch)

        items = []
        for position, line in enumerate(unique_lines):
            query = Query.from_raw(line)
            item = BatchItem(
                id=uuid4(),
                batch_id=batch.id,
                position=position,
                original_query=query.raw,
                normalized_query=query.normalized,
            )
            items.append(item)

        await self.item_repo.create_many(items)

        logger.info(f"Batch created: {batch.id} with {len(items)} items")

        return batch

    async def process_batch(self, batch_id: UUID) -> None:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            logger.error(f"Batch not found: {batch_id}")
            return

        batch.mark_processing()
        await self.batch_repo.update(batch)
        await self.session.commit()

        tasks = []
        while True:
            items = await self.item_repo.get_pending(batch_id, limit=self.settings.max_concurrent_downloads)
            if not items:
                break

            for item in items:
                task = asyncio.create_task(self._process_item_with_semaphore(batch_id, item.id))
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)
            tasks = []

        batch = await self.batch_repo.get_by_id(batch_id)
        if batch:
            batch.mark_completed()
            await self.batch_repo.update(batch)
            await self.session.commit()

        logger.info(f"Batch completed: {batch_id}")

    async def _process_item_with_semaphore(self, batch_id: UUID, item_id: UUID) -> None:
        async with self._semaphore:
            await self._process_item(batch_id, item_id)

    async def _process_item(self, batch_id: UUID, item_id: UUID) -> None:
        logger.info(f"PROCESS ITEM START: {item_id}")

        batch = await self.batch_repo.get_by_id(batch_id)
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            logger.error(f"Item not found: {item_id}")
            return

        logger.info(f"Item query: {item.original_query}")

        try:
            item.mark_searching()
            await self.item_repo.update(item)
            await self.session.commit()

            batch_config = batch.config if batch else {}
            search_config = self._build_search_config(item.normalized_query, batch_config)
            logger.info(f"Searching for: {search_config.query}, images_per_query={search_config.images_per_query}")
            results = await self.search_provider.search(search_config)
            logger.info(f"Search returned {len(results)} results")

            if not results:
                item.mark_failed("No search results found")
                await self.item_repo.update(item)
                batch = await self.batch_repo.get_by_id(batch_id)
                if batch:
                    batch.increment_processed(failed=True)
                    await self.batch_repo.update(batch)
                await self._log(item_id, "search", "failed", "No results")
                await self.session.commit()
                return

            thumbnails_data = []
            for idx, result in enumerate(results):
                file_size = await get_file_size_from_url(result.direct_url)
                if file_size is None:
                    file_size = result.file_size

                thumbnail_info = {
                    "position": idx,
                    "url": result.direct_url,
                    "source_url": result.source_url,
                    "title": result.title,
                    "mime_type": result.mime_type or "image/jpeg",
                    "width": result.width,
                    "height": result.height,
                    "file_size": file_size,
                }
                thumbnails_data.append(thumbnail_info)
                logger.info(f"Thumbnail {idx+1}: {result.direct_url[:50]}... ({result.width}x{result.height}, {file_size} bytes)")

            image_asset = ImageAsset(
                id=uuid4(),
                item_id=item_id,
                source_url=thumbnails_data[0]["source_url"] if thumbnails_data else "",
                direct_url=json.dumps(thumbnails_data),
                file_path="",
                file_name=f"thumbnails_{item_id}.json",
                mime_type="application/json",
                file_size=len(json.dumps(thumbnails_data)),
                file_hash="",
                width=None,
                height=None,
            )

            await self.image_repo.create(image_asset)

            item.mark_saved()
            await self.item_repo.update(item)

            batch = await self.batch_repo.get_by_id(batch_id)
            if batch:
                batch.increment_processed(failed=False)
                await self.batch_repo.update(batch)

            await self._log(item_id, "search", "success", f"Saved {len(thumbnails_data)} thumbnails")
            await self.session.commit()
            logger.info(f"ITEM PROCESSED SUCCESSFULLY: {item_id} with {len(thumbnails_data)} thumbnails")

        except Exception as e:
            logger.error(f"Error processing item {item_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            try:
                item = await self.item_repo.get_by_id(item_id)
                if item:
                    item.mark_failed(str(e)[:500])
                    await self.item_repo.update(item)

                    batch = await self.batch_repo.get_by_id(batch_id)
                    if batch:
                        batch.increment_processed(failed=True)
                        await self.batch_repo.update(batch)

                    await self._log(item_id, "process", "error", str(e))
                    await self.session.commit()
            except Exception as commit_error:
                logger.error(f"Failed to commit error state: {commit_error}")

    def _build_search_config(self, query: str, config: dict) -> SearchConfig:
        return SearchConfig(
            query=query,
            images_per_query=config.get("images_per_query", 10),
            lr=config.get("lr", "lang_ru"),
            safe=config.get("safe", "active"),
            img_size=config.get("img_size", "large"),
            preferred_formats=["webp", "png", "jpg", "jpeg"],
        )

    async def _log(self, item_id: UUID, action: str, status: str, message: str) -> None:
        log = ProcessingLog.create(
            item_id=item_id,
            action=action,
            status=status,
            message=message,
        )
        log.id = uuid4()
        await self.log_repo.create(log)

    async def retry_item(self, item_id: UUID) -> Optional[BatchItem]:
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            return None

        if not item.can_retry(self.settings.max_retries):
            return None

        await self.image_repo.delete_by_item(item_id)
        item.increment_retry()
        await self.item_repo.update(item)

        batch = await self.batch_repo.get_by_id(item.batch_id)
        if batch and batch.status == BatchStatus.COMPLETED:
            batch.status = BatchStatus.PROCESSING
            await self.batch_repo.update(batch)

        asyncio.create_task(self._process_item(item.batch_id, item.id))

        return item