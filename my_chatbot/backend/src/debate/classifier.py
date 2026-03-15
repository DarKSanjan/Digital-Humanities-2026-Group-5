"""Message classifier for the debate engine.

Ported from TypeScript classifier.ts. Keyword-based classification
with objection-specific domain overrides.
"""

from .types import Classification, Domain, Objection, Tone

# Domain keyword lists — checked in order: art, science, government, human
_ART_WORDS = [
    "art", "artist", "artists", "creative", "creativity",
    "music", "poem", "painting", "story", "film", "movie",
]
_SCIENCE_WORDS = [
    "science", "scientist", "research", "discovery", "lab",
    "theorem", "experiment", "scientific", "intuition",
]
_GOVERNMENT_WORDS = [
    "government", "governance", "policy", "democracy", "state",
    "leader", "leadership", "public", "election", "bureaucracy",
]
_HUMAN_WORDS = [
    "human", "humanity", "meaning", "authentic", "conscious",
    "emotion", "dignity", "soul", "free will",
]


def _has_any(text: str, words: list[str]) -> bool:
    """Return True if text contains any of the given words."""
    return any(word in text for word in words)


def classify_message(message: str) -> Classification:
    """Classify user message by domain, objection type, and tone.

    Port of TypeScript classifyMessage(). Keyword-based classification
    with objection-specific domain overrides.
    """
    text = message.lower()

    # Step 1: Determine domain from keywords (checked in order)
    domain: Domain = "human"
    if _has_any(text, _ART_WORDS):
        domain = "art"
    elif _has_any(text, _SCIENCE_WORDS):
        domain = "science"
    elif _has_any(text, _GOVERNMENT_WORDS):
        domain = "government"
    elif _has_any(text, _HUMAN_WORDS):
        domain = "human"

    # Step 2: Check objection keywords with domain overrides
    if "soul" in text:
        return Classification(
            domain="art" if domain == "human" else domain,
            objection="soul",
            tone="philosophical",
        )

    if "original" in text or "originality" in text:
        return Classification(
            domain="art" if domain == "human" else domain,
            objection="originality",
            tone="philosophical",
        )

    if "intuition" in text:
        return Classification(domain="science", objection="intuition", tone="technical")

    if "empathy" in text:
        return Classification(domain="government", objection="empathy", tone="moral")

    if "democracy" in text or "democratic" in text:
        return Classification(domain="government", objection="democracy", tone="moral")

    if "meaning" in text:
        return Classification(domain="human", objection="meaning", tone="philosophical")

    if "authentic" in text:
        return Classification(
            domain="art" if domain == "human" else domain,
            objection="authenticity",
            tone="philosophical",
        )

    if "conscious" in text:
        return Classification(
            domain="human", objection="consciousness", tone="philosophical"
        )

    if "moral" in text or "ethic" in text:
        return Classification(domain=domain, objection="morality", tone="moral")

    if "creativity" in text or "creative genius" in text:
        return Classification(domain="art", objection="creativity", tone="philosophical")

    if "bias" in text or "biased" in text:
        return Classification(
            domain="government" if domain == "human" else domain,
            objection="bias",
            tone="moral",
        )

    if "free will" in text:
        return Classification(
            domain="human", objection="free_will", tone="philosophical"
        )

    if "emotion" in text or "feel" in text:
        return Classification(
            domain="art" if domain == "art" else "human",
            objection="emotion",
            tone="philosophical",
        )

    if "trust" in text:
        return Classification(
            domain="government" if domain == "human" else domain,
            objection="trust",
            tone="moral",
        )

    if "tradition" in text or "traditional" in text:
        return Classification(domain=domain, objection="tradition", tone="general")

    if "dignity" in text:
        return Classification(domain="human", objection="dignity", tone="moral")

    # Step 3: No objection matched — assign tone based on domain
    tone: Tone
    if domain == "science":
        tone = "technical"
    elif domain == "government":
        tone = "moral"
    elif domain == "art":
        tone = "philosophical"
    else:
        tone = "general"

    return Classification(domain=domain, objection="general", tone=tone)
