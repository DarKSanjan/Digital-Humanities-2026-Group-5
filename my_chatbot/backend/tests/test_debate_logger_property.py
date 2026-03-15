"""Property-based tests for debate logger.

# Feature: debate-engine-integration, Property 5: Debate logger turn round-trip
# Feature: debate-engine-integration, Property 6: Debate logger bounded size invariant
# Feature: debate-engine-integration, Property 7: Debate logger string tracking round-trip
"""

from hypothesis import given, strategies as st, settings
from src.debate.debate_logger import DebateLogger, MAX_TURNS, MAX_ANALOGIES, MAX_EXAMPLES
from src.debate.types import DebateTurn


# --- Strategies ---

# Generate random DebateTurn objects
debate_turn_strategy = st.builds(
    DebateTurn,
    timestamp=st.text(min_size=0, max_size=30),
    user_message=st.text(min_size=0, max_size=100),
    domain=st.text(min_size=0, max_size=20),
    objection=st.text(min_size=0, max_size=20),
    tone=st.text(min_size=0, max_size=20),
    strategy=st.text(min_size=0, max_size=30),
    reply=st.text(min_size=0, max_size=100),
)

# Lists of turns for sequence-based tests
turn_list_strategy = st.lists(debate_turn_strategy, min_size=0, max_size=80)

# Non-empty strings for analogy/example tracking
non_empty_string_strategy = st.text(min_size=1, max_size=50)

# Lists of non-empty strings
non_empty_string_list_strategy = st.lists(non_empty_string_strategy, min_size=0, max_size=20)

# Mixed strings (including empty) for empty-string rejection tests
mixed_string_strategy = st.text(min_size=0, max_size=50)
mixed_string_list_strategy = st.lists(mixed_string_strategy, min_size=0, max_size=20)


class TestDebateLoggerTurnRoundTrip:
    """Property 5: Debate logger turn round-trip.

    For any sequence of DebateTurn objects logged, requesting recent turns
    with a limit shall return the most recent turns in chronological order,
    up to the requested limit, and each returned turn shall be equal to
    the originally logged turn.

    **Validates: Requirements 4.1, 4.3**
    """

    @given(turns=turn_list_strategy, limit=st.integers(min_value=1, max_value=100))
    @settings(max_examples=100)
    def test_recent_turns_are_chronological_and_equal(
        self, turns: list[DebateTurn], limit: int
    ) -> None:
        """Logged turns are retrievable in chronological order up to the limit."""
        logger = DebateLogger()
        for turn in turns:
            logger.log_turn(turn)

        recent = logger.get_recent_turns(limit)

        # Should return at most `limit` turns
        assert len(recent) <= limit

        # Should return at most the number of stored turns (capped at MAX_TURNS)
        expected_stored = min(len(turns), MAX_TURNS)
        expected_count = min(expected_stored, limit)
        assert len(recent) == expected_count

        # The returned turns should be the tail of the stored sequence
        # (most recent in chronological order)
        stored_turns = turns[-MAX_TURNS:] if len(turns) > MAX_TURNS else turns
        expected_turns = stored_turns[-limit:] if limit < len(stored_turns) else stored_turns

        for returned, original in zip(recent, expected_turns):
            assert returned.timestamp == original.timestamp
            assert returned.user_message == original.user_message
            assert returned.domain == original.domain
            assert returned.objection == original.objection
            assert returned.tone == original.tone
            assert returned.strategy == original.strategy
            assert returned.reply == original.reply


class TestDebateLoggerBoundedSizeInvariant:
    """Property 6: Debate logger bounded size invariant.

    For any sequence of insertions (turns, analogies, examples), stored list
    sizes shall never exceed maximums: 50 turns, 8 analogies, 8 examples.
    When max exceeded, oldest entry evicted first.

    **Validates: Requirements 4.2, 4.5, 4.8**
    """

    @given(turns=turn_list_strategy)
    @settings(max_examples=100)
    def test_turns_never_exceed_max(self, turns: list[DebateTurn]) -> None:
        """Turn list size never exceeds MAX_TURNS after any number of insertions."""
        logger = DebateLogger()
        for turn in turns:
            logger.log_turn(turn)
            # Invariant holds after every insertion
            current = logger.get_recent_turns(MAX_TURNS + 10)
            assert len(current) <= MAX_TURNS

    @given(analogies=st.lists(non_empty_string_strategy, min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_analogies_never_exceed_max(self, analogies: list[str]) -> None:
        """Analogy list size never exceeds MAX_ANALOGIES after any number of insertions."""
        logger = DebateLogger()
        for analogy in analogies:
            logger.remember_analogy(analogy)
            current = logger.get_recent_analogies(MAX_ANALOGIES + 10)
            assert len(current) <= MAX_ANALOGIES

    @given(examples=st.lists(non_empty_string_strategy, min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_examples_never_exceed_max(self, examples: list[str]) -> None:
        """Example list size never exceeds MAX_EXAMPLES after any number of insertions."""
        logger = DebateLogger()
        for example in examples:
            logger.remember_example(example)
            current = logger.get_recent_examples(MAX_EXAMPLES + 10)
            assert len(current) <= MAX_EXAMPLES

    @given(turns=st.lists(debate_turn_strategy, min_size=MAX_TURNS + 1, max_size=80))
    @settings(max_examples=100)
    def test_oldest_turn_evicted_first(self, turns: list[DebateTurn]) -> None:
        """When turns exceed MAX_TURNS, the oldest turn is evicted first."""
        logger = DebateLogger()
        for turn in turns:
            logger.log_turn(turn)

        recent = logger.get_recent_turns(MAX_TURNS)
        # The stored turns should be the last MAX_TURNS from the input
        expected = turns[-MAX_TURNS:]
        assert len(recent) == MAX_TURNS
        for returned, original in zip(recent, expected):
            assert returned.timestamp == original.timestamp
            assert returned.user_message == original.user_message

    @given(analogies=st.lists(non_empty_string_strategy, min_size=MAX_ANALOGIES + 1, max_size=20))
    @settings(max_examples=100)
    def test_oldest_analogy_evicted_first(self, analogies: list[str]) -> None:
        """When analogies exceed MAX_ANALOGIES, the oldest analogy is evicted first."""
        logger = DebateLogger()
        for analogy in analogies:
            logger.remember_analogy(analogy)

        recent = logger.get_recent_analogies(MAX_ANALOGIES)
        expected = analogies[-MAX_ANALOGIES:]
        assert recent == expected

    @given(examples=st.lists(non_empty_string_strategy, min_size=MAX_EXAMPLES + 1, max_size=20))
    @settings(max_examples=100)
    def test_oldest_example_evicted_first(self, examples: list[str]) -> None:
        """When examples exceed MAX_EXAMPLES, the oldest example is evicted first."""
        logger = DebateLogger()
        for example in examples:
            logger.remember_example(example)

        recent = logger.get_recent_examples(MAX_EXAMPLES)
        expected = examples[-MAX_EXAMPLES:]
        assert recent == expected


class TestDebateLoggerStringTrackingRoundTrip:
    """Property 7: Debate logger string tracking round-trip.

    For any non-empty string remembered as analogy/example, requesting recent
    analogies/examples shall include that string (if not evicted). Empty
    strings shall never be stored.

    **Validates: Requirements 4.4, 4.6, 4.7, 4.9, 4.10**
    """

    @given(analogy=non_empty_string_strategy)
    @settings(max_examples=100)
    def test_non_empty_analogy_is_retrievable(self, analogy: str) -> None:
        """A single non-empty analogy remembered is retrievable."""
        logger = DebateLogger()
        logger.remember_analogy(analogy)
        recent = logger.get_recent_analogies(MAX_ANALOGIES)
        assert analogy in recent

    @given(example=non_empty_string_strategy)
    @settings(max_examples=100)
    def test_non_empty_example_is_retrievable(self, example: str) -> None:
        """A single non-empty example remembered is retrievable."""
        logger = DebateLogger()
        logger.remember_example(example)
        recent = logger.get_recent_examples(MAX_EXAMPLES)
        assert example in recent

    @given(analogies=st.lists(non_empty_string_strategy, min_size=1, max_size=MAX_ANALOGIES))
    @settings(max_examples=100)
    def test_all_non_evicted_analogies_present(self, analogies: list[str]) -> None:
        """All non-empty analogies within capacity are retrievable."""
        logger = DebateLogger()
        for a in analogies:
            logger.remember_analogy(a)
        recent = logger.get_recent_analogies(MAX_ANALOGIES)
        # All should be present since we're within capacity
        for a in analogies:
            assert a in recent

    @given(examples=st.lists(non_empty_string_strategy, min_size=1, max_size=MAX_EXAMPLES))
    @settings(max_examples=100)
    def test_all_non_evicted_examples_present(self, examples: list[str]) -> None:
        """All non-empty examples within capacity are retrievable."""
        logger = DebateLogger()
        for e in examples:
            logger.remember_example(e)
        recent = logger.get_recent_examples(MAX_EXAMPLES)
        for e in examples:
            assert e in recent

    @given(strings=mixed_string_list_strategy)
    @settings(max_examples=100)
    def test_empty_strings_never_stored_as_analogies(self, strings: list[str]) -> None:
        """Empty strings are never stored when remembered as analogies."""
        logger = DebateLogger()
        for s in strings:
            logger.remember_analogy(s)
        recent = logger.get_recent_analogies(MAX_ANALOGIES + 10)
        assert "" not in recent

    @given(strings=mixed_string_list_strategy)
    @settings(max_examples=100)
    def test_empty_strings_never_stored_as_examples(self, strings: list[str]) -> None:
        """Empty strings are never stored when remembered as examples."""
        logger = DebateLogger()
        for s in strings:
            logger.remember_example(s)
        recent = logger.get_recent_examples(MAX_EXAMPLES + 10)
        assert "" not in recent

    @given(
        analogies=st.lists(non_empty_string_strategy, min_size=1, max_size=MAX_ANALOGIES),
        limit=st.integers(min_value=1, max_value=MAX_ANALOGIES),
    )
    @settings(max_examples=100)
    def test_analogy_limit_respected(self, analogies: list[str], limit: int) -> None:
        """Requesting analogies with a limit returns at most that many."""
        logger = DebateLogger()
        for a in analogies:
            logger.remember_analogy(a)
        recent = logger.get_recent_analogies(limit)
        assert len(recent) <= limit

    @given(
        examples=st.lists(non_empty_string_strategy, min_size=1, max_size=MAX_EXAMPLES),
        limit=st.integers(min_value=1, max_value=MAX_EXAMPLES),
    )
    @settings(max_examples=100)
    def test_example_limit_respected(self, examples: list[str], limit: int) -> None:
        """Requesting examples with a limit returns at most that many."""
        logger = DebateLogger()
        for e in examples:
            logger.remember_example(e)
        recent = logger.get_recent_examples(limit)
        assert len(recent) <= limit
