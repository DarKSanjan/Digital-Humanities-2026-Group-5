"""
Unit tests for Lip Sync Controller component.

Tests phoneme-to-viseme mapping, animation sequence generation,
and transition interpolation.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lip_sync_controller import LipSyncController, Phoneme, Viseme


class TestLipSyncController:
    """Test suite for LipSyncController class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.controller = LipSyncController()
    
    # Test phoneme-to-viseme mapping for each viseme category
    
    def test_map_open_vowels_to_viseme_a(self):
        """Test that open vowels map to viseme A."""
        open_vowels = ['AA', 'AH', 'AO', 'AW', 'AY', 'HH']
        for phoneme in open_vowels:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'A'
    
    def test_map_bilabial_consonants_to_viseme_b(self):
        """Test that bilabial consonants (lips closed) map to viseme B."""
        bilabials = ['P', 'B', 'M']
        for phoneme in bilabials:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'B'
    
    def test_map_rounded_vowels_to_viseme_c(self):
        """Test that rounded vowels map to viseme C."""
        rounded = ['UW', 'UH', 'OW', 'OY', 'SH', 'ZH', 'W']
        for phoneme in rounded:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'C'
    
    def test_map_dental_consonants_to_viseme_d(self):
        """Test that dental consonants (tongue/teeth) map to viseme D."""
        dentals = ['TH', 'DH']
        for phoneme in dentals:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'D'
    
    def test_map_front_vowels_to_viseme_e(self):
        """Test that front vowels (lips spread) map to viseme E."""
        front_vowels = ['IY', 'IH', 'EY', 'EH', 'AE', 'CH', 'JH', 'Y']
        for phoneme in front_vowels:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'E'
    
    def test_map_labiodental_consonants_to_viseme_f(self):
        """Test that labiodental consonants (lip/teeth) map to viseme F."""
        labiodentals = ['F', 'V']
        for phoneme in labiodentals:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'F'
    
    def test_map_velar_consonants_to_viseme_g(self):
        """Test that velar consonants (tongue/palate) map to viseme G."""
        velars = ['K', 'G', 'NG']
        for phoneme in velars:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'G'
    
    def test_map_alveolar_consonants_to_viseme_h(self):
        """Test that alveolar consonants (tongue forward) map to viseme H."""
        alveolars = ['L', 'N', 'T', 'D', 'S', 'Z', 'R']
        for phoneme in alveolars:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'H'
    
    def test_map_silence_to_viseme_x(self):
        """Test that silence/pauses map to viseme X (rest)."""
        silences = ['SIL', 'SP', '']
        for phoneme in silences:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'X'
    
    def test_map_unknown_phoneme_to_viseme_x(self):
        """Test that unknown phonemes default to viseme X (rest)."""
        unknown_phonemes = ['UNKNOWN', 'XYZ', '???']
        for phoneme in unknown_phonemes:
            assert self.controller.map_phoneme_to_viseme(phoneme) == 'X'
    
    def test_phoneme_mapping_case_insensitive(self):
        """Test that phoneme mapping is case-insensitive."""
        assert self.controller.map_phoneme_to_viseme('ah') == 'A'
        assert self.controller.map_phoneme_to_viseme('AH') == 'A'
        assert self.controller.map_phoneme_to_viseme('Ah') == 'A'
    
    def test_phoneme_mapping_handles_whitespace(self):
        """Test that phoneme mapping handles leading/trailing whitespace."""
        assert self.controller.map_phoneme_to_viseme(' AH ') == 'A'
        assert self.controller.map_phoneme_to_viseme('  P  ') == 'B'
    
    # Test animation sequence generation
    
    def test_generate_animation_sequence_empty_input(self):
        """Test that empty phoneme list returns empty viseme list."""
        result = self.controller.generate_animation_sequence([])
        assert result == []
    
    def test_generate_animation_sequence_single_phoneme(self):
        """Test animation sequence generation with single phoneme."""
        phonemes = [Phoneme(phoneme='AH', start=0.0, duration=0.2)]
        visemes = self.controller.generate_animation_sequence(phonemes, fps=30)
        
        assert len(visemes) == 1
        assert visemes[0].viseme == 'A'
        assert visemes[0].start == 0.0
        assert visemes[0].duration == 0.2
        assert visemes[0].frame_number == 0
    
    def test_generate_animation_sequence_multiple_phonemes(self):
        """Test animation sequence generation with multiple phonemes."""
        phonemes = [
            Phoneme(phoneme='P', start=0.0, duration=0.1),
            Phoneme(phoneme='AH', start=0.1, duration=0.2),
            Phoneme(phoneme='T', start=0.3, duration=0.1),
        ]
        visemes = self.controller.generate_animation_sequence(phonemes, fps=30)
        
        assert len(visemes) == 3
        assert visemes[0].viseme == 'B'  # P -> B
        assert visemes[1].viseme == 'A'  # AH -> A
        assert visemes[2].viseme == 'H'  # T -> H
    
    def test_generate_animation_sequence_frame_numbers(self):
        """Test that frame numbers are calculated correctly based on FPS."""
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='P', start=0.1, duration=0.1),   # No gap - consecutive
            Phoneme(phoneme='IY', start=0.2, duration=0.1),  # No gap - consecutive
        ]
        visemes = self.controller.generate_animation_sequence(phonemes, fps=30)
        
        assert visemes[0].frame_number == 0   # 0.0 * 30 = 0
        assert visemes[1].frame_number == 3   # 0.1 * 30 = 3
        assert visemes[2].frame_number == 6   # 0.2 * 30 = 6
    
    def test_generate_animation_sequence_different_fps(self):
        """Test animation sequence with different FPS values."""
        phonemes = [Phoneme(phoneme='AH', start=1.0, duration=0.1)]
        
        visemes_24fps = self.controller.generate_animation_sequence(phonemes, fps=24)
        visemes_30fps = self.controller.generate_animation_sequence(phonemes, fps=30)
        visemes_60fps = self.controller.generate_animation_sequence(phonemes, fps=60)
        
        assert visemes_24fps[0].frame_number == 24
        assert visemes_30fps[0].frame_number == 30
        assert visemes_60fps[0].frame_number == 60
    
    def test_generate_animation_sequence_preserves_timing(self):
        """Test that timing information is preserved in visemes."""
        phonemes = [
            Phoneme(phoneme='AH', start=0.5, duration=0.3),
            Phoneme(phoneme='P', start=0.8, duration=0.15),
        ]
        visemes = self.controller.generate_animation_sequence(phonemes)
        
        assert visemes[0].start == 0.5
        assert visemes[0].duration == 0.3
        assert visemes[1].start == 0.8
        assert visemes[1].duration == 0.15
    
    # Test interpolation
    
    def test_interpolate_transitions_empty_input(self):
        """Test interpolation with empty input."""
        result = self.controller.interpolate_transitions([])
        assert result == []
    
    def test_interpolate_transitions_single_viseme(self):
        """Test interpolation with single viseme."""
        visemes = [Viseme(viseme='A', start=0.0, duration=0.2)]
        result = self.controller.interpolate_transitions(visemes)
        assert len(result) == 1
        assert result[0].viseme == 'A'
    
    def test_interpolate_transitions_multiple_visemes(self):
        """Test interpolation with multiple visemes (currently pass-through)."""
        visemes = [
            Viseme(viseme='A', start=0.0, duration=0.1),
            Viseme(viseme='B', start=0.1, duration=0.1),
            Viseme(viseme='C', start=0.2, duration=0.1),
        ]
        result = self.controller.interpolate_transitions(visemes)
        
        # Current implementation returns as-is
        assert len(result) == 3
        assert result[0].viseme == 'A'
        assert result[1].viseme == 'B'
        assert result[2].viseme == 'C'
    
    # Integration tests
    
    def test_full_pipeline_simple_word(self):
        """Test full pipeline from phonemes to visemes for a simple word."""
        # Phonemes for "pat" [P AE T]
        phonemes = [
            Phoneme(phoneme='P', start=0.0, duration=0.1),
            Phoneme(phoneme='AE', start=0.1, duration=0.15),
            Phoneme(phoneme='T', start=0.25, duration=0.1),
        ]
        
        visemes = self.controller.generate_animation_sequence(phonemes, fps=30)
        interpolated = self.controller.interpolate_transitions(visemes)
        
        assert len(interpolated) == 3
        assert interpolated[0].viseme == 'B'  # P
        assert interpolated[1].viseme == 'E'  # AE
        assert interpolated[2].viseme == 'H'  # T
    
    def test_full_pipeline_with_silence(self):
        """Test full pipeline with silence/pauses."""
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.2),
            Phoneme(phoneme='SIL', start=0.2, duration=0.1),
            Phoneme(phoneme='P', start=0.3, duration=0.1),
        ]
        
        visemes = self.controller.generate_animation_sequence(phonemes, fps=30)
        
        assert visemes[0].viseme == 'A'  # AH
        assert visemes[1].viseme == 'X'  # SIL (rest)
        assert visemes[2].viseme == 'B'  # P
    
    # Test pause handling
    
    def test_generate_animation_sequence_inserts_pause_for_gap(self):
        """Test that gaps between phonemes insert neutral viseme X."""
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),  # ends at 0.1
            Phoneme(phoneme='P', start=0.3, duration=0.1),   # starts at 0.3, gap of 0.2s
        ]
        visemes = self.controller.generate_animation_sequence(phonemes, fps=30)
        
        # Should have: AH viseme, pause viseme, P viseme
        assert len(visemes) == 3
        assert visemes[0].viseme == 'A'  # AH
        assert visemes[1].viseme == 'X'  # Pause (neutral)
        assert visemes[1].start == 0.1   # Pause starts where AH ends
        assert abs(visemes[1].duration - 0.2) < 0.001  # Gap duration (with floating point tolerance)
        assert visemes[2].viseme == 'B'  # P
    
    def test_generate_animation_sequence_no_pause_for_small_gap(self):
        """Test that very small gaps (<50ms) don't insert pause."""
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),   # ends at 0.1
            Phoneme(phoneme='P', start=0.12, duration=0.1),   # starts at 0.12, gap of 0.02s (20ms)
        ]
        visemes = self.controller.generate_animation_sequence(phonemes, fps=30)
        
        # Should have only 2 visemes, no pause inserted
        assert len(visemes) == 2
        assert visemes[0].viseme == 'A'  # AH
        assert visemes[1].viseme == 'B'  # P
    
    def test_generate_animation_sequence_multiple_pauses(self):
        """Test handling of multiple pauses in sequence."""
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),   # ends at 0.1
            Phoneme(phoneme='P', start=0.25, duration=0.1),   # gap of 0.15s
            Phoneme(phoneme='IY', start=0.5, duration=0.1),   # gap of 0.15s
        ]
        visemes = self.controller.generate_animation_sequence(phonemes, fps=30)
        
        # Should have: AH, pause, P, pause, IY
        assert len(visemes) == 5
        assert visemes[0].viseme == 'A'  # AH
        assert visemes[1].viseme == 'X'  # Pause 1
        assert visemes[2].viseme == 'B'  # P
        assert visemes[3].viseme == 'X'  # Pause 2
        assert visemes[4].viseme == 'E'  # IY
    
    # Test interpolation enhancements
    
    def test_interpolate_transitions_adds_blend_for_rapid_change(self):
        """Test that rapid transitions between different visemes add blend frames."""
        visemes = [
            Viseme(viseme='A', start=0.0, duration=0.1, frame_number=0),
            Viseme(viseme='B', start=0.15, duration=0.1, frame_number=4),  # 50ms gap
        ]
        result = self.controller.interpolate_transitions(visemes, fps=30)
        
        # Should add a blend frame between A and B
        assert len(result) > len(visemes)
        assert result[0].viseme == 'A'
        # Blend frame should be inserted
        assert result[1].start == 0.1  # Starts where A ends
        assert result[2].viseme == 'B'
    
    def test_interpolate_transitions_no_blend_for_same_viseme(self):
        """Test that no blend is added when visemes are the same."""
        visemes = [
            Viseme(viseme='A', start=0.0, duration=0.1, frame_number=0),
            Viseme(viseme='A', start=0.15, duration=0.1, frame_number=4),
        ]
        result = self.controller.interpolate_transitions(visemes, fps=30)
        
        # Should not add blend for same viseme
        assert len(result) == len(visemes)
    
    def test_interpolate_transitions_no_blend_for_slow_transition(self):
        """Test that slow transitions (>100ms) don't add blend frames."""
        visemes = [
            Viseme(viseme='A', start=0.0, duration=0.1, frame_number=0),
            Viseme(viseme='B', start=0.25, duration=0.1, frame_number=7),  # 150ms gap
        ]
        result = self.controller.interpolate_transitions(visemes, fps=30)
        
        # Should not add blend for slow transition
        assert len(result) == len(visemes)
    
    def test_interpolate_transitions_handles_consecutive_visemes(self):
        """Test interpolation with consecutive visemes (no gap)."""
        visemes = [
            Viseme(viseme='A', start=0.0, duration=0.1, frame_number=0),
            Viseme(viseme='B', start=0.1, duration=0.1, frame_number=3),  # No gap
        ]
        result = self.controller.interpolate_transitions(visemes, fps=30)
        
        # Should handle consecutive visemes without errors
        assert len(result) >= len(visemes)
        assert result[0].viseme == 'A'

