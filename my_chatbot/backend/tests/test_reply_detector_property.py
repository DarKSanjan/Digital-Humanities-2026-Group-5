"""Property-based tests for reply fragment detection.

# Feature: debate-engine-integration, Property 11: Reply fragment detection correctness
"""

from hypothesis import given, strategies as st, settings
from src.debate.reply_detector import detect_used_analogies, detect_used_examples


# --- Strategies ---

# Generate non-empty fragment strings using ASCII letters/digits/spaces
# (analogy/example bank entries are English text, so ASCII is appropriate)
fragment_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z"), max_codepoint=127),
    min_size=1,
    max_size=40,
)

# Lists of known fragments
fragment_list_strategy = st.lists(fragment_strategy, min_size=0, max_size=10)

# Reply text
reply_strategy = st.text(min_size=0, max_size=200)


class TestReplyFragmentDetectionCorrectness:
    """Property 11: Reply fragment detection correctness.

    For any reply text and for any list of known fragments,
    detect_used_analogies and detect_used_examples shall return exactly
    those fragments whose text appears in the reply (case-insensitive
    partial match). When no fragments match, the returned list shall be empty.

    **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    """

    @given(
        fragments=st.lists(fragment_strategy, min_size=1, max_size=5),
        padding=st.text(min_size=0, max_size=30),
    )
    @settings(max_examples=100)
    def test_embedded_fragment_is_detected(self, fragments: list[str], padding: str) -> None:
        """When a fragment is embedded in the reply, it should be detected."""
        # Pick the first fragment and embed it in a reply
        target = fragments[0]
        reply = padding + target + padding

        result_analogies = detect_used_analogies(reply, fragments)
        result_examples = detect_used_examples(reply, fragments)

        # The embedded fragment must appear in results
        assert target in result_analogies
        assert target in result_examples

    @given(
        fragment=fragment_strategy,
        padding=st.text(min_size=0, max_size=30),
        case_transform=st.sampled_from(["upper", "lower", "title", "swapcase"]),
    )
    @settings(max_examples=100)
    def test_detection_is_case_insensitive(
        self, fragment: str, padding: str, case_transform: str
    ) -> None:
        """Detection is case-insensitive: a case-transformed fragment in the reply is still found."""
        # Transform the fragment's case in the reply text
        transformed = getattr(fragment, case_transform)()
        reply = padding + transformed + padding

        result_analogies = detect_used_analogies(reply, [fragment])
        result_examples = detect_used_examples(reply, [fragment])

        assert fragment in result_analogies
        assert fragment in result_examples

    @given(reply=reply_strategy, fragments=fragment_list_strategy)
    @settings(max_examples=100)
    def test_no_match_returns_empty(self, reply: str, fragments: list[str]) -> None:
        """When no fragments match the reply, the returned list is empty."""
        # Filter to only fragments that truly don't appear in the reply
        non_matching = [f for f in fragments if f.lower() not in reply.lower()]

        result_analogies = detect_used_analogies(reply, non_matching)
        result_examples = detect_used_examples(reply, non_matching)

        assert result_analogies == []
        assert result_examples == []

    @given(reply=reply_strategy, fragments=fragment_list_strategy)
    @settings(max_examples=100)
    def test_both_functions_behave_identically(
        self, reply: str, fragments: list[str]
    ) -> None:
        """detect_used_analogies and detect_used_examples return the same results for the same inputs."""
        result_analogies = detect_used_analogies(reply, fragments)
        result_examples = detect_used_examples(reply, fragments)

        assert result_analogies == result_examples
