"""Unit tests for mic_recorder — pyaudio microphone capture with silence detection."""

import io
import math
import struct
import threading
import wave
from unittest.mock import MagicMock, patch

import pytest

from src.mic_recorder import (
    CHANNELS,
    DEFAULT_SILENCE_DURATION,
    DEFAULT_SILENCE_THRESHOLD,
    FORMAT,
    FRAMES_PER_BUFFER,
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    MicRecorder,
    MicRecorderError,
    SilenceDetector,
)


# --- Helpers ---


def _make_frame(value: int, num_samples: int = FRAMES_PER_BUFFER) -> bytes:
    """Create a raw int16 audio frame with all samples set to *value*."""
    return struct.pack(f"<{num_samples}h", *([value] * num_samples))


def _make_sine_frame(amplitude: int, num_samples: int = FRAMES_PER_BUFFER) -> bytes:
    """Create a raw int16 audio frame with a simple pattern for RMS testing."""
    # Alternating +amplitude and -amplitude gives RMS == amplitude
    samples = [amplitude if i % 2 == 0 else -amplitude for i in range(num_samples)]
    return struct.pack(f"<{num_samples}h", *samples)


def _parse_wav(wav_bytes: bytes) -> dict:
    """Parse WAV bytes and return metadata + raw frames."""
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        return {
            "channels": wf.getnchannels(),
            "sample_width": wf.getsampwidth(),
            "framerate": wf.getframerate(),
            "frames": wf.readframes(wf.getnframes()),
            "nframes": wf.getnframes(),
        }


# --- Tests: Constants ---


class TestConstants:
    def test_sample_rate_is_whisper_compatible(self):
        assert SAMPLE_RATE == 16000

    def test_channels_mono(self):
        assert CHANNELS == 1

    def test_sample_width_16bit(self):
        assert SAMPLE_WIDTH == 2

    def test_default_silence_threshold(self):
        assert DEFAULT_SILENCE_THRESHOLD == 500


# --- Tests: is_silence ---


class TestIsSilence:
    def test_silent_frame_detected(self):
        recorder = MicRecorder(silence_threshold=500)
        frame = _make_frame(0)  # all zeros → RMS = 0
        assert recorder.is_silence(frame) is True

    def test_loud_frame_not_silence(self):
        recorder = MicRecorder(silence_threshold=500)
        frame = _make_frame(1000)  # RMS = 1000
        assert recorder.is_silence(frame) is False

    def test_frame_at_threshold_not_silence(self):
        """Frame with RMS exactly at threshold is not silence (strict <)."""
        recorder = MicRecorder(silence_threshold=500)
        frame = _make_frame(500)  # RMS = 500
        assert recorder.is_silence(frame) is False

    def test_frame_just_below_threshold(self):
        recorder = MicRecorder(silence_threshold=500)
        frame = _make_frame(499)  # RMS = 499
        assert recorder.is_silence(frame) is True

    def test_empty_frame_is_silence(self):
        recorder = MicRecorder(silence_threshold=500)
        assert recorder.is_silence(b"") is True

    def test_custom_threshold(self):
        recorder = MicRecorder(silence_threshold=100)
        frame = _make_frame(200)
        assert recorder.is_silence(frame) is False

        frame_quiet = _make_frame(50)
        assert recorder.is_silence(frame_quiet) is True


# --- Tests: _compute_rms ---


class TestComputeRms:
    def test_zero_frame(self):
        frame = _make_frame(0, num_samples=10)
        assert MicRecorder._compute_rms(frame) == 0.0

    def test_constant_frame(self):
        frame = _make_frame(1000, num_samples=10)
        rms = MicRecorder._compute_rms(frame)
        assert rms == pytest.approx(1000.0)

    def test_empty_bytes(self):
        assert MicRecorder._compute_rms(b"") == 0.0

    def test_single_sample(self):
        frame = struct.pack("<h", 500)
        rms = MicRecorder._compute_rms(frame)
        assert rms == pytest.approx(500.0)

    def test_alternating_values(self):
        """RMS of alternating +A/-A should be A."""
        frame = _make_sine_frame(300, num_samples=100)
        rms = MicRecorder._compute_rms(frame)
        assert rms == pytest.approx(300.0)


# --- Tests: _build_wav ---


class TestBuildWav:
    def test_empty_frames_produces_valid_wav(self):
        wav_bytes = MicRecorder._build_wav([])
        info = _parse_wav(wav_bytes)
        assert info["channels"] == CHANNELS
        assert info["sample_width"] == SAMPLE_WIDTH
        assert info["framerate"] == SAMPLE_RATE
        assert info["nframes"] == 0

    def test_single_frame_round_trip(self):
        frame = _make_frame(42, num_samples=10)
        wav_bytes = MicRecorder._build_wav([frame])
        info = _parse_wav(wav_bytes)
        assert info["channels"] == CHANNELS
        assert info["sample_width"] == SAMPLE_WIDTH
        assert info["framerate"] == SAMPLE_RATE
        assert info["frames"] == frame

    def test_multiple_frames_concatenated(self):
        frame1 = _make_frame(100, num_samples=5)
        frame2 = _make_frame(200, num_samples=5)
        wav_bytes = MicRecorder._build_wav([frame1, frame2])
        info = _parse_wav(wav_bytes)
        assert info["frames"] == frame1 + frame2


# --- Tests: start/stop recording ---


class TestStartStopRecording:
    def test_start_sets_recording_flag(self):
        recorder = MicRecorder()
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        # Make read block until recording stops
        mock_stream.read.side_effect = lambda *a, **kw: (
            _make_frame(0) if recorder.is_recording else (_ for _ in ()).throw(StopIteration)
        )

        with patch("src.mic_recorder.pyaudio.PyAudio", return_value=mock_pa):
            recorder.start_recording()
            assert recorder.is_recording is True
            recorder.stop_recording()
            assert recorder.is_recording is False

    def test_double_start_raises(self):
        recorder = MicRecorder()
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        mock_stream.read.side_effect = lambda *a, **kw: _make_frame(0)

        with patch("src.mic_recorder.pyaudio.PyAudio", return_value=mock_pa):
            recorder.start_recording()
            with pytest.raises(MicRecorderError, match="Already recording"):
                recorder.start_recording()
            recorder.stop_recording()

    def test_stop_without_start_raises(self):
        recorder = MicRecorder()
        with pytest.raises(MicRecorderError, match="Not currently recording"):
            recorder.stop_recording()

    def test_stop_returns_wav_bytes(self):
        recorder = MicRecorder()
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream

        test_frame = _make_frame(42, num_samples=10)
        call_count = 0

        def fake_read(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return test_frame
            # After 3 frames, simulate end
            raise OSError("stream closed")

        mock_stream.read.side_effect = fake_read

        with patch("src.mic_recorder.pyaudio.PyAudio", return_value=mock_pa):
            recorder.start_recording()
            # Give the thread a moment to capture frames
            import time
            time.sleep(0.1)
            wav_bytes = recorder.stop_recording()

        # Verify it's valid WAV
        info = _parse_wav(wav_bytes)
        assert info["channels"] == CHANNELS
        assert info["sample_width"] == SAMPLE_WIDTH
        assert info["framerate"] == SAMPLE_RATE
        assert len(info["frames"]) > 0

    def test_mic_open_failure_raises_error(self):
        recorder = MicRecorder()
        mock_pa = MagicMock()
        mock_pa.open.side_effect = OSError("No microphone found")

        with patch("src.mic_recorder.pyaudio.PyAudio", return_value=mock_pa):
            with pytest.raises(MicRecorderError, match="Failed to open microphone"):
                recorder.start_recording()

        # Should not be in recording state after failure
        assert recorder.is_recording is False

    def test_pyaudio_resources_cleaned_on_stop(self):
        recorder = MicRecorder()
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        mock_stream.read.side_effect = lambda *a, **kw: _make_frame(0)

        with patch("src.mic_recorder.pyaudio.PyAudio", return_value=mock_pa):
            recorder.start_recording()
            recorder.stop_recording()

        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_pa.terminate.assert_called_once()


# --- Tests: SilenceDetector ---


class TestSilenceDetector:
    def test_default_parameters(self):
        sd = SilenceDetector()
        assert sd.threshold == DEFAULT_SILENCE_THRESHOLD
        assert sd.silence_duration == DEFAULT_SILENCE_DURATION
        assert sd.frame_duration == FRAMES_PER_BUFFER / SAMPLE_RATE

    def test_frames_needed_calculation(self):
        sd = SilenceDetector(silence_duration=2.5, sample_rate=16000, frame_size=1024)
        frame_dur = 1024 / 16000  # 0.064s
        expected = math.ceil(2.5 / frame_dur)  # 40
        assert sd._frames_needed == expected

    def test_no_silence_initially(self):
        sd = SilenceDetector()
        assert sd.silence_detected is False

    def test_single_silent_frame_not_enough(self):
        sd = SilenceDetector()
        silent_frame = _make_frame(0)
        sd.process_frame(silent_frame)
        assert sd.silence_detected is False

    def test_sustained_silence_triggers_detection(self):
        sd = SilenceDetector(silence_duration=2.5, sample_rate=16000, frame_size=1024)
        silent_frame = _make_frame(0)
        for _ in range(sd._frames_needed - 1):
            result = sd.process_frame(silent_frame)
            assert result is False
        result = sd.process_frame(silent_frame)
        assert result is True
        assert sd.silence_detected is True

    def test_loud_frame_resets_counter(self):
        sd = SilenceDetector(silence_duration=2.5, sample_rate=16000, frame_size=1024)
        silent_frame = _make_frame(0)
        loud_frame = _make_frame(1000)
        # Feed almost enough silent frames
        for _ in range(sd._frames_needed - 1):
            sd.process_frame(silent_frame)
        # Interrupt with a loud frame
        sd.process_frame(loud_frame)
        assert sd.silence_detected is False
        # Need full duration again
        for _ in range(sd._frames_needed - 1):
            sd.process_frame(silent_frame)
        assert sd.silence_detected is False

    def test_reset_clears_counter(self):
        sd = SilenceDetector(silence_duration=2.5, sample_rate=16000, frame_size=1024)
        silent_frame = _make_frame(0)
        for _ in range(sd._frames_needed):
            sd.process_frame(silent_frame)
        assert sd.silence_detected is True
        sd.reset()
        assert sd.silence_detected is False

    def test_frame_at_threshold_is_not_silent(self):
        sd = SilenceDetector(threshold=500)
        frame = _make_frame(500)  # RMS == 500, not < 500
        for _ in range(sd._frames_needed + 10):
            sd.process_frame(frame)
        assert sd.silence_detected is False

    def test_frame_just_below_threshold_is_silent(self):
        sd = SilenceDetector(threshold=500)
        frame = _make_frame(499)
        for _ in range(sd._frames_needed):
            sd.process_frame(frame)
        assert sd.silence_detected is True

    def test_custom_short_duration(self):
        """Short silence duration needs fewer frames."""
        sd = SilenceDetector(silence_duration=0.128, sample_rate=16000, frame_size=1024)
        # 0.128s / 0.064s = 2 frames needed
        assert sd._frames_needed == 2
        silent_frame = _make_frame(0)
        sd.process_frame(silent_frame)
        assert sd.silence_detected is False
        sd.process_frame(silent_frame)
        assert sd.silence_detected is True


# --- Tests: MicRecorder silence callback integration ---


class TestMicRecorderSilenceCallback:
    def test_on_silence_callback_fires_on_sustained_silence(self):
        callback_called = threading.Event()
        recorder = MicRecorder(
            silence_threshold=500,
            silence_duration=0.128,  # 2 frames at 1024/16000
            on_silence=lambda: callback_called.set(),
        )
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream

        silent_frame = _make_frame(0)
        call_count = 0

        def fake_read(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 5:
                return silent_frame
            raise OSError("done")

        mock_stream.read.side_effect = fake_read

        with patch("src.mic_recorder.pyaudio.PyAudio", return_value=mock_pa):
            recorder.start_recording()
            # Wait for callback or timeout
            assert callback_called.wait(timeout=2.0), "on_silence callback was not called"
            recorder.stop_recording()

    def test_on_silence_not_called_with_loud_frames(self):
        callback_called = threading.Event()
        recorder = MicRecorder(
            silence_threshold=500,
            silence_duration=0.128,
            on_silence=lambda: callback_called.set(),
        )
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream

        loud_frame = _make_frame(1000)
        call_count = 0

        def fake_read(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 5:
                return loud_frame
            raise OSError("done")

        mock_stream.read.side_effect = fake_read

        with patch("src.mic_recorder.pyaudio.PyAudio", return_value=mock_pa):
            recorder.start_recording()
            import time
            time.sleep(0.3)
            recorder.stop_recording()
        assert not callback_called.is_set()

    def test_silence_detector_resets_on_new_recording(self):
        recorder = MicRecorder(silence_threshold=500, silence_duration=0.128)
        # Manually feed frames to the internal detector to simulate prior state
        silent_frame = _make_frame(0)
        for _ in range(recorder._silence_detector._frames_needed):
            recorder._silence_detector.process_frame(silent_frame)
        assert recorder._silence_detector.silence_detected is True

        # Starting a new recording should reset
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        mock_stream.read.side_effect = lambda *a, **kw: _make_frame(1000)

        with patch("src.mic_recorder.pyaudio.PyAudio", return_value=mock_pa):
            recorder.start_recording()
            assert recorder._silence_detector.silence_detected is False
            recorder.stop_recording()
