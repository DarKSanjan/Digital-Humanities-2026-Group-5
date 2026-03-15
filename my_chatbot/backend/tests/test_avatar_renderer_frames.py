"""Unit tests for AvatarRenderer frame rendering methods."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.avatar_renderer import AvatarRenderer, Phoneme, FrameData


class TestRenderFrame:
    """Test render_frame() method."""
    
    def test_render_frame_returns_frame_and_timestamp(self):
        """Test that render_frame returns both frame and timestamp."""
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
        
        frame, timestamp = renderer.render_frame('AH')
        
        # Verify frame is numpy array
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (512, 512, 3)
        assert frame.dtype == np.uint8
        
        # Verify timestamp is float
        assert isinstance(timestamp, float)
        assert timestamp > 0
    
    def test_render_frame_with_intensity(self):
        """Test render_frame with intensity parameter."""
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
        
        frame, timestamp = renderer.render_frame('AH', intensity=0.5)
        
        assert isinstance(frame, np.ndarray)
        assert isinstance(timestamp, float)
    
    def test_render_frame_raises_if_not_initialized(self):
        """Test that render_frame raises error if not initialized."""
        renderer = AvatarRenderer()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            renderer.render_frame('AH')
    
    def test_render_frame_updates_fps_tracking(self):
        """Test that render_frame updates FPS tracking."""
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
        
        # Render multiple frames
        for _ in range(5):
            renderer.render_frame('AH')
        
        # FPS should be updated
        assert renderer.current_fps > 0
    
    def test_render_frame_checks_vram_on_gpu(self):
        """Test that render_frame checks VRAM usage when on GPU."""
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
                renderer.initialize(use_gpu=True)
        
        # Mock _check_vram_usage to verify it's called
        with patch.object(renderer, '_check_vram_usage') as mock_check:
            renderer.render_frame('AH')
            mock_check.assert_called_once()


class TestRenderSequence:
    """Test render_sequence() method."""
    
    def test_render_sequence_yields_frame_data(self):
        """Test that render_sequence yields FrameData objects."""
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
        
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='B', start=0.1, duration=0.1),
        ]
        
        frames = list(renderer.render_sequence(phonemes))
        
        # Should generate frames for 0.2 seconds at 24 FPS = ~5 frames
        assert len(frames) > 0
        
        # Each should be FrameData
        for frame_data in frames:
            assert isinstance(frame_data, FrameData)
            assert isinstance(frame_data.frame, np.ndarray)
            assert isinstance(frame_data.timestamp, float)
            assert isinstance(frame_data.frame_number, int)
            assert isinstance(frame_data.fps, float)
    
    def test_render_sequence_empty_phonemes(self):
        """Test render_sequence with empty phoneme list."""
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
        
        frames = list(renderer.render_sequence([]))
        
        # Should return empty
        assert len(frames) == 0
    
    def test_render_sequence_raises_if_not_initialized(self):
        """Test that render_sequence raises error if not initialized."""
        renderer = AvatarRenderer()
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=0.1)]
        
        with pytest.raises(RuntimeError, match="not initialized"):
            list(renderer.render_sequence(phonemes))
    
    def test_render_sequence_cpu_mode_uses_sequential(self):
        """Test that CPU mode uses sequential rendering."""
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
        
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=0.1)]
        
        # Mock the sequential method to verify it's called
        with patch.object(renderer, '_render_sequence_sequential') as mock_seq:
            mock_seq.return_value = iter([])
            list(renderer.render_sequence(phonemes))
            mock_seq.assert_called_once()
    
    def test_render_sequence_gpu_mode_uses_batched(self):
        """Test that GPU mode uses batched rendering."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_device = Mock()
        mock_device.type = 'cuda'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                renderer.initialize(use_gpu=True)
        
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=0.1)]
        
        # Mock the batched method to verify it's called
        with patch.object(renderer, '_render_sequence_batched') as mock_batch:
            mock_batch.return_value = iter([])
            list(renderer.render_sequence(phonemes))
            mock_batch.assert_called_once()
    
    def test_render_sequence_correct_frame_count(self):
        """Test that render_sequence generates correct number of frames."""
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
        
        # 1 second duration at 24 FPS should give 24 frames
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=1.0)]
        
        frames = list(renderer.render_sequence(phonemes))
        
        assert len(frames) == 24
    
    def test_render_sequence_frame_numbers_sequential(self):
        """Test that frame numbers are sequential."""
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
        
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=0.2)]
        
        frames = list(renderer.render_sequence(phonemes))
        
        # Verify frame numbers are sequential
        for i, frame_data in enumerate(frames):
            assert frame_data.frame_number == i


class TestBatchRendering:
    """Test batch rendering functionality."""
    
    def test_set_batch_size(self):
        """Test setting batch size."""
        renderer = AvatarRenderer()
        
        renderer.set_batch_size(8)
        assert renderer.batch_size == 8
        
        renderer.set_batch_size(16)
        assert renderer.batch_size == 16
    
    def test_set_batch_size_invalid(self):
        """Test that invalid batch size raises error."""
        renderer = AvatarRenderer()
        
        with pytest.raises(ValueError, match="must be positive"):
            renderer.set_batch_size(0)
        
        with pytest.raises(ValueError, match="must be positive"):
            renderer.set_batch_size(-1)
    
    def test_render_batch_returns_correct_count(self):
        """Test that _render_batch returns correct number of frames."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_device = Mock()
        mock_device.type = 'cuda'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                renderer.initialize(use_gpu=True)
        
        phonemes = ['AH', 'B', 'M', 'P']
        frames = renderer._render_batch(phonemes)
        
        assert len(frames) == len(phonemes)
        for frame in frames:
            assert isinstance(frame, np.ndarray)


class TestVRAMMonitoring:
    """Test VRAM monitoring functionality."""
    
    def test_get_vram_usage_gpu_mode(self):
        """Test getting VRAM usage in GPU mode."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_device = Mock()
        mock_device.type = 'cuda'
        mock_torch.device.return_value = mock_device
        mock_torch.cuda.memory_allocated.return_value = 2 * 1024 ** 3  # 2GB
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                renderer.initialize(use_gpu=True)
            
            # Keep torch patched when calling get_vram_usage
            vram = renderer.get_vram_usage()
        
            assert vram is not None
            assert vram == pytest.approx(2.0, rel=0.1)  # ~2GB
    
    def test_get_vram_usage_cpu_mode(self):
        """Test that VRAM usage returns None in CPU mode."""
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
        
        vram = renderer.get_vram_usage()
        
        assert vram is None
    
    def test_check_vram_usage_warns_on_high_usage(self):
        """Test that high VRAM usage triggers warning and cache clear."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_device = Mock()
        mock_device.type = 'cuda'
        mock_torch.device.return_value = mock_device
        # Set high VRAM usage (5.5GB, above 90% of 6GB limit)
        mock_torch.cuda.memory_allocated.return_value = int(5.5 * 1024 ** 3)
        mock_torch.cuda.memory_reserved.return_value = int(6 * 1024 ** 3)
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                renderer.initialize(use_gpu=True)
            
            # Call _check_vram_usage with torch still patched
            renderer._check_vram_usage()
            
            # Verify cache was cleared
            mock_torch.cuda.empty_cache.assert_called()


class TestFindActivePhoneme:
    """Test _find_active_phoneme helper method."""
    
    def test_find_active_phoneme_at_start(self):
        """Test finding phoneme at start of sequence."""
        renderer = AvatarRenderer()
        
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='B', start=0.1, duration=0.1),
        ]
        
        result = renderer._find_active_phoneme(phonemes, 0.0)
        assert result == 'AH'
    
    def test_find_active_phoneme_in_middle(self):
        """Test finding phoneme in middle of sequence."""
        renderer = AvatarRenderer()
        
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='B', start=0.1, duration=0.1),
        ]
        
        result = renderer._find_active_phoneme(phonemes, 0.15)
        assert result == 'B'
    
    def test_find_active_phoneme_gap(self):
        """Test finding phoneme in gap returns None."""
        renderer = AvatarRenderer()
        
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='B', start=0.2, duration=0.1),
        ]
        
        result = renderer._find_active_phoneme(phonemes, 0.15)
        assert result is None
    
    def test_find_active_phoneme_after_end(self):
        """Test finding phoneme after sequence end returns None."""
        renderer = AvatarRenderer()
        
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
        ]
        
        result = renderer._find_active_phoneme(phonemes, 0.5)
        assert result is None
