"""Property-based tests for pause handling in Lip Sync Controller.

Feature: persuasive-chatbot
Property 19: Pause Handling in Lip Sync
Validates: Requirements 8.4
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lip_sync_controller import LipSyncController, Phoneme


# Define IPA phonemes (excluding silence markers for speech phonemes)
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
]


# Strategy for generating phoneme sequences with pauses
@st.composite
def phoneme_sequence_with_pauses(draw):
    """
    Generate a sequence of phonemes with intentional pauses (gaps) between them.
    
    Returns a tuple of (phonemes, pause_indices) where pause_indices indicates
    which gaps should have pauses.
    """
    # Generate 2-10 phonemes
    num_phonemes = draw(st.integers(min_value=2, max_value=10))
    
    phonemes = []
    current_time = 0.0
    pause_indices = []  # Track which gaps have pauses
    
    for i in range(num_phonemes):
        # Select a random speech phoneme
        phoneme_symbol = draw(st.sampled_from(SPEECH_PHONEMES))
        
        # Duration between 0.05s and 0.3s
        duration = draw(st.floats(min_value=0.05, max_value=0.3))
        
        phonemes.append(Phoneme(
            phoneme=phoneme_symbol,
            start=current_time,
            duration=duration
        ))
        
        current_time += duration
        
        # Add a pause (gap) before the next phoneme (except after the last one)
        if i < num_phonemes - 1:
            # 50% chance of adding a significant pause
            add_pause = draw(st.booleans())
            
            if add_pause:
                # Pause duration between 0.06s and 0.5s (above the 50ms threshold)
                pause_duration = draw(st.floats(min_value=0.06, max_value=0.5))
                current_time += pause_duration
                pause_indices.append(i)  # Mark that there's a pause after phoneme i
    
    return phonemes, pause_indices


@st.composite
def phoneme_sequence_with_guaranteed_pause(draw):
    """
    Generate a sequence of phonemes with at least one guaranteed pause.
    """
    phonemes, pause_indices = draw(phoneme_sequence_with_pauses())
    
    # Ensure at least one pause exists
    assume(len(pause_indices) > 0)
    
    return phonemes, pause_indices


class TestPauseHandlingProperty:
    """
    Property 19: Pause Handling in Lip Sync
    
    For any speech audio segment containing pauses (silence periods), the
    Lip Sync Controller should render closed or neutral mouth positions
    during those pauses.
    
    Validates: Requirements 8.4
    """
    
    @given(data=phoneme_sequence_with_guaranteed_pause())
    @settings(max_examples=100)
    def test_property_19_pauses_insert_neutral_viseme(self, data):
        """
        **Validates: Requirements 8.4**
        
        Property: For any speech segment with pauses, neutral viseme X should
        be inserted during pause periods.
        
        When there are gaps between phonemes (silence periods), the lip sync
        controller should insert viseme X (rest/neutral position) to represent
        closed or neutral mouth positions.
        """
        phonemes, pause_indices = data
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Verify that neutral visemes are inserted for pauses
        # We should have more visemes than phonemes if pauses were inserted
        assert len(visemes) > len(phonemes), \
            f"Expected pause visemes to be inserted, but got {len(visemes)} visemes for {len(phonemes)} phonemes"
        
        # Check that viseme X appears in the sequence (neutral/rest position)
        viseme_types = [v.viseme for v in visemes]
        assert 'X' in viseme_types, \
            "Expected neutral viseme 'X' for pauses, but none found"
    
    @given(data=phoneme_sequence_with_guaranteed_pause())
    @settings(max_examples=100)
    def test_property_19_pause_visemes_fill_gaps(self, data):
        """
        **Validates: Requirements 8.4**
        
        Property: Pause visemes should fill the time gaps between phonemes.
        
        When a pause is inserted, it should start when the previous phoneme
        ends and end when the next phoneme starts, filling the gap completely.
        """
        phonemes, pause_indices = data
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Find pause visemes (viseme X that are between speech visemes)
        for i in range(len(visemes) - 1):
            current_viseme = visemes[i]
            next_viseme = visemes[i + 1]
            
            # If current viseme is X and surrounded by non-X visemes, it's a pause
            if current_viseme.viseme == 'X':
                # Check if this pause fills a gap
                current_end = current_viseme.start + current_viseme.duration
                
                # The pause should end approximately when the next viseme starts
                # (allowing for small floating point differences)
                if i + 1 < len(visemes):
                    gap = abs(next_viseme.start - current_end)
                    assert gap < 0.001, \
                        f"Pause viseme doesn't fill gap properly: gap of {gap}s between pause end and next viseme"
    
    @given(data=phoneme_sequence_with_guaranteed_pause())
    @settings(max_examples=100)
    def test_property_19_pause_timing_matches_gap(self, data):
        """
        **Validates: Requirements 8.4**
        
        Property: Pause duration should match the gap duration between phonemes.
        
        The duration of the inserted pause viseme should equal the time gap
        between consecutive phonemes.
        """
        phonemes, pause_indices = data
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # For each pause in the original phoneme sequence, verify the pause viseme
        for pause_idx in pause_indices:
            # Calculate the expected gap
            prev_phoneme = phonemes[pause_idx]
            next_phoneme = phonemes[pause_idx + 1]
            
            prev_end = prev_phoneme.start + prev_phoneme.duration
            expected_gap = next_phoneme.start - prev_end
            
            # Find the corresponding pause viseme in the output
            # It should be between the two phonemes
            found_pause = False
            for viseme in visemes:
                if viseme.viseme == 'X' and abs(viseme.start - prev_end) < 0.001:
                    # This is the pause we're looking for
                    found_pause = True
                    
                    # Verify the duration matches the gap
                    assert abs(viseme.duration - expected_gap) < 0.001, \
                        f"Pause duration {viseme.duration} doesn't match gap {expected_gap}"
                    break
            
            assert found_pause, \
                f"Expected pause viseme after phoneme {pause_idx}, but none found"
    
    @given(
        phonemes=st.lists(
            st.builds(
                Phoneme,
                phoneme=st.sampled_from(SPEECH_PHONEMES),
                start=st.floats(min_value=0.0, max_value=5.0),
                duration=st.floats(min_value=0.05, max_value=0.3)
            ),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_property_19_no_pause_for_consecutive_phonemes(self, phonemes):
        """
        **Validates: Requirements 8.4**
        
        Property: No pause should be inserted for consecutive phonemes without gaps.
        
        When phonemes are consecutive (no gap or gap < 50ms), no pause viseme
        should be inserted between them.
        """
        # Sort phonemes by start time
        phonemes = sorted(phonemes, key=lambda p: p.start)
        
        # Make phonemes consecutive (no gaps)
        consecutive_phonemes = []
        current_time = 0.0
        for p in phonemes:
            consecutive_phonemes.append(Phoneme(
                phoneme=p.phoneme,
                start=current_time,
                duration=p.duration
            ))
            current_time += p.duration
        
        controller = LipSyncController()
        visemes = controller.generate_animation_sequence(consecutive_phonemes, fps=30)
        
        # Should have exactly the same number of visemes as phonemes (no pauses)
        assert len(visemes) == len(consecutive_phonemes), \
            f"Expected no pause insertion for consecutive phonemes, but got {len(visemes)} visemes for {len(consecutive_phonemes)} phonemes"
    
    @given(data=phoneme_sequence_with_guaranteed_pause())
    @settings(max_examples=100)
    def test_property_19_pause_viseme_is_neutral(self, data):
        """
        **Validates: Requirements 8.4**
        
        Property: Pause visemes should always be neutral (viseme X).
        
        All visemes inserted for pauses should be viseme X, representing
        closed or neutral mouth position.
        """
        phonemes, pause_indices = data
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Identify which visemes are pauses (inserted between phonemes)
        # A pause viseme is one that doesn't correspond to an original phoneme
        phoneme_starts = {p.start for p in phonemes}
        
        for viseme in visemes:
            # If this viseme's start time doesn't match any phoneme start time,
            # it's likely a pause viseme
            is_pause = not any(abs(viseme.start - ps) < 0.001 for ps in phoneme_starts)
            
            if is_pause:
                # Pause visemes should be neutral (X)
                assert viseme.viseme == 'X', \
                    f"Pause viseme should be 'X' but got '{viseme.viseme}'"
    
    @given(
        num_phonemes=st.integers(min_value=2, max_value=5),
        pause_duration=st.floats(min_value=0.06, max_value=1.0)
    )
    @settings(max_examples=100)
    def test_property_19_multiple_pauses_handled_correctly(self, num_phonemes, pause_duration):
        """
        **Validates: Requirements 8.4**
        
        Property: Multiple pauses in a sequence should all be handled correctly.
        
        When a speech segment contains multiple pauses, each pause should be
        represented with a neutral viseme X.
        """
        # Create phonemes with pauses between each pair
        phonemes = []
        current_time = 0.0
        
        for i in range(num_phonemes):
            phonemes.append(Phoneme(
                phoneme=SPEECH_PHONEMES[i % len(SPEECH_PHONEMES)],
                start=current_time,
                duration=0.1
            ))
            current_time += 0.1
            
            # Add pause after each phoneme except the last
            if i < num_phonemes - 1:
                current_time += pause_duration
        
        controller = LipSyncController()
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Should have phonemes + pauses
        expected_count = num_phonemes + (num_phonemes - 1)  # phonemes + pauses between them
        assert len(visemes) == expected_count, \
            f"Expected {expected_count} visemes (with pauses), but got {len(visemes)}"
        
        # Count neutral visemes
        neutral_count = sum(1 for v in visemes if v.viseme == 'X')
        expected_pauses = num_phonemes - 1
        assert neutral_count == expected_pauses, \
            f"Expected {expected_pauses} pause visemes, but got {neutral_count}"
    
    @given(
        gap_duration=st.floats(min_value=0.001, max_value=0.049)
    )
    @settings(max_examples=100)
    def test_property_19_small_gaps_below_threshold_ignored(self, gap_duration):
        """
        **Validates: Requirements 8.4**
        
        Property: Very small gaps below threshold should not insert pauses.
        
        Gaps smaller than 50ms should not be treated as pauses, as they
        represent natural speech timing rather than silence periods.
        """
        # Create two phonemes with a small gap
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='P', start=0.1 + gap_duration, duration=0.1)
        ]
        
        controller = LipSyncController()
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Should have exactly 2 visemes (no pause inserted)
        assert len(visemes) == 2, \
            f"Small gap of {gap_duration}s should not insert pause, but got {len(visemes)} visemes"
    
    @given(data=phoneme_sequence_with_guaranteed_pause())
    @settings(max_examples=100)
    def test_property_19_pause_preserves_phoneme_timing(self, data):
        """
        **Validates: Requirements 8.4**
        
        Property: Inserting pauses should not alter original phoneme timing.
        
        The start times and durations of phoneme-based visemes should match
        the original phonemes, even when pauses are inserted between them.
        """
        phonemes, pause_indices = data
        controller = LipSyncController()
        
        # Generate animation sequence
        visemes = controller.generate_animation_sequence(phonemes, fps=30)
        
        # Match visemes to phonemes by start time (phoneme-based visemes should
        # have start times matching the original phonemes)
        phoneme_starts = {p.start for p in phonemes}
        
        # Find visemes that correspond to phonemes (not pauses)
        phoneme_visemes = []
        for viseme in visemes:
            # Check if this viseme's start time matches a phoneme start time
            if any(abs(viseme.start - ps) < 0.001 for ps in phoneme_starts):
                phoneme_visemes.append(viseme)
        
        # Should have the same number of phoneme-based visemes as phonemes
        assert len(phoneme_visemes) == len(phonemes), \
            f"Expected {len(phonemes)} phoneme-based visemes, but got {len(phoneme_visemes)}"
        
        # Verify timing matches for each phoneme
        for phoneme in phonemes:
            # Find the corresponding viseme
            matching_viseme = None
            for viseme in phoneme_visemes:
                if abs(viseme.start - phoneme.start) < 0.001:
                    matching_viseme = viseme
                    break
            
            assert matching_viseme is not None, \
                f"No viseme found for phoneme at start time {phoneme.start}"
            
            # Verify timing is preserved
            assert abs(matching_viseme.start - phoneme.start) < 0.001, \
                f"Phoneme timing altered: expected start {phoneme.start}, got {matching_viseme.start}"
            assert abs(matching_viseme.duration - phoneme.duration) < 0.001, \
                f"Phoneme duration altered: expected {phoneme.duration}, got {matching_viseme.duration}"
    
    @given(
        fps=st.integers(min_value=24, max_value=60)
    )
    @settings(max_examples=100)
    def test_property_19_pause_handling_works_at_different_fps(self, fps):
        """
        **Validates: Requirements 8.4**
        
        Property: Pause handling should work correctly at different frame rates.
        
        The pause insertion logic should be independent of the target FPS,
        working correctly whether rendering at 24, 30, or 60 FPS.
        """
        # Create phonemes with a pause
        phonemes = [
            Phoneme(phoneme='AH', start=0.0, duration=0.1),
            Phoneme(phoneme='P', start=0.3, duration=0.1),  # 0.2s gap
        ]
        
        controller = LipSyncController()
        visemes = controller.generate_animation_sequence(phonemes, fps=fps)
        
        # Should have 3 visemes regardless of FPS: AH, pause, P
        assert len(visemes) == 3, \
            f"Expected 3 visemes at {fps} FPS, but got {len(visemes)}"
        
        # Middle viseme should be the pause
        assert visemes[1].viseme == 'X', \
            f"Expected pause viseme at {fps} FPS, but got '{visemes[1].viseme}'"
        
        # Pause duration should be 0.2s regardless of FPS
        assert abs(visemes[1].duration - 0.2) < 0.001, \
            f"Pause duration should be 0.2s at {fps} FPS, but got {visemes[1].duration}"
