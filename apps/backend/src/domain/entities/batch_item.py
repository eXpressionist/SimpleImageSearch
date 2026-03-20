from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from ..value_objects import ItemStatus


@dataclass
class BatchItem:
    id: UUID
    batch_id: UUID
    position: int
    original_query: str
    normalized_query: str
    status: ItemStatus = ItemStatus.PENDING
    error_message: str | None = None
    retry_count: int = 0
    is_approved: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def mark_searching(self) -> None:
        self.status = ItemStatus.SEARCHING
        self.updated_at = datetime.utcnow()
    
    def mark_downloading(self) -> None:
        self.status = ItemStatus.DOWNLOADING
        self.updated_at = datetime.utcnow()
    
    def mark_saved(self) -> None:
        self.status = ItemStatus.SAVED
        self.error_message = None
        self.updated_at = datetime.utcnow()
    
    def mark_failed(self, error: str) -> None:
        self.status = ItemStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.utcnow()
    
    def mark_review_needed(self, reason: str | None = None) -> None:
        self.status = ItemStatus.REVIEW_NEEDED
        if reason:
            self.error_message = reason
        self.updated_at = datetime.utcnow()
    
    def increment_retry(self) -> None:
        self.retry_count += 1
        self.status = ItemStatus.PENDING
        self.error_message = None
        self.updated_at = datetime.utcnow()
    
    def approve(self) -> None:
        self.is_approved = True
        self.updated_at = datetime.utcnow()
    
    def can_retry(self, max_retries: int = 3) -> bool:
        return self.retry_count < max_retries and self.status in (
            ItemStatus.FAILED,
            ItemStatus.REVIEW_NEEDED,
        )
