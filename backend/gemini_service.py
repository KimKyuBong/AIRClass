import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _sync_generate(self, model: str, prompt: str) -> str:
        # Import lazily so the backend can start without Gemini installed.
        from google import genai  # type: ignore

        client = genai.Client(api_key=self.api_key)
        resp = client.models.generate_content(model=model, contents=prompt)
        text = getattr(resp, "text", None)
        if not text:
            # Best-effort fallback
            return str(resp)
        return text

    async def generate(self, model: str, prompt: str) -> str:
        return await asyncio.to_thread(self._sync_generate, model, prompt)
