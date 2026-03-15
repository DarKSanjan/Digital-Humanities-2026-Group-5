"""Unit tests for audio_player — sounddevice playback with on_start/on_end callbacks."""

import io
import struct
import threading
import wave
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest

from src.audio_player import (
    DEFAULT_CHANNELS,
    DEFAULT_DTYPE,
    DEFAULT_SAMPLE_RATE,
    AudioPlayer,
    AudioPlayerError,
)


# --- Helpers ---


def _make_wav_bytes(
    samples: list[int],
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
    sample_width: int = 2,
) -> bytes:
    """Create WAV bytes from a list of int16 sample values."""
    buf = io.BytesIO()
    raw = struct.pack(f"<{len(samples)}h", *samples)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(raw)
    return buf.getvalue()


def _make_raw_pcm(samples: list[int]) -> bytes:
    """Create raw PCM int16 bytes from a list of sample values."""
    return struct.pack(f"<{len(samples)}h", *samples)


# --- Tests: Initialization ---


class TestInit:
    def test_default_parameters(self):
        player = AudioPlayer()
        assert player._default_sample_rate == DEFAULT_SAMPLE_RATE
        assert player._default_channels == DEFAULT_CHANNELS
        assert player.is_playing is False

    def test_custom_parameters(self):
        player = AudioPlayer(sample_rate=44100, channels=2)
        assert player._default_sample_rate == 44100
        assert player._default_channels == 2


# --- Tests: _decode_audio ---


class TestDecodeAudio:
    def test_decode_wav(self):
        wav_data = _make_wav_bytes([100, 200, 300], sample_rate=22050)
        player = AudioPlayer()
        samples, sr, ch = player._decode_audio(wav_data)
        assert sr == 22050
        assert ch == 1
        np.testing.assert_array_equal(samples, np.array([100, 200, 300], dtype=np.int16))

    def test_decode_raw_pcm_fallback(self):
        raw = _make_raw_pcm([500, -500, 1000])
        player = AudioPlayer(sample_rate=8000, channels=1)
        samples, sr, ch = player._decode_audio(raw)
        assert sr == 8000
        assert ch == 1
        np.testing.assert_array_equal(samples, np.array([500, -500, 1000], dtype=np.int16))

    def test_decode_odd_length_raw_raises(self):
        player = AudioPlayer()
        with pytest.raises(AudioPlayerError, match="even"):
            player._decode_audio(b"\x00\x01\x02")

    def test_decode_stereo_wav(self):
        # Stereo: interleaved L R L R
        buf = io.BytesIO()
        raw = struct.pack("<4h", 100, 200, 300, 400)
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(raw)
        wav_data = buf.getvalue()

        player = AudioPlayer()
        samples, sr, ch = player._decode_audio(wav_data)
        assert sr == 16000
        assert ch == 2
        assert samples.shape == (2, 2)  # 2 frames, 2 channels


# --- Tests: play() validation ---


class TestPlayValidation:
    def test_empty_audio_raises(self):
        player = AudioPlayer()
        with pytest.raises(AudioPlayerError, match="No audio data"):
            player.play(b"")

    def test_none_callbacks_accepted(self):
        """play() should accept None for both callbacks without error."""
        player = AudioPlayer()
        wav = _make_wav_bytes([0] * 100)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            player.play(wav, on_start=None, on_end=None)
            # Wait for playback thread to finish
            if player._playback_thread:
                player._playback_thread.join(timeout=2.0)

    def test_double_play_raises(self):
        player = AudioPlayer()
        wav = _make_wav_bytes([0] * 2000)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        # Make write block so playback stays active
        block_event = threading.Event()
        mock_stream.write.side_effect = lambda _: block_event.wait(timeout=5.0)

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            player.play(wav)
            # Give thread a moment to start
            import time
            time.sleep(0.05)
            with pytest.raises(AudioPlayerError, match="Already playing"):
                player.play(wav)
            block_event.set()
            player.stop()


# --- Tests: Callbacks ---


class TestCallbacks:
    def test_on_start_fires_on_first_frame(self):
        start_event = threading.Event()
        end_event = threading.Event()

        player = AudioPlayer()
        wav = _make_wav_bytes([100] * 512)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            player.play(
                wav,
                on_start=lambda: start_event.set(),
                on_end=lambda: end_event.set(),
            )
            assert start_event.wait(timeout=2.0), "on_start was not called"
            assert end_event.wait(timeout=2.0), "on_end was not called"

    def test_on_end_fires_after_playback(self):
        end_event = threading.Event()

        player = AudioPlayer()
        wav = _make_wav_bytes([100] * 100)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            player.play(wav, on_end=lambda: end_event.set())
            assert end_event.wait(timeout=2.0), "on_end was not called"
            assert player.is_playing is False

    def test_on_start_called_before_on_end(self):
        order = []

        player = AudioPlayer()
        wav = _make_wav_bytes([100] * 512)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            player.play(
                wav,
                on_start=lambda: order.append("start"),
                on_end=lambda: order.append("end"),
            )
            if player._playback_thread:
                player._playback_thread.join(timeout=2.0)

        assert order == ["start", "end"]

    def test_callback_exception_does_not_crash_playback(self):
        end_event = threading.Event()

        player = AudioPlayer()
        wav = _make_wav_bytes([100] * 512)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        def bad_start():
            raise RuntimeError("callback error")

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            player.play(
                wav,
                on_start=bad_start,
                on_end=lambda: end_event.set(),
            )
            assert end_event.wait(timeout=2.0), "on_end should still fire"

    def test_on_end_fires_even_on_playback_error(self):
        end_event = threading.Event()

        player = AudioPlayer()
        wav = _make_wav_bytes([100] * 512)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.write.side_effect = Exception("device error")

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            player.play(wav, on_end=lambda: end_event.set())
            assert end_event.wait(timeout=2.0), "on_end should fire on error"
            assert player.is_playing is False


# --- Tests: stop() ---


class TestStop:
    def test_stop_interrupts_playback(self):
        end_event = threading.Event()

        player = AudioPlayer()
        # Large audio to ensure playback takes time
        wav = _make_wav_bytes([100] * 100000)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        write_count = 0
        write_event = threading.Event()

        def slow_write(data):
            nonlocal write_count
            write_count += 1
            if write_count == 1:
                write_event.set()
            # Simulate slow write
            import time
            time.sleep(0.01)

        mock_stream.write.side_effect = slow_write

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            with patch("src.audio_player.sd.stop") as mock_sd_stop:
                player.play(wav, on_end=lambda: end_event.set())
                # Wait for at least one write
                write_event.wait(timeout=2.0)
                player.stop()
                assert player.is_playing is False
                mock_sd_stop.assert_called()

    def test_stop_when_not_playing_is_safe(self):
        player = AudioPlayer()
        with patch("src.audio_player.sd.stop"):
            player.stop()  # Should not raise
        assert player.is_playing is False

    def test_is_playing_false_after_natural_end(self):
        player = AudioPlayer()
        wav = _make_wav_bytes([100] * 100)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        done = threading.Event()

        with patch("src.audio_player.sd.OutputStream", return_value=mock_stream):
            player.play(wav, on_end=lambda: done.set())
            done.wait(timeout=2.0)
            assert player.is_playing is False
