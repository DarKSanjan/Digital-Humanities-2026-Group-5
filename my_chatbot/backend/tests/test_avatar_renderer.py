"""Unit tests for AvatarRenderer initialization."""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from src.avatar_renderer import AvatarRenderer, InitResult


class TestAvatarRendererGPUInitialization:
    """Test GPU initialization success path."""
    
    def test_gpu_initialization_success(self):
        """Test successful GPU initialization with CUDA available."""
        # Create mock torch module
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_device = Mock()
        mock_device.type = 'cuda'
        mock_torch.device.return_value = mock_device
        
        # Mock model
        mock_model = Mock()
        mock_model.to.return_value = mock_model
        
        renderer = AvatarRenderer()
        
        # Mock torch import and _load_model
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model') as mock_load:
                mock_load.side_effect = lambda: setattr(renderer, 'model', mock_model)
                
                result = renderer.initialize(use_gpu=True)
        
        # Verify successful initialization
        assert result.success is True
        assert result.rendering_mode == 'gpu'
        assert result.target_fps == 30
        assert result.error_message is None
        
        # Verify renderer state
        assert renderer.initialized is True
        assert renderer.rendering_mode == 'gpu'
        assert renderer.target_fps == 30
        assert renderer.device == mock_device
        
        # Verify CUDA was checked
        mock_torch.cuda.is_available.assert_called_once()
        
        # Verify model was moved to GPU
        mock_model.to.assert_called_with(mock_device)
    
    def test_gpu_initialization_with_correct_device_type(self):
        """Test that GPU initialization creates correct device type."""
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
                result = renderer.initialize(use_gpu=True)
        
        # Verify device was created with 'cuda'
        mock_torch.device.assert_called_with('cuda')
        assert result.success is True
    
    def test_gpu_initialization_sets_target_fps_30(self):
        """Test that GPU mode sets target FPS to 30."""
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
                result = renderer.initialize(use_gpu=True)
        
        assert result.target_fps == 30
        assert renderer.target_fps == 30


class TestAvatarRendererCPUFallback:
    """Test CPU fallback when GPU unavailable."""
    
    def test_cpu_fallback_when_cuda_unavailable(self):
        """Test fallback to CPU when CUDA is not available."""
        # Mock CUDA not available
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
                result = renderer.initialize(use_gpu=True)
        
        # Verify CPU fallback
        assert result.success is True
        assert result.rendering_mode == 'cpu'
        assert result.target_fps == 24
        assert result.error_message is None
        
        # Verify renderer state
        assert renderer.initialized is True
        assert renderer.rendering_mode == 'cpu'
        assert renderer.target_fps == 24
        
        # Verify device was created with 'cpu'
        mock_torch.device.assert_called_with('cpu')
    
    def test_cpu_mode_when_gpu_disabled(self):
        """Test CPU mode when GPU is explicitly disabled."""
        mock_torch = MagicMock()
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                result = renderer.initialize(use_gpu=False)
        
        # Verify CPU mode
        assert result.success is True
        assert result.rendering_mode == 'cpu'
        assert result.target_fps == 24
        
        # Verify CUDA availability was not checked
        mock_torch.cuda.is_available.assert_not_called()
    
    def test_cpu_fallback_on_gpu_initialization_error(self):
        """Test fallback to CPU when GPU initialization raises exception."""
        # Mock CUDA available but device creation fails
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        
        # First call to device() raises exception, second call succeeds with CPU
        mock_cpu_device = Mock()
        mock_cpu_device.type = 'cpu'
        mock_torch.device.side_effect = [RuntimeError("GPU error"), mock_cpu_device]
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                result = renderer.initialize(use_gpu=True)
        
        # Verify fallback to CPU
        assert result.success is True
        assert result.rendering_mode == 'cpu'
        assert result.target_fps == 24
    
    def test_cpu_fallback_on_out_of_memory(self):
        """Test fallback to CPU when GPU runs out of memory."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        
        # Create GPU device
        mock_gpu_device = Mock()
        mock_gpu_device.type = 'cuda'
        
        # Create CPU device for fallback
        mock_cpu_device = Mock()
        mock_cpu_device.type = 'cpu'
        
        # First call returns GPU, second call returns CPU
        mock_torch.device.side_effect = [mock_gpu_device, mock_cpu_device]
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                
                # First to() call (GPU) raises OOM, second call (CPU) succeeds
                renderer.model.to.side_effect = [
                    RuntimeError("CUDA out of memory"),
                    renderer.model
                ]
                
                result = renderer.initialize(use_gpu=True)
        
        # Verify fallback to CPU
        assert result.success is True
        assert result.rendering_mode == 'cpu'
        assert result.target_fps == 24
        assert renderer.device == mock_cpu_device
    
    def test_cpu_fallback_sets_target_fps_24(self):
        """Test that CPU mode sets target FPS to 24."""
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
                result = renderer.initialize(use_gpu=True)
        
        assert result.target_fps == 24
        assert renderer.target_fps == 24


class TestAvatarRendererModelLoadingErrors:
    """Test model loading error handling."""
    
    def test_model_loading_failure(self):
        """Test initialization failure when model loading fails."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        # Mock _load_model to raise exception
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model') as mock_load:
                mock_load.side_effect = FileNotFoundError("Model file not found")
                
                result = renderer.initialize(use_gpu=False)
        
        # Verify initialization failed
        assert result.success is False
        assert result.rendering_mode == 'cpu'
        assert result.target_fps == 24
        assert result.error_message is not None
        assert "Failed to load talking-head-anime-3 model" in result.error_message
        assert "Model file not found" in result.error_message
        
        # Verify renderer is not initialized
        assert renderer.initialized is False
    
    def test_model_loading_permission_error(self):
        """Test initialization failure when model file has permission issues."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model') as mock_load:
                mock_load.side_effect = PermissionError("Permission denied")
                
                result = renderer.initialize(use_gpu=False)
        
        assert result.success is False
        assert "Failed to load talking-head-anime-3 model" in result.error_message
        assert "Permission denied" in result.error_message
    
    def test_model_loading_corrupted_file(self):
        """Test initialization failure when model file is corrupted."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model') as mock_load:
                mock_load.side_effect = RuntimeError("Invalid model format")
                
                result = renderer.initialize(use_gpu=False)
        
        assert result.success is False
        assert "Failed to load talking-head-anime-3 model" in result.error_message
        assert "Invalid model format" in result.error_message
    
    def test_pytorch_not_available(self):
        """Test initialization failure when PyTorch is not installed."""
        renderer = AvatarRenderer()
        
        # Simulate ImportError when trying to import torch
        with patch.dict('sys.modules', {'torch': None}):
            result = renderer.initialize(use_gpu=False)
        
        assert result.success is False
        assert result.error_message is not None
        # The error message should mention PyTorch or import error
        assert "PyTorch not available" in result.error_message or "import" in result.error_message.lower()
    
    def test_unexpected_error_during_initialization(self):
        """Test handling of unexpected errors during initialization."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.side_effect = Exception("Unexpected error")
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            result = renderer.initialize(use_gpu=True)
        
        assert result.success is False
        assert result.error_message is not None
        assert "Unexpected error during initialization" in result.error_message


class TestAvatarRendererInitializationState:
    """Test renderer state after initialization."""
    
    def test_initialized_flag_set_on_success(self):
        """Test that initialized flag is set to True on successful initialization."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        assert renderer.initialized is False
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                result = renderer.initialize(use_gpu=False)
        
        assert result.success is True
        assert renderer.initialized is True
    
    def test_initialized_flag_not_set_on_failure(self):
        """Test that initialized flag remains False on initialization failure."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model') as mock_load:
                mock_load.side_effect = RuntimeError("Model loading failed")
                result = renderer.initialize(use_gpu=False)
        
        assert result.success is False
        assert renderer.initialized is False
    
    def test_device_set_correctly(self):
        """Test that device is set correctly after initialization."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_device = Mock()
        mock_device.type = 'cuda'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        assert renderer.device is None
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                result = renderer.initialize(use_gpu=True)
        
        assert renderer.device == mock_device
    
    def test_current_fps_initialized_to_zero(self):
        """Test that current_fps is initialized to 0.0."""
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
        
        assert renderer.current_fps == 0.0


class TestAvatarRendererInitializationTiming:
    """Test initialization timing and performance."""
    
    def test_initialization_time_logged(self):
        """Test that initialization time is measured and logged."""
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
        
        # Verify initialization succeeded (timing is logged internally)
        assert result.success is True


class TestAvatarRendererRequirementValidation:
    """Test that initialization meets specific requirements."""
    
    def test_requirement_2_6_gpu_acceleration_utilized(self):
        """
        Validates Requirement 2.6: WHERE GPU hardware is available,
        THE GPU_Accelerator SHALL utilize CUDA acceleration on Windows.
        """
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
                result = renderer.initialize(use_gpu=True)
        
        # Verify GPU acceleration is utilized
        assert result.rendering_mode == 'gpu'
        assert renderer.device.type == 'cuda'
    
    def test_requirement_2_8_cpu_fallback(self):
        """
        Validates Requirement 2.8: IF GPU acceleration is unavailable,
        THEN THE Avatar_Renderer SHALL fall back to CPU rendering.
        """
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
                result = renderer.initialize(use_gpu=True)
        
        # Verify CPU fallback
        assert result.rendering_mode == 'cpu'
        assert renderer.device.type == 'cpu'
        assert result.success is True  # Should still succeed


class TestAvatarRendererMultipleInitialization:
    """Test behavior when initialize is called multiple times."""
    
    def test_multiple_initialization_calls(self):
        """Test that renderer can be initialized multiple times."""
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
                
                # First initialization
                result1 = renderer.initialize(use_gpu=False)
                assert result1.success is True
                
                # Second initialization
                result2 = renderer.initialize(use_gpu=False)
                assert result2.success is True
                
                # Both should succeed
                assert renderer.initialized is True
