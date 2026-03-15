"""Debate history tracker with bounded FIFO lists.

Tracks recent debate turns, used analogies, and used examples
to avoid repetition in prompt building.

Ported from TypeScript debateLogger.ts.
"""

from .types import DebateTurn

MAX_TURNS = 50
MAX_ANALOGIES = 8
MAX_EXAMPLES = 8


class DebateLogger:
    """Tracks recent debate turns, used analogies, and used examples.

    Bounded FIFO lists: 50 turns max, 8 analogies max, 8 examples max.
    """

    def __init__(self) -> None:
        self._turns: list[DebateTurn] = []
        self._analogies: list[str] = []
        self._examples: list[str] = []

    def log_turn(self, turn: DebateTurn) -> None:
        """Store a debate turn, evicting the oldest if over capacity."""
        self._turns.append(turn)
        if len(self._turns) > MAX_TURNS:
            self._turns.pop(0)

    def get_recent_turns(self, limit: int = 5) -> list[DebateTurn]:
        """Return the most recent turns up to *limit*, in chronological order."""
        return self._turns[-limit:]

    def remember_analogy(self, analogy: str) -> None:
        """Store a used analogy string. Empty strings are ignored."""
        if not analogy:
            return
        self._analogies.append(analogy)
        if len(self._analogies) > MAX_ANALOGIES:
            self._analogies.pop(0)

    def get_recent_analogies(self, limit: int = 4) -> list[str]:
        """Return the most recent analogies up to *limit*."""
        return self._analogies[-limit:]

    def remember_example(self, example: str) -> None:
        """Store a used example string. Empty strings are ignored."""
        if not example:
            return
        self._examples.append(example)
        if len(self._examples) > MAX_EXAMPLES:
            self._examples.pop(0)

    def get_recent_examples(self, limit: int = 4) -> list[str]:
        """Return the most recent examples up to *limit*."""
        return self._examples[-limit:]
