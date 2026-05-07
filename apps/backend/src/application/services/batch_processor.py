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
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.head(url)
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
    except Exception as e:
        logger.debug(f"Failed to get file size for {url[:50]}...: {e}")
    return None


async def get_file_size_safe(url: str) -> int | None:
    """Get file size without blocking - returns None on any error."""
    try:
        return await asyncio.wait_for(get_file_size_from_url(url), timeout=6.0)
    except asyncio.TimeoutError:
        logger.debug(f"Timeout getting file size for {url[:50]}...")
    except Exception as e:
        logger.debug(f"Error getting file size: {e}")
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

        while True:
            items = await self.item_repo.get_pending(batch_id, limit=self.settings.max_concurrent_downloads)
            if not items:
                break

            for item in items:
                await self._process_item_with_semaphore(batch_id, item.id)

        batch = await self.batch_repo.get_by_id(batch_id)
        if batch:
            await self._sync_batch_progress(batch_id)
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
            existing_image = await self.image_repo.get_by_item(item_id)
            if existing_image:
                if item.status != ItemStatus.SAVED:
                    item.mark_saved()
                    await self.item_repo.update(item)
                    await self._log(item_id, "search", "success", "Reused existing image asset")
                await self._sync_batch_progress(batch_id)
                await self.session.commit()
                logger.info(f"ITEM ALREADY HAS IMAGE ASSET: {item_id}")
                return

            item.mark_searching()
            await self.item_repo.update(item)
            await self.session.commit()

            batch_config = batch.config if batch else {}
            search_config = self._build_search_config(item.normalized_query, batch_config)
            logger.info(f"Searching for: {search_config.query}, images_per_query={search_config.images_per_query}")
            
            try:
                results = await asyncio.wait_for(
                    self.search_provider.search(search_config),
                    timeout=90.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Search timeout for item {item_id}")
                item.mark_failed("Search timeout (90s)")
                await self.item_repo.update(item)
                batch = await self.batch_repo.get_by_id(batch_id)
                if batch:
                    batch.increment_processed(failed=True)
                    await self.batch_repo.update(batch)
                await self._log(item_id, "search", "timeout", "Search exceeded 90s timeout")
                await self.session.commit()
                return
            
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
            max_file_size_checks = 30
            for idx, result in enumerate(results):
                file_size = result.file_size
                if idx < max_file_size_checks:
                    try:
                        size = await get_file_size_safe(result.direct_url)
                        if size is not None:
                            file_size = size
                    except Exception as e:
                        logger.debug(f"Skipping file size check for thumbnail {idx}: {e}")

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
            
            logger.info(f"Collected {len(thumbnails_data)} thumbnails")

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
            await self._sync_batch_progress(batch_id)
            await self.session.commit()
            logger.info(f"ITEM PROCESSED SUCCESSFULLY: {item_id} with {len(thumbnails_data)} thumbnails")

        except Exception as e:
            logger.error(f"Error processing item {item_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            try:
                await self.session.rollback()
                item = await self.item_repo.get_by_id(item_id)
                if item:
                    item.mark_failed(str(e)[:500])
                    await self.item_repo.update(item)

                    await self._log(item_id, "process", "error", str(e))
                    await self._sync_batch_progress(batch_id)
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

    async def download_originals_for_batch(
        self,
        batch_id: UUID,
        count_per_item: int,
        target_dir: str,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            raise ValueError("Batch not found")

        if not target_dir:
            raise ValueError("Original download path is required")

        items = await self.item_repo.get_by_batch(batch_id, limit=batch.total_items)
        download_plan: list[tuple[BatchItem, dict[str, Any], int, int]] = []
        downloaded = 0
        failed_downloads = 0
        failed_items: list[dict[str, str]] = []
        skipped_items = 0

        for item in items:
            image = await self.image_repo.get_by_item(item.id)
            thumbnails = self._parse_thumbnail_payload(image.direct_url if image else "")
            if not thumbnails:
                skipped_items += 1
                continue

            selected_thumbnails = [thumbnail for thumbnail in thumbnails[:count_per_item] if thumbnail.get("url")]
            total_for_item = len(selected_thumbnails)
            for index, thumbnail in enumerate(selected_thumbnails, start=1):
                download_plan.append((item, thumbnail, index, total_for_item))

        completed = 0
        total = len(download_plan)
        self._emit_original_download_progress(
            progress_callback,
            status="running",
            total=total,
            completed=completed,
            downloaded=downloaded,
            failed_downloads=failed_downloads,
            failed_items=failed_items,
            skipped_items=skipped_items,
        )

        for item, thumbnail, index, total_for_item in download_plan:
            url = thumbnail["url"]
            filename = self.downloader.generate_item_filename(
                item.original_query,
                url,
                index,
                total_for_item,
                thumbnail.get("mime_type"),
            )

            try:
                self._emit_original_download_progress(
                    progress_callback,
                    status="running",
                    total=total,
                    completed=completed,
                    downloaded=downloaded,
                    failed_downloads=failed_downloads,
                    failed_items=failed_items,
                    skipped_items=skipped_items,
                    current_item=item.original_query,
                    current_url=url,
                )
                await self.downloader.download_to_directory(
                    url,
                    target_dir,
                    filename,
                )
                downloaded += 1
            except Exception as error:
                failed_downloads += 1
                failed_items.append(
                    {
                        "item_name": item.original_query,
                        "url": url,
                        "error": str(error),
                    }
                )
                logger.warning("Original download failed for %s: %s", url, error)
            finally:
                completed += 1
                self._emit_original_download_progress(
                    progress_callback,
                    status="running",
                    total=total,
                    completed=completed,
                    downloaded=downloaded,
                    failed_downloads=failed_downloads,
                    failed_items=failed_items,
                    skipped_items=skipped_items,
                    current_item=item.original_query,
                    current_url=url,
                )

        await self._log_batch_original_download(batch_id, downloaded, skipped_items, target_dir)
        return {
            "total": total,
            "downloaded": downloaded,
            "failed_downloads": failed_downloads,
            "failed_items": failed_items,
            "skipped_items": skipped_items,
        }

    def _emit_original_download_progress(self, callback: Any, **event: Any) -> None:
        if callback:
            callback(event)

    def _parse_thumbnail_payload(self, payload: str) -> list[dict[str, Any]]:
        if not payload:
            return []

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return []

        if not isinstance(parsed, list):
            return []

        return [item for item in parsed if isinstance(item, dict)]

    async def _log_batch_original_download(
        self,
        batch_id: UUID,
        downloaded: int,
        skipped_items: int,
        target_dir: str,
    ) -> None:
        first_item = (await self.item_repo.get_by_batch(batch_id, limit=1))[:1]
        if not first_item:
            return

        await self._log(
            first_item[0].id,
            "download_originals",
            "success",
            (
                f"Downloaded {downloaded} originals to {target_dir}; "
                f"skipped {skipped_items} items without thumbnails"
            )
        )

    async def _sync_batch_progress(self, batch_id: UUID) -> None:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            return

        saved = await self.item_repo.count_by_batch(batch_id, ItemStatus.SAVED)
        failed = await self.item_repo.count_by_batch(batch_id, ItemStatus.FAILED)
        review_needed = await self.item_repo.count_by_batch(batch_id, ItemStatus.REVIEW_NEEDED)
        pending = await self.item_repo.count_by_batch(batch_id, ItemStatus.PENDING)
        searching = await self.item_repo.count_by_batch(batch_id, ItemStatus.SEARCHING)
        downloading = await self.item_repo.count_by_batch(batch_id, ItemStatus.DOWNLOADING)

        batch.processed_items = saved + failed + review_needed
        batch.failed_items = failed

        if pending + searching + downloading > 0 and batch.processed_items < batch.total_items:
            batch.status = BatchStatus.PROCESSING
        elif failed + review_needed > 0:
            batch.status = BatchStatus.PARTIAL
        else:
            batch.status = BatchStatus.COMPLETED

        await self.batch_repo.update(batch)

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
