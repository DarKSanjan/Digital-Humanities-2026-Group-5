"""End-to-end integration test: mic button → mic_recorder → stt → pipeline → audio → lip sync.

Verifies the full wiring chain from a simulated mic button click through
to lip sync callback invocation, with all external services mocked.
"""

from __future__ import annotations

import asyncio
import sys
import time
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub customtkinter + PIL before any src imports
# ---------------------------------------------------------------------------

def _build_ctk_stub():
    ctk = types.ModuleType("customtkinter")
    ctk._appearance_mode = None
    ctk._color_theme = None
    ctk.set_appearance_mode = lambda m: setattr(ctk, "_appearance_mode", m)
    ctk.set_default_color_theme = lambda t: setattr(ctk, "_color_theme", t)

    class _FakeWidget:
        def __init__(self, master=None, **kw):
            self._master = master
            self._config = kw
            self._grid_args = None
            self._grid_row_cfg = {}
            self._grid_col_cfg = {}
        def grid(self, **kw): self._grid_args = kw
        def grid_remove(self): self._grid_args = None
        def pack(self, **kw): pass
        def configure(self, **kw): self._config.update(kw)
        def grid_rowconfigure(self, idx, **kw): self._grid_row_cfg[idx] = kw
        def grid_columnconfigure(self, idx, **kw): self._grid_col_cfg[idx] = kw
        def grid_propagate(self, val): pass

    class CTk(_FakeWidget):
        def __init__(self, **kw):
            super().__init__(**kw)
            self._title = None
            self._after_counter = 0
            self._after_callbacks = {}
        def title(self, t): self._title = t
        def geometry(self, g): pass
        def minsize(self, w, h): pass
        def after(self, ms, func=None, *args):
            self._after_counter += 1
            aid = f"after#{self._after_counter}"
            self._after_callbacks[aid] = (ms, func, args)
            # Only execute immediately for ms==0 (thread-safe scheduling).
            # Delayed callbacks (pulse animation etc.) are just stored.
            if func is not None and ms == 0:
                func(*args)
            return aid
        def after_cancel(self, aid):
            self._after_callbacks.pop(aid, None)

    class CTkFrame(_FakeWidget): pass
    class CTkLabel(_FakeWidget): pass
    class CTkButton(_FakeWidget): pass
    class CTkTextbox(_FakeWidget):
        def __init__(self, master=None, **kw):
            super().__init__(master, **kw)
            self._text_content = ""
            self._see_calls = []
        def insert(self, index, text):
            self._text_content += text
        def delete(self, start, end):
            self._text_content = ""
        def see(self, index):
            self._see_calls.append(index)
        def get(self, start, end):
            return self._text_content
    class CTkFont:
        def __init__(self, **kw): pass
    class CTkImage:
        def __init__(self, **kw): pass

    ctk.CTk = CTk
    ctk.CTkFrame = CTkFrame
    ctk.CTkLabel = CTkLabel
    ctk.CTkButton = CTkButton
    ctk.CTkTextbox = CTkTextbox
    ctk.CTkFont = CTkFont
    ctk.CTkImage = CTkImage
    return ctk


_ctk_stub = _build_ctk_stub()
sys.modules["customtkinter"] = _ctk_stub

_pil_mod = types.ModuleType("PIL")
_pil_image_mod = types.ModuleType("PIL.Image")
class _FakePILImage:
    def __init__(self, size=(512, 512)):
        self.size = size
_pil_image_mod.Image = _FakePILImage
_pil_mod.Image = _pil_image_mod
sys.modules.setdefault("PIL", _pil_mod)
sys.modules.setdefault("PIL.Image", _pil_image_mod)

# Now safe to import src modules
from src.app_controller import AppController
from src.app_gui import AppGUI
from src.audio_player import AudioPlayer
from src.streaming_pipeline import StreamingPipeline, TranscriptEntry
from src.tts_service import PhonemeData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fake_token_stream(tokens: list[str]):
    """Async generator that yields tokens one at a time."""
    for t in tokens:
        yield t


def _make_mic_mock():
    """Create a MicRecorder mock that returns valid WAV bytes on stop."""
    mic = MagicMock()
    mic._on_silence = None
    mic.start_recording = MagicMock()
    mic.stop_recording = MagicMock(return_value=b"RIFF" + b"\x00" * 40)
    mic.is_recording = False
    return mic


def _make_instant_player():
    """Create an AudioPlayer mock that fires on_start/on_end immediately."""
    player = MagicMock(spec=AudioPlayer)
    player.is_playing = False

    def _instant_play(audio_data, on_start=None, on_end=None):
        if on_start:
            on_start()
        if on_end:
            on_end()

    player.play.side_effect = _instant_play
    return player


# ---------------------------------------------------------------------------
# End-to-end wiring tests
# ---------------------------------------------------------------------------


class TestE2EWiring:
    """Full chain: mic button → mic_recorder → stt → pipeline → audio → lip sync."""

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_full_chain_mic_to_lip_sync(self, mock_chat, mock_tts):
        """Simulate mic click → stop → STT → LLM → TTS → playback → lip sync.

        Verifies every component in the chain receives the correct data
        and that lip sync callbacks are invoked.
        """
        # --- Setup mocks ---
        mock_chat.return_value = _fake_token_stream(["Hello ", "world."])
        phonemes = [PhonemeData(phoneme="HH", start=0.0, duration=0.05)]
        mock_tts.return_value = (b"\x00\x00" * 80, phonemes)

        lip_start = MagicMock()
        lip_end = MagicMock()

        gui = AppGUI()
        mic = _make_mic_mock()
        player = _make_instant_player()

        pipeline = StreamingPipeline(
            audio_player=player,
            on_lip_sync_start=lip_start,
            on_lip_sync_end=lip_end,
        )

        fake_transcribe = AsyncMock(return_value="What is AI?")

        ctrl = AppController(
            gui=gui,
            pipeline=pipeline,
            mic_recorder=mic,
            transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            # 1. Simulate mic button click → start recording
            ctrl._on_mic_toggle(True)
            mic.start_recording.assert_called_once()

            # 2. Simulate mic button click → stop recording
            ctrl._on_mic_toggle(False)
            time.sleep(0.6)

            # 3. Verify STT was called with the WAV bytes
            fake_transcribe.assert_called_once()

            # 4. Verify pipeline processed the transcribed text
            pipeline_user_msgs = [
                e for e in pipeline.session.transcript if e.role == "user"
            ]
            assert len(pipeline_user_msgs) == 1
            assert pipeline_user_msgs[0].content == "What is AI?"

            # 5. Verify LLM was called
            mock_chat.assert_called_once()

            # 6. Verify TTS was called with chunked text
            assert mock_tts.call_count >= 1

            # 7. Verify audio playback was triggered
            assert player.play.call_count >= 1

            # 8. Verify lip sync callbacks were invoked
            assert lip_start.call_count >= 1
            assert lip_end.call_count >= 1
        finally:
            ctrl.stop()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_gui_state_transitions_through_full_flow(self, mock_chat, mock_tts):
        """Verify GUI state: idle → listening → processing → speaking → idle."""
        mock_chat.return_value = _fake_token_stream(["OK."])
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        gui = AppGUI()
        mic = _make_mic_mock()
        player = _make_instant_player()

        pipeline = StreamingPipeline(audio_player=player)
        fake_transcribe = AsyncMock(return_value="test")

        states_seen: list[str] = []
        original_set_session = gui.set_session_state

        def _tracking_set_session(state: str):
            states_seen.append(state)
            original_set_session(state)

        gui.set_session_state = _tracking_set_session

        ctrl = AppController(
            gui=gui,
            pipeline=pipeline,
            mic_recorder=mic,
            transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            # Start recording → listening
            ctrl._on_mic_toggle(True)
            assert "listening" in states_seen

            # Stop recording → processing → speaking → idle
            ctrl._on_mic_toggle(False)
            time.sleep(0.6)

            assert "processing" in states_seen
            assert "idle" in states_seen
            # Final state should be idle
            assert gui.status_label._config.get("text") == "● Idle"
        finally:
            ctrl.stop()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_transcript_updated_with_user_and_assistant(self, mock_chat, mock_tts):
        """Verify both user and assistant messages appear in the GUI transcript."""
        mock_chat.return_value = _fake_token_stream(["I agree."])
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        gui = AppGUI()
        mic = _make_mic_mock()
        player = _make_instant_player()

        pipeline = StreamingPipeline(audio_player=player)
        fake_transcribe = AsyncMock(return_value="Hello bot")

        ctrl = AppController(
            gui=gui,
            pipeline=pipeline,
            mic_recorder=mic,
            transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.6)

            content = gui.transcript_textbox.get("1.0", "end")
            assert "You: Hello bot" in content
            assert "Bot: I agree." in content
        finally:
            ctrl.stop()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_lip_sync_receives_phoneme_data(self, mock_chat, mock_tts):
        """Verify lip sync start callback receives the phoneme data from TTS."""
        phonemes = [
            PhonemeData(phoneme="HH", start=0.0, duration=0.05),
            PhonemeData(phoneme="AH", start=0.05, duration=0.04),
        ]
        mock_chat.return_value = _fake_token_stream(["Hi."])
        mock_tts.return_value = (b"\x00\x00" * 80, phonemes)

        lip_start = MagicMock()
        lip_end = MagicMock()

        gui = AppGUI()
        mic = _make_mic_mock()
        player = _make_instant_player()

        pipeline = StreamingPipeline(
            audio_player=player,
            on_lip_sync_start=lip_start,
            on_lip_sync_end=lip_end,
        )
        fake_transcribe = AsyncMock(return_value="Hey")

        ctrl = AppController(
            gui=gui,
            pipeline=pipeline,
            mic_recorder=mic,
            transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.6)

            lip_start.assert_called_once()
            received_phonemes = lip_start.call_args[0][0]
            assert len(received_phonemes) == 2
            assert received_phonemes[0].phoneme == "HH"
            assert received_phonemes[1].phoneme == "AH"

            lip_end.assert_called_once()
        finally:
            ctrl.stop()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_multi_sentence_triggers_multiple_tts_and_playback(
        self, mock_chat, mock_tts
    ):
        """Multi-sentence LLM response triggers TTS and playback per chunk."""
        mock_chat.return_value = _fake_token_stream(
            ["First sentence.", " Second sentence."]
        )
        phonemes_a = [PhonemeData(phoneme="F", start=0.0, duration=0.03)]
        phonemes_b = [PhonemeData(phoneme="S", start=0.0, duration=0.04)]
        mock_tts.side_effect = [
            (b"\x00\x00" * 80, phonemes_a),
            (b"\x00\x00" * 80, phonemes_b),
        ]

        lip_start = MagicMock()
        lip_end = MagicMock()

        gui = AppGUI()
        mic = _make_mic_mock()
        player = _make_instant_player()

        pipeline = StreamingPipeline(
            audio_player=player,
            on_lip_sync_start=lip_start,
            on_lip_sync_end=lip_end,
        )
        fake_transcribe = AsyncMock(return_value="Tell me two things")

        ctrl = AppController(
            gui=gui,
            pipeline=pipeline,
            mic_recorder=mic,
            transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.6)

            # TTS called for each sentence chunk
            assert mock_tts.call_count == 2
            # Audio played for each chunk
            assert player.play.call_count == 2
            # Lip sync fired for each chunk
            assert lip_start.call_count == 2
            assert lip_end.call_count == 2
        finally:
            ctrl.stop()

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_silence_auto_stop_triggers_full_chain(self, mock_chat, mock_tts):
        """Silence detection auto-stop triggers the same full pipeline chain."""
        mock_chat.return_value = _fake_token_stream(["Auto reply."])
        mock_tts.return_value = (b"\x00\x00" * 80, [])

        gui = AppGUI()
        mic = _make_mic_mock()
        player = _make_instant_player()

        pipeline = StreamingPipeline(audio_player=player)
        fake_transcribe = AsyncMock(return_value="silence triggered")

        ctrl = AppController(
            gui=gui,
            pipeline=pipeline,
            mic_recorder=mic,
            transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            # Start recording via the GUI toggle (sets _is_recording=True)
            gui.toggle_recording()
            mic.start_recording.assert_called_once()
            assert gui._is_recording is True

            # Simulate silence callback — calls gui.toggle_recording()
            # which sees _is_recording=True, stops UI, then calls
            # _on_mic_toggle(False) triggering the full chain.
            ctrl._on_silence()
            time.sleep(0.6)

            # The full chain should have executed
            fake_transcribe.assert_called_once()
            mock_chat.assert_called_once()
            assert mock_tts.call_count >= 1
            assert player.play.call_count >= 1
        finally:
            ctrl.stop()
