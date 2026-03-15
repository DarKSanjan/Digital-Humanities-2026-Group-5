"""
Integration tests for StreamCoordinator with AvatarRenderer and LipSyncController.

Tests the complete integration of components including:
- Frame buffering (2-3 frames ahead)
- Frame dropping when rendering falls behind
- A/V sync monitoring and logging
- Requirements 2.2, 8.1, 8.2
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


class TestComponentIntegration:
    """Test integration of AvatarRenderer and LipSyncController in StreamCoordinator."""
    
    @pytest.mark.asyncio
    async def test_complete_integration_pipeline(self, stream_coordinator):
        """
        Test complete integration: phonemes -> visemes -> frames.
        
        Validates Requirements 2.2, 8.1, 8.2:
        - Lip sync controller synchronizes mouth movements with speech
        - Synchronization maintained within 100ms tolerance
        """
        # Create realistic phoneme sequence
        phonemes = [
            Phoneme(phoneme='P', start=0.0, duration=0.05),   # Bilabial
            Phoneme(phoneme='AH', start=0.05, duration=0.1),  # Open vowel
            Phoneme(phoneme='T', start=0.15, duration=0.05),  # Alveolar
            Phoneme(phoneme='IY', start=0.2, duration=0.1),   # Front vowel
        ]
        
        # Render avatar frames
        frames = []
        async for frame_data in stream_coordinator.render_avatar(phonemes):
            frames.append(frame_data)
        
        # Verify frames were generated
        assert len(frames) > 0, "Should generate frames for phoneme sequence"
        
        # Verify frame structure
        for frame in frames:
            assert isinstance(frame, FrameData)
            assert isinstance(frame.frame, np.ndarray)
            assert frame.frame.shape == (512, 512, 3), "Frame should be 512x512 RGB"
            assert frame.timestamp > 0
            assert frame.frame_number >= 0
    
    @pytest.mark.asyncio
    async def test_frame_buffering_2_3_frames_ahead(self, stream_coordinator):
        """
        Test that frame buffering maintains 2-3 frames ahead.
        
        Validates task requirement: Implement frame buffering (2-3 frames ahead)
        """
        # Create phoneme sequence that will generate multiple frames
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.2),
            Phoneme(phoneme='B', start=0.2, duration=0.2),
        ]
        
        # Start rendering and buffering
        await stream_coordinator._render_and_buffer_frames(phonemes)
        
        # Check buffer status
        status = stream_coordinator.get_buffer_status()
        
        # Buffer should have frames (up to max_size=3)
        assert status['current_size'] > 0, "Buffer should contain frames"
        assert status['current_size'] <= 3, "Buffer should not exceed max size"
        assert status['max_size'] == 3, "Buffer max size should be 3"
        
        # Verify buffer utilization is reasonable
        assert 0 <= status['utilization_pct'] <= 100
    
    @pytest.mark.asyncio
    async def test_frame_dropping_when_behind(self, stream_coordinator, caplog):
        """
        Test that frames are dropped when rendering falls behind.
        
        Validates task requirement: Add frame dropping if rendering falls behind
        """
        import logging
        caplog.set_level(logging.WARNING)
        
        # Fill the buffer first
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='B', start=0.1, duration=0.1),
            Phoneme(phoneme='M', start=0.2, duration=0.1),
        ]
        
        # Render frames to fill buffer
        await stream_coordinator._render_and_buffer_frames(phonemes)
        
        # Buffer should be at or near capacity
        status = stream_coordinator.get_buffer_status()
        initial_size = status['current_size']
        
        # Try to add more frames (should trigger dropping if buffer full)
        more_phonemes = [
            Phoneme(phoneme='P', start=0.3, duration=0.1),
            Phoneme(phoneme='T', start=0.4, duration=0.1),
        ]
        
        await stream_coordinator._render_and_buffer_frames(more_phonemes)
        
        # Check if frame dropping was logged (if buffer was full)
        if initial_size >= 3:
            # Buffer was full, should have dropped frames
            assert any(
                "dropping frame" in record.message.lower() 
                for record in caplog.records
            ), "Should log frame dropping when buffer is full"
    
    @pytest.mark.asyncio
    async def test_av_sync_monitoring_and_logging(self, stream_coordinator, caplog):
        """
        Test A/V sync drift monitoring and logging.
        
        Validates task requirement: Monitor and log A/V sync drift
        Validates Requirements 8.1, 8.2: Maintain synchronization within 100ms
        """
        import logging
        caplog.set_level(logging.DEBUG)
        
        # Test sync within tolerance
        stream_coordinator.synchronize(
            audio_timestamp=1.0,
            frame_timestamp=1.05  # 50ms drift - within tolerance
        )
        
        sync_metrics = stream_coordinator._calculate_sync_metrics()
        assert sync_metrics.within_tolerance, "50ms drift should be within 100ms tolerance"
        assert abs(sync_metrics.drift_ms - 50.0) < 1.0
        
        # Check that sync was logged
        assert any(
            "sync" in record.message.lower() 
            for record in caplog.records
        ), "Should log sync status"
        
        # Clear logs
        caplog.clear()
        
        # Test sync exceeding tolerance
        stream_coordinator.synchronize(
            audio_timestamp=2.0,
            frame_timestamp=2.15  # 150ms drift - exceeds tolerance
        )
        
        sync_metrics = stream_coordinator._calculate_sync_metrics()
        assert not sync_metrics.within_tolerance, "150ms drift should exceed 100ms tolerance"
        assert abs(sync_metrics.drift_ms - 150.0) < 1.0
        
        # Check that warning was logged
        assert any(
            "warning" in record.levelname.lower() and "drift" in record.message.lower()
            for record in caplog.records
        ), "Should log warning when sync exceeds tolerance"
    
    @pytest.mark.asyncio
    async def test_sync_stats_tracking_over_time(self, stream_coordinator):
        """
        Test that sync statistics are tracked over time.
        
        Validates task requirement: Monitor and log A/V sync drift
        """
        # Perform multiple sync checks with varying drift
        sync_checks = [
            (1.0, 1.03),   # 30ms
            (2.0, 2.05),   # 50ms
            (3.0, 3.08),   # 80ms
            (4.0, 4.12),   # 120ms - exceeds tolerance
            (5.0, 5.02),   # 20ms
        ]
        
        for audio_ts, video_ts in sync_checks:
            stream_coordinator.synchronize(audio_ts, video_ts)
        
        # Get sync statistics
        stats = stream_coordinator.get_sync_stats()
        
        # Verify stats are tracked
        assert stats['samples'] == 5, "Should track all sync checks"
        assert stats['min_drift_ms'] > 0, "Should track minimum drift"
        assert stats['max_drift_ms'] > 100, "Should track maximum drift"
        assert 0 < stats['avg_drift_ms'] < 150, "Should calculate average drift"
        
        # 4 out of 5 within tolerance (80%)
        assert 70 <= stats['within_tolerance_pct'] <= 90, "Should calculate tolerance percentage"
    
    async def create_audio_stream(self, chunks: List[AudioChunk]) -> AsyncIterator[AudioChunk]:
        """Helper to create an async audio stream."""
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.01)
    
    @pytest.mark.asyncio
    async def test_end_to_end_stream_processing_with_sync(self, stream_coordinator, caplog):
        """
        Test complete end-to-end stream processing with sync monitoring.
        
        Validates all task requirements:
        - Component integration
        - Frame buffering
        - A/V sync monitoring
        """
        import logging
        caplog.set_level(logging.INFO)
        
        # Create realistic audio stream with phonemes
        chunks = [
            AudioChunk(
                audio_data=b'\x00' * 4410,  # 0.1s at 22050Hz
                phonemes=[
                    Phoneme(phoneme='P', start=0.0, duration=0.05),
                    Phoneme(phoneme='AH', start=0.05, duration=0.05),
                ],
                timestamp=0.0,
                sample_rate=22050
            ),
            AudioChunk(
                audio_data=b'\x00' * 4410,
                phonemes=[
                    Phoneme(phoneme='T', start=0.1, duration=0.05),
                    Phoneme(phoneme='IY', start=0.15, duration=0.05),
                ],
                timestamp=0.1,
                sample_rate=22050
            ),
        ]
        
        # Process stream
        frames = []
        async for frame_data in stream_coordinator.process_speech_stream(
            self.create_audio_stream(chunks)
        ):
            frames.append(frame_data)
            
            # Verify frame timestamps are progressing
            if len(frames) > 1:
                assert frame_data.timestamp >= frames[-2].timestamp
        
        # Verify frames were generated
        assert len(frames) > 0, "Should generate frames from stream"
        
        # Verify logging occurred
        assert any(
            "processing" in record.message.lower()
            for record in caplog.records
        ), "Should log stream processing"
        
        # Verify streaming flag was managed correctly
        assert not stream_coordinator.is_streaming(), "Should clear streaming flag after completion"
    
    @pytest.mark.asyncio
    async def test_lip_sync_controller_integration(self, stream_coordinator):
        """
        Test that LipSyncController is properly integrated.
        
        Validates Requirements 2.2, 8.1: Lip sync synchronizes with speech
        """
        # Create phonemes that map to different visemes
        phonemes = [
            Phoneme(phoneme='P', start=0.0, duration=0.05),   # Maps to viseme B
            Phoneme(phoneme='AH', start=0.05, duration=0.1),  # Maps to viseme A
            Phoneme(phoneme='F', start=0.15, duration=0.05),  # Maps to viseme F
        ]
        
        # Verify lip sync controller can map these phonemes
        for phoneme in phonemes:
            viseme = stream_coordinator.lip_sync_controller.map_phoneme_to_viseme(
                phoneme.phoneme
            )
            assert viseme in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'X'], \
                f"Should map {phoneme.phoneme} to valid viseme"
        
        # Render frames using the integrated pipeline
        frames = []
        async for frame_data in stream_coordinator.render_avatar(phonemes):
            frames.append(frame_data)
        
        # Verify frames were generated with lip sync
        assert len(frames) > 0, "Should generate frames with lip sync"
    
    @pytest.mark.asyncio
    async def test_avatar_renderer_integration(self, stream_coordinator):
        """
        Test that AvatarRenderer is properly integrated.
        
        Validates Requirements 2.2: Avatar displays animated face
        """
        # Verify renderer is initialized
        assert stream_coordinator.avatar_renderer.initialized, \
            "Avatar renderer should be initialized"
        
        # Verify renderer settings
        assert stream_coordinator.avatar_renderer.target_fps in [24, 30], \
            "Should have valid target FPS"
        assert stream_coordinator.avatar_renderer.rendering_mode in ['cpu', 'gpu'], \
            "Should have valid rendering mode"
        
        # Test rendering through coordinator
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=0.1)]
        
        frames = []
        async for frame_data in stream_coordinator.render_avatar(phonemes):
            frames.append(frame_data)
        
        # Verify frames have correct structure
        assert len(frames) > 0
        for frame in frames:
            assert frame.frame.dtype == np.uint8, "Frame should be uint8"
            assert frame.fps > 0, "Should report FPS"


class TestRequirementValidation:
    """Test specific requirement validations."""
    
    @pytest.mark.asyncio
    async def test_requirement_2_2_lip_sync_while_speaking(self, stream_coordinator):
        """
        Requirement 2.2: WHILE the Chatbot is speaking, THE Lip_Sync_Controller 
        SHALL synchronize mouth movements with speech audio.
        """
        # Simulate speaking with phoneme sequence
        phonemes = [
            Phoneme(phoneme='HH', start=0.0, duration=0.05),
            Phoneme(phoneme='EH', start=0.05, duration=0.08),
            Phoneme(phoneme='L', start=0.13, duration=0.05),
            Phoneme(phoneme='OW', start=0.18, duration=0.1),
        ]
        
        # Generate animation sequence using lip sync controller
        fps = stream_coordinator.avatar_renderer.target_fps or 30
        visemes = stream_coordinator.lip_sync_controller.generate_animation_sequence(
            phonemes, fps
        )
        
        # Verify visemes were generated for all phonemes
        assert len(visemes) > 0, "Should generate visemes for phonemes"
        
        # Verify timing is preserved
        for i, phoneme in enumerate(phonemes):
            # Find corresponding viseme(s)
            matching_visemes = [
                v for v in visemes 
                if abs(v.start - phoneme.start) < 0.01
            ]
            assert len(matching_visemes) > 0, \
                f"Should have viseme for phoneme at {phoneme.start}s"
    
    @pytest.mark.asyncio
    async def test_requirement_8_1_synchronize_mouth_with_audio(self, stream_coordinator):
        """
        Requirement 8.1: THE Lip_Sync_Controller SHALL synchronize avatar 
        mouth movements with Speech_Output_Generator audio.
        """
        # Create audio chunk with phonemes (simulating TTS output)
        audio_chunk = AudioChunk(
            audio_data=b'\x00' * 8820,  # 0.2s
            phonemes=[
                Phoneme(phoneme='W', start=0.0, duration=0.05),
                Phoneme(phoneme='ER', start=0.05, duration=0.08),
                Phoneme(phoneme='D', start=0.13, duration=0.05),
            ],
            timestamp=0.0,
            sample_rate=22050
        )
        
        # Process through coordinator
        frames = []
        async for frame_data in stream_coordinator.render_avatar(audio_chunk.phonemes):
            frames.append(frame_data)
        
        # Verify frames were generated synchronized with phonemes
        assert len(frames) > 0, "Should generate synchronized frames"
        
        # Verify frame timing aligns with phoneme timing
        total_duration = max(p.start + p.duration for p in audio_chunk.phonemes)
        expected_frames = int(total_duration * (stream_coordinator.avatar_renderer.target_fps or 30))
        
        # Allow some tolerance for frame count
        assert abs(len(frames) - expected_frames) < 5, \
            "Frame count should match expected duration"
    
    @pytest.mark.asyncio
    async def test_requirement_8_2_maintain_100ms_tolerance(self, stream_coordinator):
        """
        Requirement 8.2: THE Lip_Sync_Controller SHALL maintain synchronization 
        within 100ms tolerance.
        """
        # Test various sync scenarios
        test_cases = [
            (1.0, 1.05, True),   # 50ms - within tolerance
            (2.0, 2.09, True),   # 90ms - within tolerance
            (3.0, 3.10, True),   # 100ms - at tolerance boundary
            (4.0, 4.11, False),  # 110ms - exceeds tolerance
            (5.0, 5.15, False),  # 150ms - exceeds tolerance
        ]
        
        for audio_ts, video_ts, should_be_within in test_cases:
            stream_coordinator.synchronize(audio_ts, video_ts)
            metrics = stream_coordinator._calculate_sync_metrics()
            
            assert metrics.within_tolerance == should_be_within, \
                f"Drift of {metrics.drift_ms}ms should {'be within' if should_be_within else 'exceed'} 100ms tolerance"
            
            # Verify tolerance is exactly 100ms
            assert stream_coordinator.sync_tolerance_ms == 100.0, \
                "Sync tolerance should be 100ms"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
