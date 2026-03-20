import asyncio
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.batch import (
    BatchCreateDTO, BatchResponseDTO, BatchListDTO, BatchStatsDTO
)
from src.application.dto.item import ItemListDTO, ItemWithImageDTO
from src.infrastructure.database import BatchRepository, ItemRepository, ImageRepository
from src.domain.value_objects import BatchStatus, ItemStatus
from src.api.dependencies import get_batch_processor, get_db_session
from src.application.services import BatchProcessor
from src.application.services.batch_processor import process_batch_background

router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("", response_model=BatchResponseDTO, status_code=201)
async def create_batch(
    data: BatchCreateDTO,
    background_tasks: BackgroundTasks,
    processor: BatchProcessor = Depends(get_batch_processor),
):
    batch = await processor.create_batch(
        lines=data.lines,
        name=data.name,
        config=data.config.model_dump() if data.config else None,
    )
    
    background_tasks.add_task(process_batch_background, batch.id)
    
    return BatchResponseDTO(
        id=batch.id,
        name=batch.name,
        total_items=batch.total_items,
        processed_items=batch.processed_items,
        failed_items=batch.failed_items,
        status=batch.status.value,
        progress_percent=batch.progress_percent,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


@router.get("", response_model=BatchListDTO)
async def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[BatchStatus] = None,
    session: AsyncSession = Depends(get_db_session),
):
    repo = BatchRepository(session)
    
    offset = (page - 1) * page_size
    batches = await repo.get_all(limit=page_size, offset=offset, status=status)
    total = await repo.count(status=status)
    
    return BatchListDTO(
        items=[
            BatchResponseDTO(
                id=b.id,
                name=b.name,
                total_items=b.total_items,
                processed_items=b.processed_items,
                failed_items=b.failed_items,
                status=b.status.value,
                progress_percent=b.progress_percent,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
            for b in batches
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{batch_id}", response_model=BatchResponseDTO)
async def get_batch(
    batch_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    repo = BatchRepository(session)
    batch = await repo.get_by_id(batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return BatchResponseDTO(
        id=batch.id,
        name=batch.name,
        total_items=batch.total_items,
        processed_items=batch.processed_items,
        failed_items=batch.failed_items,
        status=batch.status.value,
        progress_percent=batch.progress_percent,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


@router.get("/{batch_id}/items", response_model=ItemListDTO)
async def get_batch_items(
    batch_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[ItemStatus] = None,
    session: AsyncSession = Depends(get_db_session),
):
    repo = BatchRepository(session)
    batch = await repo.get_by_id(batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    item_repo = ItemRepository(session)
    image_repo = ImageRepository(session)
    
    offset = (page - 1) * page_size
    items = await item_repo.get_by_batch(batch_id, status=status, limit=page_size, offset=offset)
    total = await item_repo.count_by_batch(batch_id, status=status)
    
    items_with_images = []
    for item in items:
        image = await image_repo.get_by_item(item.id)
        image_dict = None
        if image:
            image_dict = {
                "id": str(image.id),
                "item_id": str(image.item_id),
                "source_url": image.source_url,
                "direct_url": image.direct_url,
                "file_path": image.file_path,
                "file_name": image.file_name,
                "mime_type": image.mime_type,
                "file_size": image.file_size,
                "width": image.width,
                "height": image.height,
                "file_hash": image.file_hash,
                "created_at": image.created_at.isoformat(),
            }
        
        items_with_images.append(ItemWithImageDTO(
            id=item.id,
            batch_id=item.batch_id,
            position=item.position,
            original_query=item.original_query,
            normalized_query=item.normalized_query,
            status=item.status.value,
            error_message=item.error_message,
            retry_count=item.retry_count,
            is_approved=item.is_approved,
            image=image_dict,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    
    return ItemListDTO(
        items=items_with_images,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{batch_id}/stats", response_model=BatchStatsDTO)
async def get_batch_stats(
    batch_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    repo = BatchRepository(session)
    batch = await repo.get_by_id(batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    item_repo = ItemRepository(session)
    
    return BatchStatsDTO(
        total=batch.total_items,
        pending=await item_repo.count_by_batch(batch_id, ItemStatus.PENDING),
        searching=await item_repo.count_by_batch(batch_id, ItemStatus.SEARCHING),
        downloading=await item_repo.count_by_batch(batch_id, ItemStatus.DOWNLOADING),
        saved=await item_repo.count_by_batch(batch_id, ItemStatus.SAVED),
        failed=await item_repo.count_by_batch(batch_id, ItemStatus.FAILED),
        review_needed=await item_repo.count_by_batch(batch_id, ItemStatus.REVIEW_NEEDED),
    )


@router.delete("/{batch_id}", status_code=204)
async def delete_batch(
    batch_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    repo = BatchRepository(session)
    deleted = await repo.delete(batch_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Batch not found")
