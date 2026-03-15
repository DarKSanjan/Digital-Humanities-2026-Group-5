"""Unit tests for AppController wiring logic.

Tests verify that GUI events are correctly routed to MicRecorder,
STT, and StreamingPipeline without requiring real hardware or APIs.
"""

from __future__ import annotations

import asyncio
import sys
import time
import types
from unittest.mock import AsyncMock, MagicMock

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
            if func is not None:
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
from src.mic_recorder import MicRecorderError
from src.stt_service import STTServiceError
from src.streaming_pipeline import SessionState, StreamingPipeline, TranscriptEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mic_mock():
    mic = MagicMock()
    mic._on_silence = None
    mic.start_recording = MagicMock()
    mic.stop_recording = MagicMock(return_value=b"RIFF" + b"\x00" * 40)
    mic.is_recording = False
    return mic


def _make_pipeline_mock():
    pipeline = MagicMock(spec=StreamingPipeline)
    pipeline.session = SessionState()
    pipeline.set_status = MagicMock()
    pipeline.process_user_input = AsyncMock()
    return pipeline


# ---------------------------------------------------------------------------
# Tests: mic toggle wiring
# ---------------------------------------------------------------------------

class TestMicToggleWiring:
    """Verify that the GUI mic toggle callback is wired correctly."""

    def test_on_mic_toggle_callback_is_set(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        assert gui._on_mic_toggle is not None

    def test_toggle_true_starts_recording(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl._on_mic_toggle(True)
        mic.start_recording.assert_called_once()

    def test_toggle_true_sets_listening_state(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl._on_mic_toggle(True)
        assert gui.status_label._config.get("text") == "🎤 Listening..."

    def test_toggle_false_stops_recording(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.2)
            mic.stop_recording.assert_called_once()
        finally:
            ctrl.stop()

    def test_toggle_false_sets_processing_state(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        # Use a slow transcribe so we can observe the "processing" state
        async def slow_transcribe(data):
            await asyncio.sleep(0.5)
            return "hello"
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=slow_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.2)
            assert gui.status_label._config.get("text") == "⏳ Processing..."
        finally:
            ctrl.stop()


# ---------------------------------------------------------------------------
# Tests: silence auto-stop
# ---------------------------------------------------------------------------

class TestSilenceAutoStop:
    """Verify silence callback triggers recording stop via GUI."""

    def test_silence_callback_wired_to_mic(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        assert mic._on_silence is not None

    def test_silence_callback_calls_toggle_recording(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        # Spy on toggle_recording
        gui.toggle_recording = MagicMock()
        ctrl._on_silence()
        gui.toggle_recording.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: transcribe and process pipeline
# ---------------------------------------------------------------------------

class TestTranscribeAndProcess:
    """Verify the async transcription → pipeline flow."""

    def test_transcription_feeds_pipeline(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        fake_transcribe = AsyncMock(return_value="Hello world")
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.4)
            fake_transcribe.assert_called_once()
            pipeline.process_user_input.assert_called_once_with("Hello world")
        finally:
            ctrl.stop()

    def test_user_message_added_to_transcript(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        fake_transcribe = AsyncMock(return_value="Test message")
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.4)
            content = gui.transcript_textbox.get("1.0", "end")
            assert "You: Test message" in content
        finally:
            ctrl.stop()

    def test_empty_transcription_returns_to_idle(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        fake_transcribe = AsyncMock(return_value="")
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.4)
            pipeline.process_user_input.assert_not_called()
            assert gui.status_label._config.get("text") == "● Idle"
        finally:
            ctrl.stop()

    def test_stt_error_shows_error_and_returns_idle(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        fake_transcribe = AsyncMock(side_effect=STTServiceError("fail"))
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(5.0)  # allow retries with backoff
            # set_status is called with a user-friendly error message
            status_text = gui.status_label._config.get("text", "")
            assert "failed" in status_text.lower() or "try" in status_text.lower()
        finally:
            ctrl.stop()


# ---------------------------------------------------------------------------
# Tests: assistant transcript update
# ---------------------------------------------------------------------------

class TestAssistantTranscript:
    """Verify assistant reply is added to the GUI transcript."""

    def test_assistant_reply_shown_in_transcript(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()

        async def fake_process(text):
            pipeline.session.transcript.append(
                TranscriptEntry(role="user", content=text)
            )
            pipeline.session.transcript.append(
                TranscriptEntry(role="assistant", content="I agree!")
            )

        pipeline.process_user_input = AsyncMock(side_effect=fake_process)
        fake_transcribe = AsyncMock(return_value="Hello")
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.5)
            content = gui.transcript_textbox.get("1.0", "end")
            assert "Bot: I agree!" in content
        finally:
            ctrl.stop()


# ---------------------------------------------------------------------------
# Tests: mic error handling
# ---------------------------------------------------------------------------

class TestMicErrorHandling:
    """Verify mic errors are handled gracefully."""

    def test_mic_start_error_reverts_to_idle(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        mic.start_recording.side_effect = MicRecorderError("No mic")
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl._on_mic_toggle(True)
        # set_status is called with the error, but set_session_state("idle")
        # was also called — the status text shows the error message
        status_text = gui.status_label._config.get("text", "")
        assert "Mic error" in status_text

    def test_mic_start_error_reverts_button_ui(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        mic.start_recording.side_effect = MicRecorderError("No mic")
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl._on_mic_toggle(True)
        # Button should be back to idle text
        assert gui.mic_button._config.get("text") == AppGUI.MIC_TEXT_IDLE


# ---------------------------------------------------------------------------
# Tests: lifecycle
# ---------------------------------------------------------------------------

class TestLifecycle:
    """Verify start/stop of the background event loop."""

    def test_start_creates_running_loop(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl.start()
        try:
            assert ctrl._loop is not None
            assert ctrl._loop.is_running()
        finally:
            ctrl.stop()

    def test_stop_cleans_up(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl.start()
        ctrl.stop()
        assert ctrl._loop is None
