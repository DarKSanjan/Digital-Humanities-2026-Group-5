#!/usr/bin/env python3
"""Quick test to verify emotion detection is working."""

import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from chatbot_app import ElevenLabsTTS

# Test emotion detection
tts = ElevenLabsTTS("dummy_key", "dummy_voice")

test_cases = [
    ("This is absolutely amazing! I'm so excited about this!", "happy/surprised"),
    ("Unfortunately, this is quite disappointing and sad.", "sad"),
    ("This is ridiculous and completely wrong!", "angry"),
    ("Wow! That's incredibly surprising and unbelievable!", "surprised"),
    ("Let me think about this carefully. Consider the implications.", "thoughtful"),
    ("Clearly, this is obviously the correct approach. Definitely.", "confident"),
    ("Hello, how are you today?", "neutral/thoughtful"),
]

print("=" * 60)
print("EMOTION DETECTION TEST")
print("=" * 60)
print()

for text, expected in test_cases:
    emotion = tts.detect_emotion(text)
    print(f"Text: {text[:50]}...")
    print(f"Expected: {expected}")
    print(f"Detected: {emotion}")
    print("-" * 60)
    print()

print("✅ Emotion detection test complete!")
print("Run the chatbot and watch the 'Emotion:' label to see it in action.")
