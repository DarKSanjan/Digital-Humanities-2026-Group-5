"""Unit tests for sentence chunker edge cases.

Tests: empty stream, single token, no punctuation, only punctuation.
"""

import asyncio

import pytest

from src.sentence_chunker import chunk_sentences, TextChunk


# --- Helpers ---

async def _tokens_to_async_gen(tokens: list[str]):
    """Convert a plain list of strings into an async generator."""
    for t in tokens:
        yield t


def _collect(tokens: list[str]) -> list[TextChunk]:
    """Run chunk_sentences synchronously and return all emitted chunks."""
    loop = asyncio.new_event_loop()
    try:
        chunks: list[TextChunk] = []

        async def _run():
            async for chunk in chunk_sentences(_tokens_to_async_gen(tokens)):
                chunks.append(chunk)

        loop.run_until_complete(_run())
        return chunks
    finally:
        loop.close()


# --- Edge Case 1: Empty stream ---

class TestEmptyStream:
    """An empty token stream (no tokens at all) should emit a single final
    empty chunk so downstream consumers know the stream completed."""

    def test_empty_stream_emits_final_chunk(self):
        chunks = _collect([])
        assert len(chunks) == 1
        assert chunks[0].text == ""
        assert chunks[0].is_final is True


# --- Edge Case 2: Single token ---

class TestSingleToken:
    """A stream with a single non-punctuation token should emit it as the
    final chunk."""

    def test_single_word_token(self):
        chunks = _collect(["hello"])
        assert len(chunks) == 1
        assert chunks[0].text == "hello"
        assert chunks[0].is_final is True

    def test_single_empty_token(self):
        """A single empty-string token behaves like an empty stream."""
        chunks = _collect([""])
        assert len(chunks) == 1
        assert chunks[0].text == ""
        assert chunks[0].is_final is True


# --- Edge Case 3: No punctuation ---

class TestNoPunctuation:
    """Tokens without any sentence-ending punctuation should all be buffered
    and emitted as a single final chunk."""

    def test_two_tokens_no_punctuation(self):
        chunks = _collect(["hello", " world"])
        assert len(chunks) == 1
        assert chunks[0].text == "hello world"
        assert chunks[0].is_final is True

    def test_multiple_tokens_no_punctuation(self):
        tokens = ["The", " quick", " brown", " fox"]
        chunks = _collect(tokens)
        assert len(chunks) == 1
        assert chunks[0].text == "The quick brown fox"
        assert chunks[0].is_final is True


# --- Edge Case 4: Only punctuation ---

class TestOnlyPunctuation:
    """Streams consisting entirely of punctuation tokens should emit at each
    sentence boundary."""

    def test_single_period(self):
        chunks = _collect(["."])
        # Period triggers a flush, then a final empty marker
        non_final = [c for c in chunks if not c.is_final]
        final = [c for c in chunks if c.is_final]
        assert len(non_final) == 1
        assert non_final[0].text == "."
        assert len(final) == 1
        assert final[0].text == ""
        assert final[0].is_final is True

    def test_multiple_punctuation_tokens(self):
        chunks = _collect([".", "!", "?"])
        non_final = [c for c in chunks if not c.is_final]
        final = [c for c in chunks if c.is_final]
        # Each punctuation token triggers its own flush
        assert len(non_final) == 3
        assert non_final[0].text == "."
        assert non_final[1].text == "!"
        assert non_final[2].text == "?"
        # Final empty marker
        assert len(final) == 1
        assert final[0].text == ""

    def test_exclamation_and_question(self):
        chunks = _collect(["!", "?"])
        non_final = [c for c in chunks if not c.is_final]
        assert len(non_final) == 2
        assert non_final[0].text == "!"
        assert non_final[1].text == "?"
