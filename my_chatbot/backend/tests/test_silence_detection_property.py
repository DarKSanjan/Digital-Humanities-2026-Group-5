"""Property-based tests for silence detection correctness.

# Feature: streaming-ui-overhaul, Property 3: Silence detection correctness

For any audio sample buffer where the RMS energy is below the silence threshold
for >= 2500ms continuously, the silence detector should report silence detected.
Conversely, if RMS exceeds the threshold within the 2500ms window, silence
should not be reported.
"""

import numpy as np
from hypothesis import given, settings, assume, strategies as st

from src.mic_recorder import (
    FRAMES_PER_BUFFER,
    SAMPLE_RATE,
    SilenceDetector,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame_from_array(samples: np.ndarray) -> bytes:
    """Pack an int16 numpy array into raw audio bytes."""
    return samples.astype("<i2").tobytes()


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# A reasonable range for the silence threshold (int16 RMS scale)
threshold_strategy = st.integers(min_value=50, max_value=5000)

# Frame size choices that divide evenly into common sample rates
frame_size_strategy = st.sampled_from([256, 512, 1024, 2048])

# Sample rate choices
sample_rate_strategy = st.sampled_from([8000, 16000, 44100])


# ---------------------------------------------------------------------------
# Property 3 — Silence detection correctness
# ---------------------------------------------------------------------------


class TestSilenceDetectionCorrectness:
    """Property 3: Silence detection triggers on sustained low energy.

    **Validates: Requirements 3.3**
    """

    @given(
        threshold=threshold_strategy,
        frame_size=frame_size_strategy,
        sample_rate=sample_rate_strategy,
        extra_frames=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=200, deadline=5000)
    def test_sustained_silence_triggers_detection(
        self,
        threshold: int,
        frame_size: int,
        sample_rate: int,
        extra_frames: int,
    ):
        """If all frames have RMS below the threshold for >= 2500ms
        continuously, silence_detected must be True."""

        silence_duration = 2.5  # 2500ms
        detector = SilenceDetector(
            threshold=threshold,
            silence_duration=silence_duration,
            sample_rate=sample_rate,
            frame_size=frame_size,
        )

        frames_needed = detector._frames_needed
        total_frames = frames_needed + extra_frames

        # Feed all-zero frames (RMS = 0, always below any positive threshold)
        zero_frame = _make_frame_from_array(np.zeros(frame_size, dtype=np.int16))
        for _ in range(total_frames):
            detector.process_frame(zero_frame)

        assert detector.silence_detected is True, (
            f"Expected silence_detected=True after {total_frames} silent frames "
            f"(needed {frames_needed}), threshold={threshold}, "
            f"frame_size={frame_size}, sample_rate={sample_rate}"
        )

    @given(
        threshold=threshold_strategy,
        frame_size=frame_size_strategy,
        sample_rate=sample_rate_strategy,
        interrupt_position=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=200, deadline=5000)
    def test_interrupted_silence_does_not_trigger(
        self,
        threshold: int,
        frame_size: int,
        sample_rate: int,
        interrupt_position: float,
    ):
        """If at least one frame within the 2500ms window has RMS >= threshold,
        silence should NOT be reported (counter resets)."""

        silence_duration = 2.5
        detector = SilenceDetector(
            threshold=threshold,
            silence_duration=silence_duration,
            sample_rate=sample_rate,
            frame_size=frame_size,
        )

        frames_needed = detector._frames_needed
        assume(frames_needed >= 2)  # need room for an interruption

        # Place the loud frame somewhere in the window
        loud_index = int(interrupt_position * (frames_needed - 1))

        zero_frame = _make_frame_from_array(np.zeros(frame_size, dtype=np.int16))
        # Loud frame: constant value = threshold → RMS == threshold (not < threshold)
        loud_val = min(threshold, 32767)
        loud_frame_data = _make_frame_from_array(
            np.full(frame_size, loud_val, dtype=np.int16)
        )

        for i in range(frames_needed):
            if i == loud_index:
                detector.process_frame(loud_frame_data)
            else:
                detector.process_frame(zero_frame)

        # After the loud frame, the counter resets. The remaining silent frames
        # after the interruption are (frames_needed - 1 - loud_index), which is
        # always < frames_needed. So silence should NOT be detected.
        assert detector.silence_detected is False, (
            f"Expected silence_detected=False when loud frame at index "
            f"{loud_index}/{frames_needed}, threshold={threshold}, "
            f"frame_size={frame_size}, sample_rate={sample_rate}"
        )

    @given(
        threshold=threshold_strategy,
        amplitude_fraction=st.floats(min_value=0.0, max_value=0.99),
    )
    @settings(max_examples=200, deadline=5000)
    def test_random_silent_frames_trigger_after_enough(
        self,
        threshold: int,
        amplitude_fraction: float,
    ):
        """Feed constant-amplitude frames below threshold for the required
        duration — silence must be detected regardless of the actual sample
        values."""

        frame_size = FRAMES_PER_BUFFER
        sample_rate = SAMPLE_RATE
        silence_duration = 2.5

        detector = SilenceDetector(
            threshold=threshold,
            silence_duration=silence_duration,
            sample_rate=sample_rate,
            frame_size=frame_size,
        )

        frames_needed = detector._frames_needed

        # Build a frame with constant amplitude below threshold
        # amplitude_fraction in [0, 0.99] → value in [0, threshold-1]
        value = int(amplitude_fraction * (threshold - 1))
        frame = _make_frame_from_array(np.full(frame_size, value, dtype=np.int16))

        for _ in range(frames_needed):
            detector.process_frame(frame)

        assert detector.silence_detected is True, (
            f"Expected silence_detected=True after {frames_needed} frames "
            f"with amplitude={value}, threshold={threshold}"
        )
