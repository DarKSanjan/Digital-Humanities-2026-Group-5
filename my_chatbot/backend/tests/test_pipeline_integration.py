"""Integration tests for the full streaming pipeline flow.

Mocks external services (OpenAI, ElevenLabs, AudioPlayer) and verifies
the end-to-end pipeline: user input → LLM stream → sentence chunking →
TTS → audio playback → lip sync callbacks.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.audio_player import AudioPlayer
from src.llm_service import LLMServiceError
from src.streaming_pipeline import (
    ChatMessage,
    StreamingPipeline,
    TranscriptEntry,
)
from src.tts_service import PhonemeData, TTSServiceError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fake_token_stream(tokens: list[str]):
    """Async generator that yields tokens one at a time."""
    for t in tokens:
        yield t


def _build_pipeline(
    *,
    on_lip_sync_start=None,
    on_lip_sync_end=None,
    system_prompt=None,
) -> tuple[StreamingPipeline, MagicMock]:
    """Create a pipeline with a mocked AudioPlayer that fires callbacks instantly."""
    player = MagicMock(spec=AudioPlayer)
    player.is_playing = False

    def _instant_play(audio_data, on_start=None, on_end=None):
        if on_start:
            on_start()
        if on_end:
            on_end()

    player.play.side_effect = _instant_play

    pipeline = StreamingPipeline(
        audio_player=player,
        on_lip_sync_start=on_lip_sync_start,
        on_lip_sync_end=on_lip_sync_end,
        system_prompt=system_prompt,
    )
    return pipeline, player


# ---------------------------------------------------------------------------
# Full pipeline flow
# ---------------------------------------------------------------------------


class TestFullPipelineFlow:
    """End-to-end pipeline: user input → LLM → chunker → TTS → playback → lip sync."""

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_multi_sentence_response_flows_through_entire_pipeline(
        self, mock_chat, mock_tts
    ):
        """Multi-sentence LLM response triggers TTS and playback for each chunk."""
        # LLM returns tokens that form two sentences
        mock_chat.return_value = _fake_token_stream(
            ["Hello ", "there.", " How ", "are ", "you?"]
        )

        phonemes_1 = [PhonemeData(phoneme="HH", start=0.0, duration=0.05)]
        phonemes_2 = [PhonemeData(phoneme="AW", start=0.0, duration=0.06)]

        mock_tts.side_effect = [
            (b"\x00\x00" * 80, phonemes_1),
            (b"\x00\x00" * 80, phonemes_2),
        ]

        lip_start = MagicMock()
        lip_end = MagicMock()
        pipeline, player = _build_pipeline(
            on_lip_sync_start=lip_start,
            on_lip_sync_end=lip_end,
        )

        await pipeline.process_user_input("Hi")

        # TTS called once per sentence chunk
        assert mock_tts.call_count == 2
        # Audio played for each chunk
        assert player.play.call_count == 2
        # Lip sync fired for each chunk
        assert lip_start.call_count == 2
        assert lip_end.call_count == 2

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_pipeline_passes_correct_text_to_tts(self, mock_chat, mock_tts):
        """Verify the chunker splits correctly and TTS receives proper text."""
        mock_chat.return_value = _fake_token_stream(["First.", " Second."])
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        pipeline, _ = _build_pipeline()
        await pipeline.process_user_input("Go")

        tts_texts = [c.args[0] for c in mock_tts.call_args_list]
        assert tts_texts == ["First.", " Second."]


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------


class TestConversationHistory:
    """Verify conversation history is correctly maintained across turns."""

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_history_maintained_across_multiple_turns(
        self, mock_chat, mock_tts
    ):
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        pipeline, _ = _build_pipeline(system_prompt="Be helpful.")

        # Turn 1
        mock_chat.return_value = _fake_token_stream(["Reply one."])
        await pipeline.process_user_input("Hello")

        # Turn 2
        mock_chat.return_value = _fake_token_stream(["Reply two."])
        await pipeline.process_user_input("Thanks")

        history = pipeline.history
        assert len(history) == 5  # system + user + assistant + user + assistant
        assert history[0] == ChatMessage(role="system", content="Be helpful.")
        assert history[1] == ChatMessage(role="user", content="Hello")
        assert history[2].role == "assistant"
        assert "Reply one." in history[2].content
        assert history[3] == ChatMessage(role="user", content="Thanks")
        assert history[4].role == "assistant"
        assert "Reply two." in history[4].content

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_history_sent_to_llm_includes_all_prior_messages(
        self, mock_chat, mock_tts
    ):
        """Second LLM call should receive full conversation history."""
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        pipeline, _ = _build_pipeline()

        # Turn 1
        mock_chat.return_value = _fake_token_stream(["Hi."])
        await pipeline.process_user_input("Hey")

        # Turn 2
        mock_chat.return_value = _fake_token_stream(["Sure."])
        await pipeline.process_user_input("Help me")

        # The second call should include all 3 prior messages
        second_call_messages = mock_chat.call_args_list[1].args[0]
        assert len(second_call_messages) == 3
        assert second_call_messages[0]["role"] == "user"
        assert second_call_messages[0]["content"] == "Hey"
        assert second_call_messages[1]["role"] == "assistant"
        assert second_call_messages[2]["role"] == "user"
        assert second_call_messages[2]["content"] == "Help me"


# ---------------------------------------------------------------------------
# Session state transitions
# ---------------------------------------------------------------------------


class TestSessionStateTransitions:
    """Verify session state transitions: idle → processing → speaking → idle."""

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_state_transitions_through_full_flow(self, mock_chat, mock_tts):
        """Track state changes during a successful pipeline run."""
        states_observed: list[str] = []

        mock_chat.return_value = _fake_token_stream(["Done."])
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        player = MagicMock(spec=AudioPlayer)
        player.is_playing = False

        def _play_tracking(audio_data, on_start=None, on_end=None):
            # Before on_start, status should be 'processing'
            states_observed.append(pipeline.session.status)
            if on_start:
                on_start()
            # After on_start, status should be 'speaking'
            states_observed.append(pipeline.session.status)
            if on_end:
                on_end()

        player.play.side_effect = _play_tracking

        pipeline = StreamingPipeline(audio_player=player)

        assert pipeline.session.status == "idle"
        await pipeline.process_user_input("Go")

        # During playback: processing → speaking, then back to idle
        assert "processing" in states_observed
        assert "speaking" in states_observed
        assert pipeline.session.status == "idle"

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_state_returns_to_idle_after_success(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["OK."])
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        pipeline, _ = _build_pipeline()
        await pipeline.process_user_input("Test")

        assert pipeline.session.status == "idle"
        assert pipeline.session.error is None


# ---------------------------------------------------------------------------
# Transcript updates
# ---------------------------------------------------------------------------


class TestTranscriptUpdates:
    """Verify transcript is updated with both user and assistant messages."""

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_transcript_contains_user_and_assistant(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["World."])
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        pipeline, _ = _build_pipeline()
        await pipeline.process_user_input("Hello")

        transcript = pipeline.session.transcript
        assert len(transcript) == 2
        assert transcript[0] == TranscriptEntry(role="user", content="Hello")
        assert transcript[1].role == "assistant"
        assert "World." in transcript[1].content

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_transcript_accumulates_across_turns(self, mock_chat, mock_tts):
        mock_tts.return_value = (b"\x00\x00" * 80, [])
        pipeline, _ = _build_pipeline()

        mock_chat.return_value = _fake_token_stream(["A."])
        await pipeline.process_user_input("One")

        mock_chat.return_value = _fake_token_stream(["B."])
        await pipeline.process_user_input("Two")

        transcript = pipeline.session.transcript
        assert len(transcript) == 4
        assert transcript[0].role == "user"
        assert transcript[1].role == "assistant"
        assert transcript[2].role == "user"
        assert transcript[3].role == "assistant"


# ---------------------------------------------------------------------------
# Error recovery
# ---------------------------------------------------------------------------


class TestErrorRecovery:
    """Test error recovery: LLM failure, TTS failure mid-stream."""

    @patch("src.streaming_pipeline.stream_chat")
    async def test_llm_failure_sets_error_and_returns_to_idle(self, mock_chat):
        mock_chat.side_effect = LLMServiceError("API rate limit exceeded")

        pipeline, player = _build_pipeline()
        await pipeline.process_user_input("Go")

        assert pipeline.session.status == "idle"
        assert pipeline.session.error == "API rate limit exceeded"
        # No TTS or playback should have been attempted
        player.play.assert_not_called()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_llm_failure_still_records_user_message_in_history(
        self, mock_chat, mock_tts
    ):
        mock_chat.side_effect = LLMServiceError("down")

        pipeline, _ = _build_pipeline()
        await pipeline.process_user_input("Hello")

        # User message should be in history even though LLM failed
        assert len(pipeline.history) == 1
        assert pipeline.history[0] == ChatMessage(role="user", content="Hello")

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_tts_failure_mid_stream_skips_chunk_and_continues(
        self, mock_chat, mock_tts
    ):
        """If TTS fails for one sentence, pipeline skips it and processes the next."""
        mock_chat.return_value = _fake_token_stream(
            ["First.", " Second.", " Third."]
        )
        # First chunk fails, second and third succeed
        mock_tts.side_effect = [
            TTSServiceError("TTS overloaded"),
            (b"\x00\x00" * 80, []),
            (b"\x00\x00" * 80, []),
        ]

        pipeline, player = _build_pipeline()
        await pipeline.process_user_input("Go")

        # TTS called for all 3 chunks
        assert mock_tts.call_count == 3
        # Audio played only for the 2 successful chunks
        assert player.play.call_count == 2
        # Pipeline completes successfully
        assert pipeline.session.status == "idle"
        assert pipeline.session.error is None
        # Assistant text still includes all chunks
        assert "First." in pipeline.history[-1].content
        assert "Third." in pipeline.history[-1].content

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_tts_failure_for_all_chunks_still_completes(
        self, mock_chat, mock_tts
    ):
        """If TTS fails for every chunk, pipeline still completes gracefully."""
        mock_chat.return_value = _fake_token_stream(["A.", " B."])
        mock_tts.side_effect = TTSServiceError("TTS down")

        pipeline, player = _build_pipeline()
        await pipeline.process_user_input("Go")

        assert pipeline.session.status == "idle"
        assert pipeline.session.error is None
        player.play.assert_not_called()
        # Assistant text is still recorded
        assert pipeline.history[-1].role == "assistant"

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    async def test_pipeline_recovers_after_llm_error_on_next_turn(
        self, mock_chat, mock_tts
    ):
        """After an LLM error, the next turn should work normally."""
        pipeline, player = _build_pipeline()

        # Turn 1: LLM fails
        mock_chat.side_effect = LLMServiceError("timeout")
        await pipeline.process_user_input("First")
        assert pipeline.session.error is not None

        # Turn 2: LLM succeeds
        mock_chat.side_effect = None
        mock_chat.return_value = _fake_token_stream(["OK."])
        mock_tts.return_value = (b"\x00\x00" * 80, [])
        await pipeline.process_user_input("Second")

        assert pipeline.session.status == "idle"
        assert pipeline.session.error is None
        player.play.assert_called_once()
