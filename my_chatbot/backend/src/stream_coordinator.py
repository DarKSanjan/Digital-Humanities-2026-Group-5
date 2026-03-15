"""
Stream Coordinator Component

Orchestrates parallel processing of audio playback and avatar rendering.
Uses Python's asyncio for concurrent task management and monitors synchronization
to maintain the 100ms tolerance between audio and video.
"""

import asyncio
import logging
import time
from typing import AsyncIterator, List, Optional
from dataclasses import dataclass
import numpy as np

from avatar_renderer import AvatarRenderer, Phoneme, FrameData
from lip_sync_controller import LipSyncController, Viseme

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """
    Audio chunk with phoneme timing data.
    
    Attributes:
        audio_data: Raw audio data as bytes
        phonemes: List of phonemes with timing information
        timestamp: Chunk timestamp in seconds
        sample_rate: Audio sample rate in Hz
    """
    audio_data: bytes
    phonemes: List[Phoneme]
    timestamp: float
    sample_rate: int = 22050


@dataclass
class SyncMetrics:
    """
    Synchronization metrics for monitoring A/V sync.
    
    Attributes:
        audio_timestamp: Current audio playback timestamp
        video_timestamp: Current video frame timestamp
        drift_ms: Synchronization drift in milliseconds
        within_tolerance: Whether drift is within 100ms tolerance
    """
    audio_timestamp: float
    video_timestamp: float
    drift_ms: float
    within_tolerance: bool


class StreamCoordinator:
    """
    Coordinates parallel processing of audio playback and avatar rendering.
    
    This component orchestrates the real-time streaming pipeline:
    1. Receives audio chunks with phoneme timing data
    2. Plays audio through system audio output
    3. Renders avatar frames in parallel based on phonemes
    4. Monitors synchronization to maintain 100ms tolerance
    5. Buffers frames ahead to smooth rendering jitter
    
    Uses asyncio for concurrent task management to ensure audio playback
    (real-time constraint) and avatar rendering run in parallel without blocking.
    """
    
    def __init__(
        self,
        avatar_renderer: AvatarRenderer,
        lip_sync_controller: LipSyncController,
        sync_tolerance_ms: float = 100.0,
        frame_buffer_size: int = 3
    ):
        """
        Initialize the stream coordinator.
        
        Args:
            avatar_renderer: Avatar renderer instance for generating frames
            lip_sync_controller: Lip sync controller for phoneme-to-viseme mapping
            sync_tolerance_ms: Maximum acceptable A/V sync drift in milliseconds
            frame_buffer_size: Number of frames to buffer ahead (2-3 recommended)
        """
        self.avatar_renderer = avatar_renderer
        self.lip_sync_controller = lip_sync_controller
        self.sync_tolerance_ms = sync_tolerance_ms
        self.frame_buffer_size = frame_buffer_size
        
        # Synchronization tracking
        self._audio_timestamp = 0.0
        self._video_timestamp = 0.0
        self._sync_drift_history: List[float] = []
        self._max_drift_history = 100  # Keep last 100 measurements
        
        # Frame buffering
        self._frame_buffer: asyncio.Queue = asyncio.Queue(maxsize=frame_buffer_size)
        self._is_streaming = False
        
        logger.info(
            f"StreamCoordinator initialized "
            f"(sync_tolerance={sync_tolerance_ms}ms, buffer_size={frame_buffer_size})"
        )
    
    async def process_speech_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[FrameData]:
        """
        Coordinate parallel audio playback and avatar rendering.
        
        This is the main entry point for processing a speech stream. It:
        1. Receives audio chunks with phoneme data
        2. Starts audio playback task (priority: real-time)
        3. Starts avatar rendering task (parallel processing)
        4. Monitors synchronization between audio and video
        5. Yields rendered frames for display
        
        Audio playback has priority as it's a real-time constraint. Avatar
        rendering runs in parallel and drops frames if falling behind to
        maintain synchronization.
        
        Args:
            audio_stream: Async iterator of audio chunks with phoneme data
            
        Yields:
            FrameData objects containing rendered avatar frames
            
        Raises:
            RuntimeError: If avatar renderer not initialized
        """
        if not self.avatar_renderer.initialized:
            raise RuntimeError("AvatarRenderer must be initialized before streaming")
        
        self._is_streaming = True
        logger.info("Starting speech stream processing")
        
        try:
            # Process each audio chunk
            async for audio_chunk in audio_stream:
                logger.debug(
                    f"Processing audio chunk: {len(audio_chunk.phonemes)} phonemes, "
                    f"{len(audio_chunk.audio_data)} bytes"
                )
                
                # Create tasks for parallel processing
                audio_task = asyncio.create_task(
                    self.play_audio(audio_chunk),
                    name="audio_playback"
                )
                
                render_task = asyncio.create_task(
                    self._render_and_buffer_frames(audio_chunk.phonemes),
                    name="avatar_rendering"
                )
                
                # Wait for both tasks to complete
                # Audio has priority, but we want both to finish
                await asyncio.gather(audio_task, render_task)
                
                # Yield buffered frames
                while not self._frame_buffer.empty():
                    try:
                        frame_data = self._frame_buffer.get_nowait()
                        
                        # Update video timestamp
                        self._video_timestamp = frame_data.timestamp
                        
                        # Check synchronization
                        sync_metrics = self._calculate_sync_metrics()
                        if not sync_metrics.within_tolerance:
                            logger.warning(
                                f"A/V sync drift: {sync_metrics.drift_ms:.1f}ms "
                                f"(tolerance: {self.sync_tolerance_ms}ms)"
                            )
                        
                        yield frame_data
                        
                    except asyncio.QueueEmpty:
                        break
        
        finally:
            self._is_streaming = False
            logger.info("Speech stream processing complete")
    
    async def play_audio(self, audio_chunk: AudioChunk) -> None:
        """
        Play audio chunk through system audio output.
        
        This method simulates audio playback. In a real implementation, this would:
        1. Send audio data to system audio device (e.g., via pyaudio, sounddevice)
        2. Track playback position for synchronization
        3. Handle audio buffer underruns
        
        Audio playback is a real-time constraint and has priority over rendering.
        
        Args:
            audio_chunk: Audio chunk with data and timing information
        """
        start_time = time.time()
        
        # Update audio timestamp
        self._audio_timestamp = audio_chunk.timestamp
        
        # TODO: Implement actual audio playback
        # In production, this would use a library like pyaudio or sounddevice:
        # 
        # import sounddevice as sd
        # audio_array = np.frombuffer(audio_chunk.audio_data, dtype=np.int16)
        # sd.play(audio_array, audio_chunk.sample_rate)
        # sd.wait()  # Wait for playback to complete
        
        # Placeholder: Simulate audio playback duration
        # Calculate duration from audio data size and sample rate
        # Assuming 16-bit audio (2 bytes per sample)
        num_samples = len(audio_chunk.audio_data) // 2
        duration = num_samples / audio_chunk.sample_rate
        
        logger.debug(
            f"Playing audio chunk: {duration:.3f}s, "
            f"{len(audio_chunk.audio_data)} bytes @ {audio_chunk.sample_rate}Hz"
        )
        
        # Simulate playback time
        await asyncio.sleep(duration)
        
        elapsed = time.time() - start_time
        logger.debug(f"Audio playback complete in {elapsed:.3f}s")
    
    async def render_avatar(self, phonemes: List[Phoneme]) -> AsyncIterator[FrameData]:
        """
        Generate avatar frames for phoneme sequence.
        
        This method:
        1. Converts phonemes to visemes using LipSyncController
        2. Generates frames using AvatarRenderer
        3. Yields frames as they're rendered
        
        Runs in parallel with audio playback. If rendering falls behind,
        frames may be dropped to maintain synchronization.
        
        Args:
            phonemes: List of phonemes with timing information
            
        Yields:
            FrameData objects containing rendered frames
        """
        if not phonemes:
            logger.debug("No phonemes to render")
            return
        
        logger.debug(f"Rendering avatar for {len(phonemes)} phonemes")
        
        # Generate viseme sequence with interpolation
        fps = self.avatar_renderer.target_fps or 30
        visemes = self.lip_sync_controller.generate_animation_sequence(phonemes, fps)
        visemes = self.lip_sync_controller.interpolate_transitions(visemes, fps)
        
        logger.debug(f"Generated {len(visemes)} visemes for animation")
        
        # Render frames using avatar renderer
        # Note: render_sequence expects Phoneme objects, but we have visemes
        # For now, convert visemes back to phoneme format for rendering
        viseme_phonemes = [
            Phoneme(phoneme=v.viseme, start=v.start, duration=v.duration)
            for v in visemes
        ]
        
        # Use the avatar renderer's render_sequence method
        # This returns an iterator, so we need to iterate in an async-friendly way
        frame_count = 0
        for frame_data in self.avatar_renderer.render_sequence(viseme_phonemes):
            frame_count += 1
            yield frame_data
            
            # Allow other tasks to run (cooperative multitasking)
            await asyncio.sleep(0)
        
        logger.debug(f"Rendered {frame_count} frames")
    
    async def _render_and_buffer_frames(self, phonemes: List[Phoneme]) -> None:
        """
        Render frames and add them to the buffer.
        
        This internal method handles the rendering pipeline and frame buffering.
        Frames are buffered ahead (2-3 frames) to smooth rendering jitter.
        
        Args:
            phonemes: List of phonemes to render
        """
        async for frame_data in self.render_avatar(phonemes):
            try:
                # Add frame to buffer (non-blocking)
                # If buffer is full, this will raise QueueFull
                self._frame_buffer.put_nowait(frame_data)
                logger.debug(
                    f"Buffered frame {frame_data.frame_number} "
                    f"(buffer size: {self._frame_buffer.qsize()})"
                )
            except asyncio.QueueFull:
                # Buffer is full, drop this frame to avoid blocking
                logger.warning(
                    f"Frame buffer full, dropping frame {frame_data.frame_number} "
                    f"to maintain sync"
                )
                # Continue rendering next frames
    
    def synchronize(self, audio_timestamp: float, frame_timestamp: float) -> None:
        """
        Maintain A/V synchronization within tolerance.
        
        This method is called to manually adjust synchronization if needed.
        It calculates the drift between audio and video timestamps and
        logs warnings if drift exceeds tolerance.
        
        Args:
            audio_timestamp: Current audio playback timestamp in seconds
            frame_timestamp: Current video frame timestamp in seconds
        """
        self._audio_timestamp = audio_timestamp
        self._video_timestamp = frame_timestamp
        
        sync_metrics = self._calculate_sync_metrics()
        
        # Log sync status
        if sync_metrics.within_tolerance:
            logger.debug(
                f"A/V sync OK: drift={sync_metrics.drift_ms:.1f}ms "
                f"(audio={audio_timestamp:.3f}s, video={frame_timestamp:.3f}s)"
            )
        else:
            logger.warning(
                f"A/V sync drift: {sync_metrics.drift_ms:.1f}ms exceeds "
                f"tolerance ({self.sync_tolerance_ms}ms)"
            )
    
    def _calculate_sync_metrics(self) -> SyncMetrics:
        """
        Calculate current synchronization metrics.
        
        Returns:
            SyncMetrics with current drift and tolerance status
        """
        # Calculate drift in milliseconds
        drift_seconds = abs(self._audio_timestamp - self._video_timestamp)
        drift_ms = drift_seconds * 1000.0
        
        # Check if within tolerance (allow small floating point tolerance)
        within_tolerance = drift_ms <= self.sync_tolerance_ms + 0.001
        
        # Track drift history
        self._sync_drift_history.append(drift_ms)
        if len(self._sync_drift_history) > self._max_drift_history:
            self._sync_drift_history.pop(0)
        
        return SyncMetrics(
            audio_timestamp=self._audio_timestamp,
            video_timestamp=self._video_timestamp,
            drift_ms=drift_ms,
            within_tolerance=within_tolerance
        )
    
    def get_sync_stats(self) -> dict:
        """
        Get synchronization statistics.
        
        Returns:
            Dictionary with sync statistics including average and max drift
        """
        if not self._sync_drift_history:
            return {
                'avg_drift_ms': 0.0,
                'max_drift_ms': 0.0,
                'min_drift_ms': 0.0,
                'samples': 0,
                'within_tolerance_pct': 100.0
            }
        
        avg_drift = sum(self._sync_drift_history) / len(self._sync_drift_history)
        max_drift = max(self._sync_drift_history)
        min_drift = min(self._sync_drift_history)
        
        within_tolerance_count = sum(
            1 for drift in self._sync_drift_history 
            if drift <= self.sync_tolerance_ms
        )
        within_tolerance_pct = (within_tolerance_count / len(self._sync_drift_history)) * 100.0
        
        return {
            'avg_drift_ms': avg_drift,
            'max_drift_ms': max_drift,
            'min_drift_ms': min_drift,
            'samples': len(self._sync_drift_history),
            'within_tolerance_pct': within_tolerance_pct
        }
    
    def reset_sync_tracking(self) -> None:
        """Reset synchronization tracking state."""
        self._audio_timestamp = 0.0
        self._video_timestamp = 0.0
        self._sync_drift_history.clear()
        logger.info("Sync tracking reset")
    
    def is_streaming(self) -> bool:
        """
        Check if currently streaming.
        
        Returns:
            True if stream is active, False otherwise
        """
        return self._is_streaming
    
    def get_buffer_status(self) -> dict:
        """
        Get frame buffer status.
        
        Returns:
            Dictionary with buffer size and capacity information
        """
        return {
            'current_size': self._frame_buffer.qsize(),
            'max_size': self.frame_buffer_size,
            'utilization_pct': (self._frame_buffer.qsize() / self.frame_buffer_size) * 100.0
        }
