"""Streaming pipeline orchestrator.

Coordinates the end-to-end flow: GPT-4 token streaming → sentence
chunking → ElevenLabs TTS → audio playback → lip sync callbacks.
Tracks conversation history and session state throughout.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable

from src.audio_player import AudioPlayer
from src.llm_service import LLMServiceError, stream_chat
from src.retry import async_retry
from src.sentence_chunker import chunk_sentences
from src.tts_service import PhonemeData, TTSServiceError, stream_tts

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ChatMessage:
    """A single message in the conversation."""

    role: str  # 'user' | 'assistant' | 'system'
    content: str


@dataclass
class TranscriptEntry:
    """A transcript entry shown in the UI."""

    role: str  # 'user' | 'assistant'
    content: str
    timestamp: float = 0.0


@dataclass
class SessionState:
    """Observable session state shared with the GUI layer."""

    status: str = "idle"  # 'idle' | 'listening' | 'processing' | 'speaking'
    transcript: list[TranscriptEntry] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class StreamingPipeline:
    """Orchestrates GPT-4 stream → sentence chunker → TTS → audio playback.

    Parameters
    ----------
    audio_player:
        An :class:`AudioPlayer` instance used for playback.
    on_lip_sync_start:
        Optional callback invoked with phoneme data when audio playback
        actually begins on the speakers.
    on_lip_sync_end:
        Optional callback invoked when audio playback ends so the avatar
        can return to the neutral viseme.
    system_prompt:
        Optional system message prepended to every request.
    """

    def __init__(
        self,
        audio_player: AudioPlayer | None = None,
        on_lip_sync_start: Callable[[list[PhonemeData]], None] | None = None,
        on_lip_sync_end: Callable[[], None] | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._audio_player = audio_player or AudioPlayer()
        self._on_lip_sync_start = on_lip_sync_start
        self._on_lip_sync_end = on_lip_sync_end

        self._history: list[ChatMessage] = []
        if system_prompt:
            self._history.append(ChatMessage(role="system", content=system_prompt))

        self.session: SessionState = SessionState()

    # -- public helpers -----------------------------------------------------

    @property
    def history(self) -> list[ChatMessage]:
        """Return a copy of the conversation history."""
        return list(self._history)

    def set_status(self, status: str) -> None:
        """Update session status."""
        self.session.status = status

    # -- callbacks ----------------------------------------------------------

    def on_playback_start(self, phonemes: list[PhonemeData]) -> None:
        """Trigger lip sync when audio playback actually begins."""
        self.set_status("speaking")
        if self._on_lip_sync_start is not None:
            try:
                self._on_lip_sync_start(phonemes)
            except Exception:
                logger.exception("Lip-sync start callback failed")

    def on_playback_end(self) -> None:
        """Reset avatar to neutral viseme when playback ends."""
        if self._on_lip_sync_end is not None:
            try:
                self._on_lip_sync_end()
            except Exception:
                logger.exception("Lip-sync end callback failed")

    # -- main pipeline ------------------------------------------------------

    async def process_user_input(self, text: str) -> None:
        """Run the full pipeline for a single user turn.

        1. Append user message to history.
        2. Stream GPT-4 tokens.
        3. Chunk into sentences.
        4. For each sentence chunk, call TTS and play audio.
        5. Track the assistant reply in history.
        6. Update session state throughout.
        """
        if not text or not text.strip():
            return

        # Record user message
        self._history.append(ChatMessage(role="user", content=text))
        self.session.transcript.append(
            TranscriptEntry(role="user", content=text)
        )

        self.set_status("processing")
        self.session.error = None

        assistant_text = ""

        try:
            messages = [
                {"role": m.role, "content": m.content} for m in self._history
            ]

            token_stream = stream_chat(messages)
            chunks = chunk_sentences(token_stream)

            async for chunk in chunks:
                if not chunk.text:
                    continue

                assistant_text += chunk.text

                try:
                    audio_bytes, phonemes = await async_retry(
                        stream_tts,
                        chunk.text,
                        max_retries=2,
                        base_delay=0.5,
                        retryable_exceptions=(TTSServiceError,),
                    )
                except TTSServiceError as exc:
                    logger.warning("TTS failed for chunk after retries, skipping: %s", exc)
                    continue

                if not audio_bytes:
                    continue

                # Play audio with lip-sync callbacks.  AudioPlayer.play()
                # is non-blocking (runs in a background thread), so we
                # wait for it to finish before processing the next chunk.
                done_event = asyncio.Event()
                loop = asyncio.get_running_loop()

                captured_phonemes = phonemes

                def _on_start() -> None:
                    self.on_playback_start(captured_phonemes)

                def _on_end() -> None:
                    self.on_playback_end()
                    loop.call_soon_threadsafe(done_event.set)

                try:
                    self._audio_player.play(
                        audio_bytes,
                        on_start=_on_start,
                        on_end=_on_end,
                    )
                    await done_event.wait()
                except Exception as exc:
                    logger.warning("Audio playback failed, continuing text-only: %s", exc)

        except LLMServiceError as exc:
            logger.error("LLM service error: %s", exc)
            self.session.error = str(exc)
            self.set_status("idle")
            return
        except Exception as exc:
            logger.exception("Unexpected pipeline error")
            self.session.error = str(exc)
            self.set_status("idle")
            return

        # Record assistant reply
        if assistant_text:
            self._history.append(
                ChatMessage(role="assistant", content=assistant_text)
            )
            self.session.transcript.append(
                TranscriptEntry(role="assistant", content=assistant_text)
            )

        self.set_status("idle")
