"""Property-based tests for the prompt builder.

# Feature: debate-engine-integration, Property 8: Prompt contains all required sections
# Feature: debate-engine-integration, Property 9: Response mode detection correctness
# Feature: debate-engine-integration, Property 10: Prompt classification metadata round-trip
"""

import re
from hypothesis import given, strategies as st, settings
from src.debate.prompt_builder import (
    build_prompt,
    detect_response_mode,
    get_relevant_arguments,
    strategy_instruction,
)
from src.debate.types import Classification, DebateTurn
from src.debate.debate_logger import DebateLogger
from src.debate.persona import get_persona
from src.debate.argument_bank import get_claims, get_rebuttals
from src.debate.analogy_bank import ANALOGY_BANK
from src.debate.example_bank import EXAMPLE_BANK


# --- Valid literal values ---

VALID_DOMAINS = ["art", "science", "government", "human"]
VALID_OBJECTIONS = [
    "soul", "originality", "intuition", "empathy", "democracy",
    "meaning", "authenticity", "consciousness", "morality", "creativity",
    "bias", "free_will", "emotion", "trust", "tradition", "dignity", "general",
]
VALID_TONES = ["philosophical", "technical", "moral", "general"]
VALID_STRATEGIES = [
    "functional_redefinition", "performance_over_origin", "inevitability_framing",
    "human_limitations_contrast", "historical_replacement_analogy",
    "hidden_assumption_exposure", "controlled_concession", "burden_shift",
    "comparative_failure_analysis",
]

# --- Strategies ---

classification_strategy = st.builds(
    Classification,
    domain=st.sampled_from(VALID_DOMAINS),
    objection=st.sampled_from(VALID_OBJECTIONS),
    tone=st.sampled_from(VALID_TONES),
)

strategy_strategy = st.sampled_from(VALID_STRATEGIES)


# User messages that avoid triggering any mode keyword
# (no brevity, simplicity, or debate keywords)
safe_user_message = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z"), max_codepoint=127),
    min_size=0,
    max_size=60,
).filter(
    lambda m: not any(
        kw in m.lower()
        for kw in [
            "debate mode", "live debate", "hard rebuttal", "attack this argument",
            "20 words", "10 words", "15 words", "30 words",
            "one sentence", "short answer", "very short", "briefly",
            "simplify", "simple", "easy", "dumb it down", "easier",
        ]
    )
)

debate_turn_strategy = st.builds(
    DebateTurn,
    timestamp=st.text(min_size=1, max_size=20),
    user_message=st.text(min_size=1, max_size=40),
    domain=st.sampled_from(VALID_DOMAINS),
    objection=st.sampled_from(VALID_OBJECTIONS),
    tone=st.sampled_from(VALID_TONES),
    strategy=st.sampled_from(VALID_STRATEGIES),
    reply=st.text(min_size=1, max_size=60),
)


# --- Helpers ---

def _make_logger(turns=None, analogies=None, examples=None):
    """Create a DebateLogger pre-populated with optional data."""
    logger = DebateLogger()
    for t in (turns or []):
        logger.log_turn(t)
    for a in (analogies or []):
        logger.remember_analogy(a)
    for e in (examples or []):
        logger.remember_example(e)
    return logger


# ============================================================
# Property 8: Prompt contains all required sections
# ============================================================

class TestPromptContainsAllRequiredSections:
    """Property 8: Prompt contains all required sections.

    For any valid user message, Classification, Strategy, and DebateLogger
    state, the prompt returned by build_prompt shall contain: the persona
    text, the classification domain/objection/tone as metadata, the strategy
    instruction, the first 4 claims for the classified domain, the first 5
    analogies for the classified domain, the first 5 examples for the
    classified domain, rebuttals when the objection is not "general" and
    rebuttals exist, and the recent debate turns/analogies/examples from
    the logger.

    **Validates: Requirements 5.1, 5.6, 5.7, 5.8**
    """

    @given(
        user_message=safe_user_message,
        classification=classification_strategy,
        strategy=strategy_strategy,
        turns=st.lists(debate_turn_strategy, min_size=0, max_size=6),
        logged_analogies=st.lists(
            st.text(min_size=1, max_size=30), min_size=0, max_size=4
        ),
        logged_examples=st.lists(
            st.text(min_size=1, max_size=30), min_size=0, max_size=4
        ),
    )
    @settings(max_examples=100)
    def test_prompt_contains_all_sections(
        self,
        user_message,
        classification,
        strategy,
        turns,
        logged_analogies,
        logged_examples,
    ):
        logger = _make_logger(turns, logged_analogies, logged_examples)
        prompt = build_prompt(user_message, classification, strategy, logger)

        # 1. Persona text is present
        persona = get_persona("post-human")
        # Check a distinctive substring from the persona
        assert "AION" in prompt

        # 2. Classification metadata lines
        assert f"Current domain: {classification.domain}" in prompt
        assert f"Objection type: {classification.objection}" in prompt
        assert f"Tone of user: {classification.tone}" in prompt

        # 3. Strategy instruction
        instr = strategy_instruction(strategy)
        assert instr in prompt

        # 4. First 4 claims for the domain
        claims = get_claims(classification.domain)[:4]
        for claim in claims:
            assert claim in prompt

        # 5. First 5 analogies for the domain
        analogies = ANALOGY_BANK.get(classification.domain, [])[:5]
        for analogy in analogies:
            assert analogy in prompt

        # 6. First 5 examples for the domain
        examples = EXAMPLE_BANK.get(classification.domain, [])[:5]
        for example in examples:
            assert example in prompt

        # 7. Rebuttals when objection != "general" and rebuttals exist
        if classification.objection != "general":
            rebuttals = get_rebuttals(classification.domain, classification.objection)
            for rebuttal in rebuttals:
                assert rebuttal in prompt

        # 8. Recent debate turns from logger
        recent_turns = logger.get_recent_turns(4)
        for turn in recent_turns:
            assert turn.user_message in prompt
            assert turn.domain in prompt
            assert turn.strategy in prompt

        # 9. Recent analogies from logger
        recent_analogy_list = logger.get_recent_analogies(4)
        for a in recent_analogy_list:
            assert a in prompt

        # 10. Recent examples from logger
        recent_example_list = logger.get_recent_examples(4)
        for e in recent_example_list:
            assert e in prompt



# ============================================================
# Property 9: Response mode detection correctness
# ============================================================

# Mode keyword mappings: keyword -> expected mode
DEBATE_KEYWORDS = ["debate mode", "live debate", "hard rebuttal", "attack this argument"]
ULTRA_SHORT_KEYWORDS = [
    "20 words", "10 words", "15 words", "30 words",
    "one sentence", "short answer", "very short", "briefly",
]
SIMPLE_KEYWORDS = ["simplify", "simple", "easy", "dumb it down", "easier"]

# All mode keywords combined (for filtering "normal" messages)
ALL_MODE_KEYWORDS = DEBATE_KEYWORDS + ULTRA_SHORT_KEYWORDS + SIMPLE_KEYWORDS


class TestResponseModeDetectionCorrectness:
    """Property 9: Response mode detection correctness.

    For any message containing a mode-specific keyword, detect_response_mode
    shall return the correct mode. For messages with no mode keywords, mode
    shall be "normal".

    **Validates: Requirements 5.2, 5.3, 5.4, 5.5**
    """

    @given(
        keyword=st.sampled_from(DEBATE_KEYWORDS),
        padding=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z"), max_codepoint=127),
            min_size=0,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_debate_keywords_return_debate_mode(self, keyword, padding):
        """Messages containing debate keywords return 'debate' mode."""
        # Ensure padding doesn't accidentally contain other mode keywords
        message = padding + " " + keyword + " " + padding
        result = detect_response_mode(message)
        assert result == "debate", f"Expected 'debate' for keyword '{keyword}', got '{result}'"

    @given(
        keyword=st.sampled_from(ULTRA_SHORT_KEYWORDS),
        padding=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z"), max_codepoint=127),
            min_size=0,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_ultra_short_keywords_return_ultra_short_mode(self, keyword, padding):
        """Messages containing ultra_short keywords return 'ultra_short' mode."""
        # Filter out padding that contains debate keywords (higher priority)
        message = padding + " " + keyword + " " + padding
        lower_msg = message.lower()
        if any(dk in lower_msg for dk in DEBATE_KEYWORDS):
            return  # Skip: debate keywords take priority
        result = detect_response_mode(message)
        assert result == "ultra_short", (
            f"Expected 'ultra_short' for keyword '{keyword}', got '{result}'"
        )

    @given(
        keyword=st.sampled_from(SIMPLE_KEYWORDS),
        padding=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z"), max_codepoint=127),
            min_size=0,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_simple_keywords_return_simple_mode(self, keyword, padding):
        """Messages containing simple keywords return 'simple' mode."""
        message = padding + " " + keyword + " " + padding
        lower_msg = message.lower()
        # Filter out higher-priority keywords
        if any(dk in lower_msg for dk in DEBATE_KEYWORDS):
            return
        if any(uk in lower_msg for uk in ULTRA_SHORT_KEYWORDS):
            return
        result = detect_response_mode(message)
        assert result == "simple", (
            f"Expected 'simple' for keyword '{keyword}', got '{result}'"
        )

    @given(
        message=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z"), max_codepoint=127),
            min_size=0,
            max_size=60,
        ).filter(
            lambda m: not any(kw in m.lower() for kw in ALL_MODE_KEYWORDS)
        ),
    )
    @settings(max_examples=100)
    def test_no_keywords_return_normal_mode(self, message):
        """Messages with no mode keywords return 'normal' mode."""
        result = detect_response_mode(message)
        assert result == "normal", f"Expected 'normal', got '{result}' for message '{message}'"



# ============================================================
# Property 10: Prompt classification metadata round-trip
# ============================================================


class TestPromptClassificationMetadataRoundTrip:
    """Property 10: Prompt classification metadata round-trip.

    For any valid Classification and Strategy, building a prompt and then
    parsing the classification metadata lines (Current domain:, Objection
    type:, Tone of user:) shall recover the original values.

    **Validates: Requirements 5.9**
    """

    @given(
        classification=classification_strategy,
        strategy=strategy_strategy,
    )
    @settings(max_examples=100)
    def test_metadata_round_trip(self, classification, strategy):
        """Classification metadata can be parsed back from the built prompt."""
        logger = DebateLogger()
        prompt = build_prompt("test message", classification, strategy, logger)

        # Parse metadata lines from the prompt
        domain_match = re.search(r"Current domain: (.+)", prompt)
        objection_match = re.search(r"Objection type: (.+)", prompt)
        tone_match = re.search(r"Tone of user: (.+)", prompt)

        assert domain_match is not None, "Could not find 'Current domain:' in prompt"
        assert objection_match is not None, "Could not find 'Objection type:' in prompt"
        assert tone_match is not None, "Could not find 'Tone of user:' in prompt"

        parsed_domain = domain_match.group(1).strip()
        parsed_objection = objection_match.group(1).strip()
        parsed_tone = tone_match.group(1).strip()

        assert parsed_domain == classification.domain, (
            f"Domain mismatch: expected '{classification.domain}', got '{parsed_domain}'"
        )
        assert parsed_objection == classification.objection, (
            f"Objection mismatch: expected '{classification.objection}', got '{parsed_objection}'"
        )
        assert parsed_tone == classification.tone, (
            f"Tone mismatch: expected '{classification.tone}', got '{parsed_tone}'"
        )
