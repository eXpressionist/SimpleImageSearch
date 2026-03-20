from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class ProcessingLog:
    id: UUID
    item_id: UUID
    action: str
    status: str
    message: str | None = None
    details: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @classmethod
    def create(
        cls,
        item_id: UUID,
        action: str,
        status: str,
        message: str | None = None,
        details: dict | None = None,
    ) -> "ProcessingLog":
        return cls(
            id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be set by DB
            item_id=item_id,
            action=action,
            status=status,
            message=message,
            details=details or {},
        )
