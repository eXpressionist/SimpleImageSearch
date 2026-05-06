from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.application.dto import (
    OpenCartGenerateRequestDTO,
    OpenCartGenerateResponseDTO,
    OpenCartHistoryDetailDTO,
    OpenCartHistoryListDTO,
)
from src.application.services import OpenCartImageMatcher
from src.domain.entities import (
    OpenCartImageMatch,
    OpenCartImageMatchRun,
    OpenCartMatchConflict,
    OpenCartMatchReport,
    OpenCartMatchSettings,
    OpenCartParseError,
    OpenCartProductInput,
)
from src.infrastructure.database import OpenCartImageMatchRunRepository
from src.infrastructure.providers.openrouter import OpenRouterClient

router = APIRouter(prefix="/opencart/image-matches", tags=["opencart"])


@router.post(
    "/generate",
    response_model=OpenCartGenerateResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
async def generate_image_matches(
    request: OpenCartGenerateRequestDTO,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    matcher = OpenCartImageMatcher()
    settings = OpenCartMatchSettings(
        use_openrouter=request.settings.use_openrouter,
        model=request.settings.model,
        fuzzy_threshold=request.settings.fuzzy_threshold,
        low_confidence_threshold=request.settings.low_confidence_threshold,
        ignore_service_words=request.settings.ignore_service_words,
    )
    products, _parse_errors = matcher.parse_products(request.products_text)
    files = matcher.parse_files(request.files_text)
    llm_matches: list[dict[str, Any]] | None = None
    used_openrouter = bool(settings.use_openrouter and request.openrouter_api_key)

    if used_openrouter:
        client = OpenRouterClient(api_key=request.openrouter_api_key)
        content = await client.match_images(
            model=settings.model,
            products=[_product_to_dict(product) for product in products],
            files=files,
        )
        llm_matches = matcher.parse_llm_json(content)

    report = matcher.generate(
        products_text=request.products_text,
        files_text=request.files_text,
        image_prefix=request.image_prefix,
        settings=settings,
        llm_matches=llm_matches,
    )
    result = _report_to_dict(report)
    run = OpenCartImageMatchRun(
        products_text=request.products_text,
        files_text=request.files_text,
        image_prefix=request.image_prefix,
        settings=_settings_to_dict(settings),
        used_openrouter=used_openrouter,
        model=settings.model if used_openrouter else None,
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
async def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = OpenCartImageMatchRunRepository(session)
    offset = (page - 1) * page_size
    runs = await repo.get_all(limit=page_size, offset=offset)
    total = await repo.count()
    return {
        "items": [_run_summary(run) for run in runs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/history/{run_id}", response_model=OpenCartHistoryDetailDTO)
async def get_history_detail(
    run_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = OpenCartImageMatchRunRepository(session)
    run = await repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OpenCart image match run not found")
    return {
        **_run_summary(run),
        "products_text": run.products_text,
        "files_text": run.files_text,
        "image_prefix": run.image_prefix,
        "settings": run.settings,
        "result": run.result,
        "sql": run.sql,
    }


def _settings_to_dict(settings: OpenCartMatchSettings) -> dict[str, Any]:
    return {
        "use_openrouter": settings.use_openrouter,
        "model": settings.model,
        "fuzzy_threshold": settings.fuzzy_threshold,
        "low_confidence_threshold": settings.low_confidence_threshold,
        "ignore_service_words": settings.ignore_service_words,
    }


def _report_to_dict(report: OpenCartMatchReport) -> dict[str, Any]:
    return {
        "matches": [_match_to_dict(match) for match in report.matches],
        "unmatched_products": [_product_to_dict(product) for product in report.unmatched_products],
        "unused_files": list(report.unused_files),
        "parse_errors": [_parse_error_to_dict(error) for error in report.parse_errors],
        "conflicts": [_conflict_to_dict(conflict) for conflict in report.conflicts],
        "low_confidence_matches": [_match_to_dict(match) for match in report.low_confidence_matches],
        "sql": report.sql,
    }


def _match_to_dict(match: OpenCartImageMatch) -> dict[str, Any]:
    return {
        "product_id": match.product_id,
        "sku": match.sku,
        "filename": match.filename,
        "image_path": match.image_path,
        "method": match.method.value,
        "confidence": match.confidence,
        "reason": match.reason,
    }


def _product_to_dict(product: OpenCartProductInput) -> dict[str, Any]:
    return {
        "product_id": product.product_id,
        "sku": product.sku,
        "line_number": product.line_number,
    }


def _parse_error_to_dict(error: OpenCartParseError) -> dict[str, Any]:
    return {
        "line_number": error.line_number,
        "line": error.line,
        "message": error.message,
    }


def _conflict_to_dict(conflict: OpenCartMatchConflict) -> dict[str, Any]:
    return {
        "product_id": conflict.product_id,
        "sku": conflict.sku,
        "filename": conflict.filename,
        "message": conflict.message,
    }


def _run_summary(run: OpenCartImageMatchRun) -> dict[str, Any]:
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
