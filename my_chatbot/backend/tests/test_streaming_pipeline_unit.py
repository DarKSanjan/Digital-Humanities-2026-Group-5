"""Unit tests for streaming_pipeline — orchestration logic."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.streaming_pipeline import (
    ChatMessage,
    SessionState,
    StreamingPipeline,
    TranscriptEntry,
)
from src.tts_service import PhonemeData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fake_token_stream(tokens: list[str]):
    """Async generator that yields tokens one at a time."""
    for t in tokens:
        yield t


def _make_pipeline(**kwargs) -> StreamingPipeline:
    """Create a pipeline with a mocked AudioPlayer."""
    player = MagicMock()
    # play() should invoke on_end immediately so the pipeline doesn't hang
    def _instant_play(audio_data, on_start=None, on_end=None):
        if on_start:
            on_start()
        if on_end:
            on_end()

    player.play.side_effect = _instant_play
    player.is_playing = False
    return StreamingPipeline(audio_player=player, **kwargs)


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


class TestSessionState:
    def test_default_state(self):
        state = SessionState()
        assert state.status == "idle"
        assert state.transcript == []
        assert state.error is None

    def test_set_status(self):
        pipeline = _make_pipeline()
        pipeline.set_status("processing")
        assert pipeline.session.status == "processing"


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------


class TestConversationHistory:
    def test_system_prompt_in_history(self):
        pipeline = _make_pipeline(system_prompt="You are helpful.")
        assert len(pipeline.history) == 1
        assert pipeline.history[0].role == "system"
        assert pipeline.history[0].content == "You are helpful."

    def test_no_system_prompt(self):
        pipeline = _make_pipeline()
        assert pipeline.history == []

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_history_tracks_user_and_assistant(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["Hello."])
        mock_tts.return_value = (b"\x00\x00" * 100, [])

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Hi"))

        assert len(pipeline.history) == 2
        assert pipeline.history[0] == ChatMessage(role="user", content="Hi")
        assert pipeline.history[1].role == "assistant"
        assert "Hello." in pipeline.history[1].content


# ---------------------------------------------------------------------------
# Pipeline flow
# ---------------------------------------------------------------------------


class TestPipelineFlow:
    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_empty_input_is_noop(self, mock_chat, mock_tts):
        pipeline = _make_pipeline()
        _run(pipeline.process_user_input(""))
        mock_chat.assert_not_called()
        mock_tts.assert_not_called()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_whitespace_input_is_noop(self, mock_chat, mock_tts):
        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("   "))
        mock_chat.assert_not_called()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_calls_tts_for_each_sentence_chunk(self, mock_chat, mock_tts):
        # Two sentences → two TTS calls
        mock_chat.return_value = _fake_token_stream(["First.", " Second."])
        mock_tts.return_value = (b"\x00\x00" * 100, [])

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Go"))

        assert mock_tts.call_count == 2

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_plays_audio_for_each_chunk(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["OK."])
        mock_tts.return_value = (b"\x00\x00" * 100, [])

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Go"))

        pipeline._audio_player.play.assert_called_once()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_skips_playback_when_tts_returns_empty_audio(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["Hi."])
        mock_tts.return_value = (b"", [])

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Go"))

        pipeline._audio_player.play.assert_not_called()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_status_returns_to_idle_after_success(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["Done."])
        mock_tts.return_value = (b"\x00\x00" * 100, [])

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Go"))

        assert pipeline.session.status == "idle"

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_transcript_updated(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["Reply."])
        mock_tts.return_value = (b"\x00\x00" * 100, [])

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Hello"))

        assert len(pipeline.session.transcript) == 2
        assert pipeline.session.transcript[0].role == "user"
        assert pipeline.session.transcript[1].role == "assistant"


# ---------------------------------------------------------------------------
# Lip-sync callbacks
# ---------------------------------------------------------------------------


class TestLipSyncCallbacks:
    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_on_playback_start_fires_lip_sync(self, mock_chat, mock_tts):
        phonemes = [PhonemeData(phoneme="AH", start=0.0, duration=0.1)]
        mock_chat.return_value = _fake_token_stream(["Hi."])
        mock_tts.return_value = (b"\x00\x00" * 100, phonemes)

        lip_start = MagicMock()
        lip_end = MagicMock()
        pipeline = _make_pipeline(
            on_lip_sync_start=lip_start,
            on_lip_sync_end=lip_end,
        )
        _run(pipeline.process_user_input("Go"))

        lip_start.assert_called_once_with(phonemes)
        lip_end.assert_called_once()

    def test_on_playback_start_sets_speaking_status(self):
        pipeline = _make_pipeline()
        pipeline.on_playback_start([])
        assert pipeline.session.status == "speaking"

    def test_on_playback_start_tolerates_callback_error(self):
        def _bad_callback(phonemes):
            raise RuntimeError("boom")

        pipeline = _make_pipeline(on_lip_sync_start=_bad_callback)
        # Should not raise
        pipeline.on_playback_start([])

    def test_on_playback_end_tolerates_callback_error(self):
        def _bad_callback():
            raise RuntimeError("boom")

        pipeline = _make_pipeline(on_lip_sync_end=_bad_callback)
        pipeline.on_playback_end()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_lip_sync_triggered_on_playback_start_not_data_receive(
        self, mock_chat, mock_tts
    ):
        """Verify lip sync fires via audio player on_start, not at TTS receive.

        The callback chain must be:
        audio_player.play(on_start=...) → on_playback_start → on_lip_sync_start
        """
        phonemes = [PhonemeData(phoneme="AH", start=0.0, duration=0.1)]
        mock_chat.return_value = _fake_token_stream(["Hi."])
        mock_tts.return_value = (b"\x00\x00" * 100, phonemes)

        call_order: list[str] = []

        def track_lip_sync(ph):
            call_order.append("lip_sync_start")

        player = MagicMock()
        player.is_playing = False

        # Simulate audio player that fires on_start callback (playback begin)
        def _play_with_start(audio_data, on_start=None, on_end=None):
            # Record that TTS data was received BEFORE on_start fires
            call_order.append("audio_player_play_called")
            # on_start fires when playback actually begins
            if on_start:
                on_start()
            if on_end:
                on_end()

        player.play.side_effect = _play_with_start

        pipeline = StreamingPipeline(
            audio_player=player,
            on_lip_sync_start=track_lip_sync,
        )
        _run(pipeline.process_user_input("Go"))

        # Lip sync must fire AFTER audio_player.play is called (i.e., via
        # the on_start callback), not before it.
        assert call_order == ["audio_player_play_called", "lip_sync_start"]

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_avatar_set_phonemes_wired_through_lip_sync_callback(
        self, mock_chat, mock_tts
    ):
        """Simulate avatar_window.set_phonemes wired as on_lip_sync_start.

        This mirrors how main.py would wire the pipeline to the avatar.
        """
        phonemes = [
            PhonemeData(phoneme="AH", start=0.0, duration=0.1),
            PhonemeData(phoneme="EH", start=0.1, duration=0.15),
        ]
        mock_chat.return_value = _fake_token_stream(["Hello."])
        mock_tts.return_value = (b"\x00\x00" * 100, phonemes)

        avatar_window = MagicMock()

        pipeline = _make_pipeline(
            on_lip_sync_start=avatar_window.set_phonemes,
        )
        _run(pipeline.process_user_input("Go"))

        avatar_window.set_phonemes.assert_called_once_with(phonemes)

    def test_on_playback_end_calls_lip_sync_end_callback(self):
        """Verify on_playback_end invokes the on_lip_sync_end callback."""
        lip_end = MagicMock()
        pipeline = _make_pipeline(on_lip_sync_end=lip_end)

        pipeline.on_playback_end()

        lip_end.assert_called_once()

    def test_on_playback_end_noop_when_no_callback(self):
        """Verify on_playback_end is safe when no callback is set."""
        pipeline = _make_pipeline()
        # Should not raise
        pipeline.on_playback_end()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_avatar_reset_to_neutral_wired_as_lip_sync_end(
        self, mock_chat, mock_tts
    ):
        """Simulate avatar_window.reset_to_neutral wired as on_lip_sync_end.

        This mirrors how main.py would wire the pipeline so the avatar
        returns to the neutral rest viseme when audio playback ends.

        Validates: Requirements 2.3
        """
        mock_chat.return_value = _fake_token_stream(["Done."])
        mock_tts.return_value = (b"\x00\x00" * 100, [])

        avatar_window = MagicMock()

        pipeline = _make_pipeline(
            on_lip_sync_end=avatar_window.reset_to_neutral,
        )
        _run(pipeline.process_user_input("Go"))

        avatar_window.reset_to_neutral.assert_called_once()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch("src.streaming_pipeline.stream_chat")
    def test_llm_error_sets_session_error(self, mock_chat):
        from src.llm_service import LLMServiceError

        mock_chat.side_effect = LLMServiceError("API down")

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Go"))

        assert pipeline.session.error == "API down"
        assert pipeline.session.status == "idle"

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_tts_error_skips_chunk_but_continues(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["A.", " B."])
        # First TTS chunk fails all retries (initial + 2 retries = 3 calls),
        # second chunk succeeds
        mock_tts.side_effect = [
            TTSServiceError("TTS down"),
            TTSServiceError("TTS down"),
            TTSServiceError("TTS down"),
            (b"\x00\x00" * 100, []),
        ]

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Go"))

        # Pipeline should still complete and record assistant text
        assert pipeline.session.status == "idle"
        assert pipeline.session.error is None
        # Audio played only for the second chunk
        pipeline._audio_player.play.assert_called_once()


from src.tts_service import TTSServiceError
