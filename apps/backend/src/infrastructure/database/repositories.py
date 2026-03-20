from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BatchModel, BatchItemModel, ImageAssetModel, ProcessingLogModel
from src.domain.entities import Batch, BatchItem, ImageAsset, ProcessingLog
from src.domain.value_objects import BatchStatus, ItemStatus


class BatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, batch: Batch) -> Batch:
        model = BatchModel(
            id=batch.id,
            name=batch.name,
            total_items=batch.total_items,
            processed_items=batch.processed_items,
            failed_items=batch.failed_items,
            status=batch.status,
            config=batch.config,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_id(self, batch_id: UUID) -> Optional[Batch]:
        result = await self.session.execute(
            select(BatchModel).where(BatchModel.id == batch_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_all(
        self, 
        limit: int = 50, 
        offset: int = 0,
        status: Optional[BatchStatus] = None,
    ) -> List[Batch]:
        query = select(BatchModel).order_by(BatchModel.created_at.desc())
        if status:
            query = query.where(BatchModel.status == status)
        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def update(self, batch: Batch) -> Batch:
        await self.session.execute(
            update(BatchModel)
            .where(BatchModel.id == batch.id)
            .values(
                processed_items=batch.processed_items,
                failed_items=batch.failed_items,
                status=batch.status,
                updated_at=datetime.utcnow(),
            )
        )
        return batch
    
    async def delete(self, batch_id: UUID) -> bool:
        model = await self.session.get(BatchModel, batch_id)
        if model:
            await self.session.delete(model)
            return True
        return False
    
    async def count(self, status: Optional[BatchStatus] = None) -> int:
        query = select(func.count(BatchModel.id))
        if status:
            query = query.where(BatchModel.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    def _to_entity(model: BatchModel) -> Batch:
        return Batch(
            id=model.id,
            name=model.name,
            total_items=model.total_items,
            processed_items=model.processed_items,
            failed_items=model.failed_items,
            status=model.status,
            config=model.config or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class ItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_many(self, items: List[BatchItem]) -> List[BatchItem]:
        models = [
            BatchItemModel(
                id=item.id,
                batch_id=item.batch_id,
                position=item.position,
                original_query=item.original_query,
                normalized_query=item.normalized_query,
                status=item.status,
                error_message=item.error_message,
                retry_count=item.retry_count,
                is_approved=item.is_approved,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]
        self.session.add_all(models)
        await self.session.flush()
        return [self._to_entity(m) for m in models]
    
    async def get_by_id(self, item_id: UUID) -> Optional[BatchItem]:
        result = await self.session.execute(
            select(BatchItemModel).where(BatchItemModel.id == item_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_batch(
        self,
        batch_id: UUID,
        status: Optional[ItemStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BatchItem]:
        query = (
            select(BatchItemModel)
            .where(BatchItemModel.batch_id == batch_id)
            .order_by(BatchItemModel.position)
        )
        if status:
            query = query.where(BatchItemModel.status == status)
        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def get_pending(self, batch_id: UUID, limit: int = 10) -> List[BatchItem]:
        result = await self.session.execute(
            select(BatchItemModel)
            .where(BatchItemModel.batch_id == batch_id)
            .where(BatchItemModel.status == ItemStatus.PENDING)
            .order_by(BatchItemModel.position)
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
    
    async def update(self, item: BatchItem) -> BatchItem:
        await self.session.execute(
            update(BatchItemModel)
            .where(BatchItemModel.id == item.id)
            .values(
                status=item.status,
                error_message=item.error_message,
                retry_count=item.retry_count,
                is_approved=item.is_approved,
                updated_at=datetime.utcnow(),
            )
        )
        return item
    
    async def count_by_batch(
        self, 
        batch_id: UUID, 
        status: Optional[ItemStatus] = None
    ) -> int:
        query = select(func.count(BatchItemModel.id)).where(BatchItemModel.batch_id == batch_id)
        if status:
            query = query.where(BatchItemModel.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def retry_item(self, item_id: UUID) -> Optional[BatchItem]:
        item = await self.get_by_id(item_id)
        if item and item.can_retry():
            item.increment_retry()
            return await self.update(item)
        return None
    
    @staticmethod
    def _to_entity(model: BatchItemModel) -> BatchItem:
        return BatchItem(
            id=model.id,
            batch_id=model.batch_id,
            position=model.position,
            original_query=model.original_query,
            normalized_query=model.normalized_query,
            status=model.status,
            error_message=model.error_message,
            retry_count=model.retry_count,
            is_approved=model.is_approved,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class ImageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, image: ImageAsset) -> ImageAsset:
        model = ImageAssetModel(
            id=image.id,
            item_id=image.item_id,
            source_url=image.source_url,
            direct_url=image.direct_url,
            file_path=image.file_path,
            file_name=image.file_name,
            mime_type=image.mime_type,
            file_size=image.file_size,
            file_hash=image.file_hash,
            width=image.width,
            height=image.height,
            created_at=image.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_id(self, image_id: UUID) -> Optional[ImageAsset]:
        result = await self.session.execute(
            select(ImageAssetModel).where(ImageAssetModel.id == image_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_item(self, item_id: UUID) -> Optional[ImageAsset]:
        result = await self.session.execute(
            select(ImageAssetModel).where(ImageAssetModel.item_id == item_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_hash(self, file_hash: str) -> Optional[ImageAsset]:
        result = await self.session.execute(
            select(ImageAssetModel).where(ImageAssetModel.file_hash == file_hash)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def delete_by_item(self, item_id: UUID) -> bool:
        result = await self.session.execute(
            select(ImageAssetModel).where(ImageAssetModel.item_id == item_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False
    
    @staticmethod
    def _to_entity(model: ImageAssetModel) -> ImageAsset:
        return ImageAsset(
            id=model.id,
            item_id=model.item_id,
            source_url=model.source_url,
            direct_url=model.direct_url,
            file_path=model.file_path,
            file_name=model.file_name,
            mime_type=model.mime_type,
            file_size=model.file_size,
            file_hash=model.file_hash,
            width=model.width,
            height=model.height,
            created_at=model.created_at,
        )


class LogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, log: ProcessingLog) -> ProcessingLog:
        model = ProcessingLogModel(
            id=log.id,
            item_id=log.item_id,
            action=log.action,
            status=log.status,
            message=log.message,
            details=log.details,
            created_at=log.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_item(self, item_id: UUID, limit: int = 50) -> List[ProcessingLog]:
        result = await self.session.execute(
            select(ProcessingLogModel)
            .where(ProcessingLogModel.item_id == item_id)
            .order_by(ProcessingLogModel.created_at.desc())
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
    
    @staticmethod
    def _to_entity(model: ProcessingLogModel) -> ProcessingLog:
        return ProcessingLog(
            id=model.id,
            item_id=model.item_id,
            action=model.action,
            status=model.status,
            message=model.message,
            details=model.details or {},
            created_at=model.created_at,
        )
