"""Debate engine package for AION chatbot.

Public API: DebateEngine facade class that orchestrates the full
classify → strategy → prompt pipeline and tracks debate history.

Requirements: 7.1, 7.2, 8.1, 8.2, 8.3, 8.4, 9.1, 9.2, 9.3, 9.4
"""

import logging
from datetime import datetime

from .types import DebateTurn
from .classifier import classify_message
from .strategy_engine import choose_strategy
from .prompt_builder import build_prompt
from .debate_logger import DebateLogger
from .analogy_bank import ANALOGY_BANK
from .example_bank import EXAMPLE_BANK
from .reply_detector import detect_used_analogies, detect_used_examples

logger = logging.getLogger(__name__)

VALID_POSITIONS = ("post-human", "humanist")


class DebateEngineError(Exception):
    """Raised when the debate engine encounters an unrecoverable error."""


class DebateEngine:
    """Facade that orchestrates the full debate pipeline.

    Usage:
        engine = DebateEngine(position="post-human")
        prompt = engine.build_debate_prompt(user_message)
        # ... send prompt to LLM, get reply ...
        engine.log_reply(user_message, reply)
    """

    def __init__(self, position: str = "post-human") -> None:
        if position not in VALID_POSITIONS:
            logger.info(
                "Invalid debate position %r, defaulting to 'post-human'", position
            )
            position = "post-human"
        self.position = position
        self.logger = DebateLogger()
        self._last_classification = None
        self._last_strategy = None

    def build_debate_prompt(self, user_message: str) -> str:
        """Classify the message, choose a strategy, and build the LLM prompt.

        Stores the classification and strategy for use in :meth:`log_reply`.

        Raises:
            DebateEngineError: If any pipeline step fails.
        """
        try:
            classification = classify_message(user_message)
            strategy = choose_strategy(classification)
            prompt = build_prompt(
                user_message, classification, strategy, self.logger, self.position
            )
            self._last_classification = classification
            self._last_strategy = strategy
            return prompt
        except Exception as exc:
            raise DebateEngineError(str(exc)) from exc

    def log_reply(self, user_message: str, reply: str) -> None:
        """Log a completed debate turn and remember detected analogies/examples.

        Uses the classification and strategy stored by the most recent
        :meth:`build_debate_prompt` call.
        """
        classification = self._last_classification
        strategy = self._last_strategy

        if classification is None or strategy is None:
            logger.warning("log_reply called before build_debate_prompt; skipping.")
            return

        turn = DebateTurn(
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            domain=classification.domain,
            objection=classification.objection,
            tone=classification.tone,
            strategy=strategy,
            reply=reply,
        )
        self.logger.log_turn(turn)

        # Detect and remember used analogies
        known_analogies = ANALOGY_BANK.get(classification.domain, [])
        for analogy in detect_used_analogies(reply, known_analogies):
            self.logger.remember_analogy(analogy)

        # Detect and remember used examples
        known_examples = EXAMPLE_BANK.get(classification.domain, [])
        for example in detect_used_examples(reply, known_examples):
            self.logger.remember_example(example)
