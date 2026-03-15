"""Sentence chunker for the streaming LLM-to-TTS pipeline.

Buffers streamed tokens and flushes at sentence boundaries (. ! ? \\n)
or when the buffer exceeds the 200-char safety limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncGenerator

# Punctuation that marks a sentence boundary
_SENTENCE_ENDINGS = frozenset(".!?")

# Safety flush threshold (characters)
_MAX_BUFFER_LEN = 200


@dataclass
class TextChunk:
    """A chunk of text emitted by the sentence chunker."""

    text: str
    is_final: bool  # True if this is the last chunk of the LLM response


async def chunk_sentences(
    token_stream: AsyncGenerator[str, None],
) -> AsyncGenerator[TextChunk, None]:
    """Buffer tokens from *token_stream*, yielding :class:`TextChunk` objects.

    Flush rules (evaluated in order after each token is appended):
    1. Buffer ends with sentence-ending punctuation (``.`` ``!`` ``?``).
    2. Buffer ends with a newline character.
    3. Buffer length ≥ 200 characters (safety flush).

    When the upstream token stream is exhausted, any remaining buffered text
    is flushed as a final chunk with ``is_final=True``.
    """
    buf: str = ""

    async for token in token_stream:
        buf += token

        # Check flush conditions
        while buf:
            # 1. Safety flush — buffer too long
            if len(buf) >= _MAX_BUFFER_LEN:
                yield TextChunk(text=buf[:_MAX_BUFFER_LEN], is_final=False)
                buf = buf[_MAX_BUFFER_LEN:]
                continue

            # 2. Sentence-ending punctuation or newline at end of buffer
            if buf and (buf[-1] in _SENTENCE_ENDINGS or buf[-1] == "\n"):
                yield TextChunk(text=buf, is_final=False)
                buf = ""
                break

            # No flush condition met yet — wait for more tokens
            break

    # Stream exhausted — flush whatever remains
    if buf:
        yield TextChunk(text=buf, is_final=True)
    else:
        # Even if buffer is empty, emit a final marker so downstream
        # consumers know the stream is done.
        yield TextChunk(text="", is_final=True)
