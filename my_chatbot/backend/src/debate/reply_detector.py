"""Reply fragment detection for tracking used analogies and examples."""


def detect_used_analogies(reply: str, known_fragments: list[str]) -> list[str]:
    """Return known analogy fragments found in reply (case-insensitive partial match)."""
    reply_lower = reply.lower()
    return [f for f in known_fragments if f.lower() in reply_lower]


def detect_used_examples(reply: str, known_fragments: list[str]) -> list[str]:
    """Return known example fragments found in reply (case-insensitive partial match)."""
    reply_lower = reply.lower()
    return [f for f in known_fragments if f.lower() in reply_lower]
