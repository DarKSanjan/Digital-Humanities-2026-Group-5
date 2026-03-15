"""Property-based tests for phoneme-to-viseme mapping in Lip Sync Controller.

Feature: persuasive-chatbot
Property 18: Phoneme-to-Viseme Mapping
Validates: Requirements 8.3
"""

import pytest
from hypothesis import given, strategies as st, settings
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lip_sync_controller import LipSyncController


# Define the standard viseme set
VALID_VISEMES = {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'X'}

# Define the IPA phoneme set that ElevenLabs and similar TTS systems use
IPA_PHONEMES = [
    # Vowels
    'AA', 'AE', 'AH', 'AO', 'AW', 'AY',
    'EH', 'ER', 'EY',
    'IH', 'IY',
    'OW', 'OY',
    'UH', 'UW',
    
    # Consonants - Stops
    'B', 'D', 'G', 'K', 'P', 'T',
    
    # Consonants - Fricatives
    'DH', 'F', 'HH', 'S', 'SH', 'TH', 'V', 'Z', 'ZH',
    
    # Consonants - Affricates
    'CH', 'JH',
    
    # Consonants - Nasals
    'M', 'N', 'NG',
    
    # Consonants - Liquids
    'L', 'R',
    
    # Consonants - Glides
    'W', 'Y',
    
    # Silence/Pauses
    'SIL', 'SP', ''
]


class TestPhonemeToVisemeMapping:
    """
    Property 18: Phoneme-to-Viseme Mapping
    
    For any speech phoneme from the IPA phoneme set, the Lip Sync Controller
    should map it to an appropriate viseme (mouth shape) from the standard
    viseme set.
    
    Validates: Requirements 8.3
    """
    
    @given(phoneme=st.sampled_from(IPA_PHONEMES))
    @settings(max_examples=100)
    def test_property_18_all_ipa_phonemes_map_to_valid_visemes(self, phoneme):
        """
        **Validates: Requirements 8.3**
        
        Property: For any IPA phoneme, the mapping should return a valid viseme.
        
        Every phoneme from the IPA phoneme set should map to one of the
        standard visemes (A, B, C, D, E, F, G, H, X).
        """
        controller = LipSyncController()
        
        # Map the phoneme to a viseme
        viseme = controller.map_phoneme_to_viseme(phoneme)
        
        # Verify the result is a valid viseme
        assert viseme in VALID_VISEMES, \
            f"Phoneme '{phoneme}' mapped to invalid viseme '{viseme}'"
    
    @given(
        phoneme=st.sampled_from(IPA_PHONEMES),
        case_variant=st.sampled_from(['upper', 'lower', 'mixed'])
    )
    @settings(max_examples=100)
    def test_property_18_mapping_is_case_insensitive(self, phoneme, case_variant):
        """
        **Validates: Requirements 8.3**
        
        Property: Phoneme-to-viseme mapping should be case-insensitive.
        
        The same phoneme in different cases (upper, lower, mixed) should
        map to the same viseme.
        """
        controller = LipSyncController()
        
        # Create case variants
        if case_variant == 'upper':
            test_phoneme = phoneme.upper()
        elif case_variant == 'lower':
            test_phoneme = phoneme.lower()
        else:  # mixed
            test_phoneme = ''.join(
                c.upper() if i % 2 == 0 else c.lower()
                for i, c in enumerate(phoneme)
            )
        
        # Map both original and variant
        original_viseme = controller.map_phoneme_to_viseme(phoneme)
        variant_viseme = controller.map_phoneme_to_viseme(test_phoneme)
        
        # Should map to the same viseme
        assert original_viseme == variant_viseme, \
            f"Phoneme '{phoneme}' and '{test_phoneme}' mapped to different visemes"
    
    @given(
        phoneme=st.sampled_from(IPA_PHONEMES),
        whitespace=st.sampled_from(['', ' ', '  ', '\t', ' \t '])
    )
    @settings(max_examples=100)
    def test_property_18_mapping_handles_whitespace(self, phoneme, whitespace):
        """
        **Validates: Requirements 8.3**
        
        Property: Phoneme-to-viseme mapping should handle whitespace correctly.
        
        Phonemes with leading/trailing whitespace should map to the same
        viseme as the trimmed phoneme.
        """
        controller = LipSyncController()
        
        # Create phoneme with whitespace
        phoneme_with_whitespace = f"{whitespace}{phoneme}{whitespace}"
        
        # Map both versions
        clean_viseme = controller.map_phoneme_to_viseme(phoneme)
        whitespace_viseme = controller.map_phoneme_to_viseme(phoneme_with_whitespace)
        
        # Should map to the same viseme
        assert clean_viseme == whitespace_viseme, \
            f"Phoneme '{phoneme}' with whitespace mapped differently"
    
    @given(phoneme=st.sampled_from(IPA_PHONEMES))
    @settings(max_examples=100)
    def test_property_18_mapping_is_deterministic(self, phoneme):
        """
        **Validates: Requirements 8.3**
        
        Property: Phoneme-to-viseme mapping should be deterministic.
        
        Mapping the same phoneme multiple times should always return the
        same viseme.
        """
        controller = LipSyncController()
        
        # Map the same phoneme multiple times
        viseme1 = controller.map_phoneme_to_viseme(phoneme)
        viseme2 = controller.map_phoneme_to_viseme(phoneme)
        viseme3 = controller.map_phoneme_to_viseme(phoneme)
        
        # All results should be identical
        assert viseme1 == viseme2 == viseme3, \
            f"Phoneme '{phoneme}' mapped inconsistently: {viseme1}, {viseme2}, {viseme3}"
    
    @given(unknown_phoneme=st.text(
        alphabet=st.characters(
            blacklist_categories=('Cs',),
            blacklist_characters=' \t\n\r'
        ),
        min_size=1,
        max_size=10
    ).filter(lambda x: x.upper() not in [p.upper() for p in IPA_PHONEMES]))
    @settings(max_examples=100)
    def test_property_18_unknown_phonemes_default_to_rest(self, unknown_phoneme):
        """
        **Validates: Requirements 8.3**
        
        Property: Unknown phonemes should map to rest position (viseme X).
        
        Any phoneme not in the IPA phoneme set should default to the rest
        position (viseme X) for graceful degradation.
        """
        controller = LipSyncController()
        
        # Map unknown phoneme
        viseme = controller.map_phoneme_to_viseme(unknown_phoneme)
        
        # Should default to rest position
        assert viseme == 'X', \
            f"Unknown phoneme '{unknown_phoneme}' should map to 'X' but got '{viseme}'"
    
    @given(phoneme=st.sampled_from([p for p in IPA_PHONEMES if p in ['SIL', 'SP', '']]))
    @settings(max_examples=100)
    def test_property_18_silence_phonemes_map_to_rest(self, phoneme):
        """
        **Validates: Requirements 8.3**
        
        Property: Silence and pause phonemes should map to rest position.
        
        Phonemes representing silence or pauses (SIL, SP, empty string)
        should map to viseme X (rest/neutral position).
        """
        controller = LipSyncController()
        
        # Map silence phoneme
        viseme = controller.map_phoneme_to_viseme(phoneme)
        
        # Should map to rest position
        assert viseme == 'X', \
            f"Silence phoneme '{phoneme}' should map to 'X' but got '{viseme}'"
    
    @given(phoneme=st.sampled_from(IPA_PHONEMES))
    @settings(max_examples=100)
    def test_property_18_mapping_returns_single_character(self, phoneme):
        """
        **Validates: Requirements 8.3**
        
        Property: Viseme identifiers should be single characters.
        
        All viseme identifiers in the standard set are single uppercase
        letters (A-H, X).
        """
        controller = LipSyncController()
        
        # Map phoneme
        viseme = controller.map_phoneme_to_viseme(phoneme)
        
        # Verify it's a single character
        assert len(viseme) == 1, \
            f"Viseme '{viseme}' for phoneme '{phoneme}' is not a single character"
        
        # Verify it's uppercase
        assert viseme.isupper(), \
            f"Viseme '{viseme}' for phoneme '{phoneme}' is not uppercase"
    
    def test_property_18_bilabial_phonemes_map_to_lips_closed(self):
        """
        **Validates: Requirements 8.3**
        
        Property: Bilabial phonemes should map to lips-closed viseme.
        
        Phonemes produced with both lips (P, B, M) should map to viseme B
        (lips closed).
        """
        controller = LipSyncController()
        bilabial_phonemes = ['P', 'B', 'M']
        
        for phoneme in bilabial_phonemes:
            viseme = controller.map_phoneme_to_viseme(phoneme)
            assert viseme == 'B', \
                f"Bilabial phoneme '{phoneme}' should map to 'B' but got '{viseme}'"
    
    def test_property_18_labiodental_phonemes_map_to_lip_teeth(self):
        """
        **Validates: Requirements 8.3**
        
        Property: Labiodental phonemes should map to lip-teeth viseme.
        
        Phonemes produced with lower lip and upper teeth (F, V) should map
        to viseme F.
        """
        controller = LipSyncController()
        labiodental_phonemes = ['F', 'V']
        
        for phoneme in labiodental_phonemes:
            viseme = controller.map_phoneme_to_viseme(phoneme)
            assert viseme == 'F', \
                f"Labiodental phoneme '{phoneme}' should map to 'F' but got '{viseme}'"
    
    def test_property_18_dental_phonemes_map_to_tongue_teeth(self):
        """
        **Validates: Requirements 8.3**
        
        Property: Dental phonemes should map to tongue-teeth viseme.
        
        Phonemes produced with tongue and teeth (TH, DH) should map to
        viseme D.
        """
        controller = LipSyncController()
        dental_phonemes = ['TH', 'DH']
        
        for phoneme in dental_phonemes:
            viseme = controller.map_phoneme_to_viseme(phoneme)
            assert viseme == 'D', \
                f"Dental phoneme '{phoneme}' should map to 'D' but got '{viseme}'"
    
    @given(phoneme=st.sampled_from(IPA_PHONEMES))
    @settings(max_examples=100)
    def test_property_18_mapping_never_returns_none(self, phoneme):
        """
        **Validates: Requirements 8.3**
        
        Property: Mapping should never return None or empty string.
        
        Every phoneme should map to a valid viseme identifier, never None
        or an empty string.
        """
        controller = LipSyncController()
        
        # Map phoneme
        viseme = controller.map_phoneme_to_viseme(phoneme)
        
        # Should not be None or empty
        assert viseme is not None, \
            f"Phoneme '{phoneme}' mapped to None"
        assert viseme != '', \
            f"Phoneme '{phoneme}' mapped to empty string"
        assert isinstance(viseme, str), \
            f"Phoneme '{phoneme}' mapped to non-string: {type(viseme)}"
