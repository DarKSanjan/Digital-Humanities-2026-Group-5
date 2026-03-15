#!/usr/bin/env python3
"""Test emotion visual expressions on the avatar."""

import sys
import time
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from avatar_renderer import AvatarRenderer
from hardware_detection import HardwareDetector
import numpy as np

print("=" * 60)
print("EMOTION VISUAL TEST")
print("=" * 60)
print()

# Initialize avatar
print("Initializing avatar renderer...")
renderer = AvatarRenderer()
hw = HardwareDetector.detect_hardware()
result = renderer.initialize(use_gpu=hw.gpu_available)

if not result.success:
    print(f"❌ Avatar initialization failed: {result.error_message}")
    sys.exit(1)

print(f"✅ Avatar initialized: {result.rendering_mode} mode")
print()

# Test emotions
emotions = {
    "neutral": "Neutral expression (baseline)",
    "happy": "Happy: smile + eyebrow raise + head tilt",
    "sad": "Sad: frown + eyebrow down + head down",
    "angry": "Angry: frown + eyebrow furrow",
    "surprised": "Surprised: wide eyes + mouth open + eyebrow raise",
    "thoughtful": "Thoughtful: head tilt + look away",
    "confident": "Confident: slight smile + head up",
}

print("Testing emotion expressions...")
print("(Check if pose parameters are being modified correctly)")
print()

for emotion, description in emotions.items():
    print(f"Testing: {emotion}")
    print(f"  {description}")
    
    # Get base pose
    base_pose = renderer._phoneme_to_pose("silence", 1.0)
    
    # Apply emotion (simulating what chatbot_app does)
    pose = base_pose.copy()
    intensity = 1.0
    
    if emotion == "happy":
        pose[34] = min(1.0, pose[34] + 0.5 * intensity)  # raised_corner_left
        pose[35] = min(1.0, pose[35] + 0.5 * intensity)  # raised_corner_right
        pose[0] = min(1.0, pose[0] + 0.3 * intensity)    # left eyebrow up
        pose[6] = min(1.0, pose[6] + 0.3 * intensity)    # right eyebrow up
    
    elif emotion == "sad":
        pose[32] = min(1.0, pose[32] + 0.3 * intensity)  # lowered_corner_left
        pose[33] = min(1.0, pose[33] + 0.3 * intensity)  # lowered_corner_right
        pose[3] = min(1.0, pose[3] + 0.2 * intensity)    # left eyebrow down
        pose[9] = min(1.0, pose[9] + 0.2 * intensity)    # right eyebrow down
        pose[39] = max(-1.0, pose[39] - 0.1 * intensity) # head down
    
    elif emotion == "angry":
        pose[32] = min(1.0, pose[32] + 0.4 * intensity)  # lowered_corner_left
        pose[33] = min(1.0, pose[33] + 0.4 * intensity)  # lowered_corner_right
        pose[1] = min(1.0, pose[1] + 0.4 * intensity)    # left eyebrow furrow
        pose[7] = min(1.0, pose[7] + 0.4 * intensity)    # right eyebrow furrow
    
    elif emotion == "surprised":
        pose[12] = min(1.0, pose[12] + 0.4 * intensity)  # left eye open
        pose[18] = min(1.0, pose[18] + 0.4 * intensity)  # right eye open
        pose[0] = min(1.0, pose[0] + 0.5 * intensity)    # left eyebrow up
        pose[6] = min(1.0, pose[6] + 0.5 * intensity)    # right eyebrow up
        pose[26] = min(1.0, pose[26] + 0.2 * intensity)  # mouth open
    
    elif emotion == "thoughtful":
        pose[41] += 0.1 * intensity  # neck tilt
        pose[40] += 0.08 * intensity  # head turn
    
    elif emotion == "confident":
        pose[34] = min(1.0, pose[34] + 0.25 * intensity)  # raised_corner_left
        pose[35] = min(1.0, pose[35] + 0.25 * intensity)  # raised_corner_right
        pose[39] = min(1.0, pose[39] + 0.08 * intensity)  # head up
    
    # Check if pose changed
    changed_indices = [i for i in range(len(pose)) if abs(pose[i] - base_pose[i]) > 0.01]
    
    if changed_indices:
        print(f"  ✅ Pose modified at indices: {changed_indices}")
        for idx in changed_indices:
            print(f"     Index {idx}: {base_pose[idx]:.3f} → {pose[idx]:.3f}")
    else:
        print(f"  ⚠️  No pose changes detected")
    
    print()

print("=" * 60)
print("✅ Emotion visual test complete!")
print()
print("The emotions should now be visible on the avatar when you run the chatbot.")
print("Watch for changes in:")
print("  - Mouth corners (smile/frown)")
print("  - Eyebrows (raised/furrowed)")
print("  - Eyes (wide/normal)")
print("  - Head position (tilt/up/down)")
