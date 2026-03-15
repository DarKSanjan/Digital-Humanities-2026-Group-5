"""Integration tests for the full debate pipeline with mocked LLM.

Tests the classify → strategy → prompt → (mocked) LLM → log_reply flow,
fallback on debate engine failure, position switching, and analogy/example
detection in replies.

**Validates: Requirements 7.1, 7.3, 8.1, 8.2, 10.6**
"""

import unittest
from unittest.mock import patch

from src.debate import DebateEngine, DebateEngineError


class TestFullDebatePipeline(unittest.TestCase):
    """Test the full classify → strategy → prompt → LLM → log_reply flow."""

    def test_build_prompt_contains_expected_sections(self):
        """Build a debate prompt and verify it contains persona, classification
        metadata, and strategy instruction sections."""
        engine = DebateEngine(position="post-human")
        prompt = engine.build_debate_prompt("Art has a soul that machines cannot replicate")

        # Persona section
        self.assertIn("AION", prompt)

        # Classification metadata
        self.assertIn("Current domain:", prompt)
        self.assertIn("Objection type:", prompt)
        self.assertIn("Tone of user:", prompt)
        self.assertIn("Debate strategy:", prompt)

        # Strategy instruction
        self.assertIn("Strategy instruction:", prompt)

        # Argument sections
        self.assertIn("Relevant post-human claims:", prompt)
        self.assertIn("Relevant rebuttals:", prompt)
        self.assertIn("Possible analogies:", prompt)
        self.assertIn("Possible concrete examples:", prompt)

        # User message echoed
        self.assertIn("Art has a soul that machines cannot replicate", prompt)

    def test_log_reply_stores_turn(self):
        """After build_debate_prompt + log_reply, the logger should contain the turn."""
        engine = DebateEngine(position="post-human")
        user_msg = "Can machines really create art with soul?"
        engine.build_debate_prompt(user_msg)

        simulated_reply = "Machines redefine what soul means in functional terms."
        engine.log_reply(user_msg, simulated_reply)

        recent = engine.logger.get_recent_turns(1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].user_message, user_msg)
        self.assertEqual(recent[0].reply, simulated_reply)

    def test_full_round_trip(self):
        """Full round-trip: build prompt, simulate LLM reply, log it, verify state."""
        engine = DebateEngine(position="post-human")
        user_msg = "Science requires human intuition"
        prompt = engine.build_debate_prompt(user_msg)

        # Prompt should reference science domain
        self.assertIn("science", prompt.lower())

        llm_reply = "Machine learning systems have accelerated protein structure prediction."
        engine.log_reply(user_msg, llm_reply)

        turns = engine.logger.get_recent_turns(5)
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].domain, "science")
        self.assertEqual(turns[0].strategy, "performance_over_origin")


class TestFallbackOnDebateEngineFailure(unittest.TestCase):
    """Test that DebateEngineError is raised when classify_message fails."""

    def test_classify_failure_raises_debate_engine_error(self):
        """When classify_message raises, build_debate_prompt should raise DebateEngineError."""
        engine = DebateEngine(position="post-human")

        with patch("src.debate.classify_message", side_effect=RuntimeError("classifier broke")):
            with self.assertRaises(DebateEngineError) as ctx:
                engine.build_debate_prompt("anything")

        self.assertIn("classifier broke", str(ctx.exception))

    def test_strategy_failure_raises_debate_engine_error(self):
        """When choose_strategy raises, build_debate_prompt should raise DebateEngineError."""
        engine = DebateEngine(position="post-human")

        with patch("src.debate.choose_strategy", side_effect=ValueError("strategy error")):
            with self.assertRaises(DebateEngineError):
                engine.build_debate_prompt("test message")


class TestPositionSwitching(unittest.TestCase):
    """Test position switching between post-human and humanist."""

    def test_post_human_uses_aion_persona(self):
        engine = DebateEngine(position="post-human")
        prompt = engine.build_debate_prompt("Tell me about art")
        self.assertIn("AION", prompt)

    def test_humanist_uses_huma_persona(self):
        engine = DebateEngine(position="humanist")
        prompt = engine.build_debate_prompt("Tell me about art")
        self.assertIn("HUMA", prompt)

    def test_invalid_position_defaults_to_post_human(self):
        engine = DebateEngine(position="invalid-position")
        self.assertEqual(engine.position, "post-human")
        prompt = engine.build_debate_prompt("Tell me about art")
        self.assertIn("AION", prompt)


class TestLogReplyDetectsAnalogiesAndExamples(unittest.TestCase):
    """Test that log_reply detects and remembers analogies/examples from the reply."""

    def test_detects_known_analogy_in_reply(self):
        engine = DebateEngine(position="post-human")
        user_msg = "Art has a soul"
        engine.build_debate_prompt(user_msg)

        # Use a known analogy from the art domain
        reply = "Photography did not eliminate art; it redefined artistic value. Machines do the same."
        engine.log_reply(user_msg, reply)

        recent_analogies = engine.logger.get_recent_analogies(4)
        self.assertTrue(len(recent_analogies) > 0)
        self.assertTrue(
            any("Photography did not eliminate art" in a for a in recent_analogies)
        )

    def test_detects_known_example_in_reply(self):
        engine = DebateEngine(position="post-human")
        user_msg = "Science needs human intuition"
        engine.build_debate_prompt(user_msg)

        # Use a known example from the science domain
        reply = "Machine learning systems have accelerated protein structure prediction."
        engine.log_reply(user_msg, reply)

        recent_examples = engine.logger.get_recent_examples(4)
        self.assertTrue(len(recent_examples) > 0)
        self.assertTrue(
            any("protein structure prediction" in e.lower() for e in recent_examples)
        )

    def test_no_detection_when_reply_has_no_known_fragments(self):
        engine = DebateEngine(position="post-human")
        user_msg = "Art has a soul"
        engine.build_debate_prompt(user_msg)

        reply = "This is a completely original reply with no known fragments."
        engine.log_reply(user_msg, reply)

        self.assertEqual(len(engine.logger.get_recent_analogies(4)), 0)
        self.assertEqual(len(engine.logger.get_recent_examples(4)), 0)


if __name__ == "__main__":
    unittest.main()
