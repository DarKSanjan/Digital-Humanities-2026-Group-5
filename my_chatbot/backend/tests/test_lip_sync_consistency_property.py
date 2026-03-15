"""Property-based tests for lip sync round-trip consistency.

Feature: persuasive-chatbot
Property 20: Lip Sync Round-Trip Consistency
Validates: Requirements 8.5
"""

import pytest
from hypothesis import given, strategies as st, settings
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lip_sync_controller import LipSyncController, Phoneme


# Define IPA phonemes for generating test data
SPEECH_PHONEMES = [
    # Vowels
    'AA', 'AE', 'AH', 'AO', 'AW', 'AY',
    'EH', 'ER', 'EY',
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
    
    # Silence/Pauses
    'SIL', 'SP',
]


# Strategy for generating realistic phoneme sequences
@st.composite
def phoneme_sequence(draw):
    """
    Generate a realistic sequence of phonemes with timing information.
    
    Returns a list of Phoneme objects representing speech audio.
    """
    # Generate 1-20 phonemes
    num_phonemes = draw(st.integers(min_value=1, max_value=20))
    
    phonemes = []
    current_time = 0.0
    
    for i in range(num_phonemes):
        # Select a random phoneme
        phoneme_symbol = draw(st.sampled_from(SPEECH_PHONEMES))
        
        # Duration between 0.03s and 0.4s (realistic speech timing)
        duration = draw(st.floats(min_value=0.03, max_value=0.4))
        
        phonemes.append(Phoneme(
            phoneme=phoneme_symbol,
            start=current_time,
            duration=duration
        ))
        
        current_time += duration
        
        # Optionally add a gap before the next phoneme
        if i < num_phonemes - 1:
            # 30% chance of adding a gap
            add_gap = draw(st.booleans())
            if add_gap:
                gap_duration = draw(st.floats(min_value=0.01, max_value=0.3))
                current_time += gap_duration
    
    return phonemes


class TestLipSyncConsistencyProperty:
    """
    Property 20: Lip Sync Round-Trip Consistency
    
    For any generated speech audio with phoneme data, rendering the animation
    sequence multiple times should produce consistent lip movements (same audio
    input → same animation output).
    
    Validates: Requirements 8.5
    """
    
    @given(phonemes=phoneme_sequence())
    @settings(max_examples=100)
    def test_property_20_same_input_produces_same_output(self, phonemes):
        """
        **Validates: Requirements 8.5**
        
        Property: Rendering the same phoneme sequence multiple times should
        produce identical animation sequences.
        
        The lip sync controller should be deterministic - given the same input,
        it should always produce the same output.
        """
        controller = LipSyncController()
        
        # Render the same phoneme sequence multiple times
        visemes1 = controller.generate_animation_sequence(phonemes, fps=30)
        visemes2 = controller.generate_animation_sequence(phonemes, fps=30)
        visemes3 = controller.generate_animation_sequence(phonemes, fps=30)
        
        # All three outputs should be identical
        assert len(visemes1) == len(visemes2) == len(visemes3), \
            f"Inconsistent output lengths: {len(visemes1)}, {len(visemes2)}, {len(visemes3)}"
        
        # Compare each viseme in the sequences
        for i, (v1, v2, v3) in enumerate(zip(visemes1, visemes2, visemes3)):
            assert v1.viseme == v2.viseme == v3.viseme, \
                f"Viseme {i}: inconsistent viseme types: {v1.viseme}, {v2.viseme}, {v3.viseme}"
            
            assert abs(v1.start - v2.start) < 0.0001, \
                f"Viseme {i}: inconsistent start times: {v1.start}, {v2.start}"
            assert abs(v1.start - v3.start) < 0.0001, \
                f"Viseme {i}: inconsistent start times: {v1.start}, {v3.start}"
            
            assert abs(v1.duration - v2.duration) < 0.0001, \
                f"Viseme {i}: inconsistent durations: {v1.duration}, {v2.duration}"
            assert abs(v1.duration - v3.duration) < 0.0001, \
                f"Viseme {i}: inconsistent durations: {v1.duration}, {v3.duration}"
            
            assert v1.frame_number == v2.frame_number == v3.frame_number, \
                f"Viseme {i}: inconsistent frame numbers: {v1.frame_number}, {v2.frame_number}, {v3.frame_number}"
    
    @given(
        phonemes=phoneme_sequence(),
        fps=st.integers(min_value=24, max_value=60)
    )
    @settings(max_examples=100)
    def test_property_20_consistency_at_different_fps(self, phonemes, fps):
        """
        **Validates: Requirements 8.5**
        
        Property: Rendering at the same FPS should produce consistent results.
        
        For a given FPS, multiple renderings should produce identical output,
        regardless of the frame rate used.
        """
        controller = LipSyncController()
        
        # Render multiple times at the same FPS
        visemes1 = controller.generate_animation_sequence(phonemes, fps=fps)
        visemes2 = controller.generate_animation_sequence(phonemes, fps=fps)
        
        # Outputs should be identical
        assert len(visemes1) == len(visemes2), \
            f"Inconsistent output lengths at {fps} FPS: {len(visemes1)}, {len(visemes2)}"
        
        for i, (v1, v2) in enumerate(zip(visemes1, visemes2)):
            assert v1.viseme == v2.viseme, \
                f"Viseme {i} at {fps} FPS: inconsistent types: {v1.viseme}, {v2.viseme}"
            assert abs(v1.start - v2.start) < 0.0001, \
                f"Viseme {i} at {fps} FPS: inconsistent start: {v1.start}, {v2.start}"
            assert abs(v1.duration - v2.duration) < 0.0001, \
                f"Viseme {i} at {fps} FPS: inconsistent duration: {v1.duration}, {v2.duration}"
    
    @given(phonemes=phoneme_sequence())
    @settings(max_examples=100)
    def test_property_20_consistency_across_controller_instances(self, phonemes):
        """
        **Validates: Requirements 8.5**
        
        Property: Different controller instances should produce identical output.
        
        Creating multiple LipSyncController instances and rendering the same
        input should produce consistent results across all instances.
        """
        # Create multiple controller instances
        controller1 = LipSyncController()
        controller2 = LipSyncController()
        controller3 = LipSyncController()
        
        # Render with each controller
        visemes1 = controller1.generate_animation_sequence(phonemes, fps=30)
        visemes2 = controller2.generate_animation_sequence(phonemes, fps=30)
        visemes3 = controller3.generate_animation_sequence(phonemes, fps=30)
        
        # All outputs should be identical
        assert len(visemes1) == len(visemes2) == len(visemes3), \
            f"Inconsistent output lengths across instances: {len(visemes1)}, {len(visemes2)}, {len(visemes3)}"
        
        for i, (v1, v2, v3) in enumerate(zip(visemes1, visemes2, visemes3)):
            assert v1.viseme == v2.viseme == v3.viseme, \
                f"Viseme {i}: inconsistent across instances: {v1.viseme}, {v2.viseme}, {v3.viseme}"
            assert abs(v1.start - v2.start) < 0.0001 and abs(v1.start - v3.start) < 0.0001, \
                f"Viseme {i}: inconsistent start times across instances"
            assert abs(v1.duration - v2.duration) < 0.0001 and abs(v1.duration - v3.duration) < 0.0001, \
                f"Viseme {i}: inconsistent durations across instances"
    
    @given(phonemes=phoneme_sequence())
    @settings(max_examples=100)
    def test_property_20_phoneme_mapping_consistency(self, phonemes):
        """
        **Validates: Requirements 8.5**
        
        Property: Phoneme-to-viseme mapping should be consistent.
        
        The same phoneme should always map to the same viseme, regardless of
        when or how many times it's mapped.
        """
        controller = LipSyncController()
        
        # Build a mapping of phoneme -> viseme by directly testing the mapping function
        phoneme_to_viseme = {}
        for phoneme in phonemes:
            viseme = controller.map_phoneme_to_viseme(phoneme.phoneme)
            if phoneme.phoneme not in phoneme_to_viseme:
                phoneme_to_viseme[phoneme.phoneme] = viseme
            else:
                # Verify consistency within the same controller
                assert phoneme_to_viseme[phoneme.phoneme] == viseme, \
                    f"Phoneme '{phoneme.phoneme}' mapped inconsistently: {phoneme_to_viseme[phoneme.phoneme]} vs {viseme}"
        
        # Map again and verify the mapping is consistent
        for phoneme in phonemes:
            viseme = controller.map_phoneme_to_viseme(phoneme.phoneme)
            expected_viseme = phoneme_to_viseme[phoneme.phoneme]
            assert viseme == expected_viseme, \
                f"Phoneme '{phoneme.phoneme}' mapped to '{viseme}' but expected '{expected_viseme}'"
    
    @given(
        phonemes=phoneme_sequence(),
        num_iterations=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=100)
    def test_property_20_consistency_over_multiple_iterations(self, phonemes, num_iterations):
        """
        **Validates: Requirements 8.5**
        
        Property: Consistency should hold over many iterations.
        
        Rendering the same input many times (2-10 iterations) should always
        produce identical output.
        """
        controller = LipSyncController()
        
        # Render multiple times
        all_visemes = []
        for _ in range(num_iterations):
            visemes = controller.generate_animation_sequence(phonemes, fps=30)
            all_visemes.append(visemes)
        
        # All outputs should be identical to the first one
        first_visemes = all_visemes[0]
        
        for iteration, visemes in enumerate(all_visemes[1:], start=2):
            assert len(visemes) == len(first_visemes), \
                f"Iteration {iteration}: inconsistent length {len(visemes)} vs {len(first_visemes)}"
            
            for i, (v1, v2) in enumerate(zip(first_visemes, visemes)):
                assert v1.viseme == v2.viseme, \
                    f"Iteration {iteration}, viseme {i}: inconsistent type"
                assert abs(v1.start - v2.start) < 0.0001, \
                    f"Iteration {iteration}, viseme {i}: inconsistent start"
                assert abs(v1.duration - v2.duration) < 0.0001, \
                    f"Iteration {iteration}, viseme {i}: inconsistent duration"
    
    @given(phonemes=phoneme_sequence())
    @settings(max_examples=100)
    def test_property_20_interpolation_consistency(self, phonemes):
        """
        **Validates: Requirements 8.5**
        
        Property: Interpolation should produce consistent results.
        
        Applying interpolation to the same viseme sequence multiple times
        should produce identical output.
        """
        controller = LipSyncController()
        
        # Generate base animation sequence
        base_visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Apply interpolation multiple times
        interpolated1 = controller.interpolate_transitions(base_visemes, fps=30)
        interpolated2 = controller.interpolate_transitions(base_visemes, fps=30)
        interpolated3 = controller.interpolate_transitions(base_visemes, fps=30)
        
        # All interpolated outputs should be identical
        assert len(interpolated1) == len(interpolated2) == len(interpolated3), \
            f"Inconsistent interpolation lengths: {len(interpolated1)}, {len(interpolated2)}, {len(interpolated3)}"
        
        for i, (v1, v2, v3) in enumerate(zip(interpolated1, interpolated2, interpolated3)):
            assert v1.viseme == v2.viseme == v3.viseme, \
                f"Interpolated viseme {i}: inconsistent types"
            assert abs(v1.start - v2.start) < 0.0001 and abs(v1.start - v3.start) < 0.0001, \
                f"Interpolated viseme {i}: inconsistent start times"
            assert abs(v1.duration - v2.duration) < 0.0001 and abs(v1.duration - v3.duration) < 0.0001, \
                f"Interpolated viseme {i}: inconsistent durations"
    
    @given(phonemes=phoneme_sequence())
    @settings(max_examples=100)
    def test_property_20_full_pipeline_consistency(self, phonemes):
        """
        **Validates: Requirements 8.5**
        
        Property: Full pipeline (generation + interpolation) should be consistent.
        
        Running the complete lip sync pipeline (generate + interpolate) multiple
        times should produce identical results.
        """
        controller = LipSyncController()
        
        # Run full pipeline multiple times
        def full_pipeline():
            visemes = controller.generate_animation_sequence(phonemes, fps=30)
            return controller.interpolate_transitions(visemes, fps=30)
        
        result1 = full_pipeline()
        result2 = full_pipeline()
        result3 = full_pipeline()
        
        # All results should be identical
        assert len(result1) == len(result2) == len(result3), \
            f"Inconsistent pipeline output lengths: {len(result1)}, {len(result2)}, {len(result3)}"
        
        for i, (v1, v2, v3) in enumerate(zip(result1, result2, result3)):
            assert v1.viseme == v2.viseme == v3.viseme, \
                f"Pipeline viseme {i}: inconsistent types: {v1.viseme}, {v2.viseme}, {v3.viseme}"
            assert abs(v1.start - v2.start) < 0.0001 and abs(v1.start - v3.start) < 0.0001, \
                f"Pipeline viseme {i}: inconsistent start times"
            assert abs(v1.duration - v2.duration) < 0.0001 and abs(v1.duration - v3.duration) < 0.0001, \
                f"Pipeline viseme {i}: inconsistent durations"
            assert v1.frame_number == v2.frame_number == v3.frame_number, \
                f"Pipeline viseme {i}: inconsistent frame numbers"
    
    @given(
        phonemes=phoneme_sequence(),
        fps1=st.integers(min_value=24, max_value=60),
        fps2=st.integers(min_value=24, max_value=60)
    )
    @settings(max_examples=100)
    def test_property_20_fps_independence(self, phonemes, fps1, fps2):
        """
        **Validates: Requirements 8.5**
        
        Property: Viseme types and timing should be independent of FPS.
        
        While frame numbers will differ, the viseme types, start times, and
        durations should be consistent regardless of the target FPS.
        """
        controller = LipSyncController()
        
        # Render at two different frame rates
        visemes1 = controller.generate_animation_sequence(phonemes, fps=fps1)
        visemes2 = controller.generate_animation_sequence(phonemes, fps=fps2)
        
        # Should have the same number of visemes
        assert len(visemes1) == len(visemes2), \
            f"Different viseme counts at {fps1} FPS ({len(visemes1)}) vs {fps2} FPS ({len(visemes2)})"
        
        # Viseme types, start times, and durations should match
        for i, (v1, v2) in enumerate(zip(visemes1, visemes2)):
            assert v1.viseme == v2.viseme, \
                f"Viseme {i}: different types at different FPS: {v1.viseme} vs {v2.viseme}"
            assert abs(v1.start - v2.start) < 0.0001, \
                f"Viseme {i}: different start times at different FPS: {v1.start} vs {v2.start}"
            assert abs(v1.duration - v2.duration) < 0.0001, \
                f"Viseme {i}: different durations at different FPS: {v1.duration} vs {v2.duration}"
    
    def test_property_20_empty_input_consistency(self):
        """
        **Validates: Requirements 8.5**
        
        Property: Empty input should consistently produce empty output.
        
        Rendering an empty phoneme sequence should always return an empty
        viseme sequence.
        """
        controller = LipSyncController()
        
        # Render empty sequence multiple times
        visemes1 = controller.generate_animation_sequence([], fps=30)
        visemes2 = controller.generate_animation_sequence([], fps=30)
        visemes3 = controller.generate_animation_sequence([], fps=30)
        
        # All should be empty
        assert len(visemes1) == 0, "Empty input should produce empty output"
        assert len(visemes2) == 0, "Empty input should produce empty output"
        assert len(visemes3) == 0, "Empty input should produce empty output"
    
    @given(phoneme_symbol=st.sampled_from(SPEECH_PHONEMES))
    @settings(max_examples=100)
    def test_property_20_single_phoneme_consistency(self, phoneme_symbol):
        """
        **Validates: Requirements 8.5**
        
        Property: Single phoneme should produce consistent output.
        
        Rendering a single phoneme multiple times should always produce
        identical output.
        """
        controller = LipSyncController()
        
        # Create a single phoneme
        phonemes = [Phoneme(phoneme=phoneme_symbol, start=0.0, duration=0.1)]
        
        # Render multiple times
        visemes1 = controller.generate_animation_sequence(phonemes, fps=30)
        visemes2 = controller.generate_animation_sequence(phonemes, fps=30)
        visemes3 = controller.generate_animation_sequence(phonemes, fps=30)
        
        # All should be identical
        assert len(visemes1) == len(visemes2) == len(visemes3), \
            "Single phoneme should produce consistent output length"
        
        if len(visemes1) > 0:
            v1, v2, v3 = visemes1[0], visemes2[0], visemes3[0]
            assert v1.viseme == v2.viseme == v3.viseme, \
                f"Single phoneme '{phoneme_symbol}' produced inconsistent visemes"
            assert abs(v1.start - v2.start) < 0.0001 and abs(v1.start - v3.start) < 0.0001, \
                "Single phoneme produced inconsistent start times"
            assert abs(v1.duration - v2.duration) < 0.0001 and abs(v1.duration - v3.duration) < 0.0001, \
                "Single phoneme produced inconsistent durations"
