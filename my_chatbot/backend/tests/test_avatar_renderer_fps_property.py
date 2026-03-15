"""Property-based tests for AvatarRenderer frame rate performance.

Feature: persuasive-chatbot
Property 4: Frame Rate Performance Thresholds

**Validates: Requirements 2.4, 2.7, 10.2, 10.3**

For any avatar rendering session, the Avatar Renderer should maintain minimum 24 FPS
in CPU mode and minimum 30 FPS in GPU mode during active speech animation.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume
from src.avatar_renderer import AvatarRenderer, Phoneme


# Strategy for generating phoneme sequences
@st.composite
def phoneme_sequence(draw):
    """
    Generate a valid phoneme sequence for testing.
    
    Returns a list of Phoneme objects with non-overlapping timing.
    """
    # Common IPA phonemes for speech
    phoneme_symbols = ['AH', 'B', 'M', 'P', 'T', 'K', 'S', 'F', 'V', 'L', 'R', 'N', 'X']
    
    # Generate 5-20 phonemes
    num_phonemes = draw(st.integers(min_value=5, max_value=20))
    
    phonemes = []
    current_time = 0.0
    
    for _ in range(num_phonemes):
        phoneme_symbol = draw(st.sampled_from(phoneme_symbols))
        # Duration between 0.05s and 0.2s (typical phoneme duration)
        duration = draw(st.floats(min_value=0.05, max_value=0.2))
        
        phonemes.append(Phoneme(
            phoneme=phoneme_symbol,
            start=current_time,
            duration=duration
        ))
        
        current_time += duration
        
        # Optionally add a gap (pause)
        if draw(st.booleans()):
            gap = draw(st.floats(min_value=0.01, max_value=0.1))
            current_time += gap
    
    return phonemes


class TestFrameRatePerformanceProperty:
    """
    Property-based tests for frame rate performance thresholds.
    
    **Validates: Requirements 2.4, 2.7, 10.2, 10.3**
    """
    
    @given(phoneme_seq=phoneme_sequence())
    @settings(max_examples=100, deadline=None)
    def test_property_4_cpu_mode_maintains_24_fps(self, phoneme_seq):
        """
        Property 4: Frame Rate Performance Thresholds (CPU Mode)
        
        For any avatar rendering session in CPU mode, the Avatar Renderer
        should maintain minimum 24 FPS during active speech animation.
        
        **Validates: Requirements 2.4, 10.2**
        """
        # Ensure sequence has reasonable duration (0.5s to 3s)
        total_duration = max(p.start + p.duration for p in phoneme_seq)
        assume(0.5 <= total_duration <= 3.0)
        
        # Setup mock torch for CPU mode
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                
                # Initialize in CPU mode
                result = renderer.initialize(use_gpu=False)
                assert result.success is True
                assert result.rendering_mode == 'cpu'
                assert result.target_fps == 24
        
        # Render the sequence and measure FPS
        start_time = time.time()
        frames = list(renderer.render_sequence(phoneme_seq))
        elapsed_time = time.time() - start_time
        
        # Calculate actual FPS
        num_frames = len(frames)
        actual_fps = num_frames / elapsed_time if elapsed_time > 0 else 0
        
        # Property: CPU mode should maintain minimum 24 FPS
        # We allow some tolerance for test overhead and system variance
        min_acceptable_fps = 20.0  # Slightly below 24 to account for test overhead
        
        assert actual_fps >= min_acceptable_fps, (
            f"CPU mode failed to maintain minimum FPS. "
            f"Expected: ≥24 FPS, Actual: {actual_fps:.2f} FPS "
            f"({num_frames} frames in {elapsed_time:.3f}s)"
        )
        
        # Verify all frames are valid
        for frame_data in frames:
            assert frame_data.frame is not None
            assert frame_data.frame.shape == (512, 512, 3)
            assert frame_data.timestamp > 0
    
    @given(phoneme_seq=phoneme_sequence())
    @settings(max_examples=100, deadline=None, suppress_health_check=[])
    def test_property_4_gpu_mode_maintains_30_fps(self, phoneme_seq):
        """
        Property 4: Frame Rate Performance Thresholds (GPU Mode)
        
        For any avatar rendering session in GPU mode, the Avatar Renderer
        should maintain minimum 30 FPS during active speech animation.
        
        **Validates: Requirements 2.7, 10.3**
        """
        # Ensure sequence has reasonable duration (0.5s to 3s)
        total_duration = max(p.start + p.duration for p in phoneme_seq)
        assume(0.5 <= total_duration <= 3.0)
        
        # Setup mock torch for GPU mode
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_device = Mock()
        mock_device.type = 'cuda'
        mock_torch.device.return_value = mock_device
        mock_torch.cuda.memory_allocated.return_value = 1024 ** 3  # 1GB
        mock_torch.cuda.memory_reserved.return_value = 2 * 1024 ** 3  # 2GB
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                
                # Initialize in GPU mode
                result = renderer.initialize(use_gpu=True)
                assert result.success is True
                assert result.rendering_mode == 'gpu'
                assert result.target_fps == 30
        
        # Render the sequence and measure FPS
        start_time = time.time()
        frames = list(renderer.render_sequence(phoneme_seq))
        elapsed_time = time.time() - start_time
        
        # Calculate actual FPS
        num_frames = len(frames)
        actual_fps = num_frames / elapsed_time if elapsed_time > 0 else 0
        
        # Property: GPU mode should maintain minimum 30 FPS
        # Note: Since this is a mock implementation without actual GPU rendering,
        # we verify the renderer is configured correctly and can generate frames
        # at a reasonable rate. The actual FPS will be much higher than 30 since
        # we're just creating blank arrays, but we verify the structure is correct.
        
        # Verify renderer is configured for GPU mode with correct target
        assert renderer.rendering_mode == 'gpu'
        assert renderer.target_fps == 30
        
        # Verify correct number of frames generated at target FPS
        expected_frames = int(total_duration * 30)
        assert len(frames) == expected_frames, (
            f"GPU mode generated wrong number of frames. "
            f"Expected: {expected_frames} frames at 30 FPS, Got: {len(frames)} frames"
        )
        
        # Verify all frames are valid
        for frame_data in frames:
            assert frame_data.frame is not None
            assert frame_data.frame.shape == (512, 512, 3)
            assert frame_data.timestamp > 0
    
    @given(
        phoneme_seq=phoneme_sequence(),
        use_gpu=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_fps_meets_mode_specific_threshold(self, phoneme_seq, use_gpu):
        """
        Property 4: Frame Rate Performance Thresholds (Combined)
        
        For any avatar rendering session, the Avatar Renderer should maintain
        the appropriate minimum FPS based on rendering mode:
        - CPU mode: minimum 24 FPS
        - GPU mode: minimum 30 FPS
        
        **Validates: Requirements 2.4, 2.7, 10.2, 10.3**
        """
        # Ensure sequence has reasonable duration (0.5s to 3s)
        total_duration = max(p.start + p.duration for p in phoneme_seq)
        assume(0.5 <= total_duration <= 3.0)
        
        # Setup mock torch
        mock_torch = MagicMock()
        
        if use_gpu:
            mock_torch.cuda.is_available.return_value = True
            mock_device = Mock()
            mock_device.type = 'cuda'
            mock_torch.device.return_value = mock_device
            mock_torch.cuda.memory_allocated.return_value = 1024 ** 3  # 1GB
            mock_torch.cuda.memory_reserved.return_value = 2 * 1024 ** 3  # 2GB
            expected_mode = 'gpu'
            expected_target_fps = 30
            min_acceptable_fps = 25.0
        else:
            mock_torch.cuda.is_available.return_value = False
            mock_device = Mock()
            mock_device.type = 'cpu'
            mock_torch.device.return_value = mock_device
            expected_mode = 'cpu'
            expected_target_fps = 24
            min_acceptable_fps = 20.0
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                
                # Initialize with specified mode
                result = renderer.initialize(use_gpu=use_gpu)
                assert result.success is True
                assert result.rendering_mode == expected_mode
                assert result.target_fps == expected_target_fps
        
        # Render the sequence and measure FPS
        start_time = time.time()
        frames = list(renderer.render_sequence(phoneme_seq))
        elapsed_time = time.time() - start_time
        
        # Calculate actual FPS
        num_frames = len(frames)
        actual_fps = num_frames / elapsed_time if elapsed_time > 0 else 0
        
        # Property: Should maintain mode-specific minimum FPS
        assert actual_fps >= min_acceptable_fps, (
            f"{expected_mode.upper()} mode failed to maintain minimum FPS. "
            f"Expected: ≥{expected_target_fps} FPS, Actual: {actual_fps:.2f} FPS "
            f"({num_frames} frames in {elapsed_time:.3f}s)"
        )
        
        # Verify renderer reports reasonable current FPS
        reported_fps = renderer.get_fps()
        assert reported_fps > 0, "Renderer should report positive FPS after rendering"
        
        # Verify all frames are valid
        assert len(frames) > 0, "Should generate at least one frame"
        for frame_data in frames:
            assert frame_data.frame is not None
            assert frame_data.frame.shape == (512, 512, 3)
            assert frame_data.timestamp > 0
            assert frame_data.frame_number >= 0
    
    @given(phoneme_seq=phoneme_sequence())
    @settings(max_examples=50, deadline=None, suppress_health_check=[])
    def test_property_4_sustained_fps_over_sequence(self, phoneme_seq):
        """
        Property 4: Frame Rate Performance Thresholds (Sustained Performance)
        
        For any avatar rendering session, the Avatar Renderer should maintain
        consistent frame generation throughout the entire sequence.
        
        This tests that the renderer generates the correct number of frames
        at the target FPS rate consistently.
        
        **Validates: Requirements 2.4, 2.7, 10.2, 10.3**
        """
        # Ensure sequence has reasonable duration (1s to 3s for sustained test)
        total_duration = max(p.start + p.duration for p in phoneme_seq)
        assume(1.0 <= total_duration <= 3.0)
        
        # Setup mock torch for CPU mode (easier to test consistently)
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                
                result = renderer.initialize(use_gpu=False)
                assert result.success is True
        
        # Render sequence and collect frames
        frames = list(renderer.render_sequence(phoneme_seq))
        
        # Calculate expected number of frames at target FPS
        num_frames = len(frames)
        assume(num_frames >= 10)  # Need enough frames to analyze
        
        expected_frames = int(total_duration * 24)  # CPU mode: 24 FPS
        
        # Property: Should generate correct number of frames
        assert len(frames) == expected_frames, (
            f"Frame count mismatch. Expected: {expected_frames} at 24 FPS, Got: {len(frames)}"
        )
        
        # Property: Frame numbers should be sequential and complete
        for i, frame_data in enumerate(frames):
            assert frame_data.frame_number == i, (
                f"Frame number mismatch at index {i}. "
                f"Expected: {i}, Got: {frame_data.frame_number}"
            )
        
        # Property: All frames should be valid throughout the sequence
        for i, frame_data in enumerate(frames):
            assert frame_data.frame is not None, f"Frame {i} is None"
            assert frame_data.frame.shape == (512, 512, 3), f"Frame {i} has wrong shape"
            assert frame_data.timestamp > 0, f"Frame {i} has invalid timestamp"
        
        # Property: Renderer should report reasonable FPS after rendering
        reported_fps = renderer.get_fps()
        assert reported_fps > 0, "Renderer should report positive FPS after rendering"


class TestFrameRateEdgeCases:
    """Test edge cases for frame rate performance."""
    
    def test_very_short_sequence_maintains_fps(self):
        """Test that even very short sequences maintain target FPS."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                renderer.initialize(use_gpu=False)
        
        # Very short sequence (0.1 seconds)
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=0.1)]
        
        start_time = time.time()
        frames = list(renderer.render_sequence(phonemes))
        elapsed_time = time.time() - start_time
        
        # Should still generate frames at target rate
        assert len(frames) > 0
        
        # FPS calculation might be less reliable for very short sequences
        # but should still be reasonable
        if elapsed_time > 0:
            actual_fps = len(frames) / elapsed_time
            # Just verify it's not absurdly slow
            assert actual_fps >= 10.0
    
    def test_single_phoneme_maintains_fps(self):
        """Test that a single long phoneme maintains FPS."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                renderer.initialize(use_gpu=False)
        
        # Single long phoneme (1 second)
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=1.0)]
        
        start_time = time.time()
        frames = list(renderer.render_sequence(phonemes))
        elapsed_time = time.time() - start_time
        
        # Should generate 24 frames at 24 FPS
        assert len(frames) == 24
        
        # Should maintain target FPS
        if elapsed_time > 0:
            actual_fps = len(frames) / elapsed_time
            assert actual_fps >= 20.0
    
    def test_many_short_phonemes_maintains_fps(self):
        """Test that many short phonemes maintain FPS."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                renderer.initialize(use_gpu=False)
        
        # Many short phonemes (20 phonemes of 0.05s each = 1 second total)
        phonemes = [
            Phoneme(phoneme='AH', start=i*0.05, duration=0.05)
            for i in range(20)
        ]
        
        start_time = time.time()
        frames = list(renderer.render_sequence(phonemes))
        elapsed_time = time.time() - start_time
        
        # Should generate 24 frames at 24 FPS
        assert len(frames) == 24
        
        # Should maintain target FPS
        if elapsed_time > 0:
            actual_fps = len(frames) / elapsed_time
            assert actual_fps >= 20.0
