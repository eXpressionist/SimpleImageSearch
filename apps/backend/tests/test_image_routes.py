import json
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_db_session, get_image_preview_service
from src.api.routes import images as image_routes
from src.application.services.image_preview import ImagePreviewService
from src.domain.entities import ImageAsset
from src.infrastructure.config import Settings
from src.infrastructure.providers.local_storage import LocalFileStorage


@pytest.fixture
async def image_client(tmp_path, monkeypatch):
    image = ImageAsset(
        id=uuid4(), item_id=uuid4(), source_url="", direct_url=json.dumps([{"url": "https://example.test/image.jpg"}]),
        file_path="", file_name="thumbnails.json", mime_type="application/json", file_size=0, file_hash="",
    )

    class ImageRepository:
        def __init__(self, _session):
            pass

        async def get_by_id(self, image_id):
            return image if image_id == image.id else None

        async def get_by_item(self, item_id):
            return image if item_id == image.item_id else None

    async def db_session():
        yield object()

    service = ImagePreviewService(LocalFileStorage(str(tmp_path)), Settings(_env_file=None))
    app = FastAPI()
    app.include_router(image_routes.router, prefix="/api")
    app.dependency_overrides[get_db_session] = db_session
    app.dependency_overrides[get_image_preview_service] = lambda: service
    monkeypatch.setattr(image_routes, "ImageRepository", ImageRepository)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, image, service


@pytest.mark.asyncio
async def test_metadata_only_assets_return_404_instead_of_serving_a_directory(image_client):
    client, image, _ = image_client
    for path in [f"{image.id}/file", f"item/{image.item_id}/file"]:
        assert (await client.get(f"/api/images/{path}")).status_code == 404


@pytest.mark.asyncio
async def test_preview_route_returns_an_image_with_cache_headers(image_client, monkeypatch):
    from test_image_preview import make_image_bytes

    client, image, service = image_client

    async def fetch(_url):
        return make_image_bytes(), "image/jpeg"

    monkeypatch.setattr(service.downloader, "fetch_image", fetch)
    response = await client.get(f"/api/images/{image.id}/preview/0")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "public, max-age=86400"
    assert response.content.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_preview_route_reports_missing_asset_or_index(image_client):
    client, image, _ = image_client
    assert (await client.get(f"/api/images/{uuid4()}/preview/0")).status_code == 404
    assert (await client.get(f"/api/images/{image.id}/preview/1")).status_code == 404
    assert (await client.get(f"/api/images/{image.id}/preview/-1")).status_code == 404


@pytest.mark.asyncio
async def test_preview_failure_is_not_cached(image_client, monkeypatch):
    client, image, service = image_client

    async def fail(_url):
        raise ValueError("HTTP 403")

    monkeypatch.setattr(service.downloader, "fetch_image", fail)
    response = await client.get(f"/api/images/{image.id}/preview/0")
    assert response.status_code == 502
    assert response.headers["cache-control"] == "no-store"
