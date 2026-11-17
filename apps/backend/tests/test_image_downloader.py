from types import SimpleNamespace
import io
import socket

import httpx
import pytest
from PIL import Image

from src.application.services.image_downloader import ImageDownloader
from src.infrastructure.config import Settings


@pytest.fixture
def downloader():
    return ImageDownloader(SimpleNamespace(), Settings(_env_file=None, allowed_domains="", blocked_domains=""))


@pytest.fixture
def mock_network(monkeypatch):
    original_client = httpx.AsyncClient

    def install(handler, address="8.8.8.8"):
        async def resolve(_host, port, **_kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

        import asyncio
        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolve)
        monkeypatch.setattr(
            "src.application.services.image_downloader.httpx.AsyncClient",
            lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
        )
    return install


def png_bytes():
    output = io.BytesIO()
    Image.new("RGB", (3, 2), "red").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_download_with_retry_does_not_retry_client_http_errors(monkeypatch):
    settings = SimpleNamespace(max_retries=3, retry_backoff_base=2, download_timeout=30)
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


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/image", "http://10.0.0.1/image", "http://[::1]/image",
    "http://[fd00::1]/image", "http://[::ffff:127.0.0.1]/image", "http://localhost/image",
    "http://user:pass@example.test/image", "file:///tmp/image.png",
])
def test_validate_url_rejects_private_addresses_and_credentials(downloader, url):
    with pytest.raises(ValueError):
        downloader._validate_url(url)


def test_domain_allowlist_requires_a_domain_boundary(downloader):
    downloader.settings.allowed_domains = "example.test"
    downloader._validate_url("https://cdn.example.test/image.jpg")
    with pytest.raises(ValueError, match="whitelist"):
        downloader._validate_url("https://example.test.attacker.test/image.jpg")
    with pytest.raises(ValueError, match="whitelist"):
        downloader._validate_url("https://notexample.test/image.jpg")


@pytest.mark.asyncio
async def test_download_pins_public_ip_and_detects_mime_from_bytes(downloader, mock_network):
    def handler(request):
        assert request.url.host == "8.8.8.8"
        assert request.headers["host"] == "cdn.example.test"
        assert request.extensions["sni_hostname"] == "cdn.example.test"
        return httpx.Response(200, content=png_bytes(), headers={"Content-Type": "text/plain"})

    mock_network(handler)
    data, mime = await downloader.fetch_image("https://cdn.example.test/image.jpg")
    assert data == png_bytes()
    assert mime == "image/png"


@pytest.mark.asyncio
async def test_redirect_to_private_address_is_blocked_before_request(downloader, mock_network):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "http://169.254.169.254/metadata"})

    mock_network(handler)
    with pytest.raises(ValueError, match="SSRF"):
        await downloader.fetch_image("https://cdn.example.test/image")
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_relative_redirect_keeps_original_hostname(downloader, mock_network):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        assert request.headers["host"] == "cdn.example.test"
        if len(paths) == 1:
            return httpx.Response(302, headers={"Location": "/final.png"})
        return httpx.Response(200, content=png_bytes())

    mock_network(handler)
    await downloader.fetch_image("https://cdn.example.test/start")
    assert paths == ["/start", "/final.png"]


@pytest.mark.asyncio
async def test_hostname_resolving_to_private_ip_never_receives_a_request(downloader, mock_network):
    def handler(_request):
        raise AssertionError("Private IP must not receive a request")

    mock_network(handler, address="10.0.0.1")
    with pytest.raises(ValueError, match="SSRF"):
        await downloader.fetch_image("https://cdn.example.test/image")


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [{}, {"Content-Length": "1000000"}])
async def test_download_rejects_oversized_responses_with_or_without_length(downloader, mock_network, headers):
    downloader.settings.max_file_size_mb = 0
    mock_network(lambda _request: httpx.Response(200, content=b"too large", headers=headers))
    with pytest.raises(ValueError, match="File too large"):
        await downloader.fetch_image("https://cdn.example.test/image")


@pytest.mark.asyncio
async def test_download_rejects_html_mislabeled_as_an_image(downloader, mock_network):
    mock_network(lambda _request: httpx.Response(200, content=b"<html>blocked</html>", headers={"Content-Type": "image/jpeg"}))
    with pytest.raises(ValueError, match="Invalid or corrupted image"):
        await downloader.fetch_image("https://cdn.example.test/image.jpg")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [408, 429, 503])
async def test_download_retries_transient_http_errors(downloader, mock_network, monkeypatch, status):
    requests = []

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(status)
        return httpx.Response(200, content=png_bytes())

    async def no_wait(_seconds):
        pass

    mock_network(handler)
    monkeypatch.setattr("src.application.services.image_downloader.asyncio.sleep", no_wait)
    await downloader.fetch_image("https://cdn.example.test/image.png")
    assert len(requests) == 2
