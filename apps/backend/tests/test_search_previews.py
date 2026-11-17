import pytest

from src.domain.interfaces import SearchConfig
from src.infrastructure.providers.brave_search import BraveSearchProvider
from src.infrastructure.providers.google_custom_search import GoogleCustomSearchProvider
from src.infrastructure.providers.serpapi_search import SerpApiSearchProvider


@pytest.mark.parametrize("provider,payload", [
    (BraveSearchProvider("test"), {"results": [{
        "properties": {"url": "https://cdn.test/original.jpg", "width": 800, "height": 600},
        "thumbnail": {"src": "https://cdn.test/thumbnail.jpg"},
        "url": "https://shop.test/product",
    }]}),
    (GoogleCustomSearchProvider("test", "cx"), {"items": [{
        "link": "https://cdn.test/original.jpg",
        "image": {"thumbnailLink": "https://cdn.test/thumbnail.jpg"},
    }]}),
    (SerpApiSearchProvider("test"), {"images_results": [{
        "original": "https://cdn.test/original.jpg", "thumbnail": "https://cdn.test/thumbnail.jpg",
    }]}),
])
def test_search_results_keep_separate_preview_and_original_urls(provider, payload):
    result = provider._parse_results(payload, SearchConfig(query="product"))[0]
    assert result.direct_url == "https://cdn.test/original.jpg"
    assert result.thumbnail_url == "https://cdn.test/thumbnail.jpg"
