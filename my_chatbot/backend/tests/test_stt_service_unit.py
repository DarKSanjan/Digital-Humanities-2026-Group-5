"""Unit tests for stt_service — OpenAI Whisper transcription via httpx."""

import asyncio
import json
from unittest.mock import patch

import pytest

from src.stt_service import STTServiceError, _get_api_key, transcribe


# --- Helpers ---


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class FakeResponse:
    """Minimal fake httpx response for non-streaming requests."""

    def __init__(self, status_code: int, body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text or json.dumps(self._body)

    def json(self):
        return self._body


class FakeClient:
    """Minimal fake httpx.AsyncClient."""

    def __init__(self, response: FakeResponse):
        self._response = response

    async def post(self, url, **kwargs):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# --- Tests: API key ---


class TestGetApiKey:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(STTServiceError, match="OPENAI_API_KEY"):
            _get_api_key()

    def test_present_api_key_returns_value(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        assert _get_api_key() == "sk-test-123"


# --- Tests: transcribe ---


class TestTranscribe:
    def test_returns_transcription_text(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        resp_body = {"text": "Hello world"}
        fake_client = FakeClient(FakeResponse(status_code=200, body=resp_body))

        with patch("src.stt_service.httpx.AsyncClient", return_value=fake_client):
            result = _run(transcribe(b"fake-wav-data"))

        assert result == "Hello world"

    def test_empty_audio_returns_empty_string(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        result = _run(transcribe(b""))
        assert result == ""

    def test_sends_correct_model_and_file(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        resp_body = {"text": "test"}

        captured_kwargs = {}

        class CapturingClient:
            async def post(self, url, **kwargs):
                captured_kwargs.update(kwargs)
                return FakeResponse(status_code=200, body=resp_body)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.stt_service.httpx.AsyncClient", return_value=CapturingClient()):
            _run(transcribe(b"wav-bytes"))

        assert "files" in captured_kwargs
        assert "data" in captured_kwargs
        assert captured_kwargs["data"]["model"] == "whisper-1"
        # Check file tuple: (filename, content, content_type)
        file_tuple = captured_kwargs["files"]["file"]
        assert file_tuple[0] == "audio.wav"
        assert file_tuple[1] == b"wav-bytes"
        assert file_tuple[2] == "audio/wav"

    def test_missing_text_field_returns_empty(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        resp_body = {}  # no "text" key
        fake_client = FakeClient(FakeResponse(status_code=200, body=resp_body))

        with patch("src.stt_service.httpx.AsyncClient", return_value=fake_client):
            result = _run(transcribe(b"fake-wav"))

        assert result == ""


# --- Tests: Error handling ---


class TestTranscribeErrors:
    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(STTServiceError, match="OPENAI_API_KEY"):
            _run(transcribe(b"audio"))

    def test_non_200_status_raises(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        fake_client = FakeClient(
            FakeResponse(status_code=401, text='{"error": "Unauthorized"}')
        )

        with patch("src.stt_service.httpx.AsyncClient", return_value=fake_client):
            with pytest.raises(STTServiceError, match="401"):
                _run(transcribe(b"audio"))

    def test_timeout_raises_stt_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        import httpx

        class TimeoutClient:
            async def post(self, *args, **kwargs):
                raise httpx.TimeoutException("timed out")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.stt_service.httpx.AsyncClient", return_value=TimeoutClient()):
            with pytest.raises(STTServiceError, match="timed out"):
                _run(transcribe(b"audio"))

    def test_http_error_raises_stt_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        import httpx

        class ErrorClient:
            async def post(self, *args, **kwargs):
                raise httpx.ConnectError("connection refused")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.stt_service.httpx.AsyncClient", return_value=ErrorClient()):
            with pytest.raises(STTServiceError, match="HTTP error"):
                _run(transcribe(b"audio"))
