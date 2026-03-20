import logging
from typing import List, Optional
import httpx

from src.domain.interfaces import SearchProvider, SearchResult, SearchConfig

logger = logging.getLogger(__name__)


class SerpApiSearchProvider(SearchProvider):
    """
    SerpAPI - provides access to Google Images, Bing, Yandex, and other search engines.
    Free tier available: 100 searches/month
    Sign up at: https://serpapi.com/
    """
    def __init__(
        self, 
        api_key: str,
        engine: str = "google_images",
        timeout: int = 10,
    ):
        self.api_key = api_key
        self.engine = engine
        self.timeout = timeout
        self.base_url = "https://serpapi.com/search"
    
    @property
    def name(self) -> str:
        return f"serpapi_{self.engine}"
    
    async def search(self, config: SearchConfig) -> List[SearchResult]:
        if not self.api_key:
            logger.error("SerpAPI key not configured", extra={
                "api_key_set": bool(self.api_key),
            })
            return []
        
        logger.info("Starting SerpAPI search", extra={
            "query": config.query, 
            "engine": self.engine,
            "images_per_query": config.images_per_query
        })
        
        params = {
            "api_key": self.api_key,
            "engine": self.engine,
            "q": config.query,
            "num": min(config.images_per_query, 10),
            "ijn": 0,  # start index
        }
        
        if "google" in self.engine:
            params["safe"] = config.safe if config.safe != "off" else "off"
        
        async with httpx.AsyncClient(timeout=self.timeout * 3) as client:
            try:
                response = await client.get(self.base_url, params=params)
                
                logger.info("SerpAPI response", extra={
                    "status": response.status_code,
                    "query": config.query,
                })
                
                if response.status_code == 401:
                    logger.error("SerpAPI 401 Unauthorized - check API key")
                    return []
                
                if response.status_code == 429:
                    logger.warning("SerpAPI rate limit exceeded")
                    return []
                
                if response.status_code == 403:
                    logger.error("SerpAPI 403 Forbidden - check API key and plan")
                    return []
                
                if response.status_code != 200:
                    logger.error(
                        "SerpAPI error",
                        extra={"status": response.status_code, "body": response.text[:500]}
                    )
                    return []
                
                data = response.json()
                return self._parse_results(data, config)
                
            except httpx.TimeoutException:
                logger.warning("SerpAPI timeout", extra={"query": config.query})
                return []
            except Exception as e:
                logger.error("SerpAPI error", extra={"error": str(e)})
                return []
    
    def _parse_results(self, data: dict, config: SearchConfig) -> List[SearchResult]:
        results = []
        
        # Google Images format
        images_results = data.get("images_results", [])
        
        for position, item in enumerate(images_results[:config.images_per_query]):
            original_url = item.get("original")
            if not original_url:
                continue
            
            results.append(SearchResult(
                direct_url=original_url,
                source_url=item.get("source", ""),
                title=item.get("title", ""),
                mime_type=item.get("format", "image/jpeg"),
                width=item.get("width"),
                height=item.get("height"),
                file_size=item.get("size"),
                position=position,
            ))
        
        if not results:
            logger.warning("No image results found in SerpAPI response")
        
        return results