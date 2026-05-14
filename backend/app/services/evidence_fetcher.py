"""Evidence fetcher — retrieves content from URLs."""
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class EvidenceFetcher:
    """Fetches content from URLs (articles, PDFs, social posts)."""

    def __init__(self, timeout: int = 30):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "PTMediaObservatory/1.0"},
        )

    async def fetch_text(self, url: str) -> Optional[str]:
        """Fetch plain text content from a URL."""
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "text" in content_type or "json" in content_type or "html" in content_type:
                return resp.text[:100_000]
            return f"[Binary content: {content_type}, {len(resp.content)} bytes]"
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    async def close(self):
        await self.client.aclose()