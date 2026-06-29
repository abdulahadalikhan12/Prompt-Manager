import asyncio
import json
from typing import AsyncIterator, Optional

import httpx
from fastapi import HTTPException

from core.config import settings
from schemas import ChatMessage, GenerateResponse, TokenUsage

TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)

MAX_RETRIES_PER_MODEL = 2
RETRY_BASE_DELAY_SECONDS = 1.0


class OpenRouterCallError(Exception):
    """Internal-only exception carrying an HTTP status code from a
    failed OpenRouter call, so the retry loop can decide whether the
    failure is worth retrying."""
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"OpenRouter call failed: {status_code}")


class OpenRouterClient:
    """
    Owns the single shared httpx.AsyncClient for this service (created
    once at startup via FastAPI's lifespan, not per-request -- see
    main.py). Implements the retry + model-fallback chain described in
    the Week 2 brief's stretch goals.
    """

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

    def _is_retryable(self, status_code: int) -> bool:
        return status_code == 429 or status_code >= 500

    async def _call_model(
        self, model: str, messages: list[ChatMessage],
        temperature: float, max_tokens: Optional[int],
    ) -> dict:
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        response = await self.client.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=TIMEOUT,
        )

        if response.status_code != 200:
            raise OpenRouterCallError(response.status_code, response.text)

        return response.json()

    async def generate(
        self, messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> GenerateResponse:
        chain = [model] if model else settings.MODEL_CHAIN
        last_error: Optional[Exception] = None

        for candidate_model in chain:
            for attempt in range(MAX_RETRIES_PER_MODEL + 1):
                try:
                    raw = await self._call_model(candidate_model, messages, temperature, max_tokens)
                    return self._parse_response(raw, candidate_model)

                except OpenRouterCallError as e:
                    last_error = e
                    if not self._is_retryable(e.status_code):
                        break
                    if attempt < MAX_RETRIES_PER_MODEL:
                        delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
                        await asyncio.sleep(delay)

                except httpx.RequestError as e:
                    last_error = e
                    if attempt < MAX_RETRIES_PER_MODEL:
                        await asyncio.sleep(RETRY_BASE_DELAY_SECONDS * (2 ** attempt))

        self._raise_clean_error(last_error)

    def _parse_response(self, raw: dict, model_used: str) -> GenerateResponse:
        choice = raw["choices"][0]
        usage = raw.get("usage", {})
        return GenerateResponse(
            content=choice["message"]["content"],
            model=model_used,
            usage=TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            ),
            finish_reason=choice.get("finish_reason"),
        )

    def _raise_clean_error(self, error: Optional[Exception]):
        if isinstance(error, OpenRouterCallError):
            raise HTTPException(status_code=502, detail=f"All models in the chain failed. Last error: {error.status_code} {error.body}")
        if isinstance(error, httpx.RequestError):
            raise HTTPException(status_code=503, detail="OpenRouter is unreachable.")
        raise HTTPException(status_code=502, detail="All models in the fallback chain failed.")

    async def stream_generate(
        self, messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Streams tokens from OpenRouter as Server-Sent Events. Only
        attempted against the FIRST model in the chain (or the
        explicitly requested one) -- falling back mid-stream to a
        different model would mean discarding partial output the user
        has already seen.
        """
        chosen_model = model or settings.MODEL_CHAIN[0]
        payload = {
            "model": chosen_model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        try:
            async with self.client.stream(
                "POST",
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=TIMEOUT,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise OpenRouterCallError(response.status_code, body.decode())

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: "):]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content")
                    if text:
                        yield text

        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="OpenRouter is unreachable.")
        except OpenRouterCallError as e:
            raise HTTPException(status_code=502, detail=f"OpenRouter returned an error: {e.status_code}")
