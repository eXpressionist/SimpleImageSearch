from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/imagesearch"
    
    # Search Provider: "brave" (recommended for images), "serpapi", or "google"
    search_provider: str = "brave"
    
    # Brave Search API - has dedicated Images API!
    # Get key at https://brave.com/search/api/ - 2000 requests/month free
    brave_api_key: str = ""
    
    # Brave search parameters
    brave_count: int = 5  # Number of images to fetch (1-150)
    brave_safesearch: str = "off"  # "off", "moderate", "strict"
    brave_country: str = "US"  # Country code
    brave_search_lang: str = "en"  # Language code
    
    # SerpAPI (alternative)
    serpapi_api_key: str = ""
    serpapi_engine: str = "google_images"
    
    # Google Custom Search (deprecated)
    google_api_key: str = ""
    google_cse_cx: str = ""
    
    # Storage
    storage_path: str = "/data/images"
    
    # Limits
    max_file_size_mb: int = 10
    download_timeout: int = 30
    max_concurrent_downloads: int = 5
    max_retries: int = 3
    retry_backoff_base: int = 2
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period_seconds: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    # Security
    allowed_domains: str = ""
    blocked_domains: str = ""
    
    @property
    def allowed_domains_list(self) -> List[str]:
        return [d.strip() for d in self.allowed_domains.split(",") if d.strip()]
    
    @property
    def blocked_domains_list(self) -> List[str]:
        return [d.strip() for d in self.blocked_domains.split(",") if d.strip()]
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()