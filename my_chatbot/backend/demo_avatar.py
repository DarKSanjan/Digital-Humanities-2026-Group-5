#!/usr/bin/env python3
"""
Demo script to visualize the avatar rendering.
Creates a window showing the avatar animating through different phonemes.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def demo_avatar():
    """Demo the avatar rendering with a visual window."""
    print("=" * 60)
    print("Avatar Rendering Demo")
    print("=" * 60)
    
    # Initialize renderer
    print("\n1. Initializing avatar renderer...")
    from avatar_renderer import AvatarRenderer
    
    renderer = AvatarRenderer()
    result = renderer.initialize(use_gpu=True)
    
    if not result.success:
        print(f"❌ Failed to initialize: {result.error_message}")
        return
    
    print(f"✅ Initialized: {result.rendering_mode} mode, {result.target_fps} FPS target")
    
    # Try to import matplotlib for visualization
    try:
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        has_display = True
    except ImportError:
        print("⚠️  matplotlib not available for visualization")
        has_display = False
    
    if not has_display:
        print("\n2. Rendering frames (no display available)...")
        # Just render some frames without display
        phonemes = ['silence', 'A', 'E', 'O', 'B', 'F', 'silence']
        for phoneme in phonemes:
            frame, timestamp = renderer.render_frame(phoneme, intensity=1.0)
            print(f"   Rendered '{phoneme}': {frame.shape}")
        print("\n✅ Rendering works! Install matplotlib to see visual output.")
        return
    
    print("\n2. Creating animation window...")
    print("   Close the window to exit.")
    
    # Create figure with better settings for smooth animation
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor('white')
    ax.set_title("Avatar Animation Demo", fontsize=16, fontweight='bold')
    ax.axis('off')
    
    # Phoneme sequence to animate
    phoneme_sequence = [
        ('silence', 0.5),
        ('A', 0.3),      # "ah" sound
        ('E', 0.3),      # "ee" sound
        ('O', 0.3),      # "oh" sound
        ('silence', 0.2),
        ('B', 0.2),      # "b" sound
        ('A', 0.2),      # "ah"
        ('D', 0.2),      # "th"
        ('silence', 0.5),
        ('F', 0.2),      # "f" sound
        ('A', 0.2),      # "ah"
        ('silence', 0.2),
        ('E', 0.3),      # "ee"
        ('silence', 0.5),
    ]
    
    # Expand sequence based on duration
    expanded_sequence = []
    for phoneme, duration in phoneme_sequence:
        # Each frame is ~33ms at 30 FPS
        num_frames = max(1, int(duration * 30))
        expanded_sequence.extend([phoneme] * num_frames)
    
    print(f"   Animation: {len(expanded_sequence)} frames")
    print(f"   Pre-rendering all frames for smooth playback...")
    
    # Pre-render all frames to avoid lag during animation
    frame_cache = {}
    unique_phonemes = list(set(expanded_sequence))
    
    for i, phoneme in enumerate(unique_phonemes):
        frame, _ = renderer.render_frame(phoneme, intensity=1.0)
        frame_cache[phoneme] = frame
        print(f"   Cached {i+1}/{len(unique_phonemes)}: {phoneme}")
    
    print(f"   ✅ All frames cached!")
    
    # Initial frame
    frame = frame_cache[expanded_sequence[0]]
    im = ax.imshow(frame, interpolation='bilinear')
    
    # Text overlay for current phoneme
    text = ax.text(0.5, 0.95, '', transform=ax.transAxes,
                   ha='center', va='top', fontsize=14,
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                   color='white')
    
    frame_count = [0]
    
    def update_frame(frame_num):
        """Update animation frame."""
        phoneme = expanded_sequence[frame_num % len(expanded_sequence)]
        
        # Use cached frame (no rendering needed!)
        frame = frame_cache[phoneme]
        im.set_array(frame)
        
        # Update text
        text.set_text(f'Phoneme: {phoneme}')
        
        frame_count[0] += 1
        
        return [im, text]
    
    # Create animation with optimized settings
    # interval is in milliseconds (33ms = ~30 FPS)
    anim = animation.FuncAnimation(
        fig, update_frame,
        frames=len(expanded_sequence),
        interval=33,
        blit=True,
        repeat=True,
        cache_frame_data=False  # We're managing our own cache
    )
    
    print("\n✅ Animation window opened!")
    print("   Watch the avatar's mouth move with different phonemes.")
    print("   The animation will loop continuously.")
    print("   Close the window when done.\n")
    
    plt.tight_layout()
    plt.show()
    
    print("\n✅ Demo complete!")

if __name__ == "__main__":
    try:
        demo_avatar()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
