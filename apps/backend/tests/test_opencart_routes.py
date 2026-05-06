from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_db_session
from src.domain.entities import OpenCartImageMatchRun


class InMemoryOpenCartImageMatchRunRepository:
    runs: list[OpenCartImageMatchRun] = []

    def __init__(self, _session):
        pass

    async def create(self, run: OpenCartImageMatchRun) -> OpenCartImageMatchRun:
        self.runs.append(run)
        return run

    async def get_by_id(self, run_id: UUID) -> OpenCartImageMatchRun | None:
        return next((run for run in self.runs if run.id == run_id), None)

    async def get_all(self, limit: int = 50, offset: int = 0) -> list[OpenCartImageMatchRun]:
        return self.runs[offset : offset + limit]

    async def count(self) -> int:
        return len(self.runs)


@pytest.fixture()
async def client(monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    from src.main import app

    InMemoryOpenCartImageMatchRunRepository.runs = []

    try:
        import src.api.routes.opencart as opencart_routes
    except ImportError:
        opencart_routes = None

    async def override_db_session():
        yield object()

    app.dependency_overrides[get_db_session] = override_db_session
    if opencart_routes is not None:
        monkeypatch.setattr(
            opencart_routes,
            "OpenCartImageMatchRunRepository",
            InMemoryOpenCartImageMatchRunRepository,
        )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.asyncio()
async def test_generate_without_openrouter_persists_history_and_hides_api_key(client: AsyncClient):
    response = await client.post(
        "/api/opencart/image-matches/generate",
        json={
            "products_text": "123\tABC-001",
            "files_text": "ABC001.jpg",
            "image_prefix": "catalog/products",
            "openrouter_api_key": "sk-secret-value",
            "settings": {
                "use_openrouter": False,
                "model": "openai/gpt-4.1-nano",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert UUID(payload["history_id"])
    assert len(payload["matches"]) == 1
    assert payload["matches"][0]["method"] == "exact"
    assert (
        "UPDATE oc_product SET image = 'catalog/products/ABC001.jpg' WHERE product_id = 123;"
        in payload["sql"]
    )
    assert "sk-secret-value" not in response.text


@pytest.mark.asyncio()
async def test_openrouter_models_are_sorted_by_name(client: AsyncClient, monkeypatch):
    import src.api.routes.opencart as opencart_routes

    class FakeOpenRouterClient:
        def __init__(self, api_key: str = "", timeout: int = 30):
            self.api_key = api_key
            self.timeout = timeout

        async def list_models(self):
            return [
                {"id": "z-provider/zeta", "name": "Zeta", "context_length": 1000},
                {"id": "a-provider/alpha-2", "name": "Alpha", "context_length": 2000},
                {"id": "a-provider/alpha-1", "name": "Alpha", "context_length": 3000},
                {"id": "missing-name/model"},
            ]

    monkeypatch.setattr(opencart_routes, "OpenRouterClient", FakeOpenRouterClient)

    response = await client.get("/api/opencart/image-matches/openrouter/models")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"id": "a-provider/alpha-1", "name": "Alpha", "context_length": 3000},
        {"id": "a-provider/alpha-2", "name": "Alpha", "context_length": 2000},
        {"id": "missing-name/model", "name": "missing-name/model", "context_length": None},
        {"id": "z-provider/zeta", "name": "Zeta", "context_length": 1000},
    ]


@pytest.mark.asyncio()
async def test_generate_with_openrouter_enabled_requires_api_key(client: AsyncClient):
    response = await client.post(
        "/api/opencart/image-matches/generate",
        json={
            "products_text": "123\tABC-001",
            "files_text": "ABC001.jpg",
            "image_prefix": "catalog/products",
            "settings": {"use_openrouter": True},
        },
    )

    assert response.status_code == 400
    assert "openrouter_api_key" in response.json()["detail"]
    assert "required" in response.json()["detail"].lower()
    assert InMemoryOpenCartImageMatchRunRepository.runs == []


@pytest.mark.asyncio()
async def test_history_list_and_detail_hide_openrouter_api_key(client: AsyncClient):
    generate_response = await client.post(
        "/api/opencart/image-matches/generate",
        json={
            "products_text": "123\tABC-001",
            "files_text": "ABC001.jpg",
            "image_prefix": "catalog/products",
            "openrouter_api_key": "sk-secret-value",
            "settings": {"use_openrouter": False},
        },
    )
    history_id = generate_response.json()["history_id"]

    list_response = await client.get("/api/opencart/image-matches/history")
    detail_response = await client.get(f"/api/opencart/image-matches/history/{history_id}")

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == history_id
    assert list_payload["items"][0]["matched_count"] == 1
    assert "openrouter_api_key" not in list_response.text
    assert "sk-secret-value" not in list_response.text

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == history_id
    assert detail_payload["result"]["matches"][0]["method"] == "exact"
    assert "openrouter_api_key" not in detail_response.text
    assert "sk-secret-value" not in detail_response.text
