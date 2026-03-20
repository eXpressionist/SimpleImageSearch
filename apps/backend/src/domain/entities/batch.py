from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from ..value_objects import BatchStatus


@dataclass
class Batch:
    id: UUID
    name: str
    total_items: int
    processed_items: int = 0
    failed_items: int = 0
    status: BatchStatus = BatchStatus.PENDING
    config: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def mark_processing(self) -> None:
        self.status = BatchStatus.PROCESSING
        self.updated_at = datetime.utcnow()
    
    def mark_completed(self) -> None:
        if self.failed_items > 0:
            self.status = BatchStatus.PARTIAL
        else:
            self.status = BatchStatus.COMPLETED
        self.updated_at = datetime.utcnow()
    
    def increment_processed(self, failed: bool = False) -> None:
        self.processed_items += 1
        if failed:
            self.failed_items += 1
        self.updated_at = datetime.utcnow()
        
        if self.processed_items >= self.total_items:
            self.mark_completed()
    
    @property
    def progress_percent(self) -> float:
        if self.total_items == 0:
            return 100.0
        return (self.processed_items / self.total_items) * 100
