import json
from typing import Any

import httpx


class OpenRouterClient:
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def match_images(self, model: str, products: list[dict[str, Any]], files: list[str]) -> str:
        payload = {
            "task": "Match OpenCart products to image filenames.",
            "instructions": (
                "Return JSON only, as an array of objects with product_id, filename, confidence, and reason. "
                "Only use product_id values and filenames from the supplied payload."
            ),
            "products": products,
            "files": files,
        }
        request_body = {
            "model": model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.base_url, headers=headers, json=request_body)
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]
