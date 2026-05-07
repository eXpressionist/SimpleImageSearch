import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.services.batch_processor import BatchProcessor
from src.domain.entities import Batch, BatchItem
from src.domain.interfaces import SearchResult
from src.domain.value_objects import BatchStatus, ItemStatus


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class UnusedSearchProvider:
    async def search(self, _config):
        raise AssertionError("search should not run for an item that already has an image")


class FakeSearchProvider:
    def __init__(self, results):
        self.results = results

    async def search(self, _config):
        return self.results


class FakeStorage:
    pass


class FakeBatchRepo:
    def __init__(self, batch):
        self.batch = batch

    async def get_by_id(self, _batch_id):
        return self.batch

    async def update(self, batch):
        self.batch = batch
        return batch


class FakeItemRepo:
    def __init__(self, item, counts=None):
        self.item = item
        self.counts = counts or {}
        self.pending_batches = []
        self.batch_items = []

    async def get_by_id(self, _item_id):
        return self.item

    async def update(self, item):
        self.item = item
        return item

    async def count_by_batch(self, _batch_id, status=None):
        return self.counts.get(status, 0)

    async def get_pending(self, _batch_id, limit=10):
        if self.pending_batches:
            return self.pending_batches.pop(0)
        return []

    async def get_by_batch(self, _batch_id, status=None, limit=100, offset=0):
        return self.batch_items[offset : offset + limit]


class FakeImageRepo:
    def __init__(self, image=None):
        self.image = image
        self.created = []

    async def get_by_item(self, _item_id):
        return self.image

    async def create(self, image):
        self.created.append(image)
        return image


class FakeLogRepo:
    def __init__(self):
        self.logs = []

    async def create(self, log):
        self.logs.append(log)
        return log


class FakeOriginalDownloader:
    def __init__(self, failed_urls=None):
        self.calls = []
        self.failed_urls = set(failed_urls or [])

    def generate_item_filename(self, item_name, url, index, total, _content_type=None):
        ext = url.rsplit(".", 1)[-1]
        suffix = f"-{index}" if total > 1 else ""
        return f"{item_name.replace(' ', '_')}{suffix}.{ext}"

    async def download_to_directory(self, url, target_dir, filename):
        self.calls.append((url, target_dir, filename))
        if url in self.failed_urls:
            raise ValueError("HTTP 403")
        return SimpleNamespace(
            file_path=f"{target_dir}/{filename}",
            file_name=filename,
            mime_type="image/jpeg",
            file_size=10,
            file_hash="hash",
            width=1,
            height=1,
        )


def make_processor(batch, item, image=None, counts=None):
    processor = BatchProcessor(
        session=FakeSession(),
        search_provider=UnusedSearchProvider(),
        storage=FakeStorage(),
    )
    processor.batch_repo = FakeBatchRepo(batch)
    processor.item_repo = FakeItemRepo(item, counts)
    processor.image_repo = FakeImageRepo(image)
    processor.log_repo = FakeLogRepo()
    return processor


def make_search_result(url: str, source_url: str = "https://example.test/page") -> SearchResult:
    return SearchResult(
        direct_url=url,
        source_url=source_url,
        title="Product image",
        mime_type="image/jpeg",
    )


@pytest.mark.asyncio
async def test_process_item_marks_existing_image_item_saved_without_duplicate_insert():
    batch_id = uuid4()
    item_id = uuid4()
    batch = Batch(id=batch_id, name="stuck", total_items=1, status=BatchStatus.PROCESSING)
    item = BatchItem(
        id=item_id,
        batch_id=batch_id,
        position=0,
        original_query="RB5009",
        normalized_query="rb5009",
        status=ItemStatus.PENDING,
    )
    existing_image = SimpleNamespace(item_id=item_id)
    processor = make_processor(
        batch,
        item,
        existing_image,
        counts={
            ItemStatus.SAVED: 1,
            ItemStatus.FAILED: 0,
            ItemStatus.REVIEW_NEEDED: 0,
            ItemStatus.PENDING: 0,
            ItemStatus.SEARCHING: 0,
            ItemStatus.DOWNLOADING: 0,
        },
    )

    await processor._process_item(batch_id, item_id)

    assert processor.item_repo.item.status == ItemStatus.SAVED
    assert processor.image_repo.created == []
    assert processor.batch_repo.batch.status == BatchStatus.COMPLETED
    assert processor.batch_repo.batch.processed_items == 1


@pytest.mark.asyncio
async def test_sync_batch_progress_finalizes_from_actual_item_status_counts():
    batch_id = uuid4()
    batch = Batch(
        id=batch_id,
        name="wrong counters",
        total_items=3,
        processed_items=1,
        failed_items=0,
        status=BatchStatus.PROCESSING,
    )
    item = BatchItem(
        id=uuid4(),
        batch_id=batch_id,
        position=0,
        original_query="x",
        normalized_query="x",
    )
    processor = make_processor(
        batch,
        item,
        counts={
            ItemStatus.SAVED: 2,
            ItemStatus.FAILED: 1,
            ItemStatus.REVIEW_NEEDED: 0,
            ItemStatus.PENDING: 0,
            ItemStatus.SEARCHING: 0,
            ItemStatus.DOWNLOADING: 0,
        },
    )

    await processor._sync_batch_progress(batch_id)

    assert processor.batch_repo.batch.processed_items == 3
    assert processor.batch_repo.batch.failed_items == 1
    assert processor.batch_repo.batch.status == BatchStatus.PARTIAL


@pytest.mark.asyncio
async def test_process_batch_processes_items_sequentially_with_one_session():
    batch_id = uuid4()
    batch = Batch(id=batch_id, name="sequential", total_items=2)
    item = BatchItem(
        id=uuid4(),
        batch_id=batch_id,
        position=0,
        original_query="x",
        normalized_query="x",
    )
    processor = make_processor(
        batch,
        item,
        counts={
            ItemStatus.SAVED: 2,
            ItemStatus.FAILED: 0,
            ItemStatus.REVIEW_NEEDED: 0,
            ItemStatus.PENDING: 0,
            ItemStatus.SEARCHING: 0,
            ItemStatus.DOWNLOADING: 0,
        },
    )
    pending_items = [
        BatchItem(id=uuid4(), batch_id=batch_id, position=0, original_query="a", normalized_query="a"),
        BatchItem(id=uuid4(), batch_id=batch_id, position=1, original_query="b", normalized_query="b"),
    ]
    processor.item_repo.pending_batches = [pending_items]
    active = 0
    max_active = 0

    async def track_processing(_batch_id, _item_id):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1

    processor._process_item_with_semaphore = track_processing

    await processor.process_batch(batch_id)

    assert max_active == 1


@pytest.mark.asyncio
async def test_download_originals_for_batch_uses_item_names_in_one_directory():
    batch_id = uuid4()
    item_id = uuid4()
    batch = Batch(
        id=batch_id,
        name="originals",
        total_items=1,
    )
    item = BatchItem(
        id=item_id,
        batch_id=batch_id,
        position=0,
        original_query="SKU phone",
        normalized_query="sku phone",
    )
    processor = make_processor(
        batch,
        item,
        counts={
            ItemStatus.SAVED: 1,
            ItemStatus.FAILED: 0,
            ItemStatus.REVIEW_NEEDED: 0,
            ItemStatus.PENDING: 0,
            ItemStatus.SEARCHING: 0,
            ItemStatus.DOWNLOADING: 0,
        },
    )
    processor.item_repo.batch_items = [item]
    processor.image_repo.image = SimpleNamespace(
        direct_url=json.dumps(
            [
                {"url": "https://cdn.example.test/a.jpg", "mime_type": "image/jpeg"},
                {"url": "https://cdn.example.test/b.png", "mime_type": "image/png"},
                {"url": "https://cdn.example.test/c.webp", "mime_type": "image/webp"},
            ]
        )
    )
    processor.downloader = FakeOriginalDownloader()

    result = await processor.download_originals_for_batch(
        batch_id,
        count_per_item=2,
        target_dir="C:/exports/images",
    )

    assert processor.downloader.calls == [
        ("https://cdn.example.test/a.jpg", "C:/exports/images", "SKU_phone-1.jpg"),
        ("https://cdn.example.test/b.png", "C:/exports/images", "SKU_phone-2.png"),
    ]
    assert result == {
        "total": 2,
        "downloaded": 2,
        "failed_downloads": 0,
        "failed_items": [],
        "skipped_items": 0,
    }


@pytest.mark.asyncio
async def test_download_originals_for_batch_continues_after_forbidden_original():
    batch_id = uuid4()
    item_id = uuid4()
    batch = Batch(id=batch_id, name="originals", total_items=1)
    item = BatchItem(
        id=item_id,
        batch_id=batch_id,
        position=0,
        original_query="Camera Lens",
        normalized_query="camera lens",
    )
    processor = make_processor(batch, item)
    processor.item_repo.batch_items = [item]
    processor.image_repo.image = SimpleNamespace(
        direct_url=json.dumps(
            [
                {"url": "https://cdn.example.test/blocked.jpg", "mime_type": "image/jpeg"},
                {"url": "https://cdn.example.test/ok.png", "mime_type": "image/png"},
            ]
        )
    )
    progress_events = []
    processor.downloader = FakeOriginalDownloader(failed_urls={"https://cdn.example.test/blocked.jpg"})

    result = await processor.download_originals_for_batch(
        batch_id,
        count_per_item=2,
        target_dir="C:/exports/images",
        progress_callback=progress_events.append,
    )

    assert processor.downloader.calls == [
        ("https://cdn.example.test/blocked.jpg", "C:/exports/images", "Camera_Lens-1.jpg"),
        ("https://cdn.example.test/ok.png", "C:/exports/images", "Camera_Lens-2.png"),
    ]
    assert result == {
        "total": 2,
        "downloaded": 1,
        "failed_downloads": 1,
        "failed_items": [
            {
                "item_name": "Camera Lens",
                "original_number": 1,
                "url": "https://cdn.example.test/blocked.jpg",
                "error": "HTTP 403",
            }
        ],
        "skipped_items": 0,
    }
    assert progress_events[-1]["status"] == "running"
    assert progress_events[-1]["completed"] == 2
    assert progress_events[-1]["failed_items"] == [
        {
            "item_name": "Camera Lens",
            "original_number": 1,
            "url": "https://cdn.example.test/blocked.jpg",
            "error": "HTTP 403",
        }
    ]


@pytest.mark.asyncio
async def test_download_originals_for_batch_reports_current_item_before_download():
    batch_id = uuid4()
    item_id = uuid4()
    batch = Batch(id=batch_id, name="originals", total_items=1)
    item = BatchItem(
        id=item_id,
        batch_id=batch_id,
        position=0,
        original_query="Slow Item",
        normalized_query="slow item",
    )
    processor = make_processor(batch, item)
    processor.item_repo.batch_items = [item]
    processor.image_repo.image = SimpleNamespace(
        direct_url=json.dumps(
            [
                {"url": "https://cdn.example.test/slow.jpg", "mime_type": "image/jpeg"},
            ]
        )
    )
    progress_events = []
    processor.downloader = FakeOriginalDownloader()

    await processor.download_originals_for_batch(
        batch_id,
        count_per_item=1,
        target_dir="C:/exports/images",
        progress_callback=progress_events.append,
    )

    assert progress_events[1]["completed"] == 0
    assert progress_events[1]["current_item"] == "Slow Item"
    assert progress_events[1]["current_url"] == "https://cdn.example.test/slow.jpg"
