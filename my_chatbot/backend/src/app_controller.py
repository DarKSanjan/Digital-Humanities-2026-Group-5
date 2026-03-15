"""Application controller wiring GUI events to the streaming pipeline.

Connects the AppGUI mic button to MicRecorder, STT transcription,
and StreamingPipeline. Manages session state transitions and
transcript updates between the pipeline and the GUI.

Requirements: 3.1, 3.2, 3.3, 1.1, 4.5
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Callable

from src.app_gui import AppGUI
from src.mic_recorder import MicRecorder, MicRecorderError
from src.retry import async_retry
from src.stt_service import STTServiceError, transcribe
from src.streaming_pipeline import StreamingPipeline

logger = logging.getLogger(__name__)


class AppController:
    """Coordinates GUI ↔ MicRecorder ↔ STT ↔ StreamingPipeline.

    Parameters
    ----------
    gui:
        The :class:`AppGUI` instance to drive.
    pipeline:
        The :class:`StreamingPipeline` that processes user text.
    mic_recorder:
        Optional :class:`MicRecorder`; one is created if not supplied.
    transcribe_fn:
        Async callable ``(bytes) -> str`` used for speech-to-text.
        Defaults to :func:`stt_service.transcribe`.
    """

    def __init__(
        self,
        gui: AppGUI,
        pipeline: StreamingPipeline,
        mic_recorder: MicRecorder | None = None,
        transcribe_fn: Callable | None = None,
    ) -> None:
        self._gui = gui
        self._pipeline = pipeline
        self._transcribe = transcribe_fn or transcribe

        # Create mic recorder with silence callback wired to auto-stop
        self._mic = mic_recorder or MicRecorder(on_silence=self._on_silence)

        # If an external recorder was provided without an on_silence
        # callback, patch it in so silence auto-stop still works.
        if mic_recorder is not None and mic_recorder._on_silence is None:
            mic_recorder._on_silence = self._on_silence

        # Wire the GUI mic-toggle callback
        self._gui._on_mic_toggle = self._on_mic_toggle

        # Async event loop running in a background thread
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_loop, daemon=True,
        )
        self._loop_thread.start()

    def _run_loop(self) -> None:
        """Target for the background thread — runs the event loop."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def stop(self) -> None:
        """Shut down the background event loop."""
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=3.0)
            self._loop_thread = None
        if self._loop is not None:
            self._loop.close()
            self._loop = None

    # ------------------------------------------------------------------
    # GUI callback
    # ------------------------------------------------------------------

    def _on_mic_toggle(self, is_recording: bool) -> None:
        """Called by AppGUI when the mic button is toggled.

        *is_recording* is ``True`` when recording just started,
        ``False`` when it just stopped.
        """
        if is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def _start_recording(self) -> None:
        """Begin mic capture and update GUI to 'listening'."""
        try:
            self._mic.start_recording()
            self._gui_call(self._gui.set_session_state, "listening")
        except MicRecorderError as exc:
            logger.error("Mic start failed: %s", exc)
            self._gui_call(self._gui.set_session_state, "idle")
            self._gui_call(self._gui.set_status, f"Mic error: {exc}")
            # Revert the button UI since recording didn't actually start
            self._gui_call(self._gui.stop_recording_ui)
            # Disable mic button so user cannot keep clicking a broken mic
            self._gui_call(self._gui.disable_mic_button)

    def _stop_recording(self) -> None:
        """Stop mic capture, then transcribe + run pipeline asynchronously."""
        try:
            wav_bytes = self._mic.stop_recording()
        except MicRecorderError as exc:
            logger.error("Mic stop failed: %s", exc)
            self._gui_call(self._gui.set_session_state, "idle")
            return

        self._gui_call(self._gui.set_session_state, "processing")

        # Offload async work to the background event loop
        if self._loop is not None and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._transcribe_and_process(wav_bytes), self._loop,
            )

    # ------------------------------------------------------------------
    # Silence auto-stop
    # ------------------------------------------------------------------

    def _on_silence(self) -> None:
        """Called by MicRecorder when sustained silence is detected.

        Triggers stop-recording from the GUI's main thread so the
        button visuals update correctly.
        """
        self._gui_call(self._gui.toggle_recording)

    # ------------------------------------------------------------------
    # Async pipeline
    # ------------------------------------------------------------------

    async def _transcribe_and_process(self, wav_bytes: bytes) -> None:
        """Transcribe WAV audio then feed text into the pipeline."""
        try:
            text = await async_retry(
                self._transcribe,
                wav_bytes,
                max_retries=2,
                base_delay=1.0,
                retryable_exceptions=(STTServiceError,),
            )
        except STTServiceError as exc:
            logger.error("STT failed after retries: %s", exc)
            self._gui_call(self._gui.set_session_state, "idle")
            self._gui_call(
                self._gui.set_status,
                "Transcription failed — please try recording again",
            )
            return

        if not text or not text.strip():
            self._gui_call(self._gui.set_session_state, "idle")
            return

        # Show user message in transcript
        self._gui_call(self._gui.add_transcript_message, "user", text)

        # Wrap pipeline callbacks so state/transcript updates hit the GUI
        original_set_status = self._pipeline.set_status

        def _patched_set_status(status: str) -> None:
            original_set_status(status)
            self._gui_call(self._gui.set_session_state, status)

        self._pipeline.set_status = _patched_set_status  # type: ignore[assignment]

        try:
            await self._pipeline.process_user_input(text)
        except Exception as exc:
            logger.exception("Pipeline error: %s", exc)
            self._gui_call(self._gui.set_session_state, "idle")
            self._gui_call(
                self._gui.set_status,
                "Something went wrong — please try again",
            )
            return
        finally:
            self._pipeline.set_status = original_set_status  # type: ignore[assignment]

        # If the pipeline recorded an error (e.g. LLM failure), surface it
        if self._pipeline.session.error:
            self._gui_call(
                self._gui.set_status,
                "Response failed — please try again",
            )
            return

        # Show assistant reply in transcript
        if self._pipeline.session.transcript:
            last = self._pipeline.session.transcript[-1]
            if last.role == "assistant":
                self._gui_call(
                    self._gui.add_transcript_message, "assistant", last.content,
                )

        # Pipeline returns to idle on its own, but ensure GUI matches
        self._gui_call(self._gui.set_session_state, "idle")

    # ------------------------------------------------------------------
    # Thread-safe GUI helper
    # ------------------------------------------------------------------

    def _gui_call(self, fn: Callable, *args) -> None:
        """Schedule *fn(*args)* on the tkinter main thread."""
        try:
            self._gui.after(0, fn, *args)
        except Exception:
            # GUI may have been destroyed
            pass
