# OpenCart Image SQL Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a separate OpenCart 3 tool that accepts pasted product IDs/SKUs and filenames, matches one image file per product, generates `oc_product.image` SQL, and stores run history without saving OpenRouter secrets.

**Architecture:** Add an isolated backend feature under the existing layered FastAPI structure: DTOs, service, provider, database model/repository, and route. Add a dedicated frontend page with paste inputs, localStorage-backed OpenRouter key, match results, copyable SQL, and history detail loading.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Pydantic, pytest, React 18, TypeScript, React Router, Vite.

---

## File Structure

Backend files:

- Create `apps/backend/src/domain/entities/opencart_image_match.py`: lightweight dataclasses/enums for parsed products, match methods, match rows, reports, and history entities.
- Create `apps/backend/src/application/dto/opencart.py`: request/response DTOs for generate and history endpoints.
- Create `apps/backend/src/application/services/opencart_matcher.py`: pure parsing, normalization, algorithmic matching, LLM response validation, SQL generation.
- Create `apps/backend/src/infrastructure/providers/openrouter.py`: OpenRouter HTTP client.
- Modify `apps/backend/src/infrastructure/database/models.py`: add `OpenCartImageMatchRunModel`.
- Modify `apps/backend/src/infrastructure/database/repositories.py`: add `OpenCartImageMatchRunRepository`.
- Create `apps/backend/src/api/routes/opencart.py`: REST endpoints.
- Modify `apps/backend/src/api/routes/__init__.py`: export `opencart_router`.
- Modify `apps/backend/src/main.py`: include the new router.
- Create `apps/backend/tests/test_opencart_matcher.py`: unit tests for parser, matcher, SQL generation, and LLM validation.
- Create `apps/backend/tests/test_opencart_routes.py`: API/history tests using mocked provider.

Frontend files:

- Create `apps/frontend/src/types/opencart.ts`: request/response types.
- Create `apps/frontend/src/api/opencart.ts`: API helpers.
- Create `apps/frontend/src/hooks/useLocalStorage.ts`: small typed localStorage hook.
- Create `apps/frontend/src/pages/OpenCartSqlPage.tsx`: UI for generation and history.
- Modify `apps/frontend/src/App.tsx`: add route.
- Modify `apps/frontend/src/components/layout/Header.tsx`: add navigation button.
- Modify `apps/frontend/src/styles.css`: layout for the new tool.

---

### Task 1: Backend Domain and DTO Shapes

**Files:**

- Create: `apps/backend/src/domain/entities/opencart_image_match.py`
- Modify: `apps/backend/src/domain/entities/__init__.py`
- Create: `apps/backend/src/application/dto/opencart.py`

- [ ] **Step 1: Write entity types**

Create `apps/backend/src/domain/entities/opencart_image_match.py` with these definitions:

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class OpenCartMatchMethod(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    LLM = "llm"


@dataclass
class OpenCartProductInput:
    product_id: int
    sku: str
    line_number: int


@dataclass
class OpenCartParseError:
    line_number: int
    line: str
    message: str


@dataclass
class OpenCartImageMatch:
    product_id: int
    sku: str
    filename: str
    image_path: str
    method: OpenCartMatchMethod
    confidence: float
    reason: str


@dataclass
class OpenCartMatchConflict:
    product_id: int | None
    sku: str | None
    filename: str | None
    message: str


@dataclass
class OpenCartMatchSettings:
    use_openrouter: bool = False
    model: str = "openai/gpt-4.1-nano"
    fuzzy_threshold: float = 0.78
    low_confidence_threshold: float = 0.86
    ignore_service_words: bool = True


@dataclass
class OpenCartMatchReport:
    matches: list[OpenCartImageMatch] = field(default_factory=list)
    unmatched_products: list[OpenCartProductInput] = field(default_factory=list)
    unused_files: list[str] = field(default_factory=list)
    parse_errors: list[OpenCartParseError] = field(default_factory=list)
    conflicts: list[OpenCartMatchConflict] = field(default_factory=list)
    low_confidence_matches: list[OpenCartImageMatch] = field(default_factory=list)
    sql: str = ""


@dataclass
class OpenCartImageMatchRun:
    id: UUID = field(default_factory=uuid4)
    products_text: str = ""
    files_text: str = ""
    image_prefix: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    used_openrouter: bool = False
    model: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    sql: str = ""
    total_products: int = 0
    total_files: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    unused_file_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
```

- [ ] **Step 2: Export the domain types**

Append to `apps/backend/src/domain/entities/__init__.py`:

```python
from .opencart_image_match import (
    OpenCartImageMatchRun,
    OpenCartImageMatch,
    OpenCartMatchConflict,
    OpenCartMatchMethod,
    OpenCartMatchReport,
    OpenCartMatchSettings,
    OpenCartParseError,
    OpenCartProductInput,
)
```

- [ ] **Step 3: Add DTOs**

Create `apps/backend/src/application/dto/opencart.py`:

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OpenCartMatchSettingsDTO(BaseModel):
    use_openrouter: bool = False
    model: str = "openai/gpt-4.1-nano"
    fuzzy_threshold: float = Field(default=0.78, ge=0.0, le=1.0)
    low_confidence_threshold: float = Field(default=0.86, ge=0.0, le=1.0)
    ignore_service_words: bool = True


class OpenCartGenerateRequestDTO(BaseModel):
    products_text: str = Field(min_length=1)
    files_text: str = Field(min_length=1)
    image_prefix: str = ""
    settings: OpenCartMatchSettingsDTO = Field(default_factory=OpenCartMatchSettingsDTO)
    openrouter_api_key: str | None = None


class OpenCartProductDTO(BaseModel):
    product_id: int
    sku: str
    line_number: int


class OpenCartParseErrorDTO(BaseModel):
    line_number: int
    line: str
    message: str


class OpenCartImageMatchDTO(BaseModel):
    product_id: int
    sku: str
    filename: str
    image_path: str
    method: str
    confidence: float
    reason: str


class OpenCartMatchConflictDTO(BaseModel):
    product_id: int | None = None
    sku: str | None = None
    filename: str | None = None
    message: str


class OpenCartGenerateResponseDTO(BaseModel):
    history_id: UUID
    matches: list[OpenCartImageMatchDTO]
    unmatched_products: list[OpenCartProductDTO]
    unused_files: list[str]
    parse_errors: list[OpenCartParseErrorDTO]
    conflicts: list[OpenCartMatchConflictDTO]
    low_confidence_matches: list[OpenCartImageMatchDTO]
    sql: str


class OpenCartHistorySummaryDTO(BaseModel):
    id: UUID
    created_at: datetime
    total_products: int
    total_files: int
    matched_count: int
    unmatched_count: int
    unused_file_count: int
    used_openrouter: bool
    model: str | None = None


class OpenCartHistoryListDTO(BaseModel):
    items: list[OpenCartHistorySummaryDTO]
    total: int
    page: int
    page_size: int


class OpenCartHistoryDetailDTO(OpenCartHistorySummaryDTO):
    products_text: str
    files_text: str
    image_prefix: str
    settings: dict[str, Any]
    result: dict[str, Any]
    sql: str
```

- [ ] **Step 4: Commit**

Run:

```bash
git add apps/backend/src/domain/entities/opencart_image_match.py apps/backend/src/domain/entities/__init__.py apps/backend/src/application/dto/opencart.py
git commit -m "Add OpenCart match DTOs"
```

---

### Task 2: Backend Matcher Tests First

**Files:**

- Create: `apps/backend/tests/test_opencart_matcher.py`

- [ ] **Step 1: Add failing tests for parsing, normalization, matching, and SQL**

Create `apps/backend/tests/test_opencart_matcher.py`:

```python
import pytest

from src.application.services.opencart_matcher import OpenCartImageMatcher
from src.domain.entities.opencart_image_match import OpenCartMatchSettings


def make_matcher() -> OpenCartImageMatcher:
    return OpenCartImageMatcher()


def test_parse_products_accepts_common_separators():
    matcher = make_matcher()

    products, errors = matcher.parse_products("123\tABC-001\n124;ABC-002\n125,ABC-003\n126   ABC-004")

    assert errors == []
    assert [(p.product_id, p.sku) for p in products] == [
        (123, "ABC-001"),
        (124, "ABC-002"),
        (125, "ABC-003"),
        (126, "ABC-004"),
    ]


def test_parse_products_reports_invalid_lines():
    matcher = make_matcher()

    products, errors = matcher.parse_products("123 ABC-001\nbad-line")

    assert [(p.product_id, p.sku) for p in products] == [(123, "ABC-001")]
    assert len(errors) == 1
    assert errors[0].line_number == 2
    assert "product_id" in errors[0].message


def test_parse_files_trims_blank_lines_and_keeps_order():
    matcher = make_matcher()

    files = matcher.parse_files("\nABC001.jpg\n abc-002-main.webp \n")

    assert files == ["ABC001.jpg", "abc-002-main.webp"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ABC-001", "abc001"),
        ("ABC_001.jpg", "abc001"),
        ("abc 001 main.webp", "abc001"),
    ],
)
def test_normalize_for_match(value, expected):
    matcher = make_matcher()

    assert matcher.normalize_for_match(value, ignore_service_words=True) == expected


def test_generate_prefers_normalized_one_to_one_matches():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001\n124\tDEF-002",
        files_text="ABC001.jpg\nDEF_002.webp",
        image_prefix="catalog/products/import/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert [(m.product_id, m.sku, m.filename, m.method.value) for m in report.matches] == [
        (123, "ABC-001", "ABC001.jpg", "normalized"),
        (124, "DEF-002", "DEF_002.webp", "normalized"),
    ]
    assert report.unmatched_products == []
    assert report.unused_files == []
    assert "UPDATE oc_product SET image = 'catalog/products/import/ABC001.jpg' WHERE product_id = 123;" in report.sql


def test_generate_reports_unmatched_products_and_unused_files():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001\n124\tDEF-002",
        files_text="ABC001.jpg\nZZZ.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert [(m.product_id, m.filename) for m in report.matches] == [(123, "ABC001.jpg")]
    assert [(p.product_id, p.sku) for p in report.unmatched_products] == [(124, "DEF-002")]
    assert report.unused_files == ["ZZZ.jpg"]


def test_generate_rejects_duplicate_file_assignment():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001\n124\tABC001",
        files_text="ABC001.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert len(report.matches) == 1
    assert len(report.unmatched_products) == 1
    assert report.conflicts


def test_sql_escapes_single_quotes_in_paths():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001",
        files_text="ABC001's.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert "ABC001''s.jpg" in report.sql
```

- [ ] **Step 2: Run tests to verify they fail because matcher does not exist**

Run:

```bash
cd apps/backend
pytest tests/test_opencart_matcher.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.application.services.opencart_matcher'`.

---

### Task 3: Backend Matcher Implementation

**Files:**

- Create: `apps/backend/src/application/services/opencart_matcher.py`
- Modify: `apps/backend/src/application/services/__init__.py`
- Test: `apps/backend/tests/test_opencart_matcher.py`

- [ ] **Step 1: Implement pure matcher**

Create `apps/backend/src/application/services/opencart_matcher.py`:

```python
import json
import re
from difflib import SequenceMatcher
from pathlib import PurePosixPath
from typing import Any

from src.domain.entities.opencart_image_match import (
    OpenCartImageMatch,
    OpenCartMatchConflict,
    OpenCartMatchMethod,
    OpenCartMatchReport,
    OpenCartMatchSettings,
    OpenCartParseError,
    OpenCartProductInput,
)


class OpenCartImageMatcher:
    _service_words = {"main", "photo", "image", "img", "foto", "product"}

    def parse_products(self, products_text: str) -> tuple[list[OpenCartProductInput], list[OpenCartParseError]]:
        products: list[OpenCartProductInput] = []
        errors: list[OpenCartParseError] = []

        for index, raw_line in enumerate(products_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = re.split(r"\t|;|,|\s{2,}", line, maxsplit=1)
            if len(parts) != 2:
                parts = line.split(maxsplit=1)
            if len(parts) != 2 or not parts[0].strip().isdigit() or not parts[1].strip():
                errors.append(OpenCartParseError(index, raw_line, "Line must contain numeric product_id and non-empty sku"))
                continue
            products.append(OpenCartProductInput(product_id=int(parts[0].strip()), sku=parts[1].strip(), line_number=index))

        return products, errors

    def parse_files(self, files_text: str) -> list[str]:
        return [line.strip() for line in files_text.splitlines() if line.strip()]

    def normalize_for_match(self, value: str, ignore_service_words: bool = True) -> str:
        stem = PurePosixPath(value.replace("\\", "/")).name
        stem = re.sub(r"\.[A-Za-z0-9]{1,8}$", "", stem)
        tokens = [token for token in re.split(r"[\s_\-.,()[\]{}]+", stem.lower()) if token]
        if ignore_service_words:
            tokens = [token for token in tokens if token not in self._service_words]
        return re.sub(r"[^a-z0-9а-яё]+", "", "".join(tokens))

    def generate(
        self,
        products_text: str,
        files_text: str,
        image_prefix: str,
        settings: OpenCartMatchSettings,
        llm_matches: list[dict[str, Any]] | None = None,
    ) -> OpenCartMatchReport:
        products, parse_errors = self.parse_products(products_text)
        files = self.parse_files(files_text)
        report = OpenCartMatchReport(parse_errors=parse_errors)
        used_files: set[str] = set()
        matched_product_ids: set[int] = set()

        file_candidates = [
            {
                "filename": filename,
                "source_key": self.normalize_for_match(filename, ignore_service_words=False),
                "normalized_key": self.normalize_for_match(filename, settings.ignore_service_words),
            }
            for filename in files
        ]

        for product in products:
            candidates = self._rank_candidates(product, file_candidates, used_files, settings)
            if not candidates:
                continue

            best = candidates[0]
            tied = [candidate for candidate in candidates if candidate["score"] == best["score"]]
            if len(tied) > 1:
                report.conflicts.append(
                    OpenCartMatchConflict(product.product_id, product.sku, None, "Multiple files have the same best score")
                )
                continue

            match = self._make_match(product, best["filename"], image_prefix, best["method"], best["score"], best["reason"])
            report.matches.append(match)
            used_files.add(best["filename"])
            matched_product_ids.add(product.product_id)

        if llm_matches:
            self._apply_llm_matches(
                report=report,
                llm_matches=llm_matches,
                products=products,
                files=files,
                image_prefix=image_prefix,
                used_files=used_files,
                matched_product_ids=matched_product_ids,
                settings=settings,
            )

        report.unmatched_products = [product for product in products if product.product_id not in matched_product_ids]
        report.unused_files = [filename for filename in files if filename not in used_files]
        report.low_confidence_matches = [
            match for match in report.matches if match.confidence < settings.low_confidence_threshold
        ]
        report.sql = self.generate_sql(report.matches)
        return report

    def generate_sql(self, matches: list[OpenCartImageMatch]) -> str:
        lines: list[str] = []
        for match in matches:
            image_path = match.image_path.replace("'", "''")
            sku = match.sku.replace("'", "''")
            filename = match.filename.replace("'", "''")
            lines.append(f"-- SKU: {sku}, file: {filename}, method: {match.method.value}")
            lines.append(f"UPDATE oc_product SET image = '{image_path}' WHERE product_id = {match.product_id};")
        return "\n".join(lines)

    def parse_llm_json(self, content: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\[[\s\S]*\]", content)
            if not match:
                return []
            data = json.loads(match.group(0))
        return data if isinstance(data, list) else []

    def _rank_candidates(
        self,
        product: OpenCartProductInput,
        file_candidates: list[dict[str, str]],
        used_files: set[str],
        settings: OpenCartMatchSettings,
    ) -> list[dict[str, Any]]:
        source_key = self.normalize_for_match(product.sku, ignore_service_words=False)
        normalized_key = self.normalize_for_match(product.sku, settings.ignore_service_words)
        ranked: list[dict[str, Any]] = []

        for candidate in file_candidates:
            if candidate["filename"] in used_files:
                continue
            method = OpenCartMatchMethod.FUZZY
            reason = "fuzzy similarity"
            score = SequenceMatcher(None, normalized_key, candidate["normalized_key"]).ratio()

            if source_key and source_key == candidate["source_key"]:
                method = OpenCartMatchMethod.EXACT
                reason = "exact normalized source match"
                score = 1.0
            elif normalized_key and normalized_key == candidate["normalized_key"]:
                method = OpenCartMatchMethod.NORMALIZED
                reason = "normalized SKU matches filename"
                score = 0.96

            if score >= settings.fuzzy_threshold:
                ranked.append({
                    "filename": candidate["filename"],
                    "method": method,
                    "score": round(score, 4),
                    "reason": reason,
                })

        return sorted(ranked, key=lambda item: item["score"], reverse=True)

    def _make_match(
        self,
        product: OpenCartProductInput,
        filename: str,
        image_prefix: str,
        method: OpenCartMatchMethod,
        confidence: float,
        reason: str,
    ) -> OpenCartImageMatch:
        prefix = image_prefix.rstrip("/")
        image_path = f"{prefix}/{filename}" if prefix else filename
        return OpenCartImageMatch(product.product_id, product.sku, filename, image_path, method, confidence, reason)

    def _apply_llm_matches(
        self,
        report: OpenCartMatchReport,
        llm_matches: list[dict[str, Any]],
        products: list[OpenCartProductInput],
        files: list[str],
        image_prefix: str,
        used_files: set[str],
        matched_product_ids: set[int],
        settings: OpenCartMatchSettings,
    ) -> None:
        products_by_id = {product.product_id: product for product in products}
        files_set = set(files)

        for row in llm_matches:
            product_id = row.get("product_id")
            filename = row.get("filename")
            confidence = float(row.get("confidence", 0.0) or 0.0)
            reason = str(row.get("reason", "OpenRouter match"))

            if product_id not in products_by_id:
                report.conflicts.append(OpenCartMatchConflict(None, None, filename, "LLM referenced unknown product_id"))
                continue
            product = products_by_id[product_id]
            if product.product_id in matched_product_ids:
                continue
            if filename not in files_set:
                report.conflicts.append(OpenCartMatchConflict(product.product_id, product.sku, filename, "LLM referenced unknown file"))
                continue
            if filename in used_files:
                report.conflicts.append(OpenCartMatchConflict(product.product_id, product.sku, filename, "LLM reused a file"))
                continue
            if confidence < settings.fuzzy_threshold:
                report.conflicts.append(OpenCartMatchConflict(product.product_id, product.sku, filename, "LLM confidence below threshold"))
                continue

            report.matches.append(self._make_match(product, filename, image_prefix, OpenCartMatchMethod.LLM, confidence, reason))
            used_files.add(filename)
            matched_product_ids.add(product.product_id)
```

- [ ] **Step 2: Export service**

Append to `apps/backend/src/application/services/__init__.py`:

```python
from .opencart_matcher import OpenCartImageMatcher
```

- [ ] **Step 3: Run matcher tests**

Run:

```bash
cd apps/backend
pytest tests/test_opencart_matcher.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add apps/backend/src/application/services/opencart_matcher.py apps/backend/src/application/services/__init__.py apps/backend/tests/test_opencart_matcher.py
git commit -m "Add OpenCart image matcher"
```

---

### Task 4: Backend Persistence and Routes

**Files:**

- Modify: `apps/backend/src/infrastructure/database/models.py`
- Modify: `apps/backend/src/infrastructure/database/repositories.py`
- Create: `apps/backend/src/infrastructure/providers/openrouter.py`
- Create: `apps/backend/src/api/routes/opencart.py`
- Modify: `apps/backend/src/api/routes/__init__.py`
- Modify: `apps/backend/src/main.py`
- Create: `apps/backend/tests/test_opencart_routes.py`

- [ ] **Step 1: Add route tests first**

Create `apps/backend/tests/test_opencart_routes.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_generate_opencart_sql_without_openrouter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/opencart/image-matches/generate",
            json={
                "products_text": "123\tABC-001",
                "files_text": "ABC001.jpg",
                "image_prefix": "catalog/products/import/",
                "settings": {"use_openrouter": False},
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["matches"][0]["product_id"] == 123
    assert data["matches"][0]["filename"] == "ABC001.jpg"
    assert "UPDATE oc_product SET image" in data["sql"]
    assert "openrouter_api_key" not in str(data)


@pytest.mark.asyncio
async def test_history_list_and_detail_hide_openrouter_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/opencart/image-matches/generate",
            json={
                "products_text": "123\tABC-001",
                "files_text": "ABC001.jpg",
                "image_prefix": "catalog/products/import/",
                "settings": {"use_openrouter": False},
                "openrouter_api_key": "secret-value",
            },
        )
        history_id = created.json()["history_id"]

        list_response = await client.get("/api/opencart/image-matches/history")
        detail_response = await client.get(f"/api/opencart/image-matches/history/{history_id}")

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert "secret-value" not in str(list_response.json())
    assert "secret-value" not in str(detail_response.json())
```

- [ ] **Step 2: Run route tests to verify they fail**

Run:

```bash
cd apps/backend
pytest tests/test_opencart_routes.py -q
```

Expected: FAIL with 404 for `/api/opencart/image-matches/generate`.

- [ ] **Step 3: Add database model**

In `apps/backend/src/infrastructure/database/models.py`, after `ProcessingLogModel`, add:

```python
class OpenCartImageMatchRunModel(Base):
    __tablename__ = "opencart_image_match_runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    products_text = Column(Text, nullable=False)
    files_text = Column(Text, nullable=False)
    image_prefix = Column(String(500), nullable=False, default="")
    settings = Column(JSON, nullable=False, default=dict)
    used_openrouter = Column(Boolean, nullable=False, default=False)
    model = Column(String(255), nullable=True)
    result = Column(JSON, nullable=False, default=dict)
    sql = Column(Text, nullable=False, default="")
    total_products = Column(Integer, nullable=False, default=0)
    total_files = Column(Integer, nullable=False, default=0)
    matched_count = Column(Integer, nullable=False, default=0)
    unmatched_count = Column(Integer, nullable=False, default=0)
    unused_file_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
```

- [ ] **Step 4: Add repository**

In `apps/backend/src/infrastructure/database/repositories.py`, update the model import and append repository code:

```python
from .models import (
    BatchModel,
    BatchItemModel,
    ImageAssetModel,
    ProcessingLogModel,
    OpenCartImageMatchRunModel,
)
from src.domain.entities import Batch, BatchItem, ImageAsset, ProcessingLog, OpenCartImageMatchRun
```

Append:

```python
class OpenCartImageMatchRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, run: OpenCartImageMatchRun) -> OpenCartImageMatchRun:
        model = OpenCartImageMatchRunModel(
            id=run.id,
            products_text=run.products_text,
            files_text=run.files_text,
            image_prefix=run.image_prefix,
            settings=run.settings,
            used_openrouter=run.used_openrouter,
            model=run.model,
            result=run.result,
            sql=run.sql,
            total_products=run.total_products,
            total_files=run.total_files,
            matched_count=run.matched_count,
            unmatched_count=run.unmatched_count,
            unused_file_count=run.unused_file_count,
            created_at=run.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def get_by_id(self, run_id: UUID) -> Optional[OpenCartImageMatchRun]:
        result = await self.session.execute(
            select(OpenCartImageMatchRunModel).where(OpenCartImageMatchRunModel.id == run_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all(self, limit: int = 50, offset: int = 0) -> List[OpenCartImageMatchRun]:
        result = await self.session.execute(
            select(OpenCartImageMatchRunModel)
            .order_by(OpenCartImageMatchRunModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(OpenCartImageMatchRunModel.id)))
        return result.scalar() or 0

    @staticmethod
    def _to_entity(model: OpenCartImageMatchRunModel) -> OpenCartImageMatchRun:
        return OpenCartImageMatchRun(
            id=model.id,
            products_text=model.products_text,
            files_text=model.files_text,
            image_prefix=model.image_prefix,
            settings=model.settings or {},
            used_openrouter=model.used_openrouter,
            model=model.model,
            result=model.result or {},
            sql=model.sql,
            total_products=model.total_products,
            total_files=model.total_files,
            matched_count=model.matched_count,
            unmatched_count=model.unmatched_count,
            unused_file_count=model.unused_file_count,
            created_at=model.created_at,
        )
```

- [ ] **Step 5: Export repository**

Append to `apps/backend/src/infrastructure/database/__init__.py`:

```python
from .repositories import OpenCartImageMatchRunRepository
```

- [ ] **Step 6: Add OpenRouter client**

Create `apps/backend/src/infrastructure/providers/openrouter.py`:

```python
import httpx


class OpenRouterClient:
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    async def match_images(self, model: str, products: list[dict], files: list[str]) -> str:
        prompt = (
            "Match OpenCart products to image filenames. "
            "Return only JSON array items with product_id, sku, filename, confidence, reason. "
            "Use each filename at most once and omit uncertain matches below 0.70."
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": {"products": products, "files": files}},
                    ],
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]
```

- [ ] **Step 7: Add route implementation**

Create `apps/backend/src/api/routes/opencart.py`:

```python
from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.application.dto.opencart import (
    OpenCartGenerateRequestDTO,
    OpenCartGenerateResponseDTO,
    OpenCartHistoryDetailDTO,
    OpenCartHistoryListDTO,
    OpenCartHistorySummaryDTO,
)
from src.application.services.opencart_matcher import OpenCartImageMatcher
from src.domain.entities.opencart_image_match import OpenCartImageMatchRun, OpenCartMatchSettings
from src.infrastructure.database import OpenCartImageMatchRunRepository
from src.infrastructure.providers.openrouter import OpenRouterClient

router = APIRouter(prefix="/opencart/image-matches", tags=["opencart"])


@router.post("/generate", response_model=OpenCartGenerateResponseDTO, status_code=201)
async def generate_opencart_image_sql(
    data: OpenCartGenerateRequestDTO,
    session: AsyncSession = Depends(get_db_session),
):
    matcher = OpenCartImageMatcher()
    settings = OpenCartMatchSettings(**data.settings.model_dump())
    llm_matches = None

    if settings.use_openrouter:
        if not data.openrouter_api_key:
            raise HTTPException(status_code=400, detail="OpenRouter API key is required when OpenRouter is enabled")
        products, _ = matcher.parse_products(data.products_text)
        files = matcher.parse_files(data.files_text)
        client = OpenRouterClient(data.openrouter_api_key)
        content = await client.match_images(
            settings.model,
            [{"product_id": p.product_id, "sku": p.sku} for p in products],
            files,
        )
        llm_matches = matcher.parse_llm_json(content)

    report = matcher.generate(
        products_text=data.products_text,
        files_text=data.files_text,
        image_prefix=data.image_prefix,
        settings=settings,
        llm_matches=llm_matches,
    )
    products, _ = matcher.parse_products(data.products_text)
    files = matcher.parse_files(data.files_text)

    result = asdict(report)
    run = OpenCartImageMatchRun(
        products_text=data.products_text,
        files_text=data.files_text,
        image_prefix=data.image_prefix,
        settings=data.settings.model_dump(),
        used_openrouter=settings.use_openrouter,
        model=settings.model if settings.use_openrouter else None,
        result=result,
        sql=report.sql,
        total_products=len(products),
        total_files=len(files),
        matched_count=len(report.matches),
        unmatched_count=len(report.unmatched_products),
        unused_file_count=len(report.unused_files),
    )
    repo = OpenCartImageMatchRunRepository(session)
    saved = await repo.create(run)
    return {"history_id": saved.id, **result}


@router.get("/history", response_model=OpenCartHistoryListDTO)
async def list_opencart_image_match_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    repo = OpenCartImageMatchRunRepository(session)
    offset = (page - 1) * page_size
    items = await repo.get_all(limit=page_size, offset=offset)
    total = await repo.count()
    return OpenCartHistoryListDTO(
        items=[OpenCartHistorySummaryDTO(**_summary(run)) for run in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/history/{run_id}", response_model=OpenCartHistoryDetailDTO)
async def get_opencart_image_match_history(
    run_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    repo = OpenCartImageMatchRunRepository(session)
    run = await repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="OpenCart image match run not found")
    return OpenCartHistoryDetailDTO(
        **_summary(run),
        products_text=run.products_text,
        files_text=run.files_text,
        image_prefix=run.image_prefix,
        settings=run.settings,
        result=run.result,
        sql=run.sql,
    )


def _summary(run: OpenCartImageMatchRun) -> dict:
    return {
        "id": run.id,
        "created_at": run.created_at,
        "total_products": run.total_products,
        "total_files": run.total_files,
        "matched_count": run.matched_count,
        "unmatched_count": run.unmatched_count,
        "unused_file_count": run.unused_file_count,
        "used_openrouter": run.used_openrouter,
        "model": run.model,
    }
```

- [ ] **Step 8: Wire router exports**

Modify `apps/backend/src/api/routes/__init__.py` to include:

```python
from .opencart import router as opencart_router
```

Modify `apps/backend/src/main.py`:

```python
from src.api.routes import batches_router, items_router, images_router, health_router, opencart_router

app.include_router(opencart_router, prefix="/api")
```

- [ ] **Step 9: Run backend route tests**

Run:

```bash
cd apps/backend
pytest tests/test_opencart_matcher.py tests/test_opencart_routes.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

Run:

```bash
git add apps/backend/src/infrastructure/database/models.py apps/backend/src/infrastructure/database/repositories.py apps/backend/src/infrastructure/database/__init__.py apps/backend/src/infrastructure/providers/openrouter.py apps/backend/src/api/routes/opencart.py apps/backend/src/api/routes/__init__.py apps/backend/src/main.py apps/backend/tests/test_opencart_routes.py
git commit -m "Add OpenCart image SQL API"
```

---

### Task 5: Frontend API and Types

**Files:**

- Create: `apps/frontend/src/types/opencart.ts`
- Create: `apps/frontend/src/api/opencart.ts`
- Create: `apps/frontend/src/hooks/useLocalStorage.ts`

- [ ] **Step 1: Add TypeScript types**

Create `apps/frontend/src/types/opencart.ts`:

```typescript
export interface OpenCartMatchSettings {
  use_openrouter: boolean;
  model: string;
  fuzzy_threshold: number;
  low_confidence_threshold: number;
  ignore_service_words: boolean;
}

export interface OpenCartGenerateRequest {
  products_text: string;
  files_text: string;
  image_prefix: string;
  settings: OpenCartMatchSettings;
  openrouter_api_key?: string;
}

export interface OpenCartProduct {
  product_id: number;
  sku: string;
  line_number: number;
}

export interface OpenCartParseError {
  line_number: number;
  line: string;
  message: string;
}

export interface OpenCartImageMatch {
  product_id: number;
  sku: string;
  filename: string;
  image_path: string;
  method: string;
  confidence: number;
  reason: string;
}

export interface OpenCartMatchConflict {
  product_id: number | null;
  sku: string | null;
  filename: string | null;
  message: string;
}

export interface OpenCartGenerateResponse {
  history_id: string;
  matches: OpenCartImageMatch[];
  unmatched_products: OpenCartProduct[];
  unused_files: string[];
  parse_errors: OpenCartParseError[];
  conflicts: OpenCartMatchConflict[];
  low_confidence_matches: OpenCartImageMatch[];
  sql: string;
}

export interface OpenCartHistorySummary {
  id: string;
  created_at: string;
  total_products: number;
  total_files: number;
  matched_count: number;
  unmatched_count: number;
  unused_file_count: number;
  used_openrouter: boolean;
  model: string | null;
}

export interface OpenCartHistoryList {
  items: OpenCartHistorySummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface OpenCartHistoryDetail extends OpenCartHistorySummary {
  products_text: string;
  files_text: string;
  image_prefix: string;
  settings: OpenCartMatchSettings;
  result: OpenCartGenerateResponse;
  sql: string;
}
```

- [ ] **Step 2: Add API helpers**

Create `apps/frontend/src/api/opencart.ts`:

```typescript
import { api } from './client';
import type {
  OpenCartGenerateRequest,
  OpenCartGenerateResponse,
  OpenCartHistoryDetail,
  OpenCartHistoryList,
} from '@/types/opencart';

export function generateOpenCartImageSql(data: OpenCartGenerateRequest) {
  return api.post<OpenCartGenerateResponse>('/opencart/image-matches/generate', data);
}

export function getOpenCartHistory(page = 1, pageSize = 20) {
  return api.get<OpenCartHistoryList>(`/opencart/image-matches/history?page=${page}&page_size=${pageSize}`);
}

export function getOpenCartHistoryDetail(id: string) {
  return api.get<OpenCartHistoryDetail>(`/opencart/image-matches/history/${id}`);
}
```

- [ ] **Step 3: Add localStorage hook**

Create `apps/frontend/src/hooks/useLocalStorage.ts`:

```typescript
import { useEffect, useState } from 'react';

export function useLocalStorage(key: string, initialValue: string) {
  const [value, setValue] = useState(() => {
    return window.localStorage.getItem(key) ?? initialValue;
  });

  useEffect(() => {
    window.localStorage.setItem(key, value);
  }, [key, value]);

  return [value, setValue] as const;
}
```

- [ ] **Step 4: Run frontend type check**

Run:

```bash
cd apps/frontend
npm run lint
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add apps/frontend/src/types/opencart.ts apps/frontend/src/api/opencart.ts apps/frontend/src/hooks/useLocalStorage.ts
git commit -m "Add OpenCart frontend API types"
```

---

### Task 6: Frontend Page and Navigation

**Files:**

- Create: `apps/frontend/src/pages/OpenCartSqlPage.tsx`
- Modify: `apps/frontend/src/App.tsx`
- Modify: `apps/frontend/src/components/layout/Header.tsx`
- Modify: `apps/frontend/src/styles.css`

- [ ] **Step 1: Add page component**

Create `apps/frontend/src/pages/OpenCartSqlPage.tsx`:

```tsx
import { useEffect, useMemo, useState } from 'react';
import { generateOpenCartImageSql, getOpenCartHistory, getOpenCartHistoryDetail } from '@/api/opencart';
import { useLocalStorage } from '@/hooks/useLocalStorage';
import type {
  OpenCartGenerateResponse,
  OpenCartHistoryDetail,
  OpenCartHistorySummary,
  OpenCartMatchSettings,
} from '@/types/opencart';

const defaultSettings: OpenCartMatchSettings = {
  use_openrouter: false,
  model: 'openai/gpt-4.1-nano',
  fuzzy_threshold: 0.78,
  low_confidence_threshold: 0.86,
  ignore_service_words: true,
};

export function OpenCartSqlPage() {
  const [productsText, setProductsText] = useState('');
  const [filesText, setFilesText] = useState('');
  const [imagePrefix, setImagePrefix] = useState('catalog/products/');
  const [apiKey, setApiKey] = useLocalStorage('openrouter_api_key', '');
  const [settings, setSettings] = useState(defaultSettings);
  const [result, setResult] = useState<OpenCartGenerateResponse | null>(null);
  const [history, setHistory] = useState<OpenCartHistorySummary[]>([]);
  const [selectedHistory, setSelectedHistory] = useState<OpenCartHistoryDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    return productsText.trim().length > 0 && filesText.trim().length > 0 && (!settings.use_openrouter || apiKey.trim().length > 0);
  }, [apiKey, filesText, productsText, settings.use_openrouter]);

  useEffect(() => {
    void refreshHistory();
  }, []);

  async function refreshHistory() {
    const response = await getOpenCartHistory();
    setHistory(response.items);
  }

  async function handleGenerate() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await generateOpenCartImageSql({
        products_text: productsText,
        files_text: filesText,
        image_prefix: imagePrefix,
        settings,
        openrouter_api_key: settings.use_openrouter ? apiKey : undefined,
      });
      setResult(response);
      setSelectedHistory(null);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate SQL');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleOpenHistory(id: string) {
    setIsLoading(true);
    setError(null);
    try {
      const detail = await getOpenCartHistoryDetail(id);
      setSelectedHistory(detail);
      setResult(detail.result);
      setProductsText(detail.products_text);
      setFilesText(detail.files_text);
      setImagePrefix(detail.image_prefix);
      setSettings(detail.settings);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open history item');
    } finally {
      setIsLoading(false);
    }
  }

  const visibleResult = result;

  return (
    <div className="opencart-page">
      <section className="panel opencart-tool">
        <div className="panel-header">
          <div>
            <h1>OpenCart SQL</h1>
            <p>Generate SQL for assigning main product images by product ID.</p>
          </div>
          <button className="primary-button" type="button" disabled={!canSubmit || isLoading} onClick={handleGenerate}>
            {isLoading ? 'Working...' : 'Match and generate SQL'}
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="opencart-grid">
          <label className="field">
            <span>Products: product_id + SKU</span>
            <textarea value={productsText} onChange={(event) => setProductsText(event.target.value)} rows={12} />
          </label>
          <label className="field">
            <span>Files</span>
            <textarea value={filesText} onChange={(event) => setFilesText(event.target.value)} rows={12} />
          </label>
        </div>

        <div className="settings-grid">
          <label className="field">
            <span>Image path prefix</span>
            <input value={imagePrefix} onChange={(event) => setImagePrefix(event.target.value)} />
          </label>
          <label className="field">
            <span>OpenRouter API key</span>
            <input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
          </label>
          <label className="field">
            <span>Model</span>
            <input value={settings.model} onChange={(event) => setSettings({ ...settings, model: event.target.value })} />
          </label>
        </div>

        <div className="toggle-row">
          <label><input type="checkbox" checked={settings.use_openrouter} onChange={(event) => setSettings({ ...settings, use_openrouter: event.target.checked })} /> Use OpenRouter</label>
          <label><input type="checkbox" checked={settings.ignore_service_words} onChange={(event) => setSettings({ ...settings, ignore_service_words: event.target.checked })} /> Ignore service words</label>
        </div>
      </section>

      {visibleResult && (
        <section className="panel">
          <div className="panel-header">
            <h2>Result</h2>
            <button type="button" onClick={() => navigator.clipboard.writeText(visibleResult.sql)}>Copy SQL</button>
          </div>
          <div className="summary-row">
            <span>Matched: {visibleResult.matches.length}</span>
            <span>Without file: {visibleResult.unmatched_products.length}</span>
            <span>Unused files: {visibleResult.unused_files.length}</span>
            <span>Conflicts: {visibleResult.conflicts.length}</span>
          </div>
          <pre className="sql-output">{visibleResult.sql}</pre>
          <table className="data-table">
            <thead><tr><th>ID</th><th>SKU</th><th>File</th><th>Path</th><th>Method</th><th>Confidence</th></tr></thead>
            <tbody>
              {visibleResult.matches.map((match) => (
                <tr key={`${match.product_id}-${match.filename}`}>
                  <td>{match.product_id}</td>
                  <td>{match.sku}</td>
                  <td>{match.filename}</td>
                  <td>{match.image_path}</td>
                  <td>{match.method}</td>
                  <td>{Math.round(match.confidence * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="report-grid">
            <ReportList title="Products without file" items={visibleResult.unmatched_products.map((item) => `${item.product_id} / ${item.sku}`)} />
            <ReportList title="Unused files" items={visibleResult.unused_files} />
            <ReportList title="Parse errors" items={visibleResult.parse_errors.map((item) => `Line ${item.line_number}: ${item.message}`)} />
            <ReportList title="Conflicts" items={visibleResult.conflicts.map((item) => item.message)} />
          </div>
        </section>
      )}

      <section className="panel">
        <h2>History</h2>
        <div className="history-list">
          {history.map((item) => (
            <button key={item.id} type="button" className="history-item" onClick={() => handleOpenHistory(item.id)}>
              <span>{new Date(item.created_at).toLocaleString()}</span>
              <span>{item.matched_count}/{item.total_products} matched</span>
              <span>Unused files: {item.unused_file_count}</span>
              <span>{item.used_openrouter ? `LLM: ${item.model}` : 'Algorithmic'}</span>
            </button>
          ))}
          {history.length === 0 && <p>No history yet.</p>}
        </div>
        {selectedHistory && <p className="muted">Opened history item {selectedHistory.id}</p>}
      </section>
    </div>
  );
}

function ReportList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="report-list">
      <h3>{title}</h3>
      {items.length === 0 ? <p>None</p> : <ul>{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>}
    </div>
  );
}
```

- [ ] **Step 2: Wire route**

Modify `apps/frontend/src/App.tsx`:

```tsx
import { OpenCartSqlPage } from '@/pages/OpenCartSqlPage';

<Route path="opencart-sql" element={<OpenCartSqlPage />} />
```

- [ ] **Step 3: Add navigation**

In `apps/frontend/src/components/layout/Header.tsx`, add a third nav button:

```tsx
<button
  className={`nav-button ${location.pathname === '/opencart-sql' ? 'is-active' : ''}`}
  type="button"
  onClick={() => navigate('/opencart-sql')}
>
  OpenCart SQL
</button>
```

- [ ] **Step 4: Add CSS**

Append to `apps/frontend/src/styles.css`:

```css
.opencart-page {
  display: grid;
  gap: 24px;
}

.panel {
  border: 1px solid #d8dee8;
  border-radius: 8px;
  background: #fff;
  padding: 20px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.opencart-grid,
.settings-grid,
.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.field {
  display: grid;
  gap: 8px;
}

.field textarea,
.field input {
  width: 100%;
  border: 1px solid #c7d0dd;
  border-radius: 6px;
  padding: 10px;
  font: inherit;
}

.toggle-row,
.summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 16px;
}

.sql-output {
  max-height: 360px;
  overflow: auto;
  border: 1px solid #d8dee8;
  border-radius: 6px;
  padding: 12px;
  background: #111827;
  color: #f9fafb;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 16px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #e5e9f0;
  padding: 8px;
  text-align: left;
  vertical-align: top;
}

.history-list {
  display: grid;
  gap: 8px;
}

.history-item {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
  border: 1px solid #d8dee8;
  border-radius: 6px;
  background: #fff;
  padding: 10px;
  text-align: left;
}

.error-banner {
  border: 1px solid #f3b4b4;
  border-radius: 6px;
  background: #fff1f1;
  color: #9f1d1d;
  padding: 10px;
  margin-bottom: 16px;
}

.muted {
  color: #667085;
}
```

- [ ] **Step 5: Run frontend checks**

Run:

```bash
cd apps/frontend
npm run build
npm run lint
```

Expected: both PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add apps/frontend/src/pages/OpenCartSqlPage.tsx apps/frontend/src/App.tsx apps/frontend/src/components/layout/Header.tsx apps/frontend/src/styles.css
git commit -m "Add OpenCart SQL page"
```

---

### Task 7: Full Verification

**Files:**

- No new files.

- [ ] **Step 1: Run backend unit and route tests**

Run:

```bash
cd apps/backend
pytest tests/test_opencart_matcher.py tests/test_opencart_routes.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend build and lint**

Run:

```bash
cd apps/frontend
npm run build
npm run lint
```

Expected: PASS.

- [ ] **Step 3: Run full backend test suite if existing tests are present**

Run:

```bash
cd apps/backend
pytest -q
```

Expected: PASS.

- [ ] **Step 4: Manual API smoke test**

Start the backend, then send:

```bash
curl -X POST http://localhost:8000/api/opencart/image-matches/generate \
  -H "Content-Type: application/json" \
  -d "{\"products_text\":\"123\tABC-001\",\"files_text\":\"ABC001.jpg\",\"image_prefix\":\"catalog/products/\",\"settings\":{\"use_openrouter\":false}}"
```

Expected: response includes one match and SQL assigning `catalog/products/ABC001.jpg` to `product_id = 123`.

- [ ] **Step 5: Manual frontend smoke test**

Start the frontend and backend. Open `/opencart-sql`, paste:

```text
123	ABC-001
124	DEF-002
```

Files:

```text
ABC001.jpg
DEF_002.webp
unused.jpg
```

Expected:

- two matches;
- SQL with two `UPDATE oc_product` statements;
- `unused.jpg` in unused files;
- history item appears after generation;
- opening history restores the report;
- OpenRouter key remains in browser storage and does not appear in history JSON.

- [ ] **Step 6: Final commit if verification caused fixes**

If verification required changes, commit them:

```bash
git add apps/backend/src apps/backend/tests apps/frontend/src
git commit -m "Fix OpenCart SQL verification issues"
```

---

## Self-Review

Spec coverage:

- Paste-based product and file input: Task 2, Task 3, Task 6.
- OpenCart 3 `oc_product.image` SQL by `product_id`: Task 3.
- One SKU to one file: Task 3 tests and validation.
- Unmatched SKU and unused file reporting: Task 2, Task 3, Task 6.
- OpenRouter with browser-stored key and backend one-request use: Task 4, Task 5, Task 6.
- History without secrets: Task 4 tests and repository.
- Frontend result table, SQL copy, and history: Task 6.
- Verification: Task 7.

Red-flag scan:

- No incomplete markers or empty "handle later" steps are present.

Type consistency:

- Backend DTO names, route payload keys, TypeScript types, and frontend API helpers use the same snake_case API fields.
- History detail returns `result` and `sql`; frontend reads `detail.result` and displays the restored report.
