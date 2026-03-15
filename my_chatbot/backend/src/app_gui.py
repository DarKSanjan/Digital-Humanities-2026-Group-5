"""
Main customtkinter GUI window for the persuasive chatbot.

Provides a dark-themed, responsive layout with placeholder areas for:
- Avatar display (centered, top)
- Mic button (below avatar)
- Collapsible transcript panel (bottom)
- Status label (bottom bar)

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import customtkinter as ctk
from PIL import Image

from src.design_system import design_system

# Set dark theme globally
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppGUI(ctk.CTk):
    """Main application window with dark theme and responsive grid layout."""

    DEFAULT_WIDTH = 800
    DEFAULT_HEIGHT = 600
    MIN_WIDTH = 480
    MIN_HEIGHT = 400

    # Mic button appearance constants
    MIC_TEXT_IDLE = "🎤  Mic"
    MIC_TEXT_RECORDING = "🔴  Recording"
    PULSE_INTERVAL_MS = 500

    # Session state visual indicators — colors filled in __init__ from design_system
    STATE_CONFIG: dict = {}

    def __init__(self, on_mic_toggle=None):
        super().__init__()

        self._on_mic_toggle = on_mic_toggle
        self._is_recording = False
        self._pulse_after_id = None

        # Build state config with design_system colors
        self._state_config = {
            "idle": {"text": "● Idle", "color": design_system.colors.text_secondary},
            "listening": {"text": "🎤 Listening...", "color": design_system.colors.success},
            "processing": {"text": "⏳ Processing...", "color": design_system.colors.warning},
            "speaking": {"text": "🔊 Speaking...", "color": design_system.colors.info},
        }

        self.title("Persuasive Chatbot")
        self.geometry(f"{self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}")
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.configure(fg_color=design_system.colors.bg_primary)

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self):
        """Create the responsive grid layout with placeholder areas."""
        # Row 0: avatar area   (expands vertically)
        # Row 1: mic button    (fixed height)
        # Row 2: transcript    (expands vertically)
        # Row 3: status bar    (fixed height)
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=2)
        self.grid_rowconfigure(3, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._create_avatar_area()
        self._create_mic_area()
        self._create_transcript_area()
        self._create_status_bar()

    # ------------------------------------------------------------------
    # Placeholder areas
    # ------------------------------------------------------------------

    def _create_avatar_area(self):
        """Centered avatar display area (row 0)."""
        self.avatar_frame = ctk.CTkFrame(
            self,
            fg_color=design_system.colors.bg_secondary,
            corner_radius=12,
        )
        self.avatar_frame.grid(
            row=0, column=0, sticky="nsew",
            padx=design_system.spacing.md, pady=(design_system.spacing.md, design_system.spacing.sm),
        )
        # Centre content inside the avatar frame
        self.avatar_frame.grid_rowconfigure(0, weight=1)
        self.avatar_frame.grid_columnconfigure(0, weight=1)

        # Track the current CTkImage so it isn't garbage-collected
        self._avatar_ctk_image = None

        self.avatar_placeholder = ctk.CTkLabel(
            self.avatar_frame,
            text="Avatar Display",
            font=ctk.CTkFont(
                family=design_system.typography.font_primary,
                size=design_system.typography.size_lg,
            ),
            text_color=design_system.colors.text_tertiary,
        )
        self.avatar_placeholder.grid(row=0, column=0)

    def _create_mic_area(self):
        """Mic button area centred below the avatar (row 1)."""
        self.mic_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mic_frame.grid(
            row=1, column=0,
            pady=design_system.spacing.sm,
        )

        self.mic_button = ctk.CTkButton(
            self.mic_frame,
            text=self.MIC_TEXT_IDLE,
            width=120,
            height=design_system.buttons.height_lg,
            font=ctk.CTkFont(
                family=design_system.typography.font_primary,
                size=design_system.typography.size_base,
                weight="bold",
            ),
            fg_color=design_system.buttons.primary_bg,
            hover_color=design_system.buttons.primary_bg_hover,
            corner_radius=design_system.buttons.border_radius,
            command=self.toggle_recording,
        )
        self.mic_button.pack()

    def _create_transcript_area(self):
        """Collapsible transcript panel (row 2)."""
        self.transcript_frame = ctk.CTkFrame(
            self,
            fg_color=design_system.colors.bg_secondary,
            corner_radius=12,
        )
        self.transcript_frame.grid(
            row=2, column=0, sticky="nsew",
            padx=design_system.spacing.md, pady=design_system.spacing.sm,
        )
        self.transcript_frame.grid_rowconfigure(1, weight=1)
        self.transcript_frame.grid_columnconfigure(0, weight=1)

        # Header row with toggle button
        self._transcript_visible = True

        self.transcript_toggle = ctk.CTkButton(
            self.transcript_frame,
            text="▼ Transcript",
            width=140,
            height=28,
            font=ctk.CTkFont(
                family=design_system.typography.font_primary,
                size=design_system.typography.size_sm,
            ),
            fg_color="transparent",
            hover_color=design_system.colors.bg_tertiary,
            text_color=design_system.colors.text_secondary,
            anchor="w",
            command=self._toggle_transcript,
        )
        self.transcript_toggle.grid(row=0, column=0, sticky="w", padx=8, pady=(4, 0))

        # Scrollable text area
        self.transcript_textbox = ctk.CTkTextbox(
            self.transcript_frame,
            font=ctk.CTkFont(
                family=design_system.typography.font_primary,
                size=design_system.typography.size_sm,
            ),
            fg_color=design_system.colors.bg_tertiary,
            text_color=design_system.colors.text_primary,
            corner_radius=8,
            state="disabled",
        )
        self.transcript_textbox.grid(
            row=1, column=0, sticky="nsew",
            padx=design_system.spacing.sm, pady=design_system.spacing.sm,
        )

    def _create_status_bar(self):
        """Status label at the bottom of the window (row 3)."""
        self.status_frame = ctk.CTkFrame(
            self,
            fg_color=design_system.colors.bg_secondary,
            corner_radius=0,
            height=32,
        )
        self.status_frame.grid(row=3, column=0, sticky="ew")
        self.status_frame.grid_propagate(False)
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="idle",
            font=ctk.CTkFont(
                family=design_system.typography.font_primary,
                size=design_system.typography.size_sm,
            ),
            text_color=design_system.colors.text_secondary,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=design_system.spacing.md)

    # ------------------------------------------------------------------
    # Mic recording toggle
    # ------------------------------------------------------------------

    def toggle_recording(self):
        """Toggle the recording state and update visuals."""
        if self._is_recording:
            self.stop_recording_ui()
        else:
            self.start_recording_ui()
        if self._on_mic_toggle is not None:
            self._on_mic_toggle(self._is_recording)

    def start_recording_ui(self):
        """Set the mic button to recording visual state and start pulse."""
        self._is_recording = True
        self.mic_button.configure(
            text=self.MIC_TEXT_RECORDING,
            fg_color=design_system.colors.error,
            hover_color=design_system.buttons.danger_bg_hover,
        )
        self._pulse_animation()

    def stop_recording_ui(self):
        """Set the mic button back to idle visual state and stop pulse."""
        self._is_recording = False
        if self._pulse_after_id is not None:
            self.after_cancel(self._pulse_after_id)
            self._pulse_after_id = None
        self.mic_button.configure(
            text=self.MIC_TEXT_IDLE,
            fg_color=design_system.buttons.primary_bg,
            hover_color=design_system.buttons.primary_bg_hover,
        )

    def _pulse_animation(self):
        """Alternate the mic button color to create a pulse effect while recording."""
        if not self._is_recording:
            return
        current_fg = self.mic_button._config.get("fg_color", "")
        if current_fg == design_system.colors.error:
            self.mic_button.configure(fg_color=design_system.buttons.danger_bg_hover)
        else:
            self.mic_button.configure(fg_color=design_system.colors.error)
        self._pulse_after_id = self.after(self.PULSE_INTERVAL_MS, self._pulse_animation)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def update_avatar_frame(self, image: Image.Image):
        """Update the avatar display with a new PIL Image frame.

        Accepts a PIL Image (as produced by AvatarWindow rendering),
        wraps it in a CTkImage that scales with the display, and sets
        it on the avatar label.  The placeholder text is cleared on the
        first real frame.
        """
        avatar_size = design_system.layout.avatar_size  # (w, h)
        ctk_img = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=avatar_size,
        )
        # Keep a reference so the image isn't garbage-collected
        self._avatar_ctk_image = ctk_img
        self.avatar_placeholder.configure(image=ctk_img, text="")

    def set_status(self, text: str):
        """Update the status bar text."""
        self.status_label.configure(text=text)

    def set_session_state(self, state: str):
        """Update the status label text and color based on session state.

        Accepts the same state strings as SessionState.status:
        'idle', 'listening', 'processing', 'speaking'.
        Unknown states fall back to idle styling.
        """
        cfg = self._state_config.get(state, self._state_config["idle"])
        self.status_label.configure(text=cfg["text"], text_color=cfg["color"])

    def add_transcript_message(self, role: str, content: str):
        """Append a message to the transcript textbox with role prefix.

        Messages are formatted as "You: <content>" for user messages
        and "Bot: <content>" for assistant messages.  The textbox
        auto-scrolls to show the latest entry.
        """
        prefix = "You" if role == "user" else "Bot"
        line = f"{prefix}: {content}\n"
        self.transcript_textbox.configure(state="normal")
        self.transcript_textbox.insert("end", line)
        self.transcript_textbox.see("end")
        self.transcript_textbox.configure(state="disabled")

    def clear_transcript(self):
        """Remove all text from the transcript textbox."""
        self.transcript_textbox.configure(state="normal")
        self.transcript_textbox.delete("1.0", "end")
        self.transcript_textbox.configure(state="disabled")

    def disable_mic_button(self):
        """Disable the mic button (e.g. after mic access failure)."""
        self.mic_button.configure(state="disabled")

    def enable_mic_button(self):
        """Re-enable the mic button."""
        self.mic_button.configure(state="normal")

    def _toggle_transcript(self):
        """Show or hide the transcript text area."""
        if self._transcript_visible:
            self.transcript_textbox.grid_remove()
            self.transcript_toggle.configure(text="▶ Transcript")
            self._transcript_visible = False
        else:
            self.transcript_textbox.grid()
            self.transcript_toggle.configure(text="▼ Transcript")
            self._transcript_visible = True
