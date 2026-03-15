#!/usr/bin/env python3
"""Test smooth emotion transitions and sentence-by-sentence detection."""

import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from chatbot_app import ElevenLabsTTS

print("=" * 70)
print("SMOOTH EMOTION TRANSITIONS TEST")
print("=" * 70)
print()

# Test emotion detection
tts = ElevenLabsTTS("dummy_key", "dummy_voice")

# Test multi-sentence text with different emotions
test_text = """
I'm absolutely thrilled about this development! It's truly amazing. 
However, unfortunately there are some concerning issues we need to address. 
Let me think about this carefully and consider all the options. 
Clearly, the solution is obvious once we examine the facts.
"""

print("Testing sentence-by-sentence emotion detection:")
print("-" * 70)
print(f"Text: {test_text.strip()}")
print("-" * 70)
print()

emotions_timeline = tts.detect_emotions_per_sentence(test_text)

print("Emotions Timeline:")
print()
for i, emotion_data in enumerate(emotions_timeline, 1):
    print(f"Sentence {i}:")
    print(f"  Text: {emotion_data['text']}")
    print(f"  Emotion: {emotion_data['emotion']}")
    print(f"  Duration: {emotion_data['duration']:.2f}s")
    print(f"  Position: chars {emotion_data['start_char']}-{emotion_data['end_char']}")
    print()

print("=" * 70)
print("✅ Smooth emotion test complete!")
print()
print("Expected behavior in chatbot:")
print("  1. Emotions change smoothly between sentences")
print("  2. Fade in: neutral → emotion (0.8 units/sec)")
print("  3. Hold: emotion stays for sentence duration")
print("  4. Fade out: emotion → neutral (0.8 units/sec)")
print("  5. No jerky transitions!")
print()
print("Idle animations:")
print("  - Random blinking (2.5-5.0 second intervals)")
print("  - Looking around (3-8 second intervals)")
print("  - Subtle breathing animation")
print("  - Gentle head sway")
