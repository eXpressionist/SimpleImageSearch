from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class OpenCartMatchMethod(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    LLM = "llm"


@dataclass
class OpenCartProductInput:
    product_id: int
    sku: str
    line_number: int


@dataclass
class OpenCartParseError:
    line_number: int
    line: str
    message: str


@dataclass
class OpenCartImageMatch:
    product_id: int
    sku: str
    filename: str
    image_path: str
    method: OpenCartMatchMethod
    confidence: float
    reason: str


@dataclass
class OpenCartMatchConflict:
    product_id: int | None
    sku: str | None
    filename: str | None
    message: str


@dataclass
class OpenCartMatchSettings:
    use_openrouter: bool = False
    model: str = "openai/gpt-4.1-nano"
    fuzzy_threshold: float = 0.78
    low_confidence_threshold: float = 0.86
    ignore_service_words: bool = True


@dataclass
class OpenCartMatchReport:
    matches: list[OpenCartImageMatch] = field(default_factory=list)
    unmatched_products: list[OpenCartProductInput] = field(default_factory=list)
    unused_files: list[str] = field(default_factory=list)
    parse_errors: list[OpenCartParseError] = field(default_factory=list)
    conflicts: list[OpenCartMatchConflict] = field(default_factory=list)
    low_confidence_matches: list[OpenCartImageMatch] = field(default_factory=list)
    sql: str = ""


@dataclass
class OpenCartImageMatchRun:
    id: UUID = field(default_factory=uuid4)
    products_text: str = ""
    files_text: str = ""
    image_prefix: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    used_openrouter: bool = False
    model: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    sql: str = ""
    total_products: int = 0
    total_files: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    unused_file_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
