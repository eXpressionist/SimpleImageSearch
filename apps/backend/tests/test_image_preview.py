import asyncio
import io
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image

from src.application.services.image_preview import ImagePreviewService
from src.infrastructure.config import Settings
from src.infrastructure.providers.local_storage import LocalFileStorage


def make_image_bytes(size=(1200, 800)):
    output = io.BytesIO()
    Image.new("RGB", size, "blue").save(output, format="JPEG")
    return output.getvalue()


def make_asset(payload):
    return SimpleNamespace(id=uuid4(), mime_type="application/json", direct_url=json.dumps(payload))


@pytest.fixture
def preview_service(tmp_path):
    return ImagePreviewService(LocalFileStorage(str(tmp_path)), Settings(_env_file=None))


@pytest.mark.asyncio
async def test_preview_prefers_thumbnail_and_caches_resized_image(preview_service, monkeypatch):
    image = make_asset([{"url": "https://example.test/original.jpg", "thumbnail_url": "https://example.test/thumbnail.jpg"}])
    calls = []

    async def fetch(url):
        calls.append(url)
        return make_image_bytes(), "image/jpeg"

    monkeypatch.setattr(preview_service.downloader, "fetch_image", fetch)
    path = await preview_service.get_preview(image, 0)
    assert calls == ["https://example.test/thumbnail.jpg"]
    with Image.open(path) as result:
        assert result.size == (512, 341)
        assert result.format == "PNG"
    assert await preview_service.get_preview(image, 0) == path
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_preview_falls_back_to_original_when_thumbnail_is_unavailable(preview_service, monkeypatch):
    image = make_asset([{"url": "https://example.test/original.jpg", "thumbnail_url": "https://example.test/expired.jpg"}])
    calls = []

    async def fetch(url):
        calls.append(url)
        if "expired" in url:
            raise ValueError("HTTP 403")
        return make_image_bytes(), "image/jpeg"

    monkeypatch.setattr(preview_service.downloader, "fetch_image", fetch)
    assert (await preview_service.get_preview(image, 0)).is_file()
    assert calls == ["https://example.test/expired.jpg", "https://example.test/original.jpg"]


@pytest.mark.asyncio
async def test_preview_supports_existing_batches_without_thumbnail_urls(preview_service, monkeypatch):
    image = make_asset([{"url": "https://example.test/original.jpg"}])

    async def fetch(url):
        assert url == "https://example.test/original.jpg"
        return make_image_bytes(), "image/jpeg"

    monkeypatch.setattr(preview_service.downloader, "fetch_image", fetch)
    assert (await preview_service.get_preview(image, 0)).is_file()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,index", [([], 0), ({}, 0), ([None], 0), ([{}], -1), ([{}], 1)])
async def test_preview_rejects_invalid_metadata(preview_service, payload, index):
    with pytest.raises(IndexError):
        await preview_service.get_preview(make_asset(payload), index)


@pytest.mark.asyncio
async def test_failed_preview_does_not_create_a_cache_file(preview_service, monkeypatch):
    image = make_asset([{"url": "https://example.test/blocked.jpg"}])

    async def fail(_url):
        raise ValueError("HTTP 403")

    monkeypatch.setattr(preview_service.downloader, "fetch_image", fail)
    with pytest.raises(ValueError, match="No image source"):
        await preview_service.get_preview(image, 0)
    assert not list(preview_service.storage.base_path.rglob("*.png"))


@pytest.mark.asyncio
async def test_concurrent_viewers_share_one_preview_download(preview_service, monkeypatch):
    image = make_asset([{"url": "https://example.test/original.jpg"}])
    calls = []

    async def fetch(url):
        calls.append(url)
        await asyncio.sleep(0)
        return make_image_bytes(), "image/jpeg"

    monkeypatch.setattr(preview_service.downloader, "fetch_image", fetch)
    first, second = await asyncio.gather(
        preview_service.get_preview(image, 0), preview_service.get_preview(image, 0)
    )
    assert first == second
    assert calls == ["https://example.test/original.jpg"]
