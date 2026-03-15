"""Audio player using sounddevice with playback start/end callbacks.

Provides an AudioPlayer class that plays audio bytes (WAV or raw PCM)
through the default output device via sounddevice. Fires an on_start
callback when the first audio frame is actually played and an on_end
callback when playback completes.
"""

from __future__ import annotations

import io
import struct
import threading
import wave
from typing import Callable

import numpy as np
import sounddevice as sd

# Default playback parameters (matches mic_recorder constants)
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_DTYPE = "int16"


class AudioPlayerError(Exception):
    """Raised when the audio player encounters an error."""


class AudioPlayer:
    """Plays audio via sounddevice with start/end callbacks.

    Parameters
    ----------
    sample_rate:
        Sample rate for raw PCM playback. Ignored when playing WAV
        files (the WAV header sample rate is used instead).
    channels:
        Number of channels for raw PCM playback. Ignored for WAV.
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
    ) -> None:
        self._default_sample_rate = sample_rate
        self._default_channels = channels
        self._lock = threading.Lock()
        self._playing = False
        self._stop_event = threading.Event()
        self._playback_thread: threading.Thread | None = None

    @property
    def is_playing(self) -> bool:
        """Return whether audio is currently playing."""
        return self._playing

    def play(
        self,
        audio_data: bytes,
        on_start: Callable[[], None] | None = None,
        on_end: Callable[[], None] | None = None,
    ) -> None:
        """Play audio via sounddevice with start/end callbacks.

        Parameters
        ----------
        audio_data:
            Audio bytes — either a complete WAV file or raw PCM
            int16 samples.
        on_start:
            Called when the first audio frame is actually played.
        on_end:
            Called when playback completes (or is stopped).

        Raises
        ------
        AudioPlayerError
            If already playing, audio_data is empty, or playback fails.
        """
        with self._lock:
            if self._playing:
                raise AudioPlayerError("Already playing audio")

        if not audio_data:
            raise AudioPlayerError("No audio data provided")

        try:
            samples, sample_rate, channels = self._decode_audio(audio_data)
        except Exception as exc:
            raise AudioPlayerError(f"Failed to decode audio data: {exc}") from exc

        with self._lock:
            self._playing = True
            self._stop_event.clear()

        self._playback_thread = threading.Thread(
            target=self._playback_worker,
            args=(samples, sample_rate, channels, on_start, on_end),
            daemon=True,
        )
        self._playback_thread.start()

    def stop(self) -> None:
        """Stop current playback.

        Safe to call even if nothing is playing.
        """
        self._stop_event.set()
        sd.stop()
        if self._playback_thread is not None:
            self._playback_thread.join(timeout=2.0)
            self._playback_thread = None
        with self._lock:
            self._playing = False

    def _decode_audio(self, audio_data: bytes) -> tuple[np.ndarray, int, int]:
        """Decode audio bytes into a numpy array.

        Attempts to read as WAV first; falls back to raw PCM int16.

        Returns
        -------
        tuple[np.ndarray, int, int]
            (samples, sample_rate, channels)
        """
        # Try WAV first
        try:
            buf = io.BytesIO(audio_data)
            with wave.open(buf, "rb") as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
                samples = np.frombuffer(raw, dtype=np.int16)
                if channels > 1:
                    samples = samples.reshape(-1, channels)
                return samples, sample_rate, channels
        except (wave.Error, EOFError, struct.error):
            pass

        # Fall back to raw PCM int16
        if len(audio_data) % 2 != 0:
            raise AudioPlayerError(
                "Raw PCM data length must be even (int16 = 2 bytes per sample)"
            )
        samples = np.frombuffer(audio_data, dtype=np.int16)
        return samples, self._default_sample_rate, self._default_channels

    def _playback_worker(
        self,
        samples: np.ndarray,
        sample_rate: int,
        channels: int,
        on_start: Callable[[], None] | None,
        on_end: Callable[[], None] | None,
    ) -> None:
        """Background thread that performs the actual playback."""
        started = False
        try:
            if self._stop_event.is_set():
                return

            # Use a blocking OutputStream so we know exactly when frames
            # are written to the device.
            blocksize = 1024
            total_frames = len(samples) if samples.ndim == 1 else samples.shape[0]
            offset = 0

            with sd.OutputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype=DEFAULT_DTYPE,
                blocksize=blocksize,
            ) as stream:
                while offset < total_frames and not self._stop_event.is_set():
                    end = min(offset + blocksize, total_frames)
                    chunk = samples[offset:end]

                    # Pad the last chunk if needed
                    if len(chunk) < blocksize:
                        if samples.ndim == 1:
                            chunk = np.pad(chunk, (0, blocksize - len(chunk)))
                        else:
                            chunk = np.pad(
                                chunk,
                                ((0, blocksize - len(chunk)), (0, 0)),
                            )

                    stream.write(chunk)

                    if not started:
                        started = True
                        if on_start is not None:
                            try:
                                on_start()
                            except Exception:
                                pass

                    offset = end
        except Exception as exc:
            # Playback failed — still mark as not playing
            _ = exc
        finally:
            with self._lock:
                self._playing = False
            if on_end is not None:
                try:
                    on_end()
                except Exception:
                    pass
