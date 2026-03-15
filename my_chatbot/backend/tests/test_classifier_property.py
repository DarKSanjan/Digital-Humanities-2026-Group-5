"""Property-based tests for the message classifier.

# Feature: debate-engine-integration, Property 1: Classifier output structural validity
# Feature: debate-engine-integration, Property 2: Classifier keyword correctness

**Validates: Requirements 1.1, 1.2, 1.3**
"""

from hypothesis import given, strategies as st, settings
from src.debate.classifier import classify_message
from src.debate.types import Classification

VALID_DOMAINS = {"art", "science", "government", "human"}
VALID_OBJECTIONS = {
    "soul", "originality", "intuition", "empathy", "democracy",
    "meaning", "authenticity", "consciousness", "morality", "creativity",
    "bias", "free_will", "emotion", "trust", "tradition", "dignity", "general",
}
VALID_TONES = {"philosophical", "technical", "moral", "general"}

# ---------------------------------------------------------------------------
# Domain keyword mapping: keyword -> expected domain
# ---------------------------------------------------------------------------
DOMAIN_KEYWORDS: dict[str, str] = {
    "art": "art",
    "artist": "art",
    "artists": "art",
    "music": "art",
    "poem": "art",
    "painting": "art",
    "story": "art",
    "film": "art",
    "movie": "art",
    "science": "science",
    "scientist": "science",
    "research": "science",
    "discovery": "science",
    "lab": "science",
    "theorem": "science",
    "experiment": "science",
    "scientific": "science",
}

GOVERNMENT_DOMAIN_KEYWORDS: dict[str, str] = {
    "government": "government",
    "governance": "government",
    "policy": "government",
    "election": "government",
    "bureaucracy": "government",
    "leadership": "government",
    "leader": "government",
}

# ---------------------------------------------------------------------------
# Objection keyword mapping: keyword -> (expected_objection, domain_override_fn)
# domain_override_fn takes the default domain and returns the expected domain.
# ---------------------------------------------------------------------------
# Each entry: keyword -> (objection, callable(default_domain) -> expected_domain)
OBJECTION_KEYWORDS: dict[str, tuple[str, object]] = {
    "soul": ("soul", lambda d: "art" if d == "human" else d),
    "original": ("originality", lambda d: "art" if d == "human" else d),
    "originality": ("originality", lambda d: "art" if d == "human" else d),
    "intuition": ("intuition", lambda _: "science"),
    "empathy": ("empathy", lambda _: "government"),
    "democracy": ("democracy", lambda _: "government"),
    "democratic": ("democracy", lambda _: "government"),
    "meaning": ("meaning", lambda _: "human"),
    "authentic": ("authenticity", lambda d: "art" if d == "human" else d),
    "conscious": ("consciousness", lambda _: "human"),
    "moral": ("morality", lambda d: d),
    "ethic": ("morality", lambda d: d),
    "bias": ("bias", lambda d: "government" if d == "human" else d),
    "biased": ("bias", lambda d: "government" if d == "human" else d),
    "free will": ("free_will", lambda _: "human"),
    "tradition": ("tradition", lambda d: d),
    "traditional": ("tradition", lambda d: d),
    "dignity": ("dignity", lambda _: "human"),
    "trust": ("trust", lambda d: "government" if d == "human" else d),
}

# Strategies for Hypothesis
domain_keyword_strategy = st.sampled_from(list(DOMAIN_KEYWORDS.keys()))
objection_keyword_strategy = st.sampled_from(list(OBJECTION_KEYWORDS.keys()))
government_keyword_strategy = st.sampled_from(list(GOVERNMENT_DOMAIN_KEYWORDS.keys()))


class TestClassifierOutputStructuralValidity:
    """Property 1: Classifier output structural validity.

    **Validates: Requirements 1.1**

    For any input string (including empty strings, unicode, and arbitrary text),
    classify_message shall return a Classification where domain is one of the
    four valid domains, objection is one of the 17 defined types or "general",
    and tone is one of the four valid tones.
    """

    @given(message=st.text())
    @settings(max_examples=100)
    def test_returns_classification_with_valid_fields(self, message: str) -> None:
        result = classify_message(message)
        assert isinstance(result, Classification)
        assert result.domain in VALID_DOMAINS, (
            f"domain '{result.domain}' not in {VALID_DOMAINS}"
        )
        assert result.objection in VALID_OBJECTIONS, (
            f"objection '{result.objection}' not in {VALID_OBJECTIONS}"
        )
        assert result.tone in VALID_TONES, (
            f"tone '{result.tone}' not in {VALID_TONES}"
        )

    @given(message=st.from_regex(r"[\u0000-\uffff]{0,50}", fullmatch=True))
    @settings(max_examples=100)
    def test_unicode_input_returns_valid_classification(self, message: str) -> None:
        result = classify_message(message)
        assert isinstance(result, Classification)
        assert result.domain in VALID_DOMAINS
        assert result.objection in VALID_OBJECTIONS
        assert result.tone in VALID_TONES

    @settings(max_examples=100)
    @given(message=st.just(""))
    def test_empty_string_returns_valid_classification(self, message: str) -> None:
        result = classify_message(message)
        assert isinstance(result, Classification)
        assert result.domain in VALID_DOMAINS
        assert result.objection in VALID_OBJECTIONS
        assert result.tone in VALID_TONES


class TestClassifierKeywordCorrectness:
    """Property 2: Classifier keyword correctness.

    **Validates: Requirements 1.2, 1.3**

    For any message containing a recognized keyword, the classifier shall
    assign the corresponding domain and/or objection type, including domain
    overrides where the TypeScript logic specifies them.
    """

    @given(
        keyword=domain_keyword_strategy,
        prefix=st.text(max_size=20),
        suffix=st.text(max_size=20),
    )
    @settings(max_examples=100)
    def test_domain_keyword_assigns_correct_domain(
        self, keyword: str, prefix: str, suffix: str
    ) -> None:
        """Messages containing a domain keyword get the correct domain assigned."""
        # Build a message with the keyword surrounded by random text.
        # Use spaces to ensure the keyword is a standalone token in the text.
        message = f"{prefix} {keyword} {suffix}"
        result = classify_message(message)

        expected_domain = DOMAIN_KEYWORDS[keyword]

        # The domain keyword should be detected. However, if an objection
        # keyword also appears in the random prefix/suffix, the objection
        # handler may override the domain. We only assert domain when no
        # objection keyword accidentally appears.
        lower_msg = message.lower()
        has_objection_keyword = any(
            ok in lower_msg for ok in OBJECTION_KEYWORDS
        )
        if not has_objection_keyword:
            assert result.domain == expected_domain, (
                f"For keyword '{keyword}' expected domain '{expected_domain}', "
                f"got '{result.domain}' (message: {message!r})"
            )

    @given(
        keyword=objection_keyword_strategy,
        prefix=st.text(max_size=20),
        suffix=st.text(max_size=20),
    )
    @settings(max_examples=100)
    def test_objection_keyword_assigns_correct_objection(
        self, keyword: str, prefix: str, suffix: str
    ) -> None:
        """Messages containing an objection keyword get the correct objection assigned."""
        message = f"{prefix} {keyword} {suffix}"
        result = classify_message(message)

        expected_objection, _ = OBJECTION_KEYWORDS[keyword]

        # Check that the expected objection is assigned. If a higher-priority
        # objection keyword also appears in the random text, it may take
        # precedence. We check that the result is either our expected
        # objection or another valid objection from a higher-priority keyword.
        objection_priority = list(OBJECTION_KEYWORDS.keys())
        lower_msg = message.lower()

        # Find the first objection keyword that appears in the message
        first_match = None
        for ok in objection_priority:
            if ok in lower_msg:
                first_match = ok
                break

        if first_match == keyword:
            assert result.objection == expected_objection, (
                f"For keyword '{keyword}' expected objection '{expected_objection}', "
                f"got '{result.objection}' (message: {message!r})"
            )

    @given(
        keyword=objection_keyword_strategy,
    )
    @settings(max_examples=100)
    def test_objection_keyword_domain_override(self, keyword: str) -> None:
        """Objection keywords apply the correct domain override."""
        # Use a clean message with only the objection keyword to avoid
        # interference from random text containing other keywords.
        message = f"I think about {keyword} a lot"
        result = classify_message(message)

        expected_objection, domain_override_fn = OBJECTION_KEYWORDS[keyword]

        # Determine what the default domain would be without the objection
        # by checking domain keywords in the message
        lower_msg = message.lower()
        default_domain = "human"
        art_words = [
            "art", "artist", "artists", "creative", "creativity",
            "music", "poem", "painting", "story", "film", "movie",
        ]
        science_words = [
            "science", "scientist", "research", "discovery", "lab",
            "theorem", "experiment", "scientific", "intuition",
        ]
        gov_words = [
            "government", "governance", "policy", "democracy", "state",
            "leader", "leadership", "public", "election", "bureaucracy",
        ]
        human_words = [
            "human", "humanity", "meaning", "authentic", "conscious",
            "emotion", "dignity", "soul", "free will",
        ]
        if any(w in lower_msg for w in art_words):
            default_domain = "art"
        elif any(w in lower_msg for w in science_words):
            default_domain = "science"
        elif any(w in lower_msg for w in gov_words):
            default_domain = "government"
        elif any(w in lower_msg for w in human_words):
            default_domain = "human"

        expected_domain = domain_override_fn(default_domain)

        # Only check if our keyword is the first objection keyword matched
        objection_priority = list(OBJECTION_KEYWORDS.keys())
        first_match = None
        for ok in objection_priority:
            if ok in lower_msg:
                first_match = ok
                break

        if first_match == keyword:
            assert result.objection == expected_objection, (
                f"For keyword '{keyword}' expected objection '{expected_objection}', "
                f"got '{result.objection}'"
            )
            assert result.domain == expected_domain, (
                f"For keyword '{keyword}' with default domain '{default_domain}', "
                f"expected domain override to '{expected_domain}', "
                f"got '{result.domain}'"
            )
