"""TTS service for ElevenLabs text-to-speech with phoneme alignment.

Provides an async function that sends text to the ElevenLabs TTS API
and returns audio bytes along with phoneme timing data for lip sync.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

# Default voice ID (ElevenLabs "Rachel")
_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# ElevenLabs API base
_ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


class TTSServiceError(Exception):
    """Raised when the TTS service encounters an error."""


@dataclass
class PhonemeData:
    """Phoneme timing data for lip sync alignment."""

    phoneme: str    # IPA symbol
    start: float    # seconds
    duration: float  # seconds


def _get_api_key() -> str:
    """Read the ElevenLabs API key from the environment."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise TTSServiceError(
            "ELEVENLABS_API_KEY environment variable is not set. "
            "Please set it to your ElevenLabs API key."
        )
    return key


def _get_voice_id() -> str:
    """Read the voice ID from the environment, falling back to default."""
    return os.environ.get("ELEVENLABS_VOICE_ID", _DEFAULT_VOICE_ID)


def _parse_phonemes(alignment_data: dict) -> list[PhonemeData]:
    """Parse phoneme alignment from the ElevenLabs response.

    The alignment object contains parallel arrays:
    - ``characters``: list of characters
    - ``character_start_times_seconds``: start time per character
    - ``character_end_times_seconds``: end time per character

    We extract entries that look like IPA phonemes (non-space, non-empty).
    """
    characters = alignment_data.get("characters", [])
    starts = alignment_data.get("character_start_times_seconds", [])
    ends = alignment_data.get("character_end_times_seconds", [])

    phonemes: list[PhonemeData] = []
    for char, start, end in zip(characters, starts, ends):
        if not char or not char.strip():
            continue
        duration = max(0.0, end - start)
        phonemes.append(PhonemeData(phoneme=char, start=start, duration=duration))

    return phonemes


async def stream_tts(text: str) -> tuple[bytes, list[PhonemeData]]:
    """Call ElevenLabs TTS, return audio bytes + phoneme alignment data.

    Parameters
    ----------
    text:
        The text to synthesize into speech.

    Returns
    -------
    tuple[bytes, list[PhonemeData]]
        A tuple of (audio_bytes, phoneme_data) where audio_bytes is the
        raw audio content and phoneme_data contains timing information
        for each phoneme.

    Raises
    ------
    TTSServiceError
        If the API key is missing, the request fails, or the API
        returns an error response.
    """
    if not text or not text.strip():
        return b"", []

    api_key = _get_api_key()
    voice_id = _get_voice_id()

    url = f"{_ELEVENLABS_API_BASE}/text-to-speech/{voice_id}/with-timestamps"

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=120.0)) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                raise TTSServiceError(
                    f"ElevenLabs API returned status {response.status_code}: "
                    f"{response.text}"
                )

            data = response.json()

            # Extract audio bytes (base64-encoded in response)
            import base64

            audio_b64 = data.get("audio_base64", "")
            if not audio_b64:
                raise TTSServiceError(
                    "ElevenLabs API response missing audio_base64 field"
                )
            audio_bytes = base64.b64decode(audio_b64)

            # Extract phoneme alignment
            alignment = data.get("alignment", {})
            phonemes = _parse_phonemes(alignment)

            return audio_bytes, phonemes

        except httpx.TimeoutException as exc:
            raise TTSServiceError(
                f"ElevenLabs API request timed out: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise TTSServiceError(
                f"HTTP error communicating with ElevenLabs API: {exc}"
            ) from exc
        except (json.JSONDecodeError, KeyError) as exc:
            raise TTSServiceError(
                f"Failed to parse ElevenLabs API response: {exc}"
            ) from exc
