"""
Unit tests for app_gui.py — AppGUI window skeleton.

Tests verify layout structure, dark theme, responsive grid config,
and placeholder components without requiring a live display.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Stub out customtkinter before importing app_gui so tests run headless.
# ---------------------------------------------------------------------------

def _build_ctk_stub():
    """Return a fake customtkinter module with the classes AppGUI needs."""
    ctk = types.ModuleType("customtkinter")

    # Track global calls
    ctk._appearance_mode = None
    ctk._color_theme = None

    def set_appearance_mode(mode):
        ctk._appearance_mode = mode

    def set_default_color_theme(theme):
        ctk._color_theme = theme

    ctk.set_appearance_mode = set_appearance_mode
    ctk.set_default_color_theme = set_default_color_theme

    # --- Fake widget base ---------------------------------------------------
    class _FakeWidget:
        def __init__(self, master=None, **kw):
            self._master = master
            self._config = kw
            self._grid_args = None
            self._pack_args = None
            self._grid_propagate_val = None
            self._grid_row_cfg = {}
            self._grid_col_cfg = {}

        def grid(self, **kw):
            self._grid_args = kw

        def grid_remove(self):
            self._grid_args = None

        def pack(self, **kw):
            self._pack_args = kw

        def configure(self, **kw):
            self._config.update(kw)

        def grid_rowconfigure(self, idx, **kw):
            self._grid_row_cfg[idx] = kw

        def grid_columnconfigure(self, idx, **kw):
            self._grid_col_cfg[idx] = kw

        def grid_propagate(self, val):
            self._grid_propagate_val = val

    class CTk(_FakeWidget):
        def __init__(self, **kw):
            super().__init__(**kw)
            self._title = None
            self._geometry = None
            self._minsize = None
            self._after_counter = 0
            self._after_callbacks = {}

        def title(self, t):
            self._title = t

        def geometry(self, g):
            self._geometry = g

        def minsize(self, w, h):
            self._minsize = (w, h)

        def after(self, ms, func=None, *args):
            self._after_counter += 1
            after_id = f"after#{self._after_counter}"
            self._after_callbacks[after_id] = (ms, func, args)
            return after_id

        def after_cancel(self, after_id):
            self._after_callbacks.pop(after_id, None)

    class CTkFrame(_FakeWidget):
        pass

    class CTkLabel(_FakeWidget):
        pass

    class CTkButton(_FakeWidget):
        pass

    class CTkTextbox(_FakeWidget):
        """Fake CTkTextbox that tracks insert/delete/see calls."""
        def __init__(self, master=None, **kw):
            super().__init__(master, **kw)
            self._text_content = ""
            self._see_calls = []

        def insert(self, index, text):
            if index == "end":
                self._text_content += text
            else:
                self._text_content = text + self._text_content

        def delete(self, start, end):
            self._text_content = ""

        def see(self, index):
            self._see_calls.append(index)

        def get(self, start, end):
            return self._text_content

    class CTkFont:
        def __init__(self, **kw):
            self._kw = kw

    class CTkImage:
        """Fake CTkImage that records constructor args."""
        def __init__(self, light_image=None, dark_image=None, size=None):
            self.light_image = light_image
            self.dark_image = dark_image
            self.size = size

    ctk.CTk = CTk
    ctk.CTkFrame = CTkFrame
    ctk.CTkLabel = CTkLabel
    ctk.CTkButton = CTkButton
    ctk.CTkTextbox = CTkTextbox
    ctk.CTkFont = CTkFont
    ctk.CTkImage = CTkImage

    return ctk


# Install the stub before any import of app_gui
_ctk_stub = _build_ctk_stub()
sys.modules["customtkinter"] = _ctk_stub

# Stub PIL.Image so the import in app_gui succeeds headless
_pil_mod = types.ModuleType("PIL")
_pil_image_mod = types.ModuleType("PIL.Image")


class _FakePILImage:
    """Minimal stand-in for PIL.Image.Image."""
    def __init__(self, size=(512, 512)):
        self.size = size


_pil_image_mod.Image = _FakePILImage
_pil_mod.Image = _pil_image_mod
sys.modules.setdefault("PIL", _pil_mod)
sys.modules.setdefault("PIL.Image", _pil_image_mod)

# Now we can safely import
from src.app_gui import AppGUI
from src.design_system import design_system


class TestAppGUIInit(unittest.TestCase):
    """Verify window-level initialisation."""

    def setUp(self):
        # Reset global state tracked by the stub
        _ctk_stub._appearance_mode = None
        _ctk_stub._color_theme = None
        # Re-import to re-trigger module-level set_appearance_mode
        import importlib
        import src.app_gui
        importlib.reload(src.app_gui)
        self.gui = src.app_gui.AppGUI()

    def test_dark_theme_set(self):
        self.assertEqual(_ctk_stub._appearance_mode, "dark")

    def test_window_title(self):
        self.assertEqual(self.gui._title, "Persuasive Chatbot")

    def test_default_geometry(self):
        expected = f"{AppGUI.DEFAULT_WIDTH}x{AppGUI.DEFAULT_HEIGHT}"
        self.assertEqual(self.gui._geometry, expected)

    def test_minimum_size(self):
        self.assertEqual(self.gui._minsize, (AppGUI.MIN_WIDTH, AppGUI.MIN_HEIGHT))


class TestResponsiveGrid(unittest.TestCase):
    """Verify grid weight configuration for responsive resizing."""

    def setUp(self):
        self.gui = AppGUI()

    def test_column_zero_expands(self):
        self.assertIn(0, self.gui._grid_col_cfg)
        self.assertEqual(self.gui._grid_col_cfg[0].get("weight"), 1)

    def test_avatar_row_has_weight(self):
        self.assertGreater(self.gui._grid_row_cfg[0].get("weight", 0), 0)

    def test_mic_row_fixed(self):
        self.assertEqual(self.gui._grid_row_cfg[1].get("weight", -1), 0)

    def test_transcript_row_has_weight(self):
        self.assertGreater(self.gui._grid_row_cfg[2].get("weight", 0), 0)

    def test_status_row_fixed(self):
        self.assertEqual(self.gui._grid_row_cfg[3].get("weight", -1), 0)


class TestPlaceholderAreas(unittest.TestCase):
    """Verify all four placeholder areas are created."""

    def setUp(self):
        self.gui = AppGUI()

    def test_avatar_frame_exists(self):
        self.assertIsNotNone(self.gui.avatar_frame)

    def test_avatar_placeholder_label(self):
        self.assertIsNotNone(self.gui.avatar_placeholder)

    def test_mic_frame_exists(self):
        self.assertIsNotNone(self.gui.mic_frame)

    def test_mic_button_exists(self):
        self.assertIsNotNone(self.gui.mic_button)

    def test_transcript_frame_exists(self):
        self.assertIsNotNone(self.gui.transcript_frame)

    def test_transcript_textbox_exists(self):
        self.assertIsNotNone(self.gui.transcript_textbox)

    def test_transcript_toggle_exists(self):
        self.assertIsNotNone(self.gui.transcript_toggle)

    def test_status_frame_exists(self):
        self.assertIsNotNone(self.gui.status_frame)

    def test_status_label_exists(self):
        self.assertIsNotNone(self.gui.status_label)


class TestStatusLabel(unittest.TestCase):
    """Verify status label default and update."""

    def setUp(self):
        self.gui = AppGUI()

    def test_default_status_is_idle(self):
        self.assertEqual(self.gui.status_label._config.get("text"), "idle")

    def test_set_status_updates_text(self):
        self.gui.set_status("listening")
        self.assertEqual(self.gui.status_label._config.get("text"), "listening")


class TestSetSessionState(unittest.TestCase):
    """Verify set_session_state updates text and color for each state."""

    def setUp(self):
        self.gui = AppGUI()

    def test_idle_state_text(self):
        self.gui.set_session_state("idle")
        self.assertEqual(self.gui.status_label._config.get("text"), "● Idle")

    def test_idle_state_color(self):
        self.gui.set_session_state("idle")
        self.assertEqual(
            self.gui.status_label._config.get("text_color"),
            design_system.colors.text_secondary,
        )

    def test_listening_state_text(self):
        self.gui.set_session_state("listening")
        self.assertEqual(self.gui.status_label._config.get("text"), "🎤 Listening...")

    def test_listening_state_color(self):
        self.gui.set_session_state("listening")
        self.assertEqual(
            self.gui.status_label._config.get("text_color"),
            design_system.colors.success,
        )

    def test_processing_state_text(self):
        self.gui.set_session_state("processing")
        self.assertEqual(self.gui.status_label._config.get("text"), "⏳ Processing...")

    def test_processing_state_color(self):
        self.gui.set_session_state("processing")
        self.assertEqual(
            self.gui.status_label._config.get("text_color"),
            design_system.colors.warning,
        )

    def test_speaking_state_text(self):
        self.gui.set_session_state("speaking")
        self.assertEqual(self.gui.status_label._config.get("text"), "🔊 Speaking...")

    def test_speaking_state_color(self):
        self.gui.set_session_state("speaking")
        self.assertEqual(
            self.gui.status_label._config.get("text_color"),
            design_system.colors.info,
        )

    def test_unknown_state_falls_back_to_idle(self):
        self.gui.set_session_state("unknown_state")
        self.assertEqual(self.gui.status_label._config.get("text"), "● Idle")
        self.assertEqual(
            self.gui.status_label._config.get("text_color"),
            design_system.colors.text_secondary,
        )

    def test_state_transitions(self):
        """Verify switching between states updates both text and color."""
        self.gui.set_session_state("listening")
        self.assertIn("Listening", self.gui.status_label._config.get("text"))
        self.gui.set_session_state("processing")
        self.assertIn("Processing", self.gui.status_label._config.get("text"))
        self.gui.set_session_state("speaking")
        self.assertIn("Speaking", self.gui.status_label._config.get("text"))
        self.gui.set_session_state("idle")
        self.assertIn("Idle", self.gui.status_label._config.get("text"))


class TestTranscriptToggle(unittest.TestCase):
    """Verify transcript collapse/expand behaviour."""

    def setUp(self):
        self.gui = AppGUI()

    def test_initially_visible(self):
        self.assertTrue(self.gui._transcript_visible)

    def test_toggle_hides(self):
        self.gui._toggle_transcript()
        self.assertFalse(self.gui._transcript_visible)

    def test_toggle_shows_again(self):
        self.gui._toggle_transcript()  # hide
        self.gui._toggle_transcript()  # show
        self.assertTrue(self.gui._transcript_visible)

    def test_toggle_updates_button_text_on_hide(self):
        self.gui._toggle_transcript()
        self.assertIn("▶", self.gui.transcript_toggle._config.get("text", ""))

    def test_toggle_updates_button_text_on_show(self):
        self.gui._toggle_transcript()
        self.gui._toggle_transcript()
        self.assertIn("▼", self.gui.transcript_toggle._config.get("text", ""))


class TestAvatarDisplay(unittest.TestCase):
    """Verify avatar frame display via update_avatar_frame."""

    def setUp(self):
        self.gui = AppGUI()

    def test_avatar_ctk_image_initially_none(self):
        self.assertIsNone(self.gui._avatar_ctk_image)

    def test_update_avatar_frame_sets_image(self):
        fake_img = _FakePILImage(size=(256, 256))
        self.gui.update_avatar_frame(fake_img)
        self.assertIsNotNone(self.gui._avatar_ctk_image)

    def test_update_avatar_frame_clears_placeholder_text(self):
        fake_img = _FakePILImage(size=(256, 256))
        self.gui.update_avatar_frame(fake_img)
        self.assertEqual(self.gui.avatar_placeholder._config.get("text"), "")

    def test_update_avatar_frame_stores_ctk_image_reference(self):
        fake_img = _FakePILImage(size=(256, 256))
        self.gui.update_avatar_frame(fake_img)
        ctk_img = self.gui._avatar_ctk_image
        self.assertIsInstance(ctk_img, _ctk_stub.CTkImage)

    def test_update_avatar_frame_uses_design_system_size(self):
        from src.design_system import design_system
        fake_img = _FakePILImage(size=(256, 256))
        self.gui.update_avatar_frame(fake_img)
        ctk_img = self.gui._avatar_ctk_image
        self.assertEqual(ctk_img.size, design_system.layout.avatar_size)

    def test_update_avatar_frame_passes_image_to_ctk_image(self):
        fake_img = _FakePILImage(size=(128, 128))
        self.gui.update_avatar_frame(fake_img)
        ctk_img = self.gui._avatar_ctk_image
        self.assertIs(ctk_img.light_image, fake_img)
        self.assertIs(ctk_img.dark_image, fake_img)

    def test_successive_updates_replace_image(self):
        img1 = _FakePILImage(size=(100, 100))
        img2 = _FakePILImage(size=(200, 200))
        self.gui.update_avatar_frame(img1)
        first_ref = self.gui._avatar_ctk_image
        self.gui.update_avatar_frame(img2)
        second_ref = self.gui._avatar_ctk_image
        self.assertIsNot(first_ref, second_ref)
        self.assertIs(second_ref.light_image, img2)


class TestMicToggle(unittest.TestCase):
    """Verify mic toggle button recording state and visual feedback."""

    def setUp(self):
        self.gui = AppGUI()

    def test_initially_not_recording(self):
        self.assertFalse(self.gui._is_recording)

    def test_initial_button_text_is_idle(self):
        self.assertEqual(self.gui.mic_button._config.get("text"), AppGUI.MIC_TEXT_IDLE)

    def test_toggle_starts_recording(self):
        self.gui.toggle_recording()
        self.assertTrue(self.gui._is_recording)

    def test_toggle_sets_recording_text(self):
        self.gui.toggle_recording()
        self.assertEqual(self.gui.mic_button._config.get("text"), AppGUI.MIC_TEXT_RECORDING)

    def test_toggle_sets_red_color(self):
        self.gui.toggle_recording()
        # After toggle, the button is in recording state; the pulse may have
        # already alternated the color, so accept either recording color.
        fg = self.gui.mic_button._config.get("fg_color")
        self.assertIn(fg, (
            design_system.colors.error,
            design_system.buttons.danger_bg_hover,
        ))

    def test_toggle_twice_stops_recording(self):
        self.gui.toggle_recording()
        self.gui.toggle_recording()
        self.assertFalse(self.gui._is_recording)

    def test_toggle_twice_restores_idle_text(self):
        self.gui.toggle_recording()
        self.gui.toggle_recording()
        self.assertEqual(self.gui.mic_button._config.get("text"), AppGUI.MIC_TEXT_IDLE)

    def test_toggle_twice_restores_primary_color(self):
        self.gui.toggle_recording()
        self.gui.toggle_recording()
        self.assertEqual(
            self.gui.mic_button._config.get("fg_color"),
            design_system.buttons.primary_bg,
        )

    def test_callback_called_on_toggle(self):
        calls = []
        gui = AppGUI(on_mic_toggle=lambda recording: calls.append(recording))
        gui.toggle_recording()
        self.assertEqual(calls, [True])

    def test_callback_called_with_false_on_stop(self):
        calls = []
        gui = AppGUI(on_mic_toggle=lambda recording: calls.append(recording))
        gui.toggle_recording()
        gui.toggle_recording()
        self.assertEqual(calls, [True, False])

    def test_no_callback_does_not_raise(self):
        gui = AppGUI(on_mic_toggle=None)
        gui.toggle_recording()  # should not raise

    def test_start_recording_ui_sets_state(self):
        self.gui.start_recording_ui()
        self.assertTrue(self.gui._is_recording)
        self.assertEqual(self.gui.mic_button._config.get("text"), AppGUI.MIC_TEXT_RECORDING)

    def test_stop_recording_ui_clears_state(self):
        self.gui.start_recording_ui()
        self.gui.stop_recording_ui()
        self.assertFalse(self.gui._is_recording)
        self.assertEqual(self.gui.mic_button._config.get("text"), AppGUI.MIC_TEXT_IDLE)

    def test_pulse_animation_schedules_after(self):
        self.gui.start_recording_ui()
        # start_recording_ui calls _pulse_animation which should schedule an after()
        self.assertIsNotNone(self.gui._pulse_after_id)
        self.assertIn(self.gui._pulse_after_id, self.gui._after_callbacks)

    def test_pulse_animation_alternates_color(self):
        self.gui.start_recording_ui()
        # First pulse call sets fg_color to danger_bg_hover (since it was error)
        first_fg = self.gui.mic_button._config.get("fg_color")
        # Manually invoke the scheduled callback to simulate the pulse
        after_id = self.gui._pulse_after_id
        _, func, _ = self.gui._after_callbacks[after_id]
        func()
        second_fg = self.gui.mic_button._config.get("fg_color")
        self.assertNotEqual(first_fg, second_fg)

    def test_stop_recording_cancels_pulse(self):
        self.gui.start_recording_ui()
        after_id = self.gui._pulse_after_id
        self.gui.stop_recording_ui()
        self.assertIsNone(self.gui._pulse_after_id)
        self.assertNotIn(after_id, self.gui._after_callbacks)


class TestTranscriptMessages(unittest.TestCase):
    """Verify add_transcript_message and clear_transcript behaviour."""

    def setUp(self):
        self.gui = AppGUI()

    def test_add_user_message(self):
        self.gui.add_transcript_message("user", "Hello")
        content = self.gui.transcript_textbox.get("1.0", "end")
        self.assertIn("You: Hello", content)

    def test_add_assistant_message(self):
        self.gui.add_transcript_message("assistant", "Hi there")
        content = self.gui.transcript_textbox.get("1.0", "end")
        self.assertIn("Bot: Hi there", content)

    def test_multiple_messages_appended(self):
        self.gui.add_transcript_message("user", "First")
        self.gui.add_transcript_message("assistant", "Second")
        content = self.gui.transcript_textbox.get("1.0", "end")
        self.assertIn("You: First", content)
        self.assertIn("Bot: Second", content)

    def test_message_order_preserved(self):
        self.gui.add_transcript_message("user", "A")
        self.gui.add_transcript_message("assistant", "B")
        content = self.gui.transcript_textbox.get("1.0", "end")
        idx_a = content.index("You: A")
        idx_b = content.index("Bot: B")
        self.assertLess(idx_a, idx_b)

    def test_auto_scroll_called(self):
        self.gui.add_transcript_message("user", "Scroll test")
        self.assertIn("end", self.gui.transcript_textbox._see_calls)

    def test_textbox_returns_to_disabled(self):
        self.gui.add_transcript_message("user", "Check state")
        self.assertEqual(
            self.gui.transcript_textbox._config.get("state"), "disabled"
        )

    def test_clear_transcript_empties_textbox(self):
        self.gui.add_transcript_message("user", "To be cleared")
        self.gui.clear_transcript()
        content = self.gui.transcript_textbox.get("1.0", "end")
        self.assertEqual(content, "")

    def test_clear_transcript_returns_to_disabled(self):
        self.gui.add_transcript_message("user", "Something")
        self.gui.clear_transcript()
        self.assertEqual(
            self.gui.transcript_textbox._config.get("state"), "disabled"
        )

    def test_unknown_role_uses_bot_prefix(self):
        self.gui.add_transcript_message("system", "System msg")
        content = self.gui.transcript_textbox.get("1.0", "end")
        self.assertIn("Bot: System msg", content)


if __name__ == "__main__":
    unittest.main()
