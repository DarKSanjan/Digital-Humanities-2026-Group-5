"""Unit tests for main.py GUI launch integration.

Verifies that launch_gui and _build_lip_sync_callbacks correctly wire
the AppGUI, StreamingPipeline, AudioPlayer, AppController, and
MicRecorder together using mocked components.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub customtkinter + PIL before any src imports (same pattern as other tests)
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
            self._mainloop_called = False
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
        def mainloop(self):
            self._mainloop_called = True

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

# ---------------------------------------------------------------------------
# Stub backend-only modules that main.py imports at module level.
# These live under src/ (added to sys.path by main.py) and are not
# available in the test environment.
# ---------------------------------------------------------------------------
for _mod_name in (
    "websocket_server",
    "hardware_detection",
    "avatar_renderer",
    "lip_sync_controller",
    "stream_coordinator",
    "avatar_window",
):
    if _mod_name not in sys.modules:
        _stub = types.ModuleType(_mod_name)
        _stub.__dict__.setdefault("WebSocketIPCServer", MagicMock)
        _stub.__dict__.setdefault("HardwareDetector", MagicMock)
        _stub.__dict__.setdefault("AvatarRenderer", MagicMock)
        _stub.__dict__.setdefault("LipSyncController", MagicMock)
        _stub.__dict__.setdefault("StreamCoordinator", MagicMock)
        _stub.__dict__.setdefault("AvatarWindow", MagicMock)
        sys.modules[_mod_name] = _stub

# Now safe to import
from src.main import BackendService, _build_lip_sync_callbacks, launch_gui
from src.app_gui import AppGUI
from src.streaming_pipeline import StreamingPipeline
from src.audio_player import AudioPlayer
from src.app_controller import AppController


# ---------------------------------------------------------------------------
# Tests: _build_lip_sync_callbacks
# ---------------------------------------------------------------------------

class TestBuildLipSyncCallbacks:
    """Verify lip sync callback factory."""

    def test_returns_two_callables(self):
        on_start, on_end = _build_lip_sync_callbacks(None)
        assert callable(on_start)
        assert callable(on_end)

    def test_start_calls_set_phonemes_when_window_running(self):
        window = MagicMock()
        window.running = True
        on_start, _ = _build_lip_sync_callbacks(window)
        phonemes = [{"phoneme": "a", "start": 0.0, "duration": 0.1}]
        on_start(phonemes)
        window.set_phonemes.assert_called_once_with(phonemes)

    def test_start_noop_when_window_none(self):
        on_start, _ = _build_lip_sync_callbacks(None)
        # Should not raise
        on_start([{"phoneme": "a"}])

    def test_start_noop_when_window_not_running(self):
        window = MagicMock()
        window.running = False
        on_start, _ = _build_lip_sync_callbacks(window)
        on_start([{"phoneme": "a"}])
        window.set_phonemes.assert_not_called()

    def test_end_calls_set_phoneme_silence(self):
        window = MagicMock()
        window.running = True
        _, on_end = _build_lip_sync_callbacks(window)
        on_end()
        window.set_phoneme.assert_called_once_with("silence")

    def test_end_noop_when_window_none(self):
        _, on_end = _build_lip_sync_callbacks(None)
        on_end()  # Should not raise

    def test_end_noop_when_window_not_running(self):
        window = MagicMock()
        window.running = False
        _, on_end = _build_lip_sync_callbacks(window)
        on_end()
        window.set_phoneme.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: launch_gui wiring
# ---------------------------------------------------------------------------

class TestLaunchGui:
    """Verify launch_gui creates and wires all components correctly."""

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_creates_gui(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        MockGUI.return_value.mainloop = MagicMock()
        launch_gui(service)
        MockGUI.assert_called_once()

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_creates_audio_player(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        MockGUI.return_value.mainloop = MagicMock()
        launch_gui(service)
        MockAP.assert_called_once()

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_creates_pipeline_with_audio_player(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        MockGUI.return_value.mainloop = MagicMock()
        launch_gui(service)
        call_kwargs = MockPipeline.call_args
        assert call_kwargs.kwargs["audio_player"] is MockAP.return_value

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_creates_pipeline_with_lip_sync_callbacks(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        MockGUI.return_value.mainloop = MagicMock()
        launch_gui(service)
        call_kwargs = MockPipeline.call_args
        assert call_kwargs.kwargs["on_lip_sync_start"] is not None
        assert call_kwargs.kwargs["on_lip_sync_end"] is not None

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_creates_mic_recorder(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        MockGUI.return_value.mainloop = MagicMock()
        launch_gui(service)
        MockMic.assert_called_once()

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_creates_controller_with_gui_pipeline_mic(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        MockGUI.return_value.mainloop = MagicMock()
        launch_gui(service)
        MockCtrl.assert_called_once_with(
            gui=MockGUI.return_value,
            pipeline=MockPipeline.return_value,
            mic_recorder=MockMic.return_value,
        )

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_controller_start_called_before_mainloop(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        call_order = []
        MockCtrl.return_value.start = MagicMock(side_effect=lambda: call_order.append("start"))
        MockGUI.return_value.mainloop = MagicMock(side_effect=lambda: call_order.append("mainloop"))
        launch_gui(service)
        assert call_order == ["start", "mainloop"]

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_controller_stop_called_after_mainloop(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        MockGUI.return_value.mainloop = MagicMock()
        launch_gui(service)
        MockCtrl.return_value.stop.assert_called_once()

    @patch("src.main.AppController")
    @patch("src.main.MicRecorder")
    @patch("src.main.StreamingPipeline")
    @patch("src.main.AudioPlayer")
    @patch("src.main.AppGUI")
    def test_controller_stop_called_even_on_keyboard_interrupt(self, MockGUI, MockAP, MockPipeline, MockMic, MockCtrl):
        service = MagicMock(spec=BackendService)
        service.avatar_window = None
        MockGUI.return_value.mainloop = MagicMock(side_effect=KeyboardInterrupt)
        launch_gui(service)
        MockCtrl.return_value.stop.assert_called_once()
