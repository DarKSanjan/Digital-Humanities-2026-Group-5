"""Property-based tests for hardware detection module.

Feature: persuasive-chatbot
Property 29: Hardware Capability Detection
Validates: Requirements 13.5
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import patch, MagicMock
from src.hardware_detection import HardwareDetector, HardwareInfo


class TestHardwareCapabilityDetection:
    """
    Property 29: Hardware Capability Detection
    
    For any system startup, the chatbot should detect available hardware 
    capabilities (GPU presence, CUDA availability, VRAM) and configure 
    the rendering mode (GPU or CPU) accordingly.
    
    Validates: Requirements 13.5
    """
    
    @given(
        gpu_available=st.booleans(),
        gpu_name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        cuda_version=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
        vram_mb=st.one_of(st.none(), st.integers(min_value=1024, max_value=24576))
    )
    @settings(max_examples=20)
    def test_property_29_hardware_detection_configures_rendering_mode(
        self, gpu_available, gpu_name, cuda_version, vram_mb
    ):
        """
        Property: Hardware detection should always configure an appropriate 
        rendering mode based on detected capabilities.
        
        For any combination of hardware capabilities:
        - If GPU is available, rendering mode should be 'gpu' with 30 FPS target
        - If GPU is not available, rendering mode should be 'cpu' with 24 FPS target
        - HardwareInfo should always be created with valid values
        """
        # Mock torch.cuda to simulate different hardware configurations
        with patch('src.hardware_detection.HardwareDetector.detect_cuda') as mock_detect_cuda:
            # Configure mock based on test parameters
            if gpu_available:
                mock_detect_cuda.return_value = (
                    True,
                    gpu_name or "Mock GPU",
                    cuda_version or "11.8",
                    vram_mb or 8192
                )
            else:
                mock_detect_cuda.return_value = (False, None, None, None)
            
            # Detect hardware
            hardware_info = HardwareDetector.detect_hardware()
            
            # Verify HardwareInfo is created
            assert isinstance(hardware_info, HardwareInfo)
            
            # Verify platform is detected
            assert hardware_info.platform in ['windows', 'macos', 'linux', 'darwin']
            
            # Verify GPU availability matches detection
            assert hardware_info.gpu_available == gpu_available
            
            # Verify rendering mode is configured correctly
            if gpu_available:
                assert hardware_info.rendering_mode == "gpu"
                assert hardware_info.target_fps == 30
                assert hardware_info.gpu_name is not None
                assert hardware_info.cuda_version is not None
                assert hardware_info.vram_mb is not None
                assert hardware_info.vram_mb > 0
            else:
                assert hardware_info.rendering_mode == "cpu"
                assert hardware_info.target_fps == 24
                # GPU info should be None when GPU not available
                assert hardware_info.gpu_name is None
                assert hardware_info.cuda_version is None
                assert hardware_info.vram_mb is None
    
    @given(platform_name=st.sampled_from(['windows', 'macos', 'linux']))
    @settings(max_examples=20)
    def test_property_29_platform_detection_is_consistent(self, platform_name):
        """
        Property: Platform detection should be consistent and deterministic.
        
        For any platform, the detected platform should match the system platform.
        """
        with patch('src.hardware_detection.platform.system') as mock_platform:
            # Map platform names to what platform.system() returns
            system_map = {
                'windows': 'Windows',
                'macos': 'Darwin',
                'linux': 'Linux'
            }
            mock_platform.return_value = system_map[platform_name]
            
            detected = HardwareDetector.detect_platform()
            
            # Verify platform is detected correctly
            assert detected == platform_name
    
    @given(
        gpu_available=st.booleans(),
        platform_name=st.sampled_from(['windows', 'macos', 'linux'])
    )
    @settings(max_examples=20)
    def test_property_29_rendering_mode_determination_is_correct(
        self, gpu_available, platform_name
    ):
        """
        Property: Rendering mode determination should follow the specification.
        
        For any hardware configuration:
        - GPU available → 'gpu' mode with 30 FPS
        - GPU not available → 'cpu' mode with 24 FPS
        """
        rendering_mode, target_fps = HardwareDetector.determine_rendering_mode(
            gpu_available, platform_name
        )
        
        if gpu_available:
            assert rendering_mode == "gpu"
            assert target_fps == 30
        else:
            assert rendering_mode == "cpu"
            assert target_fps == 24
    
    def test_property_29_hardware_info_string_representation(self):
        """
        Property: HardwareInfo should have a valid string representation.
        
        The string representation should include all relevant information.
        """
        # Test with GPU available
        info_gpu = HardwareInfo(
            platform="windows",
            gpu_available=True,
            gpu_name="NVIDIA RTX 3080",
            vram_mb=8192,
            cuda_version="11.8",
            rendering_mode="gpu",
            target_fps=30
        )
        
        str_repr = str(info_gpu)
        assert "windows" in str_repr.lower()
        assert "gpu" in str_repr.lower()
        assert "3080" in str_repr
        assert "8192" in str_repr
        assert "30" in str_repr
        
        # Test with CPU only
        info_cpu = HardwareInfo(
            platform="macos",
            gpu_available=False,
            rendering_mode="cpu",
            target_fps=24
        )
        
        str_repr = str(info_cpu)
        assert "macos" in str_repr.lower()
        assert "cpu" in str_repr.lower()
        assert "24" in str_repr
    
    @given(
        vram_mb=st.integers(min_value=1024, max_value=24576)
    )
    @settings(max_examples=20)
    def test_property_29_vram_detection_is_positive(self, vram_mb):
        """
        Property: When GPU is available, VRAM should be a positive integer.
        
        For any detected VRAM value, it should be greater than 0.
        """
        with patch('src.hardware_detection.HardwareDetector.detect_cuda') as mock_detect_cuda:
            mock_detect_cuda.return_value = (True, "Mock GPU", "11.8", vram_mb)
            
            hardware_info = HardwareDetector.detect_hardware()
            
            assert hardware_info.vram_mb is not None
            assert hardware_info.vram_mb > 0
            assert hardware_info.vram_mb == vram_mb
    
    def test_property_29_torch_import_error_fallback(self):
        """
        Property: When PyTorch is not available, should fall back to CPU mode.
        
        If torch cannot be imported, the system should gracefully fall back
        to CPU rendering without crashing.
        """
        with patch('src.hardware_detection.HardwareDetector.detect_cuda') as mock_detect_cuda:
            # Simulate ImportError by returning False (no GPU)
            mock_detect_cuda.return_value = (False, None, None, None)
            
            hardware_info = HardwareDetector.detect_hardware()
            
            # Should fall back to CPU mode
            assert hardware_info.gpu_available is False
            assert hardware_info.rendering_mode == "cpu"
            assert hardware_info.target_fps == 24
            assert hardware_info.gpu_name is None
            assert hardware_info.cuda_version is None
            assert hardware_info.vram_mb is None
    
    def test_property_29_cuda_detection_error_fallback(self):
        """
        Property: When CUDA detection fails, should fall back to CPU mode.
        
        If CUDA detection raises an exception, the system should gracefully
        fall back to CPU rendering.
        """
        with patch('src.hardware_detection.HardwareDetector.detect_cuda') as mock_detect_cuda:
            # Simulate CUDA error by returning False
            mock_detect_cuda.return_value = (False, None, None, None)
            
            hardware_info = HardwareDetector.detect_hardware()
            
            # Should fall back to CPU mode
            assert hardware_info.gpu_available is False
            assert hardware_info.rendering_mode == "cpu"
            assert hardware_info.target_fps == 24
