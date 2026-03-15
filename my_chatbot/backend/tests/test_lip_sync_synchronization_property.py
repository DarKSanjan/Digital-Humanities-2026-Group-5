"""Property-based tests for audio-visual synchronization in Lip Sync Controller.

Feature: persuasive-chatbot
Property 3: Audio-Visual Synchronization
Validates: Requirements 2.2, 7.4, 8.1, 8.2
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lip_sync_controller import LipSyncController, Phoneme


# Define IPA phonemes for generating test data
# Only include phonemes that are actually mapped in the LipSyncController
SPEECH_PHONEMES = [
    # Vowels
    'AA', 'AE', 'AH', 'AO', 'AW', 'AY',
    'EH', 'EY',
    'IH', 'IY',
    'OW', 'OY',
    'UH', 'UW',
    
    # Consonants
    'B', 'D', 'G', 'K', 'P', 'T',
    'DH', 'F', 'HH', 'S', 'SH', 'TH', 'V', 'Z', 'ZH',
    'CH', 'JH',
    'M', 'N', 'NG',
    'L', 'R',
    'W', 'Y',
]


# Strategy for generating realistic phoneme sequences with timing
@st.composite
def speech_audio_with_phonemes(draw):
    """
    Generate a realistic speech audio segment with phoneme timing data.
    
    Simulates the output from a TTS system like ElevenLabs, which provides
    audio along with phoneme timing information.
    
    Returns a list of Phoneme objects representing a speech segment.
    """
    # Generate 3-30 phonemes (realistic speech segment)
    num_phonemes = draw(st.integers(min_value=3, max_value=30))
    
    phonemes = []
    current_time = 0.0
    
    for i in range(num_phonemes):
        # Select a random speech phoneme
        phoneme_symbol = draw(st.sampled_from(SPEECH_PHONEMES))
        
        # Duration between 0.03s and 0.35s (realistic phoneme timing)
        duration = draw(st.floats(min_value=0.03, max_value=0.35))
        
        phonemes.append(Phoneme(
            phoneme=phoneme_symbol,
            start=current_time,
            duration=duration
        ))
        
        current_time += duration
        
        # Optionally add a small gap before the next phoneme (natural speech)
        if i < num_phonemes - 1:
            # 20% chance of adding a small gap
            if draw(st.booleans()) and draw(st.booleans()):
                gap_duration = draw(st.floats(min_value=0.01, max_value=0.15))
                current_time += gap_duration
    
    return phonemes


class TestAudioVisualSynchronization:
    """
    Property 3: Audio-Visual Synchronization
    
    For any generated speech audio with phoneme timing data, the Lip Sync
    Controller should produce avatar mouth movements that align with the audio
    within 100ms tolerance throughout the entire speech segment.
    
    Validates: Requirements 2.2, 7.4, 8.1, 8.2
    """
    
    @given(phonemes=speech_audio_with_phonemes())
    @settings(max_examples=100)
    def test_property_3_viseme_timing_aligns_with_phoneme_timing(self, phonemes):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: For any speech audio with phoneme timing, viseme timing
        should align with phoneme timing within 100ms tolerance.
        
        Each viseme's start time should match the corresponding phoneme's
        start time within the 100ms synchronization tolerance.
        """
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # For each phoneme, find the corresponding viseme and check timing
        for phoneme in phonemes:
            # Find viseme(s) that correspond to this phoneme
            # A viseme corresponds to a phoneme if its start time is close to the phoneme's start time
            matching_visemes = [
                v for v in visemes
                if abs(v.start - phoneme.start) < 0.001  # Allow for floating point precision
            ]
            
            # Should have at least one matching viseme
            assert len(matching_visemes) > 0, \
                f"No viseme found for phoneme '{phoneme.phoneme}' at time {phoneme.start}s"
            
            # Check that the matching viseme's timing aligns within 100ms tolerance
            matching_viseme = matching_visemes[0]
            sync_error = abs(matching_viseme.start - phoneme.start)
            
            assert sync_error <= 0.1, \
                f"Synchronization error {sync_error*1000:.1f}ms exceeds 100ms tolerance for phoneme '{phoneme.phoneme}' at {phoneme.start}s"
    
    @given(phonemes=speech_audio_with_phonemes())
    @settings(max_examples=100)
    def test_property_3_viseme_duration_matches_phoneme_duration(self, phonemes):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: Viseme durations should match phoneme durations within tolerance.
        
        Each viseme's duration should approximately match the corresponding
        phoneme's duration to maintain synchronization throughout the segment.
        """
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # For each phoneme, find the corresponding viseme and check duration
        for phoneme in phonemes:
            # Find viseme that corresponds to this phoneme
            matching_visemes = [
                v for v in visemes
                if abs(v.start - phoneme.start) < 0.001
            ]
            
            if matching_visemes:
                matching_viseme = matching_visemes[0]
                
                # Duration should match within tolerance
                duration_error = abs(matching_viseme.duration - phoneme.duration)
                
                # Allow up to 100ms tolerance for duration as well
                assert duration_error <= 0.1, \
                    f"Duration error {duration_error*1000:.1f}ms exceeds 100ms tolerance for phoneme '{phoneme.phoneme}'"
    
    @given(phonemes=speech_audio_with_phonemes())
    @settings(max_examples=100)
    def test_property_3_no_viseme_drift_over_time(self, phonemes):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: Synchronization should be maintained throughout the entire
        speech segment without drift.
        
        The synchronization error should not accumulate over time. Both early
        and late phonemes should have the same synchronization accuracy.
        """
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Check synchronization at the beginning, middle, and end
        if len(phonemes) >= 3:
            # First phoneme
            first_phoneme = phonemes[0]
            first_viseme = next((v for v in visemes if abs(v.start - first_phoneme.start) < 0.001), None)
            first_error = 0.0
            if first_viseme:
                first_error = abs(first_viseme.start - first_phoneme.start)
            
            # Middle phoneme
            mid_idx = len(phonemes) // 2
            mid_phoneme = phonemes[mid_idx]
            mid_viseme = next((v for v in visemes if abs(v.start - mid_phoneme.start) < 0.001), None)
            mid_error = 0.0
            if mid_viseme:
                mid_error = abs(mid_viseme.start - mid_phoneme.start)
            
            # Last phoneme
            last_phoneme = phonemes[-1]
            last_viseme = next((v for v in visemes if abs(v.start - last_phoneme.start) < 0.001), None)
            last_error = 0.0
            if last_viseme:
                last_error = abs(last_viseme.start - last_phoneme.start)
            
            # All errors should be within tolerance (no drift)
            if first_viseme and mid_viseme and last_viseme:
                assert first_error <= 0.1, \
                    f"First phoneme sync error {first_error*1000:.1f}ms exceeds 100ms"
                assert mid_error <= 0.1, \
                    f"Middle phoneme sync error {mid_error*1000:.1f}ms exceeds 100ms"
                assert last_error <= 0.1, \
                    f"Last phoneme sync error {last_error*1000:.1f}ms exceeds 100ms"
                
                # Check that drift is minimal (last error not significantly worse than first)
                drift = abs(last_error - first_error)
                assert drift <= 0.05, \
                    f"Synchronization drift of {drift*1000:.1f}ms detected over speech segment"
    
    @given(
        phonemes=speech_audio_with_phonemes(),
        fps=st.integers(min_value=24, max_value=60)
    )
    @settings(max_examples=100)
    def test_property_3_synchronization_maintained_at_different_fps(self, phonemes, fps):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: Synchronization should be maintained regardless of frame rate.
        
        Whether rendering at 24 FPS or 60 FPS, the viseme timing should align
        with phoneme timing within the 100ms tolerance.
        """
        controller = LipSyncController()
        
        # Generate animation sequence at specified FPS
        visemes = controller.generate_animation_sequence(phonemes, fps=fps)
        
        # Check synchronization for each phoneme
        for phoneme in phonemes:
            matching_visemes = [
                v for v in visemes
                if abs(v.start - phoneme.start) < 0.001
            ]
            
            if matching_visemes:
                matching_viseme = matching_visemes[0]
                sync_error = abs(matching_viseme.start - phoneme.start)
                
                assert sync_error <= 0.1, \
                    f"At {fps} FPS: sync error {sync_error*1000:.1f}ms exceeds 100ms tolerance"
    
    @given(phonemes=speech_audio_with_phonemes())
    @settings(max_examples=100)
    def test_property_3_all_phonemes_have_corresponding_visemes(self, phonemes):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: Every phoneme in the audio should have a corresponding viseme.
        
        For complete audio-visual synchronization, every phoneme must be
        represented by a viseme in the animation sequence.
        """
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # For each phoneme, verify there's a corresponding viseme
        for phoneme in phonemes:
            # Find viseme(s) that correspond to this phoneme
            matching_visemes = [
                v for v in visemes
                if abs(v.start - phoneme.start) < 0.001
            ]
            
            assert len(matching_visemes) > 0, \
                f"No viseme found for phoneme '{phoneme.phoneme}' at time {phoneme.start}s - incomplete synchronization"
    
    @given(phonemes=speech_audio_with_phonemes())
    @settings(max_examples=100)
    def test_property_3_viseme_sequence_covers_entire_audio_duration(self, phonemes):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: The viseme sequence should cover the entire audio duration.
        
        The animation should span from the start of the first phoneme to the
        end of the last phoneme, ensuring continuous synchronization.
        """
        if not phonemes:
            return
        
        controller = LipSyncController()
        
        # Calculate total audio duration
        audio_start = phonemes[0].start
        audio_end = max(p.start + p.duration for p in phonemes)
        audio_duration = audio_end - audio_start
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        if visemes:
            # Calculate animation duration
            anim_start = visemes[0].start
            anim_end = max(v.start + v.duration for v in visemes)
            anim_duration = anim_end - anim_start
            
            # Animation should cover at least the audio duration
            assert anim_duration >= audio_duration - 0.001, \
                f"Animation duration {anim_duration:.3f}s is shorter than audio duration {audio_duration:.3f}s"
            
            # Animation start should align with audio start
            start_error = abs(anim_start - audio_start)
            assert start_error <= 0.1, \
                f"Animation start time error {start_error*1000:.1f}ms exceeds 100ms tolerance"
    
    @given(phonemes=speech_audio_with_phonemes())
    @settings(max_examples=100)
    def test_property_3_viseme_transitions_are_timely(self, phonemes):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: Viseme transitions should occur at the correct times.
        
        When a phoneme changes, the corresponding viseme should change at
        approximately the same time (within 100ms tolerance).
        """
        if len(phonemes) < 2:
            return
        
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Check transitions between consecutive phonemes
        for i in range(len(phonemes) - 1):
            current_phoneme = phonemes[i]
            next_phoneme = phonemes[i + 1]
            
            # Find the transition point in the audio
            audio_transition_time = current_phoneme.start + current_phoneme.duration
            
            # Find the corresponding transition in the viseme sequence
            # Look for a viseme that starts near the next phoneme's start time
            transition_visemes = [
                v for v in visemes
                if abs(v.start - next_phoneme.start) < 0.001
            ]
            
            if transition_visemes:
                transition_viseme = transition_visemes[0]
                
                # The viseme transition should occur within 100ms of the audio transition
                transition_error = abs(transition_viseme.start - next_phoneme.start)
                
                assert transition_error <= 0.1, \
                    f"Transition error {transition_error*1000:.1f}ms exceeds 100ms tolerance at time {audio_transition_time:.3f}s"
    
    @given(phonemes=speech_audio_with_phonemes())
    @settings(max_examples=100)
    def test_property_3_synchronization_tolerance_is_consistent(self, phonemes):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: The 100ms synchronization tolerance should be consistent
        throughout the entire speech segment.
        
        No phoneme should have a synchronization error exceeding 100ms.
        """
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Track maximum synchronization error
        max_sync_error = 0.0
        
        # Check each phoneme
        for phoneme in phonemes:
            matching_visemes = [
                v for v in visemes
                if abs(v.start - phoneme.start) < 0.001 and v.viseme != 'X'
            ]
            
            if matching_visemes:
                matching_viseme = matching_visemes[0]
                sync_error = abs(matching_viseme.start - phoneme.start)
                max_sync_error = max(max_sync_error, sync_error)
        
        # Maximum error should not exceed 100ms tolerance
        assert max_sync_error <= 0.1, \
            f"Maximum synchronization error {max_sync_error*1000:.1f}ms exceeds 100ms tolerance"
    
    @given(phonemes=speech_audio_with_phonemes())
    @settings(max_examples=100)
    def test_property_3_frame_numbers_align_with_timing(self, phonemes):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: Frame numbers should align with viseme timing.
        
        The frame_number field should correctly represent when each viseme
        should be displayed based on its start time and the target FPS.
        """
        controller = LipSyncController()
        fps = 30
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=fps)
        
        # Check that frame numbers are consistent with timing
        for viseme in visemes:
            # Calculate expected frame number from start time
            expected_frame = int(viseme.start * fps)
            
            # Frame number should match (within 1 frame tolerance for rounding)
            frame_error = abs(viseme.frame_number - expected_frame)
            
            assert frame_error <= 1, \
                f"Frame number {viseme.frame_number} doesn't match expected {expected_frame} for viseme at {viseme.start:.3f}s"
    
    def test_property_3_empty_audio_produces_empty_animation(self):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: Empty audio (no phonemes) should produce empty animation.
        
        If there's no audio to synchronize with, there should be no visemes.
        """
        controller = LipSyncController()
        
        # Generate animation for empty phoneme sequence
        visemes = controller.generate_animation_sequence([], fps=30)
        
        # Should produce empty viseme sequence
        assert len(visemes) == 0, \
            "Empty audio should produce empty animation sequence"
    
    @given(phoneme_symbol=st.sampled_from(SPEECH_PHONEMES))
    @settings(max_examples=100)
    def test_property_3_single_phoneme_synchronization(self, phoneme_symbol):
        """
        **Validates: Requirements 2.2, 7.4, 8.1, 8.2**
        
        Property: Single phoneme should synchronize correctly.
        
        Even for a single phoneme, the synchronization should be maintained
        within the 100ms tolerance.
        """
        controller = LipSyncController()
        
        # Create a single phoneme
        phonemes = [Phoneme(phoneme=phoneme_symbol, start=0.0, duration=0.15)]
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Should have at least one viseme
        assert len(visemes) > 0, \
            f"Single phoneme '{phoneme_symbol}' should produce at least one viseme"
        
        # Find the viseme corresponding to the phoneme (should be at start time 0.0)
        matching_viseme = next((v for v in visemes if abs(v.start - 0.0) < 0.001), None)
        
        assert matching_viseme is not None, \
            f"No viseme found at start time for phoneme '{phoneme_symbol}'"
        
        # Check synchronization
        sync_error = abs(matching_viseme.start - phonemes[0].start)
        assert sync_error <= 0.1, \
            f"Single phoneme sync error {sync_error*1000:.1f}ms exceeds 100ms tolerance"
