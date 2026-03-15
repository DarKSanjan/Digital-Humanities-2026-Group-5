"""
Unit tests for StreamCoordinator component.

Tests the stream coordinator's ability to orchestrate parallel audio playback
and avatar rendering with synchronization monitoring.
"""

import pytest
import asyncio
import time
from typing import List, AsyncIterator
import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from stream_coordinator import (
    StreamCoordinator,
    AudioChunk,
    SyncMetrics
)
from avatar_renderer import AvatarRenderer, Phoneme, FrameData
from lip_sync_controller import LipSyncController


@pytest.fixture
def avatar_renderer():
    """Create and initialize an avatar renderer for testing."""
    renderer = AvatarRenderer()
    result = renderer.initialize(use_gpu=False)  # Use CPU for testing
    assert result.success
    return renderer


@pytest.fixture
def lip_sync_controller():
    """Create a lip sync controller for testing."""
    return LipSyncController()


@pytest.fixture
def stream_coordinator(avatar_renderer, lip_sync_controller):
    """Create a stream coordinator for testing."""
    return StreamCoordinator(
        avatar_renderer=avatar_renderer,
        lip_sync_controller=lip_sync_controller,
        sync_tolerance_ms=100.0,
        frame_buffer_size=3
    )


class TestStreamCoordinatorInitialization:
    """Test stream coordinator initialization."""
    
    def test_initialization(self, stream_coordinator):
        """Test that stream coordinator initializes correctly."""
        assert stream_coordinator.avatar_renderer is not None
        assert stream_coordinator.lip_sync_controller is not None
        assert stream_coordinator.sync_tolerance_ms == 100.0
        assert stream_coordinator.frame_buffer_size == 3
        assert not stream_coordinator.is_streaming()
    
    def test_custom_sync_tolerance(self, avatar_renderer, lip_sync_controller):
        """Test initialization with custom sync tolerance."""
        coordinator = StreamCoordinator(
            avatar_renderer=avatar_renderer,
            lip_sync_controller=lip_sync_controller,
            sync_tolerance_ms=50.0
        )
        assert coordinator.sync_tolerance_ms == 50.0
    
    def test_custom_buffer_size(self, avatar_renderer, lip_sync_controller):
        """Test initialization with custom buffer size."""
        coordinator = StreamCoordinator(
            avatar_renderer=avatar_renderer,
            lip_sync_controller=lip_sync_controller,
            frame_buffer_size=5
        )
        assert coordinator.frame_buffer_size == 5


class TestAudioPlayback:
    """Test audio playback functionality."""
    
    @pytest.mark.asyncio
    async def test_play_audio_basic(self, stream_coordinator):
        """Test basic audio playback."""
        # Create a simple audio chunk
        audio_chunk = AudioChunk(
            audio_data=b'\x00' * 4410,  # 0.1 seconds at 22050Hz, 16-bit
            phonemes=[Phoneme(phoneme='AH', start=0.0, duration=0.1)],
            timestamp=0.0,
            sample_rate=22050
        )
        
        start_time = time.time()
        await stream_coordinator.play_audio(audio_chunk)
        elapsed = time.time() - start_time
        
        # Should take approximately 0.1 seconds (with some tolerance)
        assert 0.05 <= elapsed <= 0.2
    
    @pytest.mark.asyncio
    async def test_play_audio_updates_timestamp(self, stream_coordinator):
        """Test that audio playback updates the audio timestamp."""
        audio_chunk = AudioChunk(
            audio_data=b'\x00' * 2205,
            phonemes=[],
            timestamp=1.5,
            sample_rate=22050
        )
        
        await stream_coordinator.play_audio(audio_chunk)
        
        # Check that audio timestamp was updated
        assert stream_coordinator._audio_timestamp == 1.5


class TestAvatarRendering:
    """Test avatar rendering functionality."""
    
    @pytest.mark.asyncio
    async def test_render_avatar_basic(self, stream_coordinator):
        """Test basic avatar rendering."""
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='B', start=0.1, duration=0.1),
        ]
        
        frames = []
        async for frame_data in stream_coordinator.render_avatar(phonemes):
            frames.append(frame_data)
        
        # Should generate frames for the phoneme sequence
        assert len(frames) > 0
        
        # Check frame data structure
        for frame in frames:
            assert isinstance(frame, FrameData)
            assert isinstance(frame.frame, np.ndarray)
            assert frame.timestamp > 0
            assert frame.frame_number >= 0
    
    @pytest.mark.asyncio
    async def test_render_avatar_empty_phonemes(self, stream_coordinator):
        """Test rendering with empty phoneme list."""
        frames = []
        async for frame_data in stream_coordinator.render_avatar([]):
            frames.append(frame_data)
        
        # Should not generate any frames
        assert len(frames) == 0
    
    @pytest.mark.asyncio
    async def test_render_avatar_uses_lip_sync(self, stream_coordinator):
        """Test that rendering uses lip sync controller."""
        phonemes = [
            Phoneme(phoneme='P', start=0.0, duration=0.05),
            Phoneme(phoneme='AH', start=0.05, duration=0.1),
        ]
        
        frames = []
        async for frame_data in stream_coordinator.render_avatar(phonemes):
            frames.append(frame_data)
        
        # Should generate frames based on viseme sequence
        assert len(frames) > 0


class TestSynchronization:
    """Test synchronization monitoring."""
    
    def test_synchronize_within_tolerance(self, stream_coordinator):
        """Test synchronization when within tolerance."""
        stream_coordinator.synchronize(
            audio_timestamp=1.0,
            frame_timestamp=1.05  # 50ms drift
        )
        
        sync_metrics = stream_coordinator._calculate_sync_metrics()
        assert abs(sync_metrics.drift_ms - 50.0) < 0.01  # Allow floating point tolerance
        assert sync_metrics.within_tolerance
    
    def test_synchronize_exceeds_tolerance(self, stream_coordinator):
        """Test synchronization when exceeding tolerance."""
        stream_coordinator.synchronize(
            audio_timestamp=1.0,
            frame_timestamp=1.15  # 150ms drift
        )
        
        sync_metrics = stream_coordinator._calculate_sync_metrics()
        assert abs(sync_metrics.drift_ms - 150.0) < 0.01  # Allow floating point tolerance
        assert not sync_metrics.within_tolerance
    
    def test_synchronize_exact_match(self, stream_coordinator):
        """Test synchronization with exact timestamp match."""
        stream_coordinator.synchronize(
            audio_timestamp=2.5,
            frame_timestamp=2.5
        )
        
        sync_metrics = stream_coordinator._calculate_sync_metrics()
        assert sync_metrics.drift_ms == 0.0
        assert sync_metrics.within_tolerance
    
    def test_sync_stats_tracking(self, stream_coordinator):
        """Test that sync statistics are tracked correctly."""
        # Perform several synchronization checks
        stream_coordinator.synchronize(1.0, 1.05)  # 50ms
        stream_coordinator.synchronize(2.0, 2.08)  # 80ms
        stream_coordinator.synchronize(3.0, 3.15)  # 150ms
        
        stats = stream_coordinator.get_sync_stats()
        
        assert stats['samples'] == 3
        assert abs(stats['min_drift_ms'] - 50.0) < 0.01  # Allow floating point tolerance
        assert abs(stats['max_drift_ms'] - 150.0) < 0.01  # Allow floating point tolerance
        assert 50.0 <= stats['avg_drift_ms'] <= 150.0
        # 2 out of 3 within tolerance (100ms)
        assert abs(stats['within_tolerance_pct'] - 66.67) < 1.0
    
    def test_reset_sync_tracking(self, stream_coordinator):
        """Test resetting sync tracking."""
        stream_coordinator.synchronize(1.0, 1.05)
        stream_coordinator.synchronize(2.0, 2.08)
        
        stream_coordinator.reset_sync_tracking()
        
        stats = stream_coordinator.get_sync_stats()
        assert stats['samples'] == 0
        assert stats['avg_drift_ms'] == 0.0


class TestBufferManagement:
    """Test frame buffer management."""
    
    def test_buffer_status_initial(self, stream_coordinator):
        """Test initial buffer status."""
        status = stream_coordinator.get_buffer_status()
        
        assert status['current_size'] == 0
        assert status['max_size'] == 3
        assert status['utilization_pct'] == 0.0
    
    @pytest.mark.asyncio
    async def test_buffer_fills_during_rendering(self, stream_coordinator):
        """Test that buffer fills during rendering."""
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
        ]
        
        # Start rendering and buffering
        await stream_coordinator._render_and_buffer_frames(phonemes)
        
        # Buffer should have frames
        status = stream_coordinator.get_buffer_status()
        assert status['current_size'] > 0


class TestStreamProcessing:
    """Test end-to-end stream processing."""
    
    async def create_audio_stream(self, chunks: List[AudioChunk]) -> AsyncIterator[AudioChunk]:
        """Helper to create an async audio stream."""
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.01)  # Small delay between chunks
    
    @pytest.mark.asyncio
    async def test_process_speech_stream_basic(self, stream_coordinator):
        """Test basic speech stream processing."""
        # Create audio chunks
        chunks = [
            AudioChunk(
                audio_data=b'\x00' * 2205,  # 0.05s
                phonemes=[Phoneme(phoneme='AH', start=0.0, duration=0.05)],
                timestamp=0.0,
                sample_rate=22050
            ),
            AudioChunk(
                audio_data=b'\x00' * 2205,
                phonemes=[Phoneme(phoneme='B', start=0.05, duration=0.05)],
                timestamp=0.05,
                sample_rate=22050
            ),
        ]
        
        # Process stream
        frames = []
        async for frame_data in stream_coordinator.process_speech_stream(
            self.create_audio_stream(chunks)
        ):
            frames.append(frame_data)
        
        # Should generate frames
        assert len(frames) > 0
        
        # Check that streaming flag was set and cleared
        assert not stream_coordinator.is_streaming()
    
    @pytest.mark.asyncio
    async def test_process_speech_stream_requires_initialization(
        self, lip_sync_controller
    ):
        """Test that stream processing requires initialized renderer."""
        # Create uninitialized renderer
        renderer = AvatarRenderer()
        coordinator = StreamCoordinator(
            avatar_renderer=renderer,
            lip_sync_controller=lip_sync_controller
        )
        
        chunks = [
            AudioChunk(
                audio_data=b'\x00' * 2205,
                phonemes=[],
                timestamp=0.0,
                sample_rate=22050
            )
        ]
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="must be initialized"):
            async for _ in coordinator.process_speech_stream(
                self.create_audio_stream(chunks)
            ):
                pass
    
    @pytest.mark.asyncio
    async def test_process_speech_stream_parallel_execution(
        self, stream_coordinator
    ):
        """Test that audio and rendering execute in parallel."""
        chunks = [
            AudioChunk(
                audio_data=b'\x00' * 4410,  # 0.1s
                phonemes=[
                    Phoneme(phoneme='AH', start=0.0, duration=0.05),
                    Phoneme(phoneme='B', start=0.05, duration=0.05),
                ],
                timestamp=0.0,
                sample_rate=22050
            ),
        ]
        
        start_time = time.time()
        
        frames = []
        async for frame_data in stream_coordinator.process_speech_stream(
            self.create_audio_stream(chunks)
        ):
            frames.append(frame_data)
        
        elapsed = time.time() - start_time
        
        # Should complete in roughly the audio duration (parallel execution)
        # If sequential, it would take audio_duration + rendering_duration
        # With parallel execution, it should be closer to max(audio, rendering)
        assert elapsed < 0.5  # Should be much faster than sequential


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_audio_stream(self, stream_coordinator):
        """Test processing an empty audio stream."""
        async def empty_stream():
            return
            yield  # Make it a generator
        
        frames = []
        async for frame_data in stream_coordinator.process_speech_stream(empty_stream()):
            frames.append(frame_data)
        
        # Should handle empty stream gracefully
        assert len(frames) == 0
    
    def test_get_sync_stats_no_history(self, stream_coordinator):
        """Test getting sync stats with no history."""
        stats = stream_coordinator.get_sync_stats()
        
        assert stats['samples'] == 0
        assert stats['avg_drift_ms'] == 0.0
        assert stats['max_drift_ms'] == 0.0
        assert stats['within_tolerance_pct'] == 100.0
