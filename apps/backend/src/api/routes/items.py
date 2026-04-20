from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.item import ItemResponseDTO, ItemWithImageDTO
from src.infrastructure.database import ItemRepository, ImageRepository
from src.api.dependencies import get_batch_processor, get_db_session
from src.application.services import BatchProcessor
from src.application.services.batch_processor import process_batch_background

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/{item_id}", response_model=ItemWithImageDTO)
async def get_item(
    item_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    item_repo = ItemRepository(session)
    image_repo = ImageRepository(session)
    
    item = await item_repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    image = await image_repo.get_by_item(item_id)
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
    
    return ItemWithImageDTO(
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
    )


@router.post("/{item_id}/retry", response_model=ItemResponseDTO)
async def retry_item(
    item_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
    processor: BatchProcessor = Depends(get_batch_processor),
):
    item_repo = ItemRepository(session)
    item = await item_repo.get_by_id(item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if not item.can_retry(3):
        raise HTTPException(status_code=400, detail="Item cannot be retried")
    
    updated_item = await processor.retry_item(item_id)
    if not updated_item:
        raise HTTPException(status_code=500, detail="Retry failed")
    
    return ItemResponseDTO(
        id=updated_item.id,
        batch_id=updated_item.batch_id,
        position=updated_item.position,
        original_query=updated_item.original_query,
        normalized_query=updated_item.normalized_query,
        status=updated_item.status.value,
        error_message=updated_item.error_message,
        retry_count=updated_item.retry_count,
        is_approved=updated_item.is_approved,
        created_at=updated_item.created_at,
        updated_at=updated_item.updated_at,
    )


@router.post("/{item_id}/approve", response_model=ItemResponseDTO)
async def approve_item(
    item_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    item_repo = ItemRepository(session)
    item = await item_repo.get_by_id(item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.approve()
    await item_repo.update(item)
    
    return ItemResponseDTO(
        id=item.id,
        batch_id=item.batch_id,
        position=item.position,
        original_query=item.original_query,
        normalized_query=item.normalized_query,
        status=item.status.value,
        error_message=item.error_message,
        retry_count=item.retry_count,
        is_approved=item.is_approved,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/recover-stuck")
async def recover_stuck_items(
    batch_id: Optional[UUID] = Query(None, description="Batch ID to recover, or None for all batches"),
    stuck_minutes: int = Query(5, ge=1, le=60, description="Minutes before item is considered stuck"),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_db_session),
):
    item_repo = ItemRepository(session)
    
    recovered_count = await item_repo.recover_stuck_items(batch_id, stuck_minutes)
    await session.commit()
    
    if recovered_count > 0 and batch_id:
        background_tasks.add_task(process_batch_background, batch_id)
    
    return {
        "recovered_count": recovered_count,
        "message": f"Recovered {recovered_count} stuck items"
    }
