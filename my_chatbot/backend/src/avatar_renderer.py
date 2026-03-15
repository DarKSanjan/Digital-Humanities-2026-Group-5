"""Avatar rendering component using talking-head-anime-3 model."""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Iterator, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class InitResult:
    """
    Result of avatar renderer initialization.
    
    Attributes:
        success: Whether initialization succeeded
        rendering_mode: 'gpu' or 'cpu'
        target_fps: Target frames per second
        error_message: Error message if initialization failed
    """
    success: bool
    rendering_mode: str
    target_fps: int
    error_message: Optional[str] = None


@dataclass
class Phoneme:
    """
    Phoneme timing information for lip sync.
    
    Attributes:
        phoneme: IPA phoneme symbol
        start: Start time in seconds
        duration: Duration in seconds
    """
    phoneme: str
    start: float
    duration: float


@dataclass
class FrameData:
    """
    Frame data with timestamp information.
    
    Attributes:
        frame: RGB image array with shape (height, width, 3)
        timestamp: Frame timestamp in seconds
        frame_number: Sequential frame index
        fps: Current rendering FPS
    """
    frame: np.ndarray
    timestamp: float
    frame_number: int
    fps: float


class AvatarRenderer:
    """
    Renders animated character face using talking-head-anime-3 model.
    
    Supports GPU acceleration via CUDA on Windows with graceful fallback to CPU.
    Tracks rendering performance and maintains target FPS.
    """
    
    def __init__(self):
        """Initialize the avatar renderer (call initialize() to load model)."""
        self.model = None
        self.device = None
        self.rendering_mode = None
        self.target_fps = None
        self.current_fps = 0.0
        self.initialized = False
        self.batch_size = 4  # Default batch size for GPU efficiency
        self.vram_limit_gb = 6.0  # Target VRAM usage limit
        self._frame_times = []  # Track frame rendering times for FPS calculation
        self._max_frame_time_samples = 30  # Rolling average window
        self.character_image = None  # Loaded character image tensor
        
        logger.info("AvatarRenderer created (not yet initialized)")
    
    def initialize(self, use_gpu: bool = True) -> InitResult:
        """
        Initialize renderer with GPU or CPU backend.
        
        This method:
        1. Attempts to load PyTorch and detect CUDA availability
        2. Loads the talking-head-anime-3 model
        3. Configures GPU acceleration if available and requested
        4. Falls back to CPU if GPU initialization fails
        5. Sets target FPS based on rendering mode
        
        Args:
            use_gpu: Whether to attempt GPU initialization (default: True)
            
        Returns:
            InitResult with success status, rendering mode, and target FPS
        """
        start_time = time.time()
        logger.info(f"Initializing AvatarRenderer (use_gpu={use_gpu})...")
        
        try:
            # Import PyTorch
            import torch
            
            # Determine device
            if use_gpu and torch.cuda.is_available():
                try:
                    self.device = torch.device('cuda')
                    self.rendering_mode = 'gpu'
                    self.target_fps = 30
                    logger.info("GPU/CUDA available, attempting GPU initialization")
                except Exception as e:
                    logger.warning(f"GPU initialization failed: {e}, falling back to CPU")
                    self.device = torch.device('cpu')
                    self.rendering_mode = 'cpu'
                    self.target_fps = 24
            else:
                self.device = torch.device('cpu')
                self.rendering_mode = 'cpu'
                self.target_fps = 24
                if use_gpu:
                    logger.info("CUDA not available, using CPU rendering")
                else:
                    logger.info("GPU disabled by configuration, using CPU rendering")
            
            # Load talking-head-anime-3 model
            # Note: load_poser() already creates the model on the specified device
            try:
                self._load_model()
                logger.info(f"Model loaded successfully on {self.device}")
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    logger.warning(f"GPU out of memory: {e}, falling back to CPU")
                    # Fall back to CPU and try again
                    self.device = torch.device('cpu')
                    self.rendering_mode = 'cpu'
                    self.target_fps = 24
                    try:
                        self._load_model()
                        logger.info(f"Model loaded successfully on CPU after GPU OOM")
                    except Exception as cpu_error:
                        error_msg = f"Failed to load model even on CPU: {cpu_error}"
                        logger.error(error_msg)
                        return InitResult(
                            success=False,
                            rendering_mode='cpu',
                            target_fps=24,
                            error_message=error_msg
                        )
                else:
                    error_msg = f"Failed to load talking-head-anime-3 model: {e}"
                    logger.error(error_msg)
                    return InitResult(
                        success=False,
                        rendering_mode='cpu',
                        target_fps=24,
                        error_message=error_msg
                    )
            except Exception as e:
                error_msg = f"Failed to load talking-head-anime-3 model: {e}"
                logger.error(error_msg)
                return InitResult(
                    success=False,
                    rendering_mode='cpu',
                    target_fps=24,
                    error_message=error_msg
                )
            
            self.initialized = True
            elapsed = time.time() - start_time
            
            logger.info(
                f"AvatarRenderer initialized successfully in {elapsed:.2f}s "
                f"(mode={self.rendering_mode}, target_fps={self.target_fps})"
            )
            
            return InitResult(
                success=True,
                rendering_mode=self.rendering_mode,
                target_fps=self.target_fps
            )
            
        except ImportError as e:
            error_msg = f"PyTorch not available: {e}"
            logger.error(error_msg)
            return InitResult(
                success=False,
                rendering_mode='cpu',
                target_fps=24,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error during initialization: {e}"
            logger.error(error_msg)
            return InitResult(
                success=False,
                rendering_mode='cpu',
                target_fps=24,
                error_message=error_msg
            )
    
    def _load_model(self):
        """
        Load the talking-head-anime-3 model.
        
        Loads the poser model from the tha3 library. Uses separable_float
        for CPU mode (smaller, faster) and standard_float for GPU mode
        (larger, more accurate).
        
        Raises:
            Exception: If model loading fails
        """
        import sys
        import os
        from pathlib import Path
        
        # Add tha3_repo to path
        tha3_path = Path(__file__).parent.parent / "tha3_repo"
        if str(tha3_path) not in sys.path:
            sys.path.insert(0, str(tha3_path))
        
        logger.info("Loading talking-head-anime-3 model...")
        
        # Save current directory and change to tha3_repo
        # (model loader expects to be run from tha3_repo directory)
        original_cwd = os.getcwd()
        os.chdir(str(tha3_path))
        
        try:
            from tha3.poser.modes.load_poser import load_poser
            
            # Choose model variant based on rendering mode
            # separable_float: smaller, faster, good for CPU
            # standard_float: larger, more accurate, good for GPU
            if self.rendering_mode == 'gpu':
                model_name = "standard_float"
            else:
                model_name = "separable_float"
            
            logger.info(f"Loading {model_name} model variant...")
            self.model = load_poser(model_name, self.device)
            
            # Force all modules to load now (they lazy-load by default)
            # This ensures they're loaded while we're in the correct directory
            if hasattr(self.model, 'get_modules'):
                logger.info("Pre-loading all model modules...")
                self.model.get_modules()
            
            # Load a default character image if available
            self._load_default_character()
            
            logger.info(f"Model loaded successfully: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load tha3 model: {e}")
            raise
        finally:
            # Restore original directory
            os.chdir(original_cwd)
    
    def _load_default_character(self):
        """Load a default character image for rendering."""
        from pathlib import Path
        from PIL import Image
        import torch
        
        # Look for sample images in tha3_repo/data/images
        images_dir = Path(__file__).parent.parent / "tha3_repo" / "data" / "images"
        
        # Try to find a sample image
        sample_images = list(images_dir.glob("*.png"))
        
        if sample_images:
            # Load the first available image
            image_path = sample_images[0]
            logger.info(f"Loading default character from: {image_path.name}")
            
            try:
                # Load and preprocess image
                pil_image = Image.open(image_path).convert('RGBA')
                
                # Resize to 512x512 if needed
                if pil_image.size != (512, 512):
                    pil_image = pil_image.resize((512, 512), Image.Resampling.LANCZOS)
                
                # Convert to tensor (C, H, W) format with values in [0, 1]
                import numpy as np
                image_array = np.array(pil_image).astype(np.float32) / 255.0
                
                # Convert RGBA to tensor: (H, W, C) -> (C, H, W)
                image_tensor = torch.from_numpy(image_array).permute(2, 0, 1)
                
                # Move to device
                self.character_image = image_tensor.to(self.device)
                
                logger.info(f"Default character loaded: {image_tensor.shape}")
                
            except Exception as e:
                logger.warning(f"Failed to load default character: {e}")
                self.character_image = None
        else:
            logger.warning("No sample images found in tha3_repo/data/images")
            self.character_image = None
    
    def render_frame(self, phoneme: str, intensity: float = 1.0) -> Tuple[np.ndarray, float]:
        """
        Render single frame for given phoneme.
        
        Args:
            phoneme: IPA phoneme symbol or viseme (e.g., 'AH', 'B', 'M', 'A', 'X')
            intensity: Phoneme intensity/emphasis (0.0 to 1.0)
            
        Returns:
            Tuple of (RGB image array with shape (height, width, 3), timestamp in seconds)
            
        Raises:
            RuntimeError: If renderer not initialized
        """
        if not self.initialized:
            raise RuntimeError("AvatarRenderer not initialized. Call initialize() first.")
        
        start_time = time.time()
        
        # Map phoneme/viseme to mouth pose parameters
        pose_params = self._phoneme_to_pose(phoneme, intensity)
        
        try:
            # Render frame using the model
            if self.model is not None and self.character_image is not None:
                import torch
                
                # Create pose tensor with batch dimension
                pose_tensor = torch.tensor([pose_params], dtype=self.model.get_dtype()).to(self.device)
                
                # Add batch dimension to character image if needed
                if self.character_image.dim() == 3:
                    input_image = self.character_image.unsqueeze(0)
                else:
                    input_image = self.character_image
                
                # Render using the poser
                with torch.no_grad():
                    output_image = self.model.pose(input_image, pose_tensor)
                
                # Remove batch dimension and convert to numpy
                # Output is (1, C, H, W) in [0, 1] range
                output_np = output_image[0].cpu().numpy()
                
                # Convert from (C, H, W) to (H, W, C)
                output_np = np.transpose(output_np, (1, 2, 0))
                
                # Clamp values to [0, 1] range to avoid artifacts
                output_np = np.clip(output_np, 0.0, 1.0)
                
                # Convert RGBA to RGB with proper alpha compositing
                if output_np.shape[2] == 4:
                    # Has alpha channel - composite over white background for better visibility
                    rgb = output_np[:, :, :3]
                    alpha = output_np[:, :, 3:4]
                    
                    # Alpha compositing: result = foreground * alpha + background * (1 - alpha)
                    # Using white background (1.0)
                    background = np.ones_like(rgb)
                    composited = rgb * alpha + background * (1.0 - alpha)
                    frame = (composited * 255).astype(np.uint8)
                else:
                    frame = (output_np * 255).astype(np.uint8)
            else:
                # Fallback: Return a blank frame if model not loaded
                frame = np.zeros((512, 512, 3), dtype=np.uint8)
                
        except Exception as e:
            logger.error(f"Frame rendering error: {e}")
            # Return blank frame on error
            frame = np.zeros((512, 512, 3), dtype=np.uint8)
        
        # Track rendering time for FPS calculation
        elapsed = time.time() - start_time
        self._update_fps_tracking(elapsed)
        
        # Monitor VRAM usage if on GPU
        if self.device is not None and self.device.type == 'cuda':
            self._check_vram_usage()
        
        timestamp = time.time()
        
        return frame, timestamp
    
    def _phoneme_to_pose(self, phoneme: str, intensity: float = 1.0) -> List[float]:
        """
        Convert phoneme/viseme to pose parameters for the model.
        
        The tha3 model has multiple pose parameters for different facial features.
        We'll focus on mouth parameters for lip sync.
        
        Args:
            phoneme: Phoneme or viseme identifier
            intensity: Intensity of the expression (0.0 to 1.0)
            
        Returns:
            List of pose parameter values (45 parameters for tha3 model)
        """
        # tha3 model has 45 parameters:
        # 0-11: Eyebrows
        # 12-23: Eyes
        # 24-25: Iris size
        # 26-36: Mouth (aaa, iii, uuu, eee, ooo, delta, lowered_corner, raised_corner, smirk)
        # 37-38: Iris rotation
        # 39-41: Head rotation (head_x, head_y, neck_z)
        # 42-43: Body rotation
        # 44: Breathing
        
        # Initialize all parameters to 0 (neutral pose)
        pose = [0.0] * 45
        
        # Map visemes/phonemes to mouth parameters
        phoneme_upper = phoneme.upper().strip()
        
        # Mouth shape parameters (indices 26-36)
        if phoneme_upper in ['A', 'AA', 'AH', 'AO', 'AW', 'AY']:
            # Open vowels - mouth_aaa (index 26)
            pose[26] = intensity * 1.0
        elif phoneme_upper in ['I', 'IY', 'IH']:
            # High front vowels - mouth_iii (index 27)
            pose[27] = intensity * 0.8
        elif phoneme_upper in ['U', 'UW', 'UH']:
            # High back vowels - mouth_uuu (index 28)
            pose[28] = intensity * 0.8
        elif phoneme_upper in ['E', 'EY', 'EH', 'AE']:
            # Mid/low front vowels - mouth_eee (index 29)
            pose[29] = intensity * 0.9
            # Add slight smile for 'E' sounds
            pose[34] = intensity * 0.3  # mouth_raised_corner_left
            pose[35] = intensity * 0.3  # mouth_raised_corner_right
        elif phoneme_upper in ['O', 'OW', 'OY']:
            # Mid back vowels - mouth_ooo (index 30)
            pose[30] = intensity * 0.9
        elif phoneme_upper in ['B', 'P', 'M']:
            # Bilabial - lips closed, slight mouth_delta (index 31)
            pose[31] = intensity * 0.4
        elif phoneme_upper in ['F', 'V']:
            # Labiodental - lower lip to upper teeth
            pose[32] = intensity * 0.3  # mouth_lowered_corner
            pose[33] = intensity * 0.3
        elif phoneme_upper in ['D', 'T', 'TH', 'DH']:
            # Dental/alveolar - teeth together
            pose[31] = intensity * 0.5  # mouth_delta
        elif phoneme_upper in ['G', 'K']:
            # Velar - mouth open wide
            pose[26] = intensity * 0.7  # mouth_aaa
        elif phoneme_upper in ['X', 'SIL', 'SILENCE', 'SP', '']:
            # Rest/neutral - all zeros (already set)
            pass
        else:
            # Default for other consonants - slight mouth opening
            pose[26] = intensity * 0.3
        
        return pose
    
    def _update_fps_tracking(self, frame_time: float) -> None:
        """
        Update FPS tracking with new frame time.
        
        Args:
            frame_time: Time taken to render frame in seconds
        """
        self._frame_times.append(frame_time)
        
        # Keep only recent samples for rolling average
        if len(self._frame_times) > self._max_frame_time_samples:
            self._frame_times.pop(0)
        
        # Calculate current FPS from average frame time
        if self._frame_times:
            avg_frame_time = sum(self._frame_times) / len(self._frame_times)
            if avg_frame_time > 0:
                self.current_fps = 1.0 / avg_frame_time
    
    def _check_vram_usage(self) -> None:
        """
        Monitor VRAM usage and log warnings if approaching limit.
        
        Checks current VRAM usage and logs warnings if exceeding target limit.
        """
        try:
            import torch
            if torch.cuda.is_available():
                # Get memory usage in bytes
                allocated = torch.cuda.memory_allocated(self.device)
                reserved = torch.cuda.memory_reserved(self.device)
                
                # Convert to GB
                allocated_gb = allocated / (1024 ** 3)
                reserved_gb = reserved / (1024 ** 3)
                
                # Log warning if approaching limit
                if allocated_gb > self.vram_limit_gb * 0.9:
                    logger.warning(
                        f"VRAM usage high: {allocated_gb:.2f}GB allocated "
                        f"(target: {self.vram_limit_gb}GB)"
                    )
                    # Clear cache to free up memory
                    torch.cuda.empty_cache()
                    logger.info("CUDA cache cleared to free VRAM")
                
                # Log detailed stats at debug level
                logger.debug(
                    f"VRAM: {allocated_gb:.2f}GB allocated, "
                    f"{reserved_gb:.2f}GB reserved"
                )
        except Exception as e:
            logger.warning(f"Failed to check VRAM usage: {e}")
    
    def render_sequence(self, phonemes: List[Phoneme]) -> Iterator[FrameData]:
        """
        Stream frames for phoneme sequence with batching for GPU efficiency.
        
        Generates frames for a sequence of phonemes with timing information.
        Yields frames at the target FPS rate. Uses batching when on GPU for
        improved performance.
        
        Args:
            phonemes: List of phonemes with timing information
            
        Yields:
            FrameData objects containing RGB image arrays with timestamps
            
        Raises:
            RuntimeError: If renderer not initialized
        """
        if not self.initialized:
            raise RuntimeError("AvatarRenderer not initialized. Call initialize() first.")
        
        logger.info(f"Rendering sequence of {len(phonemes)} phonemes")
        
        # Calculate total duration
        if not phonemes:
            logger.warning("Empty phoneme sequence provided")
            return
        
        total_duration = max(p.start + p.duration for p in phonemes)
        frame_duration = 1.0 / self.target_fps
        num_frames = int(total_duration * self.target_fps)
        
        logger.info(
            f"Generating {num_frames} frames at {self.target_fps} FPS "
            f"(duration: {total_duration:.2f}s)"
        )
        
        # Determine if we should use batching (GPU mode only)
        use_batching = (
            self.rendering_mode == 'gpu' and 
            self.device is not None and 
            self.device.type == 'cuda'
        )
        
        if use_batching:
            logger.info(f"Using batch rendering with batch_size={self.batch_size}")
            yield from self._render_sequence_batched(phonemes, num_frames, frame_duration)
        else:
            logger.info("Using sequential rendering (CPU mode)")
            yield from self._render_sequence_sequential(phonemes, num_frames, frame_duration)
    
    def _render_sequence_sequential(
        self, 
        phonemes: List[Phoneme], 
        num_frames: int, 
        frame_duration: float
    ) -> Iterator[FrameData]:
        """
        Render frames sequentially (CPU mode).
        
        Args:
            phonemes: List of phonemes with timing
            num_frames: Total number of frames to generate
            frame_duration: Duration of each frame in seconds
            
        Yields:
            FrameData objects for each frame
        """
        for frame_idx in range(num_frames):
            frame_time = frame_idx * frame_duration
            
            # Find active phoneme at this time
            active_phoneme = self._find_active_phoneme(phonemes, frame_time)
            
            # Render frame for active phoneme (or neutral if none)
            phoneme_str = active_phoneme if active_phoneme else 'X'  # X = rest/neutral
            frame, timestamp = self.render_frame(phoneme_str)
            
            yield FrameData(
                frame=frame,
                timestamp=timestamp,
                frame_number=frame_idx,
                fps=self.current_fps
            )
    
    def _render_sequence_batched(
        self, 
        phonemes: List[Phoneme], 
        num_frames: int, 
        frame_duration: float
    ) -> Iterator[FrameData]:
        """
        Render frames in batches for GPU efficiency.
        
        Processes multiple frames together to maximize GPU utilization.
        
        Args:
            phonemes: List of phonemes with timing
            num_frames: Total number of frames to generate
            frame_duration: Duration of each frame in seconds
            
        Yields:
            FrameData objects for each frame
        """
        batch_start_time = time.time()
        
        for batch_start in range(0, num_frames, self.batch_size):
            batch_end = min(batch_start + self.batch_size, num_frames)
            batch_indices = range(batch_start, batch_end)
            
            # Prepare batch of phonemes
            batch_phonemes = []
            batch_times = []
            
            for frame_idx in batch_indices:
                frame_time = frame_idx * frame_duration
                active_phoneme = self._find_active_phoneme(phonemes, frame_time)
                phoneme_str = active_phoneme if active_phoneme else 'X'
                
                batch_phonemes.append(phoneme_str)
                batch_times.append(frame_time)
            
            # Render batch
            batch_frames = self._render_batch(batch_phonemes)
            
            # Yield frames from batch
            for i, (frame_idx, frame) in enumerate(zip(batch_indices, batch_frames)):
                timestamp = time.time()
                
                yield FrameData(
                    frame=frame,
                    timestamp=timestamp,
                    frame_number=frame_idx,
                    fps=self.current_fps
                )
            
            # Monitor VRAM after each batch
            if self.device is not None and self.device.type == 'cuda':
                self._check_vram_usage()
        
        total_time = time.time() - batch_start_time
        avg_fps = num_frames / total_time if total_time > 0 else 0
        logger.info(
            f"Batch rendering complete: {num_frames} frames in {total_time:.2f}s "
            f"(avg {avg_fps:.1f} FPS)"
        )
    
    def _find_active_phoneme(self, phonemes: List[Phoneme], frame_time: float) -> Optional[str]:
        """
        Find the active phoneme at a given time.
        
        Args:
            phonemes: List of phonemes with timing
            frame_time: Time to check in seconds
            
        Returns:
            Phoneme string if found, None otherwise
        """
        for phoneme in phonemes:
            if phoneme.start <= frame_time < phoneme.start + phoneme.duration:
                return phoneme.phoneme
        return None
    
    def _render_batch(self, phonemes: List[str]) -> List[np.ndarray]:
        """
        Render a batch of frames for GPU efficiency.
        
        This method processes multiple phonemes together to maximize GPU
        utilization and reduce overhead.
        
        Args:
            phonemes: List of phoneme strings to render
            
        Returns:
            List of rendered frames as numpy arrays
        """
        start_time = time.time()
        
        if self.model is None or self.character_image is None:
            # Fallback: Generate blank frames
            frames = [np.zeros((512, 512, 3), dtype=np.uint8) for _ in phonemes]
            return frames
        
        try:
            import torch
            
            # Prepare batch of pose parameters
            pose_params_list = [self._phoneme_to_pose(p) for p in phonemes]
            pose_batch = torch.tensor(pose_params_list, dtype=self.model.get_dtype()).to(self.device)
            
            # Batch the character image
            batch_size = len(phonemes)
            image_batch = self.character_image.unsqueeze(0).repeat(batch_size, 1, 1, 1)
            
            # Render batch
            with torch.no_grad():
                output_batch = self.model.pose(image_batch, pose_batch)
            
            # Convert batch to numpy frames
            frames = []
            for i in range(batch_size):
                output_np = output_batch[i].cpu().numpy()
                
                # Convert from (C, H, W) to (H, W, C)
                output_np = np.transpose(output_np, (1, 2, 0))
                
                # Convert RGBA to RGB
                if output_np.shape[2] == 4:
                    rgb = output_np[:, :, :3]
                    alpha = output_np[:, :, 3:4]
                    frame = (rgb * alpha * 255).astype(np.uint8)
                else:
                    frame = (output_np * 255).astype(np.uint8)
                
                frames.append(frame)
                
        except Exception as e:
            logger.error(f"Batch rendering error: {e}")
            # Fallback to blank frames
            frames = [np.zeros((512, 512, 3), dtype=np.uint8) for _ in phonemes]
        
        # Track batch rendering time
        elapsed = time.time() - start_time
        batch_fps = len(phonemes) / elapsed if elapsed > 0 else 0
        logger.debug(f"Rendered batch of {len(phonemes)} frames in {elapsed:.3f}s ({batch_fps:.1f} FPS)")
        
        # Update FPS tracking with average per-frame time
        if len(phonemes) > 0:
            avg_frame_time = elapsed / len(phonemes)
            self._update_fps_tracking(avg_frame_time)
        
        return frames
    
    def get_fps(self) -> float:
        """
        Return current rendering frame rate.
        
        Returns:
            Current FPS (frames per second)
        """
        return self.current_fps
    
    def get_rendering_mode(self) -> Optional[str]:
        """
        Return current rendering mode.
        
        Returns:
            'gpu' or 'cpu', or None if not initialized
        """
        return self.rendering_mode
    
    def get_target_fps(self) -> Optional[int]:
        """
        Return target frame rate.
        
        Returns:
            Target FPS, or None if not initialized
        """
        return self.target_fps
    
    def set_batch_size(self, batch_size: int) -> None:
        """
        Set batch size for GPU rendering.
        
        Larger batch sizes can improve GPU utilization but require more VRAM.
        Only affects GPU rendering mode.
        
        Args:
            batch_size: Number of frames to render in each batch (must be > 0)
            
        Raises:
            ValueError: If batch_size is not positive
        """
        if batch_size <= 0:
            raise ValueError(f"Batch size must be positive, got {batch_size}")
        
        self.batch_size = batch_size
        logger.info(f"Batch size set to {batch_size}")
    
    def get_vram_usage(self) -> Optional[float]:
        """
        Get current VRAM usage in GB.
        
        Returns:
            VRAM usage in GB, or None if not using GPU
        """
        if self.device is None or self.device.type != 'cuda':
            return None
        
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(self.device)
                return allocated / (1024 ** 3)
        except Exception as e:
            logger.warning(f"Failed to get VRAM usage: {e}")
        
        return None
    
    def shutdown(self) -> None:
        """
        Clean up resources.
        
        Releases model and clears GPU memory if applicable.
        """
        logger.info("Shutting down AvatarRenderer...")
        
        if self.model is not None:
            del self.model
            self.model = None
        
        # Clear CUDA cache if using GPU
        if self.device is not None and self.device.type == 'cuda':
            try:
                import torch
                torch.cuda.empty_cache()
                logger.info("CUDA cache cleared")
            except Exception as e:
                logger.warning(f"Failed to clear CUDA cache: {e}")
        
        self.initialized = False
        self.device = None
        self.rendering_mode = None
        self.target_fps = None
        self.current_fps = 0.0
        
        logger.info("AvatarRenderer shutdown complete")
