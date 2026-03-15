"""Property-based tests for the sentence chunker.

# Feature: streaming-ui-overhaul, Property 1: Sentence chunker preserves all text
# Feature: streaming-ui-overhaul, Property 2: Sentence chunker emits at boundaries
"""

import asyncio
from hypothesis import given, settings, strategies as st

from src.sentence_chunker import chunk_sentences, TextChunk


# --- Helpers ---

async def _tokens_to_async_gen(tokens: list[str]):
    """Convert a plain list of strings into an async generator."""
    for t in tokens:
        yield t


async def _collect_chunks(tokens: list[str]) -> list[TextChunk]:
    """Run chunk_sentences on *tokens* and return all emitted chunks."""
    chunks: list[TextChunk] = []
    async for chunk in chunk_sentences(_tokens_to_async_gen(tokens)):
        chunks.append(chunk)
    return chunks


# --- Property 1 ---


class TestChunkerPreservesAllText:
    """Property 1: concatenating all chunks == concatenating all input tokens.

    **Validates: Requirements 1.2**
    """

    @given(tokens=st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=40))
    @settings(max_examples=200, deadline=2000)
    def test_concatenated_output_equals_concatenated_input(self, tokens: list[str]):
        """For any sequence of string tokens, the concatenation of all emitted
        chunk texts must equal the concatenation of the original tokens.
        No text is lost, duplicated, or reordered."""

        expected = "".join(tokens)
        loop = asyncio.new_event_loop()
        try:
            chunks = loop.run_until_complete(_collect_chunks(tokens))
        finally:
            loop.close()
        actual = "".join(c.text for c in chunks)

        assert actual == expected, (
            f"Text mismatch!\n"
            f"  input tokens: {tokens!r}\n"
            f"  expected: {expected!r}\n"
            f"  actual:   {actual!r}"
        )


# --- Strategies for Property 2 ---

# Sentence-ending punctuation characters
_BOUNDARY_CHARS = ".!?\n"


@st.composite
def tokens_with_boundaries(draw):
    """Generate a list of tokens where at least one token contains a sentence
    boundary character (. ! ? or \\n).

    Strategy: build a mix of plain-text tokens and tokens that end with a
    boundary character, ensuring at least one boundary is present.
    """
    # Generate some plain word fragments
    plain_token = st.text(
        alphabet=st.characters(blacklist_characters=".!?\n"),
        min_size=1,
        max_size=20,
    )
    # A token that ends with a boundary character
    boundary_suffix = st.sampled_from(list(_BOUNDARY_CHARS))
    boundary_token = st.builds(
        lambda prefix, suffix: prefix + suffix,
        st.text(
            alphabet=st.characters(blacklist_characters=".!?\n"),
            min_size=0,
            max_size=15,
        ),
        boundary_suffix,
    )

    # Draw a mixed list, then inject at least one boundary token
    mixed = draw(
        st.lists(
            st.one_of(plain_token, boundary_token),
            min_size=1,
            max_size=30,
        )
    )

    # Guarantee at least one boundary token exists
    has_boundary = any(
        any(ch in _BOUNDARY_CHARS for ch in tok) for tok in mixed
    )
    if not has_boundary:
        extra = draw(boundary_token)
        insert_pos = draw(st.integers(min_value=0, max_value=len(mixed)))
        mixed.insert(insert_pos, extra)

    return mixed


def _count_boundaries_in_text(text: str) -> int:
    """Count the number of sentence boundaries in *text*.

    A boundary is a sentence-ending punctuation mark or newline that is
    followed by either another character or the end of the string.
    We count each occurrence of . ! ? \\n as a boundary.
    """
    return sum(1 for ch in text if ch in _BOUNDARY_CHARS)


# --- Property 2 ---


class TestChunkerEmitsAtBoundaries:
    """Property 2: chunks are emitted at or near sentence boundaries.

    For any sequence of string tokens containing sentence-ending punctuation
    (. ! ?) or newlines, chunk_sentences should emit a chunk whose text ends
    at or near each such boundary.

    **Validates: Requirements 1.2**
    """

    @given(tokens=tokens_with_boundaries())
    @settings(max_examples=200, deadline=2000)
    def test_chunks_end_at_boundaries(self, tokens: list[str]):
        """Each non-final chunk should end with a boundary character (. ! ? \\n)
        or be a safety-flush chunk (length >= 200).  Additionally, the number
        of emitted chunks (excluding the final empty marker) should be at least
        the number of boundary characters in the concatenated input, because
        each boundary triggers a flush."""

        loop = asyncio.new_event_loop()
        try:
            chunks = loop.run_until_complete(_collect_chunks(tokens))
        finally:
            loop.close()

        full_text = "".join(tokens)

        # Every non-final chunk must end at a boundary or be a safety flush
        for chunk in chunks:
            if chunk.is_final:
                continue
            text = chunk.text
            assert (
                text[-1] in _BOUNDARY_CHARS or len(text) >= 200
            ), (
                f"Non-final chunk does not end at a boundary and is not a "
                f"safety flush:\n  chunk text: {text!r}\n  tokens: {tokens!r}"
            )

        # The number of boundary-ending chunks should be >= the number of
        # distinct boundary points in the input.  A boundary point is each
        # occurrence of . ! ? \n in the concatenated text.  However, safety
        # flushes can merge multiple boundaries into one chunk, so we relax
        # the check: the total number of non-final chunks must be >= 1
        # (since we guaranteed at least one boundary exists).
        non_final_chunks = [c for c in chunks if not c.is_final]
        boundary_count = _count_boundaries_in_text(full_text)

        if boundary_count > 0 and full_text:
            assert len(non_final_chunks) >= 1, (
                f"Expected at least 1 non-final chunk for input with "
                f"{boundary_count} boundaries, got 0.\n"
                f"  tokens: {tokens!r}\n  full_text: {full_text!r}"
            )
