"""Unit tests for tts_service — ElevenLabs TTS with phoneme alignment."""

import asyncio
import base64
import json
from unittest.mock import patch

import pytest

from src.tts_service import (
    PhonemeData,
    TTSServiceError,
    _get_api_key,
    _get_voice_id,
    _parse_phonemes,
    stream_tts,
)


# --- Helpers ---


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_elevenlabs_response(
    audio_bytes: bytes = b"fake-audio-data",
    characters: list[str] | None = None,
    starts: list[float] | None = None,
    ends: list[float] | None = None,
) -> dict:
    """Build a fake ElevenLabs with-timestamps response body."""
    if characters is None:
        characters = ["H", "e", "l", "l", "o"]
    if starts is None:
        starts = [0.0, 0.05, 0.1, 0.15, 0.2]
    if ends is None:
        ends = [0.05, 0.1, 0.15, 0.2, 0.25]

    return {
        "audio_base64": base64.b64encode(audio_bytes).decode(),
        "alignment": {
            "characters": characters,
            "character_start_times_seconds": starts,
            "character_end_times_seconds": ends,
        },
    }


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


# --- Tests: API key & voice ID ---


class TestGetApiKey:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        with pytest.raises(TTSServiceError, match="ELEVENLABS_API_KEY"):
            _get_api_key()

    def test_present_api_key_returns_value(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test-123")
        assert _get_api_key() == "el-test-123"


class TestGetVoiceId:
    def test_default_voice_id(self, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
        voice_id = _get_voice_id()
        assert voice_id == "21m00Tcm4TlvDq8ikWAM"

    def test_custom_voice_id(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_VOICE_ID", "custom-voice-42")
        assert _get_voice_id() == "custom-voice-42"


# --- Tests: Phoneme parsing ---


class TestParsePhonemes:
    def test_parses_valid_alignment(self):
        alignment = {
            "characters": ["H", "e", "l"],
            "character_start_times_seconds": [0.0, 0.1, 0.2],
            "character_end_times_seconds": [0.1, 0.2, 0.3],
        }
        result = _parse_phonemes(alignment)
        assert len(result) == 3
        assert result[0].phoneme == "H"
        assert result[0].start == pytest.approx(0.0)
        assert result[0].duration == pytest.approx(0.1)
        assert result[1].phoneme == "e"
        assert result[1].start == pytest.approx(0.1)
        assert result[1].duration == pytest.approx(0.1)
        assert result[2].phoneme == "l"
        assert result[2].start == pytest.approx(0.2)
        assert result[2].duration == pytest.approx(0.1)

    def test_skips_spaces(self):
        alignment = {
            "characters": ["H", " ", "i"],
            "character_start_times_seconds": [0.0, 0.1, 0.2],
            "character_end_times_seconds": [0.1, 0.2, 0.3],
        }
        result = _parse_phonemes(alignment)
        assert len(result) == 2
        assert result[0].phoneme == "H"
        assert result[1].phoneme == "i"

    def test_skips_empty_strings(self):
        alignment = {
            "characters": ["a", "", "b"],
            "character_start_times_seconds": [0.0, 0.1, 0.2],
            "character_end_times_seconds": [0.1, 0.2, 0.3],
        }
        result = _parse_phonemes(alignment)
        assert len(result) == 2

    def test_empty_alignment(self):
        result = _parse_phonemes({})
        assert result == []

    def test_negative_duration_clamped_to_zero(self):
        alignment = {
            "characters": ["x"],
            "character_start_times_seconds": [0.5],
            "character_end_times_seconds": [0.3],  # end < start
        }
        result = _parse_phonemes(alignment)
        assert result[0].duration == 0.0


# --- Tests: stream_tts ---


class TestStreamTts:
    def test_returns_audio_and_phonemes(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
        audio_content = b"real-audio-bytes"
        resp_body = _make_elevenlabs_response(audio_bytes=audio_content)
        fake_client = FakeClient(FakeResponse(status_code=200, body=resp_body))

        with patch("src.tts_service.httpx.AsyncClient", return_value=fake_client):
            audio, phonemes = _run(stream_tts("Hello"))

        assert audio == audio_content
        assert len(phonemes) == 5
        assert phonemes[0].phoneme == "H"

    def test_empty_text_returns_empty(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
        audio, phonemes = _run(stream_tts(""))
        assert audio == b""
        assert phonemes == []

    def test_whitespace_only_returns_empty(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
        audio, phonemes = _run(stream_tts("   "))
        assert audio == b""
        assert phonemes == []

    def test_uses_correct_url_with_voice_id(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
        monkeypatch.setenv("ELEVENLABS_VOICE_ID", "my-voice")
        resp_body = _make_elevenlabs_response()

        captured_url = None

        class CapturingClient:
            async def post(self, url, **kwargs):
                nonlocal captured_url
                captured_url = url
                return FakeResponse(status_code=200, body=resp_body)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.tts_service.httpx.AsyncClient", return_value=CapturingClient()):
            _run(stream_tts("Test"))

        assert "my-voice" in captured_url
        assert "/with-timestamps" in captured_url


# --- Tests: Error handling ---


class TestStreamTtsErrors:
    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        with pytest.raises(TTSServiceError, match="ELEVENLABS_API_KEY"):
            _run(stream_tts("Hello"))

    def test_non_200_status_raises(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
        fake_client = FakeClient(
            FakeResponse(status_code=401, text='{"detail": "Unauthorized"}')
        )

        with patch("src.tts_service.httpx.AsyncClient", return_value=fake_client):
            with pytest.raises(TTSServiceError, match="401"):
                _run(stream_tts("Hello"))

    def test_missing_audio_base64_raises(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
        fake_client = FakeClient(
            FakeResponse(status_code=200, body={"alignment": {}})
        )

        with patch("src.tts_service.httpx.AsyncClient", return_value=fake_client):
            with pytest.raises(TTSServiceError, match="audio_base64"):
                _run(stream_tts("Hello"))

    def test_timeout_raises_tts_error(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
        import httpx

        class TimeoutClient:
            async def post(self, *args, **kwargs):
                raise httpx.TimeoutException("timed out")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.tts_service.httpx.AsyncClient", return_value=TimeoutClient()):
            with pytest.raises(TTSServiceError, match="timed out"):
                _run(stream_tts("Hello"))

    def test_http_error_raises_tts_error(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test")
        import httpx

        class ErrorClient:
            async def post(self, *args, **kwargs):
                raise httpx.ConnectError("connection refused")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.tts_service.httpx.AsyncClient", return_value=ErrorClient()):
            with pytest.raises(TTSServiceError, match="HTTP error"):
                _run(stream_tts("Hello"))
