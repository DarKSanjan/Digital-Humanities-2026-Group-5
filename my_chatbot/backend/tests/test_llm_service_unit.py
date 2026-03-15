"""Unit tests for llm_service — OpenAI streaming chat via httpx."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm_service import stream_chat, LLMServiceError, _get_api_key


# --- Helpers ---


def _collect(messages: list[dict]) -> list[str]:
    """Run stream_chat synchronously and return all yielded tokens."""
    loop = asyncio.new_event_loop()
    try:
        tokens: list[str] = []

        async def _run():
            async for token in stream_chat(messages):
                tokens.append(token)

        loop.run_until_complete(_run())
        return tokens
    finally:
        loop.close()


def _make_sse_line(content: str | None = None, done: bool = False) -> str:
    """Build a single SSE data line in OpenAI streaming format."""
    if done:
        return "data: [DONE]"
    chunk = {"choices": [{"delta": {}}]}
    if content is not None:
        chunk["choices"][0]["delta"]["content"] = content
    return f"data: {json.dumps(chunk)}"


class FakeAsyncLineIterator:
    """Simulates ``response.aiter_lines()``."""

    def __init__(self, lines: list[str]):
        self._lines = lines
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._index]
        self._index += 1
        return line


class FakeResponse:
    """Minimal fake httpx streaming response."""

    def __init__(self, status_code: int, lines: list[str] | None = None, body: bytes = b""):
        self.status_code = status_code
        self._lines = lines or []
        self._body = body

    def aiter_lines(self):
        return FakeAsyncLineIterator(self._lines)

    async def aread(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeClient:
    """Minimal fake httpx.AsyncClient that returns a FakeResponse."""

    def __init__(self, response: FakeResponse):
        self._response = response

    def stream(self, method, url, **kwargs):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# --- Tests: API key ---


class TestGetApiKey:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(LLMServiceError, match="OPENAI_API_KEY"):
            _get_api_key()

    def test_present_api_key_returns_value(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        assert _get_api_key() == "sk-test-123"


# --- Tests: Streaming ---


class TestStreamChat:
    def test_yields_content_tokens(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        lines = [
            _make_sse_line("Hello"),
            _make_sse_line(" world"),
            _make_sse_line("!"),
            _make_sse_line(done=True),
        ]
        fake_resp = FakeResponse(status_code=200, lines=lines)
        fake_client = FakeClient(fake_resp)

        with patch("src.llm_service.httpx.AsyncClient", return_value=fake_client):
            tokens = _collect([{"role": "user", "content": "Hi"}])

        assert tokens == ["Hello", " world", "!"]

    def test_skips_empty_delta(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        lines = [
            _make_sse_line(None),  # delta with no content
            _make_sse_line("token"),
            _make_sse_line(done=True),
        ]
        fake_resp = FakeResponse(status_code=200, lines=lines)
        fake_client = FakeClient(fake_resp)

        with patch("src.llm_service.httpx.AsyncClient", return_value=fake_client):
            tokens = _collect([{"role": "user", "content": "Hi"}])

        assert tokens == ["token"]

    def test_skips_non_data_lines(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        lines = [
            "",  # empty line
            "event: ping",  # non-data line
            _make_sse_line("ok"),
            _make_sse_line(done=True),
        ]
        fake_resp = FakeResponse(status_code=200, lines=lines)
        fake_client = FakeClient(fake_resp)

        with patch("src.llm_service.httpx.AsyncClient", return_value=fake_client):
            tokens = _collect([{"role": "user", "content": "Hi"}])

        assert tokens == ["ok"]

    def test_handles_malformed_json_gracefully(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        lines = [
            "data: {not valid json",
            _make_sse_line("good"),
            _make_sse_line(done=True),
        ]
        fake_resp = FakeResponse(status_code=200, lines=lines)
        fake_client = FakeClient(fake_resp)

        with patch("src.llm_service.httpx.AsyncClient", return_value=fake_client):
            tokens = _collect([{"role": "user", "content": "Hi"}])

        assert tokens == ["good"]


# --- Tests: Error handling ---


class TestStreamChatErrors:
    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(LLMServiceError, match="OPENAI_API_KEY"):
            _collect([{"role": "user", "content": "Hi"}])

    def test_non_200_status_raises(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        fake_resp = FakeResponse(
            status_code=429,
            body=b'{"error": {"message": "Rate limit exceeded"}}',
        )
        fake_client = FakeClient(fake_resp)

        with patch("src.llm_service.httpx.AsyncClient", return_value=fake_client):
            with pytest.raises(LLMServiceError, match="429"):
                _collect([{"role": "user", "content": "Hi"}])

    def test_timeout_raises_llm_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        import httpx

        class TimeoutClient:
            def stream(self, *args, **kwargs):
                raise httpx.TimeoutException("timed out")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.llm_service.httpx.AsyncClient", return_value=TimeoutClient()):
            with pytest.raises(LLMServiceError, match="timed out"):
                _collect([{"role": "user", "content": "Hi"}])

    def test_http_error_raises_llm_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        import httpx

        class ErrorClient:
            def stream(self, *args, **kwargs):
                raise httpx.ConnectError("connection refused")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.llm_service.httpx.AsyncClient", return_value=ErrorClient()):
            with pytest.raises(LLMServiceError, match="HTTP error"):
                _collect([{"role": "user", "content": "Hi"}])
