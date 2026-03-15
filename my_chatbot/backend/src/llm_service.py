"""LLM service for streaming GPT-4 chat completions via httpx.

Provides an async generator that yields individual tokens from the
OpenAI streaming API.
"""

from __future__ import annotations

import json
import os
from typing import AsyncGenerator

import httpx

# OpenAI API endpoint
_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

# Default model
_MODEL = "gpt-4"


class LLMServiceError(Exception):
    """Raised when the LLM service encounters an error."""


def _get_api_key() -> str:
    """Read the OpenAI API key from the environment."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise LLMServiceError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it to your OpenAI API key."
        )
    return key


async def stream_chat(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream GPT-4 tokens via OpenAI streaming API using httpx.

    Parameters
    ----------
    messages:
        List of message dicts in OpenAI format, e.g.
        ``[{"role": "user", "content": "Hello"}]``.

    Yields
    ------
    str
        Individual content tokens as they arrive from the API.

    Raises
    ------
    LLMServiceError
        If the API key is missing, the request fails, or the API
        returns an error response.
    """
    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": _MODEL,
        "messages": messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=120.0)) as client:
        try:
            async with client.stream(
                "POST",
                _OPENAI_CHAT_URL,
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise LLMServiceError(
                        f"OpenAI API returned status {response.status_code}: "
                        f"{body.decode(errors='replace')}"
                    )

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data = line[len("data: "):]

                    if data.strip() == "[DONE]":
                        return

                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content

        except httpx.TimeoutException as exc:
            raise LLMServiceError(
                f"OpenAI API request timed out: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMServiceError(
                f"HTTP error communicating with OpenAI API: {exc}"
            ) from exc
