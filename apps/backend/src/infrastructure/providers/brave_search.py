import logging
import json
import mimetypes
from typing import List
import httpx

from src.domain.interfaces import SearchProvider, SearchResult, SearchConfig

logger = logging.getLogger(__name__)


def guess_mime_type(url: str) -> str:
    """Guess mime type from URL extension."""
    ext = url.split('.')[-1].lower().split('?')[0]
    mime = mimetypes.guess_type(f"file.{ext}")[0]
    return mime or "image/jpeg"


class BraveSearchProvider(SearchProvider):
    """
    Brave Search API - Image Search
    Docs: https://brave.com/search/api/
    Free tier: 2000 requests/month
    """
    def __init__(
        self,
        api_key: str,
        timeout: int = 10,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.search.brave.com/res/v1/images/search"

    @property
    def name(self) -> str:
        return "brave_images"

    async def search(self, config: SearchConfig) -> List[SearchResult]:
        logger.info("=" * 60)
        logger.info("BRAVE SEARCH START")
        logger.info(f"API Key present: {bool(self.api_key)}")
        logger.info(f"API Key prefix: {self.api_key[:10] if self.api_key else 'NONE'}...")
        logger.info(f"Query: {config.query}")
        logger.info(f"Num requested: {config.images_per_query}")

        if not self.api_key:
            logger.error("BRAVE API KEY NOT CONFIGURED!")
            return []

        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        }

        params = {
            "q": config.query,
            "count": min(config.images_per_query, 200),
            "safesearch": "off",
        }

        logger.info(f"Request URL: {self.base_url}")
        logger.info(f"Request params: {params}")

        async with httpx.AsyncClient(timeout=self.timeout * 3) as client:
            try:
                response = await client.get(self.base_url, headers=headers, params=params)

                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")

                if response.status_code == 401:
                    logger.error("Brave API 401 Unauthorized - INVALID API KEY")
                    logger.error(f"Response body: {response.text[:1000]}")
                    return []

                if response.status_code == 429:
                    logger.warning("Brave API rate limit exceeded")
                    return []

                if response.status_code == 403:
                    logger.error("Brave API 403 Forbidden - check API key and permissions")
                    logger.error(f"Response body: {response.text[:1000]}")
                    return []

                if response.status_code != 200:
                    logger.error(f"Brave API error {response.status_code}")
                    logger.error(f"Response body: {response.text[:1000]}")
                    return []

                data = response.json()
                logger.info(f"Response JSON keys: {list(data.keys())}")

                # Log full response for debugging (truncate if too large)
                response_str = json.dumps(data, indent=2)[:2000]
                logger.info(f"Full response (truncated):\n{response_str}")

                results = self._parse_results(data, config)

                logger.info(f"Parsed {len(results)} results")
                for i, r in enumerate(results):
                    logger.info(f" Result {i}: {r.direct_url[:80]}...")

                logger.info("=" * 60)
                return results

            except httpx.TimeoutException:
                logger.error(f"Brave API TIMEOUT after {self.timeout * 3}s")
                return []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                return []
            except Exception as e:
                logger.error(f"Brave API exception: {type(e).__name__}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return []

    def _parse_results(self, data: dict, config: SearchConfig) -> List[SearchResult]:
        results = []

        logger.info(f"Parsing response, top-level keys: {list(data.keys())}")

        # Brave Images response format - try multiple possible keys
        possible_keys = ["results", "images", "image_results", "web", "value"]
        results_list = []

        for key in possible_keys:
            if key in data and isinstance(data[key], list):
                results_list = data[key]
                logger.info(f"Found results in key '{key}' with {len(results_list)} items")
                break

        if not results_list:
            logger.warning("No results list found in any expected key")
            # Try to find any list in the response
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    logger.info(f"Found list in '{key}': {len(value)} items")
                    if isinstance(value[0], dict):
                        results_list = value
                        break

        for position, item in enumerate(results_list[:config.images_per_query]):
            logger.info(f"Parsing item {position}: keys = {list(item.keys()) if isinstance(item, dict) else 'not a dict'}")

            if not isinstance(item, dict):
                logger.warning(f"Item {position} is not a dict: {type(item)}")
                continue

            # Log all keys and values for first item
            if position == 0:
                logger.info(f"First item full data: {json.dumps(item, indent=2)[:500]}")

            # Brave Images specific: URL is in properties.url (full resolution image)
            # Thumbnail is in thumbnail.src
            image_url = None
            width = None
            height = None

            # Priority: properties.url (full image), then thumbnail.src
            if "properties" in item and isinstance(item["properties"], dict):
                props = item["properties"]
                image_url = props.get("url")
                width = props.get("width")
                height = props.get("height")
                if image_url:
                    logger.info(f"Found URL in properties.url: {image_url[:80]}...")

            if not image_url and "thumbnail" in item and isinstance(item["thumbnail"], dict):
                image_url = item["thumbnail"].get("src")
                width = item["thumbnail"].get("width")
                height = item["thumbnail"].get("height")
                if image_url:
                    logger.info(f"Found URL in thumbnail.src: {image_url[:80]}...")

            # Fallback: try other common keys
            if not image_url:
                possible_url_keys = [
                    "url", "image_url", "original_url", "source_url",
                    "thumbnail_url", "src", "image"
                ]
                for key in possible_url_keys:
                    if key in item and item[key]:
                        val = item[key]
                        if isinstance(val, str):
                            image_url = val
                            logger.info(f"Found URL in '{key}': {image_url[:80]}...")
                            break

            if not image_url:
                logger.warning(f"No URL found for item {position}")
                continue

            # Get source/domain
            source = item.get("source", "")
            if isinstance(source, dict):
                source_url = source.get("url", "") or source.get("domain", "")
            else:
                source_url = str(source) if source else ""

            # Also get page URL if available
            page_url = item.get("url", "")

            results.append(SearchResult(
                direct_url=image_url,
                source_url=page_url or source_url,
                title=item.get("title", ""),
                mime_type=guess_mime_type(image_url),
                width=width,
                height=height,
                file_size=None,
                position=position,
            ))

        def get_image_size(result: SearchResult) -> int:
            if result.width and result.height:
                return result.width * result.height
            return 0

        results.sort(key=get_image_size, reverse=True)

        for i, r in enumerate(results):
            r.position = i

        logger.info(f"Successfully parsed {len(results)} image results")
        return results