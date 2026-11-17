from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import ImageRepository
from src.api.dependencies import get_file_service, get_db_session, get_image_preview_service
from src.application.services import FileStorageService
from src.application.services.image_preview import ImagePreviewService
from src.domain.entities import ImageAsset

router = APIRouter(prefix="/images", tags=["images"])


def image_file_response(image: ImageAsset, file_service: FileStorageService) -> FileResponse:
    if not image.file_path or not Path(image.file_path).is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=image.file_path,
        media_type=image.mime_type if image.mime_type.startswith("image/") else file_service.get_content_type(image.file_name),
        filename=image.file_name,
        content_disposition_type="inline",
    )


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
    
    return image_file_response(image, file_service)


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
    
    return image_file_response(image, file_service)


@router.get("/{image_id}/preview/{index}")
async def get_image_preview(
    image_id: UUID,
    index: int,
    session: AsyncSession = Depends(get_db_session),
    preview_service: ImagePreviewService = Depends(get_image_preview_service),
):
    image = await ImageRepository(session).get_by_id(image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        file_path = await preview_service.get_preview(image, index)
    except IndexError as error:
        raise HTTPException(status_code=404, detail="Preview not found") from error
    except ValueError as error:
        raise HTTPException(
            status_code=502, detail="Image preview is unavailable",
            headers={"Cache-Control": "no-store"},
        ) from error
    return FileResponse(
        path=file_path, media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
