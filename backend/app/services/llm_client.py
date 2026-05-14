"""LLM client wrapper for NVIDIA NIM-compatible API."""
import os
import json
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"


class LLMClient:
    """Client for NVIDIA NIM (OpenAI-compatible) chat completions."""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=120.0)

    async def chat(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion request and return the response text."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        for attempt in range(3):
            try:
                resp = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1}/3)")
                    import asyncio
                    await asyncio.sleep(wait)
                    continue
                raise
            except Exception:
                if attempt == 2:
                    raise
                import asyncio
                await asyncio.sleep(2 ** attempt)

    async def close(self):
        await self.client.aclose()