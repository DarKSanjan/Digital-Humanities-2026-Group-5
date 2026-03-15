"""Unit tests for error handling: mic disable, retry in controller, pipeline playback errors.

Tests verify the error handling enhancements from task 6.3:
- Mic button disables on mic access failure
- STT retry logic in AppController
- Playback errors handled gracefully in pipeline
- LLM errors surface in session state
"""

from __future__ import annotations

import asyncio
import sys
import time
import types
from unittest.mock import AsyncMock, MagicMock, patch

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
        def insert(self, index, text): self._text_content += text
        def delete(self, start, end): self._text_content = ""
        def see(self, index): self._see_calls.append(index)
        def get(self, start, end): return self._text_content
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

from src.app_controller import AppController
from src.app_gui import AppGUI
from src.audio_player import AudioPlayerError
from src.llm_service import LLMServiceError
from src.mic_recorder import MicRecorderError
from src.stt_service import STTServiceError
from src.streaming_pipeline import SessionState, StreamingPipeline, TranscriptEntry
from src.tts_service import TTSServiceError


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


async def _fake_token_stream(tokens):
    for t in tokens:
        yield t


def _make_pipeline(**kwargs):
    player = MagicMock()
    def _instant_play(audio_data, on_start=None, on_end=None):
        if on_start:
            on_start()
        if on_end:
            on_end()
    player.play.side_effect = _instant_play
    player.is_playing = False
    return StreamingPipeline(audio_player=player, **kwargs)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Tests: mic button disable on failure
# ---------------------------------------------------------------------------

class TestMicDisableOnFailure:
    """Verify mic button is disabled when mic access fails."""

    def test_mic_error_disables_button(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        mic.start_recording.side_effect = MicRecorderError("No mic found")
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl._on_mic_toggle(True)
        assert gui.mic_button._config.get("state") == "disabled"

    def test_mic_error_shows_status_message(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        mic.start_recording.side_effect = MicRecorderError("No mic found")
        pipeline = _make_pipeline_mock()
        ctrl = AppController(gui, pipeline, mic_recorder=mic)
        ctrl._on_mic_toggle(True)
        status = gui.status_label._config.get("text", "")
        assert "Mic error" in status


class TestMicButtonEnableDisable:
    """Verify the GUI disable/enable mic button methods."""

    def test_disable_mic_button(self):
        gui = AppGUI()
        gui.disable_mic_button()
        assert gui.mic_button._config.get("state") == "disabled"

    def test_enable_mic_button(self):
        gui = AppGUI()
        gui.disable_mic_button()
        gui.enable_mic_button()
        assert gui.mic_button._config.get("state") == "normal"


# ---------------------------------------------------------------------------
# Tests: STT retry in controller
# ---------------------------------------------------------------------------

class TestSTTRetryInController:
    """Verify STT calls are retried before giving up."""

    def test_stt_retried_on_transient_failure(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        call_count = 0

        async def flaky_transcribe(data):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise STTServiceError("transient")
            return "Hello"

        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=flaky_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(3.0)  # allow retries with backoff
            assert call_count >= 2
            pipeline.process_user_input.assert_called_once_with("Hello")
        finally:
            ctrl.stop()

    def test_stt_shows_friendly_error_after_exhaustion(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        fake_transcribe = AsyncMock(side_effect=STTServiceError("API down"))
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(5.0)  # allow all retries to exhaust
            status = gui.status_label._config.get("text", "")
            assert "failed" in status.lower() or "try" in status.lower()
        finally:
            ctrl.stop()


# ---------------------------------------------------------------------------
# Tests: pipeline playback error handling
# ---------------------------------------------------------------------------

class TestPipelinePlaybackError:
    """Verify audio playback errors are caught and pipeline continues."""

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_playback_error_continues_pipeline(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["Hello.", " World."])
        mock_tts.return_value = (b"\x00\x00" * 100, [])

        player = MagicMock()
        player.is_playing = False
        player.play.side_effect = AudioPlayerError("device busy")

        pipeline = StreamingPipeline(audio_player=player)
        _run(pipeline.process_user_input("Go"))

        # Pipeline should complete despite playback errors
        assert pipeline.session.status == "idle"
        assert pipeline.session.error is None
        # Assistant text should still be recorded
        assert any(e.role == "assistant" for e in pipeline.session.transcript)

    @patch("src.streaming_pipeline.stream_tts", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_playback_error_still_records_text(self, mock_chat, mock_tts):
        mock_chat.return_value = _fake_token_stream(["Reply."])
        mock_tts.return_value = (b"\x00\x00" * 100, [])

        player = MagicMock()
        player.is_playing = False
        player.play.side_effect = RuntimeError("audio fail")

        pipeline = StreamingPipeline(audio_player=player)
        _run(pipeline.process_user_input("Go"))

        assert len(pipeline.history) == 2
        assert pipeline.history[1].role == "assistant"
        assert "Reply." in pipeline.history[1].content


# ---------------------------------------------------------------------------
# Tests: LLM error in pipeline
# ---------------------------------------------------------------------------

class TestPipelineLLMError:
    """Verify LLM errors set session error and return to idle."""

    @patch("src.streaming_pipeline.stream_chat")
    def test_llm_error_sets_session_error(self, mock_chat):
        mock_chat.side_effect = LLMServiceError("API down")
        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Go"))
        assert pipeline.session.error == "API down"
        assert pipeline.session.status == "idle"


# ---------------------------------------------------------------------------
# Tests: TTS retry in pipeline
# ---------------------------------------------------------------------------

class TestPipelineTTSRetry:
    """Verify TTS calls are retried in the pipeline."""

    @patch("src.streaming_pipeline.async_retry", new_callable=AsyncMock)
    @patch("src.streaming_pipeline.stream_chat")
    def test_tts_uses_retry(self, mock_chat, mock_retry):
        mock_chat.return_value = _fake_token_stream(["Hi."])
        mock_retry.return_value = (b"\x00\x00" * 100, [])

        pipeline = _make_pipeline()
        _run(pipeline.process_user_input("Go"))

        # async_retry should have been called for TTS
        mock_retry.assert_called()


# ---------------------------------------------------------------------------
# Tests: controller surfaces pipeline error in status
# ---------------------------------------------------------------------------

class TestControllerPipelineError:
    """Verify controller shows friendly error when pipeline fails."""

    def test_pipeline_exception_shows_friendly_status(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()
        pipeline.process_user_input = AsyncMock(side_effect=RuntimeError("boom"))
        fake_transcribe = AsyncMock(return_value="Hello")
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.5)
            status = gui.status_label._config.get("text", "")
            assert "try again" in status.lower()
        finally:
            ctrl.stop()

    def test_pipeline_session_error_surfaces_in_status(self):
        gui = AppGUI()
        mic = _make_mic_mock()
        pipeline = _make_pipeline_mock()

        async def fake_process(text):
            pipeline.session.error = "LLM failed"

        pipeline.process_user_input = AsyncMock(side_effect=fake_process)
        fake_transcribe = AsyncMock(return_value="Hello")
        ctrl = AppController(
            gui, pipeline, mic_recorder=mic, transcribe_fn=fake_transcribe,
        )
        ctrl.start()
        try:
            ctrl._on_mic_toggle(False)
            time.sleep(0.5)
            status = gui.status_label._config.get("text", "")
            assert "failed" in status.lower() or "try again" in status.lower()
        finally:
            ctrl.stop()
