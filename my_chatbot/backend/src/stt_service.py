"""STT service for OpenAI Whisper transcription via httpx.

Provides an async function that sends audio data to the OpenAI
Whisper API and returns the transcription text.
"""

from __future__ import annotations

import os

import httpx

# OpenAI Whisper transcription endpoint
_OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"

# Default model
_MODEL = "whisper-1"


class STTServiceError(Exception):
    """Raised when the STT service encounters an error."""


def _get_api_key() -> str:
    """Read the OpenAI API key from the environment."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise STTServiceError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it to your OpenAI API key."
        )
    return key


async def transcribe(audio_data: bytes) -> str:
    """Send audio to Whisper API, return transcription text.

    Parameters
    ----------
    audio_data:
        Raw audio bytes in WAV format.

    Returns
    -------
    str
        The transcribed text from the audio.

    Raises
    ------
    STTServiceError
        If the API key is missing, the request fails, or the API
        returns an error response.
    """
    if not audio_data:
        return ""

    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    files = {
        "file": ("audio.wav", audio_data, "audio/wav"),
    }

    data = {
        "model": _MODEL,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=120.0)) as client:
        try:
            response = await client.post(
                _OPENAI_TRANSCRIPTION_URL,
                headers=headers,
                files=files,
                data=data,
            )

            if response.status_code != 200:
                raise STTServiceError(
                    f"OpenAI Whisper API returned status {response.status_code}: "
                    f"{response.text}"
                )

            result = response.json()
            return result.get("text", "")

        except httpx.TimeoutException as exc:
            raise STTServiceError(
                f"OpenAI Whisper API request timed out: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise STTServiceError(
                f"HTTP error communicating with OpenAI Whisper API: {exc}"
            ) from exc
