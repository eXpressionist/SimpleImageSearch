from typing import AsyncGenerator, Union
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import async_session_factory
from src.infrastructure.providers import GoogleCustomSearchProvider, BraveSearchProvider, SerpApiSearchProvider, LocalFileStorage
from src.infrastructure.config import get_settings
from src.application.services import BatchProcessor, FileStorageService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_search_provider() -> Union[BraveSearchProvider, SerpApiSearchProvider, GoogleCustomSearchProvider]:
    settings = get_settings()
    provider = settings.search_provider.lower()
    
    if provider == "brave" and settings.brave_api_key:
        return BraveSearchProvider(
            api_key=settings.brave_api_key,
            timeout=settings.download_timeout,
        )
    
    if provider == "serpapi" and settings.serpapi_api_key:
        return SerpApiSearchProvider(
            api_key=settings.serpapi_api_key,
            engine=settings.serpapi_engine,
            timeout=settings.download_timeout,
        )
    
    if settings.google_api_key and settings.google_cse_cx:
        return GoogleCustomSearchProvider(
            api_key=settings.google_api_key,
            cx=settings.google_cse_cx,
            timeout=settings.download_timeout,
        )
    
    raise ValueError(
        f"No search provider configured. "
        f"Set BRAVE_API_KEY (recommended), SERPAPI_API_KEY, or GOOGLE_API_KEY + GOOGLE_CSE_CX"
    )


def get_storage() -> LocalFileStorage:
    settings = get_settings()
    return LocalFileStorage(
        base_path=settings.storage_path,
        max_file_size_bytes=settings.max_file_size_bytes,
    )


def get_batch_processor(
    session: AsyncSession = Depends(get_db_session),
    search_provider: Union[BraveSearchProvider, SerpApiSearchProvider, GoogleCustomSearchProvider] = Depends(get_search_provider),
    storage: LocalFileStorage = Depends(get_storage),
) -> BatchProcessor:
    return BatchProcessor(
        session=session,
        search_provider=search_provider,
        storage=storage,
    )


def get_file_service() -> FileStorageService:
    return FileStorageService()