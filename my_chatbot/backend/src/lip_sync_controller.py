"""
Lip Sync Controller Component

Synchronizes avatar mouth movements with speech audio using phoneme timing.
Maps speech phonemes to visual mouth shapes (visemes) for realistic lip sync.
"""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class Phoneme:
    """Represents a speech phoneme with timing information."""
    phoneme: str      # IPA phoneme symbol
    start: float      # Start time in seconds
    duration: float   # Duration in seconds


@dataclass
class Viseme:
    """Represents a visual mouth shape with timing information."""
    viseme: str       # Viseme identifier (A, B, C, D, E, F, G, H, X)
    start: float      # Start time in seconds
    duration: float   # Duration in seconds
    frame_number: int = 0  # Sequential frame index


class LipSyncController:
    """
    Controls lip synchronization by mapping phonemes to visemes.
    
    Standard viseme set:
    - A: Open vowels (ah, aa)
    - B: Lips closed (p, b, m)
    - C: Lips rounded (oo, ow)
    - D: Tongue/teeth (th, dh)
    - E: Lips spread (ee, eh)
    - F: Lower lip/upper teeth (f, v)
    - G: Tongue/palate (k, g, ng)
    - H: Tongue forward (l, n, t, d)
    - X: Rest/neutral position
    """
    
    def __init__(self):
        """Initialize the lip sync controller with phoneme-to-viseme mappings."""
        self._phoneme_to_viseme_map = self._create_phoneme_mapping()
    
    def _create_phoneme_mapping(self) -> Dict[str, str]:
        """
        Create comprehensive mapping from IPA phonemes to visemes.
        
        Returns:
            Dictionary mapping phoneme symbols to viseme identifiers
        """
        return {
            # Viseme A: Open vowels
            'AA': 'A',  # father
            'AH': 'A',  # but
            'AO': 'A',  # bought
            'AW': 'A',  # how
            'AY': 'A',  # my
            
            # Viseme B: Lips closed (bilabial)
            'P': 'B',   # pat
            'B': 'B',   # bat
            'M': 'B',   # mat
            
            # Viseme C: Lips rounded
            'UW': 'C',  # boot
            'UH': 'C',  # book
            'OW': 'C',  # boat
            'OY': 'C',  # boy
            
            # Viseme D: Tongue/teeth (dental)
            'TH': 'D',  # thin
            'DH': 'D',  # then
            
            # Viseme E: Lips spread (front vowels)
            'IY': 'E',  # beat
            'IH': 'E',  # bit
            'EY': 'E',  # bait
            'EH': 'E',  # bet
            'AE': 'E',  # bat
            
            # Viseme F: Lower lip/upper teeth (labiodental)
            'F': 'F',   # fat
            'V': 'F',   # vat
            
            # Viseme G: Tongue/palate (velar)
            'K': 'G',   # cat
            'G': 'G',   # gap
            'NG': 'G',  # sing
            
            # Viseme H: Tongue forward (alveolar)
            'L': 'H',   # lap
            'N': 'H',   # nap
            'T': 'H',   # tap
            'D': 'H',   # dap
            'S': 'H',   # sap
            'Z': 'H',   # zap
            'R': 'H',   # rap
            
            # Additional consonants
            'SH': 'C',  # ship (rounded)
            'ZH': 'C',  # measure (rounded)
            'CH': 'E',  # chip (spread)
            'JH': 'E',  # jump (spread)
            'W': 'C',   # wet (rounded)
            'Y': 'E',   # yet (spread)
            'HH': 'A',  # hat (open)
            
            # Viseme X: Rest/silence
            'SIL': 'X',  # silence
            'SP': 'X',   # short pause
            '': 'X',     # empty/unknown
        }
    
    def map_phoneme_to_viseme(self, phoneme: str) -> str:
        """
        Map a speech phoneme to its corresponding visual mouth shape (viseme).
        
        Args:
            phoneme: IPA phoneme symbol (e.g., 'AH', 'P', 'IY')
        
        Returns:
            Viseme identifier (A, B, C, D, E, F, G, H, or X)
            Returns 'X' (rest) for unknown phonemes
        """
        # Normalize phoneme to uppercase
        phoneme_upper = phoneme.upper().strip()
        
        # Look up in mapping, default to rest position for unknown phonemes
        return self._phoneme_to_viseme_map.get(phoneme_upper, 'X')
    
    def generate_animation_sequence(
        self, 
        phonemes: List[Phoneme], 
        fps: int = 30
    ) -> List[Viseme]:
        """
        Convert phoneme timeline to frame-by-frame viseme sequence.
        
        Handles pauses in speech by inserting neutral mouth positions (viseme X)
        during gaps between phonemes. Maintains 100ms synchronization tolerance.
        
        Args:
            phonemes: List of phonemes with timing information
            fps: Target frames per second for animation
        
        Returns:
            List of visemes with frame numbers for animation
        """
        if not phonemes:
            return []
        
        visemes = []
        frame_duration = 1.0 / fps  # Duration of one frame in seconds
        pause_threshold = 0.05  # 50ms - minimum gap to consider as a pause
        
        for i, phoneme in enumerate(phonemes):
            # Check for pause before this phoneme
            if i > 0:
                prev_phoneme = phonemes[i - 1]
                prev_end = prev_phoneme.start + prev_phoneme.duration
                gap = phoneme.start - prev_end
                
                # If there's a significant gap, insert neutral viseme for pause
                if gap > pause_threshold:
                    pause_viseme = Viseme(
                        viseme='X',  # Neutral/rest position
                        start=prev_end,
                        duration=gap,
                        frame_number=int(prev_end * fps)
                    )
                    visemes.append(pause_viseme)
            
            # Map phoneme to viseme
            viseme_id = self.map_phoneme_to_viseme(phoneme.phoneme)
            
            # Create viseme with timing
            viseme = Viseme(
                viseme=viseme_id,
                start=phoneme.start,
                duration=phoneme.duration,
                frame_number=int(phoneme.start * fps)
            )
            visemes.append(viseme)
        
        return visemes
    
    def interpolate_transitions(self, visemes: List[Viseme], fps: int = 30) -> List[Viseme]:
        """
        Smooth transitions between mouth shapes by adding interpolation frames.
        
        Adds intermediate visemes between rapid transitions to create more
        natural-looking mouth movements. Uses a simple blending approach where
        rapid transitions (< 100ms) get an intermediate frame.
        
        Args:
            visemes: List of visemes to interpolate
            fps: Target frames per second for animation
        
        Returns:
            List of visemes with smooth transitions
        """
        if len(visemes) <= 1:
            return visemes
        
        interpolated = []
        transition_threshold = 0.1  # 100ms - rapid transitions need interpolation
        
        for i in range(len(visemes)):
            current = visemes[i]
            interpolated.append(current)
            
            # Check if there's a next viseme and if transition is rapid
            if i < len(visemes) - 1:
                next_viseme = visemes[i + 1]
                current_end = current.start + current.duration
                transition_time = next_viseme.start - current_end
                
                # If visemes are different and transition is very rapid, add blend frame
                if (current.viseme != next_viseme.viseme and 
                    transition_time < transition_threshold and
                    transition_time >= 0):
                    
                    # Create intermediate viseme at the transition point
                    # Use the current viseme but with shorter duration
                    blend_start = current_end
                    blend_duration = min(transition_time, 1.0 / fps)
                    
                    if blend_duration > 0:
                        blend_viseme = Viseme(
                            viseme=current.viseme,  # Hold current shape briefly
                            start=blend_start,
                            duration=blend_duration,
                            frame_number=int(blend_start * fps)
                        )
                        interpolated.append(blend_viseme)
        
        return interpolated
