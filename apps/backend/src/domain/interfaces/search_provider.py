from typing import Protocol, List
from dataclasses import dataclass, field


@dataclass
class SearchConfig:
    query: str
    images_per_query: int = 10
    lr: str = "lang_ru"
    safe: str = "active"
    img_size: str | None = "large"
    img_type: str | None = None
    file_type: str | None = None
    rights: str | None = None
    site_search: str | None = None
    
    preferred_formats: list[str] = field(default_factory=lambda: ["webp", "png", "jpg", "jpeg"])


@dataclass
class SearchResult:
    direct_url: str
    source_url: str
    title: str
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    position: int = 0


class SearchProvider(Protocol):
    async def search(self, config: SearchConfig) -> List[SearchResult]:
        """
        Search for images.
        
        Returns empty list if no results or error.
        Should never raise exceptions - handle internally.
        """
        ...
    
    @property
    def name(self) -> str:
        """Provider name for logging"""
        ...
