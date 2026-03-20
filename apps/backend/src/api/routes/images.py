from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import ImageRepository
from src.api.dependencies import get_file_service, get_db_session
from src.application.services import FileStorageService

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{image_id}/file")
async def get_image_file(
    image_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    file_service: FileStorageService = Depends(get_file_service),
):
    image_repo = ImageRepository(session)
    image = await image_repo.get_by_id(image_id)
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path = Path(image.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    content_type = file_service.get_content_type(image.file_name)
    
    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=image.file_name,
    )


@router.get("/item/{item_id}/file")
async def get_item_image_file(
    item_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    file_service: FileStorageService = Depends(get_file_service),
):
    image_repo = ImageRepository(session)
    image = await image_repo.get_by_item(item_id)
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found for item")
    
    file_path = Path(image.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    content_type = file_service.get_content_type(image.file_name)
    
    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=image.file_name,
    )
