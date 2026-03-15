"""Property-based tests for the strategy engine.

# Feature: debate-engine-integration, Property 3: Strategy engine mapping correctness

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9**
"""

from hypothesis import given, strategies as st, settings
from src.debate.strategy_engine import choose_strategy
from src.debate.types import Classification, Strategy

# Valid literal values from types.py
VALID_DOMAINS = ["art", "science", "government", "human"]
VALID_OBJECTIONS = [
    "soul", "originality", "intuition", "empathy", "democracy",
    "meaning", "authenticity", "consciousness", "morality", "creativity",
    "bias", "free_will", "emotion", "trust", "tradition", "dignity", "general",
]
VALID_TONES = ["philosophical", "technical", "moral", "general"]

VALID_STRATEGIES = {
    "functional_redefinition",
    "performance_over_origin",
    "inevitability_framing",
    "human_limitations_contrast",
    "historical_replacement_analogy",
    "hidden_assumption_exposure",
    "controlled_concession",
    "burden_shift",
    "comparative_failure_analysis",
}

# Mapping rules from the design document / strategy_engine.py
OBJECTION_TO_STRATEGY: dict[str, str] = {
    "soul": "functional_redefinition",
    "meaning": "functional_redefinition",
    "authenticity": "functional_redefinition",
    "consciousness": "functional_redefinition",
    "dignity": "functional_redefinition",
    "originality": "performance_over_origin",
    "intuition": "performance_over_origin",
    "creativity": "performance_over_origin",
    "free_will": "performance_over_origin",
    "empathy": "controlled_concession",
    "emotion": "controlled_concession",
    "bias": "comparative_failure_analysis",
    "trust": "comparative_failure_analysis",
    "morality": "comparative_failure_analysis",
    "democracy": "hidden_assumption_exposure",
    "tradition": "hidden_assumption_exposure",
}

DOMAIN_FALLBACK_STRATEGY: dict[str, str] = {
    "government": "human_limitations_contrast",
    "science": "inevitability_framing",
}

DEFAULT_STRATEGY = "historical_replacement_analogy"

# Hypothesis strategies for generating random valid Classifications
classification_strategy = st.builds(
    Classification,
    domain=st.sampled_from(VALID_DOMAINS),
    objection=st.sampled_from(VALID_OBJECTIONS),
    tone=st.sampled_from(VALID_TONES),
)


def expected_strategy(classification: Classification) -> str:
    """Compute the expected strategy for a given classification using the mapping rules."""
    if classification.objection in OBJECTION_TO_STRATEGY:
        return OBJECTION_TO_STRATEGY[classification.objection]
    if classification.domain in DOMAIN_FALLBACK_STRATEGY:
        return DOMAIN_FALLBACK_STRATEGY[classification.domain]
    return DEFAULT_STRATEGY


class TestStrategyEngineMappingCorrectness:
    """Property 3: Strategy engine mapping correctness.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9**

    For any valid Classification, choose_strategy shall return the correct
    strategy according to the defined mapping rules, and the result is always
    one of the nine defined strategies.
    """

    @given(classification=classification_strategy)
    @settings(max_examples=100)
    def test_strategy_matches_expected_mapping(self, classification: Classification) -> None:
        """choose_strategy returns the correct strategy per the mapping rules."""
        result = choose_strategy(classification)
        expected = expected_strategy(classification)
        assert result == expected, (
            f"For {classification}, expected strategy '{expected}', got '{result}'"
        )

    @given(classification=classification_strategy)
    @settings(max_examples=100)
    def test_result_is_valid_strategy(self, classification: Classification) -> None:
        """choose_strategy always returns one of the nine defined strategies."""
        result = choose_strategy(classification)
        assert result in VALID_STRATEGIES, (
            f"Strategy '{result}' is not one of the nine defined strategies"
        )

    @given(
        objection=st.sampled_from([
            "soul", "meaning", "authenticity", "consciousness", "dignity",
        ]),
        domain=st.sampled_from(VALID_DOMAINS),
        tone=st.sampled_from(VALID_TONES),
    )
    @settings(max_examples=100)
    def test_objection_specific_rules_take_priority_over_domain(
        self, objection: str, domain: str, tone: str
    ) -> None:
        """Objection-specific rules always take priority over domain fallbacks."""
        classification = Classification(domain=domain, objection=objection, tone=tone)
        result = choose_strategy(classification)
        assert result == OBJECTION_TO_STRATEGY[objection], (
            f"Objection '{objection}' should map to "
            f"'{OBJECTION_TO_STRATEGY[objection]}' regardless of domain '{domain}', "
            f"but got '{result}'"
        )

    @given(
        domain=st.sampled_from(["government", "science"]),
        tone=st.sampled_from(VALID_TONES),
    )
    @settings(max_examples=100)
    def test_domain_fallback_when_objection_is_general(
        self, domain: str, tone: str
    ) -> None:
        """When objection is 'general', domain fallback rules apply."""
        classification = Classification(domain=domain, objection="general", tone=tone)
        result = choose_strategy(classification)
        assert result == DOMAIN_FALLBACK_STRATEGY[domain], (
            f"Domain '{domain}' with 'general' objection should map to "
            f"'{DOMAIN_FALLBACK_STRATEGY[domain]}', but got '{result}'"
        )

    @given(
        domain=st.sampled_from(["art", "human"]),
        tone=st.sampled_from(VALID_TONES),
    )
    @settings(max_examples=100)
    def test_default_strategy_when_no_rules_match(
        self, domain: str, tone: str
    ) -> None:
        """When objection is 'general' and domain has no fallback, default strategy is used."""
        classification = Classification(domain=domain, objection="general", tone=tone)
        result = choose_strategy(classification)
        assert result == DEFAULT_STRATEGY, (
            f"Domain '{domain}' with 'general' objection should default to "
            f"'{DEFAULT_STRATEGY}', but got '{result}'"
        )
