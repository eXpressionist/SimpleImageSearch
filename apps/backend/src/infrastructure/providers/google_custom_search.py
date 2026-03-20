import logging
from typing import List
import httpx

from src.domain.interfaces import SearchProvider, SearchResult, SearchConfig

logger = logging.getLogger(__name__)


class GoogleCustomSearchProvider(SearchProvider):
    def __init__(
        self, 
        api_key: str, 
        cx: str, 
        timeout: int = 10,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.cx = cx
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    @property
    def name(self) -> str:
        return "google_custom_search"
    
    async def search(self, config: SearchConfig) -> List[SearchResult]:
        if not self.api_key or not self.cx:
            logger.error("Google API key or CX not configured", extra={
                "api_key_set": bool(self.api_key),
                "cx_set": bool(self.cx),
                "api_key_prefix": self.api_key[:10] if self.api_key else None,
                "cx_value": self.cx[:20] if self.cx else None,
            })
            return []
        
        logger.info("Starting Google search", extra={"query": config.query, "images_per_query": config.images_per_query})
        
        params = self._build_params(config)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.base_url, params=params)
                
                logger.info("Google API response", extra={
                    "status": response.status_code,
                    "query": config.query,
                })
                
                if response.status_code == 429:
                    logger.warning("Google API rate limit exceeded")
                    return []
                
                if response.status_code == 403:
                    logger.error("Google API 403 Forbidden - check API key and CX", extra={
                        "status": response.status_code,
                        "body": response.text[:500],
                    })
                    return []
                
                if response.status_code != 200:
                    logger.error(
                        "Google API error",
                        extra={"status": response.status_code, "body": response.text[:500]}
                    )
                    return []
                
                data = response.json()
                return self._parse_results(data, config)
                
            except httpx.TimeoutException:
                logger.warning("Google API timeout", extra={"query": config.query})
                return []
            except Exception as e:
                logger.error("Google API error", extra={"error": str(e)})
                return []
    
    def _build_params(self, config: SearchConfig) -> dict:
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": config.query,
            "searchType": "image",
            "num": min(config.images_per_query, 10),
            "safe": config.safe,
        }
        
        if config.lr:
            params["lr"] = config.lr
        if config.img_size:
            params["imgSize"] = config.img_size
        if config.img_type:
            params["imgType"] = config.img_type
        if config.file_type:
            params["fileType"] = config.file_type
        if config.rights:
            params["rights"] = config.rights
        if config.site_search:
            params["siteSearch"] = config.site_search
        
        return params
    
    def _parse_results(self, data: dict, config: SearchConfig) -> List[SearchResult]:
        items = data.get("items", [])
        if not items:
            return []
        
        results = []
        
        def get_format_priority(url: str) -> int:
            url_lower = url.lower()
            for i, fmt in enumerate(config.preferred_formats):
                if url_lower.endswith(f".{fmt}"):
                    return i
            return len(config.preferred_formats)
        
        sorted_items = sorted(items, key=lambda x: get_format_priority(x.get("link", "")))
        
        for position, item in enumerate(sorted_items[:config.images_per_query]):
            link = item.get("link", "")
            if not link:
                continue
            
            image_info = item.get("image", {})
            
            results.append(SearchResult(
                direct_url=link,
                source_url=image_info.get("contextLink", ""),
                title=item.get("title", ""),
                mime_type=item.get("mime"),
                width=image_info.get("width"),
                height=image_info.get("height"),
                file_size=None,
                position=position,
            ))
        
        return results