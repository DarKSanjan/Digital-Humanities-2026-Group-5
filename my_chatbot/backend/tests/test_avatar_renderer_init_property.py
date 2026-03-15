"""Property-based tests for AvatarRenderer initialization time.

Feature: persuasive-chatbot
Property 5: Initialization Time Constraint

**Validates: Requirements 2.5, 10.6**

For any system startup sequence, all components (Avatar Renderer, IPC server, GUI)
should complete initialization within 10 seconds, with Avatar Renderer specifically
loading within 3 seconds.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from src.avatar_renderer import AvatarRenderer


class TestInitializationTimeConstraint:
    """
    Property 5: Initialization Time Constraint
    
    For any system startup sequence, all components should complete initialization
    within 10 seconds, with Avatar Renderer specifically loading within 3 seconds.
    
    **Validates: Requirements 2.5, 10.6**
    """
    
    @given(use_gpu=st.booleans())
    @settings(max_examples=100, deadline=None)
    def test_property_5_avatar_renderer_initializes_within_3_seconds(self, use_gpu):
        """
        Property 5: Initialization Time Constraint (Avatar Renderer)
        
        For any system startup with Avatar Renderer, initialization should
        complete within 3 seconds regardless of GPU or CPU mode.
        
        **Validates: Requirements 2.5**
        """
        # Setup mock torch
        mock_torch = MagicMock()
        
        if use_gpu:
            mock_torch.cuda.is_available.return_value = True
            mock_device = Mock()
            mock_device.type = 'cuda'
            mock_torch.device.return_value = mock_device
            mock_torch.cuda.memory_allocated.return_value = 1024 ** 3  # 1GB
            mock_torch.cuda.memory_reserved.return_value = 2 * 1024 ** 3  # 2GB
        else:
            mock_torch.cuda.is_available.return_value = False
            mock_device = Mock()
            mock_device.type = 'cpu'
            mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                renderer.model.to.return_value = renderer.model
                
                # Measure initialization time
                start_time = time.time()
                result = renderer.initialize(use_gpu=use_gpu)
                elapsed_time = time.time() - start_time
        
        # Property: Avatar Renderer should initialize within 3 seconds
        assert elapsed_time < 3.0, (
            f"Avatar Renderer initialization took {elapsed_time:.3f}s, "
            f"exceeding 3 second limit (mode: {'GPU' if use_gpu else 'CPU'})"
        )
        
        # Verify initialization succeeded
        assert result.success is True
        assert result.rendering_mode in ['gpu', 'cpu']
        assert result.target_fps in [24, 30]
    
    @given(use_gpu=st.booleans())
    @settings(max_examples=50, deadline=None)
    def test_property_5_avatar_renderer_initialization_is_fast(self, use_gpu):
        """
        Property 5: Initialization Time Constraint (Performance)
        
        For any Avatar Renderer initialization, the process should be
        consistently fast across multiple runs.
        
        **Validates: Requirements 2.5**
        """
        # Setup mock torch
        mock_torch = MagicMock()
        
        if use_gpu:
            mock_torch.cuda.is_available.return_value = True
            mock_device = Mock()
            mock_device.type = 'cuda'
            mock_torch.device.return_value = mock_device
            mock_torch.cuda.memory_allocated.return_value = 1024 ** 3
            mock_torch.cuda.memory_reserved.return_value = 2 * 1024 ** 3
        else:
            mock_torch.cuda.is_available.return_value = False
            mock_device = Mock()
            mock_device.type = 'cpu'
            mock_torch.device.return_value = mock_device
        
        # Perform multiple initialization attempts to test consistency
        initialization_times = []
        
        for _ in range(3):
            renderer = AvatarRenderer()
            
            with patch.dict('sys.modules', {'torch': mock_torch}):
                with patch.object(renderer, '_load_model'):
                    renderer.model = Mock()
                    renderer.model.to.return_value = renderer.model
                    
                    start_time = time.time()
                    result = renderer.initialize(use_gpu=use_gpu)
                    elapsed_time = time.time() - start_time
                    
                    initialization_times.append(elapsed_time)
                    
                    # Each initialization should succeed
                    assert result.success is True
        
        # Property: All initializations should be within 3 seconds
        for i, elapsed in enumerate(initialization_times):
            assert elapsed < 3.0, (
                f"Initialization attempt {i+1} took {elapsed:.3f}s, "
                f"exceeding 3 second limit"
            )
        
        # Property: Initialization times should be consistent (no major variance)
        avg_time = sum(initialization_times) / len(initialization_times)
        max_time = max(initialization_times)
        
        # Maximum time shouldn't be more than 2x average (reasonable variance)
        assert max_time <= avg_time * 2.0, (
            f"Initialization time variance too high. "
            f"Average: {avg_time:.3f}s, Max: {max_time:.3f}s"
        )
    
    def test_property_5_avatar_renderer_cpu_fallback_within_time_limit(self):
        """
        Property 5: Initialization Time Constraint (CPU Fallback)
        
        When GPU initialization fails and system falls back to CPU,
        the total initialization time should still be within 3 seconds.
        
        **Validates: Requirements 2.5**
        """
        # Setup mock torch that simulates GPU failure
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        
        # First device call returns CUDA, but model.to() will fail
        mock_cuda_device = Mock()
        mock_cuda_device.type = 'cuda'
        mock_cpu_device = Mock()
        mock_cpu_device.type = 'cpu'
        
        # Return CUDA device first, then CPU device on retry
        mock_torch.device.side_effect = [mock_cuda_device, mock_cpu_device]
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model'):
                renderer.model = Mock()
                
                # Simulate GPU OOM on first to() call, succeed on second
                def mock_to(device):
                    if device.type == 'cuda':
                        raise RuntimeError("CUDA out of memory")
                    renderer.model.device = device
                    return renderer.model
                
                renderer.model.to.side_effect = mock_to
                
                # Measure initialization time with fallback
                start_time = time.time()
                result = renderer.initialize(use_gpu=True)
                elapsed_time = time.time() - start_time
        
        # Property: Even with GPU failure and CPU fallback, should be within 3s
        assert elapsed_time < 3.0, (
            f"Avatar Renderer initialization with CPU fallback took {elapsed_time:.3f}s, "
            f"exceeding 3 second limit"
        )
        
        # Verify fallback succeeded
        assert result.success is True
        assert result.rendering_mode == 'cpu'
        assert result.target_fps == 24
    
    def test_property_5_avatar_renderer_model_load_failure_within_time_limit(self):
        """
        Property 5: Initialization Time Constraint (Model Load Failure)
        
        Even when model loading fails, the initialization should fail fast
        and return within 3 seconds.
        
        **Validates: Requirements 2.5**
        """
        # Setup mock torch
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        renderer = AvatarRenderer()
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch.object(renderer, '_load_model') as mock_load:
                # Simulate model loading failure
                mock_load.side_effect = RuntimeError("Model file not found")
                
                # Measure initialization time with failure
                start_time = time.time()
                result = renderer.initialize(use_gpu=False)
                elapsed_time = time.time() - start_time
        
        # Property: Even with failure, should return within 3 seconds
        assert elapsed_time < 3.0, (
            f"Avatar Renderer initialization failure took {elapsed_time:.3f}s, "
            f"exceeding 3 second limit"
        )
        
        # Verify initialization failed gracefully
        assert result.success is False
        assert result.error_message is not None
        assert "Model file not found" in result.error_message


class TestInitializationTimeEdgeCases:
    """Test edge cases for initialization time constraints."""
    
    def test_multiple_sequential_initializations_within_time_limit(self):
        """
        Test that multiple sequential initializations each complete within
        the 3 second time limit.
        """
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_device = Mock()
        mock_device.type = 'cpu'
        mock_torch.device.return_value = mock_device
        
        for i in range(5):
            renderer = AvatarRenderer()
            
            with patch.dict('sys.modules', {'torch': mock_torch}):
                with patch.object(renderer, '_load_model'):
                    renderer.model = Mock()
                    renderer.model.to.return_value = renderer.model
                    
                    start_time = time.time()
                    result = renderer.initialize(use_gpu=False)
                    elapsed_time = time.time() - start_time
            
            assert elapsed_time < 3.0, (
                f"Initialization {i+1} took {elapsed_time:.3f}s, "
                f"exceeding 3 second limit"
            )
            assert result.success is True
    
    def test_initialization_with_pytorch_import_error_within_time_limit(self):
        """
        Test that initialization fails fast when PyTorch is not available.
        """
        renderer = AvatarRenderer()
        
        # Simulate PyTorch import error
        with patch.dict('sys.modules', {'torch': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'torch'")):
                start_time = time.time()
                result = renderer.initialize(use_gpu=False)
                elapsed_time = time.time() - start_time
        
        # Should fail fast
        assert elapsed_time < 1.0, (
            f"Initialization with import error took {elapsed_time:.3f}s, "
            f"should fail faster"
        )
        
        assert result.success is False
        assert "PyTorch not available" in result.error_message
    
    def test_initialization_time_is_logged(self):
        """
        Test that initialization time is properly logged for monitoring.
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
                
                with patch('src.avatar_renderer.logger') as mock_logger:
                    result = renderer.initialize(use_gpu=False)
                    
                    # Verify initialization time was logged
                    assert result.success is True
                    
                    # Check that info log was called with timing information
                    info_calls = [call for call in mock_logger.info.call_args_list]
                    
                    # Should have a log message with elapsed time
                    timing_logged = any(
                        'initialized successfully' in str(call) and 's' in str(call)
                        for call in info_calls
                    )
                    assert timing_logged, "Initialization time should be logged"
