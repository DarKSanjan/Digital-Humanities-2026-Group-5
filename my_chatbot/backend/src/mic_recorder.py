"""Microphone recorder using pyaudio with background thread capture.

Provides a MicRecorder class that captures audio from the default
microphone in a background thread, supports start/stop toggle, and
returns WAV bytes. Includes RMS-based silence detection.
"""

from __future__ import annotations

import io
import math
import struct
import threading
import wave
from typing import Callable

import pyaudio

# Audio format constants (Whisper-compatible)
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 1024

# Default silence detection threshold (int16 RMS scale)
DEFAULT_SILENCE_THRESHOLD = 500

# Default sustained silence duration in seconds
DEFAULT_SILENCE_DURATION = 2.5


class SilenceDetector:
    """Tracks consecutive silent frames and reports sustained silence.

    Parameters
    ----------
    threshold:
        RMS value below which a frame is considered silent.
    silence_duration:
        Seconds of continuous silence required to trigger detection.
    sample_rate:
        Audio sample rate in Hz.
    frame_size:
        Number of samples per frame.
    """

    def __init__(
        self,
        threshold: int = DEFAULT_SILENCE_THRESHOLD,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        sample_rate: int = SAMPLE_RATE,
        frame_size: int = FRAMES_PER_BUFFER,
    ) -> None:
        self.threshold = threshold
        self.silence_duration = silence_duration
        self.frame_duration = frame_size / sample_rate
        self._silent_frames: int = 0
        self._frames_needed = math.ceil(silence_duration / self.frame_duration)

    @property
    def silence_detected(self) -> bool:
        """Return True if sustained silence threshold has been reached."""
        return self._silent_frames >= self._frames_needed

    def process_frame(self, frame: bytes) -> bool:
        """Process an audio frame and update the silence counter.

        Parameters
        ----------
        frame:
            Raw audio bytes (int16 samples).

        Returns
        -------
        bool
            True if sustained silence has been detected.
        """
        rms = MicRecorder._compute_rms(frame)
        if rms < self.threshold:
            self._silent_frames += 1
        else:
            self._silent_frames = 0
        return self.silence_detected

    def reset(self) -> None:
        """Reset the silence counter."""
        self._silent_frames = 0


class MicRecorderError(Exception):
    """Raised when the mic recorder encounters an error."""


class MicRecorder:
    """Captures audio from the default microphone via pyaudio.

    Audio is captured in a background thread. Call ``start_recording``
    to begin and ``stop_recording`` to stop and retrieve WAV bytes.

    Parameters
    ----------
    silence_threshold:
        RMS threshold below which a frame is considered silence.
        Defaults to ``DEFAULT_SILENCE_THRESHOLD`` (500).
    """

    def __init__(
        self,
        silence_threshold: int = DEFAULT_SILENCE_THRESHOLD,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        on_silence: Callable[[], None] | None = None,
    ) -> None:
        self.silence_threshold = silence_threshold
        self._on_silence = on_silence
        self._silence_detector = SilenceDetector(
            threshold=silence_threshold,
            silence_duration=silence_duration,
        )
        self._frames: list[bytes] = []
        self._recording = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._pa: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None

    @property
    def is_recording(self) -> bool:
        """Return whether the recorder is currently capturing audio."""
        return self._recording

    def start_recording(self) -> None:
        """Start pyaudio stream capture in a background thread.

        Raises
        ------
        MicRecorderError
            If already recording or if microphone access fails.
        """
        with self._lock:
            if self._recording:
                raise MicRecorderError("Already recording")

            self._frames = []
            self._recording = True
            self._silence_detector.reset()

        try:
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=FRAMES_PER_BUFFER,
            )
        except Exception as exc:
            with self._lock:
                self._recording = False
            if self._stream is not None:
                try:
                    self._stream.close()
                except Exception:
                    pass
            if self._pa is not None:
                try:
                    self._pa.terminate()
                except Exception:
                    pass
            self._stream = None
            self._pa = None
            raise MicRecorderError(f"Failed to open microphone: {exc}") from exc

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop_recording(self) -> bytes:
        """Stop recording and return captured audio as WAV bytes.

        Returns
        -------
        bytes
            WAV-formatted audio data.

        Raises
        ------
        MicRecorderError
            If not currently recording.
        """
        with self._lock:
            if not self._recording:
                raise MicRecorderError("Not currently recording")
            self._recording = False

        # Wait for capture thread to finish
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        # Close pyaudio resources
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

        return self._build_wav(self._frames)

    def is_silence(self, frame: bytes) -> bool:
        """Check if an audio frame's RMS is below the silence threshold.

        Parameters
        ----------
        frame:
            Raw audio bytes (int16 samples).

        Returns
        -------
        bool
            True if the frame RMS is below ``silence_threshold``.
        """
        rms = self._compute_rms(frame)
        return rms < self.silence_threshold

    @staticmethod
    def _compute_rms(frame: bytes) -> float:
        """Compute the RMS energy of an int16 audio frame.

        Parameters
        ----------
        frame:
            Raw audio bytes (int16 little-endian samples).

        Returns
        -------
        float
            The RMS value of the frame.
        """
        if not frame:
            return 0.0

        num_samples = len(frame) // SAMPLE_WIDTH
        if num_samples == 0:
            return 0.0

        samples = struct.unpack(f"<{num_samples}h", frame[:num_samples * SAMPLE_WIDTH])
        sum_squares = sum(s * s for s in samples)
        return math.sqrt(sum_squares / num_samples)

    def _capture_loop(self) -> None:
        """Background thread loop that reads frames from the pyaudio stream."""
        silence_fired = False
        while self._recording:
            try:
                data = self._stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                self._frames.append(data)
                if not silence_fired and self._silence_detector.process_frame(data):
                    silence_fired = True
                    if self._on_silence is not None:
                        self._on_silence()
            except Exception:
                break

    @staticmethod
    def _build_wav(frames: list[bytes]) -> bytes:
        """Build a WAV file from raw PCM frames.

        Parameters
        ----------
        frames:
            List of raw PCM audio byte chunks.

        Returns
        -------
        bytes
            Complete WAV file bytes.
        """
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()
