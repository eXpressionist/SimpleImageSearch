from enum import Enum


class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"


class ItemStatus(str, Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    SAVED = "saved"
    FAILED = "failed"
    REVIEW_NEEDED = "review_needed"
