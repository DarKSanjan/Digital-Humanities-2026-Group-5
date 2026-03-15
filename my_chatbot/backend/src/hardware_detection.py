"""Hardware detection and configuration module for cross-platform GPU/CPU rendering."""

import platform
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HardwareInfo:
    """
    Hardware capabilities information.
    
    Attributes:
        platform: Operating system platform ('windows' or 'macos')
        gpu_available: Whether GPU/CUDA is available
        gpu_name: Name of the GPU device (if available)
        vram_mb: VRAM in megabytes (if available)
        cuda_version: CUDA version string (if available)
        rendering_mode: Rendering mode to use ('gpu' or 'cpu')
        target_fps: Target frames per second based on rendering mode
    """
    platform: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    vram_mb: Optional[int] = None
    cuda_version: Optional[str] = None
    rendering_mode: str = "cpu"
    target_fps: int = 24
    
    def __str__(self) -> str:
        """Return human-readable hardware info string."""
        lines = [
            f"Platform: {self.platform}",
            f"GPU Available: {self.gpu_available}",
        ]
        
        if self.gpu_available:
            lines.append(f"GPU Name: {self.gpu_name}")
            lines.append(f"VRAM: {self.vram_mb} MB")
            lines.append(f"CUDA Version: {self.cuda_version}")
        
        lines.append(f"Rendering Mode: {self.rendering_mode}")
        lines.append(f"Target FPS: {self.target_fps}")
        
        return "\n".join(lines)


class HardwareDetector:
    """
    Detects hardware capabilities and configures rendering mode.
    
    Detects:
    - Operating system platform
    - CUDA availability using torch.cuda.is_available()
    - GPU name, VRAM, and CUDA version
    - Determines rendering mode (GPU/CPU) based on capabilities
    """
    
    @staticmethod
    def detect_platform() -> str:
        """
        Detect the operating system platform.
        
        Returns:
            'windows' for Windows, 'macos' for macOS, or the platform name
        """
        system = platform.system().lower()
        
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        else:
            return system
    
    @staticmethod
    def detect_cuda() -> tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """
        Detect CUDA availability and GPU information.
        
        Returns:
            Tuple of (cuda_available, gpu_name, cuda_version, vram_mb)
        """
        try:
            import torch
            
            if not torch.cuda.is_available():
                logger.info("CUDA not available")
                return False, None, None, None
            
            # Get GPU name
            gpu_name = torch.cuda.get_device_name(0)
            
            # Get CUDA version
            cuda_version = torch.version.cuda
            
            # Get VRAM in MB
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_mb = vram_bytes // (1024 * 1024)
            
            logger.info(f"CUDA available: {gpu_name}, {vram_mb}MB VRAM, CUDA {cuda_version}")
            return True, gpu_name, cuda_version, vram_mb
            
        except ImportError:
            logger.warning("PyTorch not installed, CUDA detection skipped")
            return False, None, None, None
        except Exception as e:
            logger.error(f"Error detecting CUDA: {e}")
            return False, None, None, None
    
    @staticmethod
    def determine_rendering_mode(gpu_available: bool, platform_name: str) -> tuple[str, int]:
        """
        Determine rendering mode and target FPS based on hardware capabilities.
        
        Args:
            gpu_available: Whether GPU/CUDA is available
            platform_name: The platform name ('windows', 'macos', etc.)
            
        Returns:
            Tuple of (rendering_mode, target_fps)
            - GPU mode: 'gpu', 30 FPS
            - CPU mode: 'cpu', 24 FPS
        """
        if gpu_available:
            # GPU acceleration available
            rendering_mode = "gpu"
            target_fps = 30
            logger.info("Rendering mode: GPU (30 FPS target)")
        else:
            # Fall back to CPU rendering
            rendering_mode = "cpu"
            target_fps = 24
            logger.info("Rendering mode: CPU (24 FPS target)")
        
        return rendering_mode, target_fps
    
    @classmethod
    def detect_hardware(cls) -> HardwareInfo:
        """
        Detect all hardware capabilities and configure rendering.
        
        This is the main entry point for hardware detection. It:
        1. Detects the operating system platform
        2. Checks for CUDA availability
        3. Retrieves GPU information if available
        4. Determines the appropriate rendering mode and target FPS
        
        Returns:
            HardwareInfo object with all detected capabilities
        """
        logger.info("Starting hardware detection...")
        
        # Detect platform
        platform_name = cls.detect_platform()
        logger.info(f"Platform: {platform_name}")
        
        # Detect CUDA and GPU info
        gpu_available, gpu_name, cuda_version, vram_mb = cls.detect_cuda()
        
        # Determine rendering mode
        rendering_mode, target_fps = cls.determine_rendering_mode(gpu_available, platform_name)
        
        # Create HardwareInfo object
        hardware_info = HardwareInfo(
            platform=platform_name,
            gpu_available=gpu_available,
            gpu_name=gpu_name,
            vram_mb=vram_mb,
            cuda_version=cuda_version,
            rendering_mode=rendering_mode,
            target_fps=target_fps
        )
        
        logger.info("Hardware detection complete:")
        logger.info(str(hardware_info))
        
        return hardware_info


def get_hardware_info() -> HardwareInfo:
    """
    Convenience function to detect hardware capabilities.
    
    Returns:
        HardwareInfo object with detected capabilities
    """
    return HardwareDetector.detect_hardware()
