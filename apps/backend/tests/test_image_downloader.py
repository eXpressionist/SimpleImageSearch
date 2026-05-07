from types import SimpleNamespace

import pytest

from src.application.services.image_downloader import ImageDownloader


@pytest.mark.asyncio
async def test_download_with_retry_does_not_retry_client_http_errors(monkeypatch):
    settings = SimpleNamespace(max_retries=3, retry_backoff_base=2)
    downloader = ImageDownloader(storage=SimpleNamespace(), settings=settings)
    calls = 0

    async def fail_with_forbidden(_url):
        nonlocal calls
        calls += 1
        raise ValueError("HTTP 403")

    async def fail_if_sleep_is_called(_seconds):
        raise AssertionError("Client HTTP errors should not wait before failing")

    monkeypatch.setattr(downloader, "_download", fail_with_forbidden)
    monkeypatch.setattr("src.application.services.image_downloader.asyncio.sleep", fail_if_sleep_is_called)

    with pytest.raises(ValueError, match="HTTP 403"):
        await downloader._download_with_retry("https://cdn.example.test/blocked.jpg")

    assert calls == 1
