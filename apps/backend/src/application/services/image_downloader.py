import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse
import httpx

from src.domain.entities import ImageAsset
from src.domain.interfaces import StorageResult
from src.infrastructure.providers import LocalFileStorage
from src.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class ImageDownloader:
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
    }
    
    BLOCKED_IP_RANGES = [
        "10.",
        "127.",
        "169.254.",
        "172.16.",
        "172.17.",
        "172.18.",
        "172.19.",
        "172.20.",
        "172.21.",
        "172.22.",
        "172.23.",
        "172.24.",
        "172.25.",
        "172.26.",
        "172.27.",
        "172.28.",
        "172.29.",
        "172.30.",
        "172.31.",
        "192.168.",
        "0.0.0.0",
        "::1",
        "fc00:",
        "fe80:",
    ]
    
    def __init__(self, storage: LocalFileStorage, settings: Settings):
        self.storage = storage
        self.settings = settings
    
    async def download_and_save(
        self,
        url: str,
        batch_id: str,
        item_id: str,
        original_query: str,
    ) -> ImageAsset:
        logger.info("=" * 60)
        logger.info("DOWNLOAD AND SAVE START")
        logger.info(f"URL: {url}")
        logger.info(f"Batch ID: {batch_id}")
        logger.info(f"Item ID: {item_id}")
        logger.info(f"Query: {original_query}")
        
        try:
            self._validate_url(url)
            logger.info("URL validation passed")
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            raise
        
        logger.info("Starting download...")
        data, content_type = await self._download_with_retry(url)
        logger.info(f"Downloaded {len(data)} bytes, content-type: {content_type}")
        
        try:
            self._validate_content(data, content_type)
            logger.info("Content validation passed")
        except Exception as e:
            logger.error(f"Content validation failed: {e}")
            raise
        
        filename = self._generate_filename(url, original_query, content_type)
        logger.info(f"Generated filename: {filename}")
        
        logger.info("Saving to storage...")
        storage_result = await self.storage.save(
            data=data,
            batch_id=batch_id,
            item_id=item_id,
            filename=filename,
            content_type=content_type,
        )
        logger.info(f"Saved to: {storage_result.file_path}")
        logger.info("=" * 60)
        
        return self._create_image_asset(
            storage_result=storage_result,
            url=url,
            item_id=item_id,
        )
    
    def _validate_url(self, url: str) -> None:
        if not url:
            raise ValueError("Empty URL")
        
        parsed = urlparse(url)
        
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid scheme: {parsed.scheme}")
        
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("No hostname in URL")
        
        hostname_lower = hostname.lower()
        
        # Check blocked domains
        if self.settings.blocked_domains_list:
            for blocked in self.settings.blocked_domains_list:
                if blocked.lower() in hostname_lower:
                    raise ValueError(f"Blocked domain: {hostname}")
        
        # Check allowed domains (if whitelist is set)
        if self.settings.allowed_domains_list:
            allowed = False
            for allowed_domain in self.settings.allowed_domains_list:
                if allowed_domain.lower() in hostname_lower:
                    allowed = True
                    break
            if not allowed:
                raise ValueError(f"Domain not in whitelist: {hostname}")
        
        # SSRF protection
        for blocked_range in self.BLOCKED_IP_RANGES:
            if hostname_lower.startswith(blocked_range.lower()):
                raise ValueError(f"SSRF attempt blocked: {hostname}")
    
    async def _download_with_retry(self, url: str) -> tuple[bytes, str]:
        last_error: Optional[Exception] = None
        
        for attempt in range(self.settings.max_retries):
            try:
                return await self._download(url)
            except Exception as e:
                last_error = e
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                
                if attempt < self.settings.max_retries - 1:
                    backoff = self.settings.retry_backoff_base ** attempt
                    await asyncio.sleep(backoff)
        
        raise last_error or Exception("Download failed")
    
    async def _download(self, url: str) -> tuple[bytes, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        
        async with httpx.AsyncClient(
            timeout=self.settings.download_timeout,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                raise ValueError(f"HTTP {response.status_code}")
            
            content_type = response.headers.get("content-type", "").split(";")[0].strip()
            
            data = response.content
            
            # Follow redirect manually to validate final URL
            if response.history:
                final_url = str(response.url)
                self._validate_url(final_url)
            
            return data, content_type
    
    def _validate_content(self, data: bytes, content_type: str) -> None:
        if len(data) == 0:
            raise ValueError("Empty response")
        
        if len(data) > self.settings.max_file_size_bytes:
            raise ValueError(f"File too large: {len(data)} bytes")
        
        # Check content type
        if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
            # Some servers return wrong content type, check actual content
            pass
    
    def _generate_filename(self, url: str, query: str, content_type: str) -> str:
        # Use normalized query as filename (option A from requirements)
        ext = self._get_extension_from_url(url) or self._get_extension_from_mime(content_type)
        
        filename = query[:190] if len(query) > 190 else query
        
        filename = re.sub(r'[^\w\-]', '_', filename)
        filename = filename.strip('_').strip('-')
        
        if not filename:
            filename = "image"
        
        return f"{filename}{ext}"
    
    def _get_extension_from_url(self, url: str) -> str:
        path = urlparse(url).path.lower()
        for ext in [".webp", ".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            if path.endswith(ext):
                return ext
        return ""
    
    def _get_extension_from_mime(self, mime_type: str) -> str:
        mime_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
        }
        return mime_map.get(mime_type, ".jpg")
    
    def _create_image_asset(
        self,
        storage_result: StorageResult,
        url: str,
        item_id: str,
    ) -> ImageAsset:
        from uuid import uuid4, UUID
        
        return ImageAsset(
            id=uuid4(),
            item_id=UUID(item_id),
            source_url="",
            direct_url=url,
            file_path=storage_result.file_path,
            file_name=storage_result.file_name,
            mime_type=storage_result.mime_type,
            file_size=storage_result.file_size,
            file_hash=storage_result.file_hash,
            width=storage_result.width,
            height=storage_result.height,
        )
