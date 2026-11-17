import asyncio
import ipaddress
import logging
import re
import socket
from typing import Optional
from urllib.parse import urlparse
import httpx

from src.domain.entities import ImageAsset
from src.domain.interfaces import StorageResult
from src.infrastructure.providers import LocalFileStorage
from src.infrastructure.config import Settings
from src.infrastructure.image_processing import inspect_image

logger = logging.getLogger(__name__)


class ImageDownloader:
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
        data, content_type = await self.fetch_image(url)
        filename = self._generate_filename(url, original_query, content_type)
        storage_result = await self.storage.save(
            data=data,
            batch_id=batch_id,
            item_id=item_id,
            filename=filename,
            content_type=content_type,
        )
        
        return self._create_image_asset(
            storage_result=storage_result,
            url=url,
            item_id=item_id,
        )

    async def download_to_directory(
        self,
        url: str,
        target_dir: str,
        filename: str,
    ) -> StorageResult:
        data, content_type = await self.fetch_image(url)

        return await self.storage.save_to_directory(
            data=data,
            target_dir=target_dir,
            filename=filename,
            content_type=content_type,
        )

    async def fetch_image(self, url: str) -> tuple[bytes, str]:
        self._validate_url(url)
        data, content_type = await self._download_with_retry(url)
        self._validate_content(data, content_type)
        mime_type, _, _ = await asyncio.to_thread(inspect_image, data)
        return data, mime_type
    
    def _validate_url(self, url: str) -> None:
        if not url:
            raise ValueError("Empty URL")
        
        parsed = urlparse(url)
        
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid scheme: {parsed.scheme}")
        
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("No hostname in URL")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in image URLs are not allowed")
        hostname_lower = hostname.lower().rstrip(".")

        def matches_domain(domain: str) -> bool:
            domain = domain.lower().strip(".")
            return hostname_lower == domain or hostname_lower.endswith(f".{domain}")
        
        # Check blocked domains
        if self.settings.blocked_domains_list:
            for blocked in self.settings.blocked_domains_list:
                if matches_domain(blocked):
                    raise ValueError(f"Blocked domain: {hostname}")
        
        # Check allowed domains (if whitelist is set)
        if self.settings.allowed_domains_list:
            allowed = False
            for allowed_domain in self.settings.allowed_domains_list:
                if matches_domain(allowed_domain):
                    allowed = True
                    break
            if not allowed:
                raise ValueError(f"Domain not in whitelist: {hostname}")
        
        if hostname_lower == "localhost" or hostname_lower.endswith(".localhost"):
            raise ValueError(f"SSRF attempt blocked: {hostname}")
        try:
            address = ipaddress.ip_address(hostname_lower)
        except ValueError:
            return
        if not address.is_global:
            raise ValueError(f"SSRF attempt blocked: {hostname}")

    async def _resolve_public_host(self, url: str) -> str:
        parsed = urlparse(url)
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
        if not addresses or any(not ipaddress.ip_address(info[4][0]).is_global for info in addresses):
            raise ValueError(f"SSRF attempt blocked: {parsed.hostname}")
        return addresses[0][4][0]
    
    async def _download_with_retry(self, url: str) -> tuple[bytes, str]:
        last_error: Optional[Exception] = None
        
        for attempt in range(self.settings.max_retries):
            try:
                return await asyncio.wait_for(self._download(url), timeout=self.settings.download_timeout)
            except Exception as e:
                last_error = e
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")

                if self._is_non_retryable_download_error(e):
                    raise
                
                if attempt < self.settings.max_retries - 1:
                    backoff = self.settings.retry_backoff_base ** attempt
                    await asyncio.sleep(backoff)
        
        raise last_error or Exception("Download failed")

    def _is_non_retryable_download_error(self, error: Exception) -> bool:
        match = re.fullmatch(r"HTTP (\d{3})", str(error))
        if not match:
            return isinstance(error, ValueError)

        status_code = int(match.group(1))
        return 400 <= status_code < 500 and status_code not in {408, 429}
    
    async def _download(self, url: str) -> tuple[bytes, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        
        async with httpx.AsyncClient(
            timeout=self.settings.download_timeout,
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(max_keepalive_connections=0),
        ) as client:
            for redirect in range(6):
                self._validate_url(url)
                address = await self._resolve_public_host(url)
                original_url = httpx.URL(url)
                # Pin the checked IP so DNS rebinding cannot change the connection target.
                request_url = original_url.copy_with(host=address)
                request_headers = {**headers, "Host": original_url.netloc.decode("ascii")}
                client.cookies.clear()
                async with client.stream(
                    "GET", request_url, headers=request_headers,
                    extensions={"sni_hostname": original_url.host},
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location or redirect == 5:
                            raise ValueError("Invalid or excessive image redirects")
                        url = str(original_url.join(location))
                        continue
                    if response.status_code != 200:
                        raise ValueError(f"HTTP {response.status_code}")
                    length = response.headers.get("content-length", "")
                    if length.isdigit() and int(length) > self.settings.max_file_size_bytes:
                        raise ValueError("File too large")
                    data = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                        data.extend(chunk)
                        if len(data) > self.settings.max_file_size_bytes:
                            raise ValueError("File too large")
                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    return bytes(data), content_type
        raise ValueError("Download failed")
    
    def _validate_content(self, data: bytes, content_type: str) -> None:
        if len(data) == 0:
            raise ValueError("Empty response")
        
        if len(data) > self.settings.max_file_size_bytes:
            raise ValueError(f"File too large: {len(data)} bytes")
        
    
    def _generate_filename(self, url: str, query: str, content_type: str) -> str:
        # Use normalized query as filename (option A from requirements)
        ext = self._get_extension_from_url(url) or self._get_extension_from_mime(content_type)
        
        filename = query[:190] if len(query) > 190 else query
        
        filename = re.sub(r'[^\w\-]', '_', filename)
        filename = filename.strip('_').strip('-')
        
        if not filename:
            filename = "image"
        
        return f"{filename}{ext}"

    def generate_sku_filename(self, url: str, number: int, content_type: str | None = None) -> str:
        ext = self._get_extension_from_url(url) or self._get_extension_from_mime(content_type or "")
        return f"SKU-{number}{ext}"

    def generate_item_filename(
        self,
        item_name: str,
        url: str,
        index: int,
        total: int,
        content_type: str | None = None,
    ) -> str:
        ext = self._get_extension_from_url(url) or self._get_extension_from_mime(content_type or "")
        base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", item_name.strip())
        base = re.sub(r"\s+", "_", base)
        base = base.strip("._-") or "image"

        suffix = f"-{index}" if total > 1 else ""
        max_base_length = 200 - len(suffix) - len(ext)
        return f"{base[:max_base_length]}{suffix}{ext}"
    
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
