#!/usr/bin/env python3
"""
Save sample avatar frames as images to see what the character looks like.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def save_samples():
    """Save sample avatar frames."""
    print("=" * 60)
    print("Saving Avatar Sample Images")
    print("=" * 60)
    
    # Initialize renderer
    print("\n1. Initializing avatar renderer...")
    from avatar_renderer import AvatarRenderer
    
    renderer = AvatarRenderer()
    result = renderer.initialize(use_gpu=True)
    
    if not result.success:
        print(f"❌ Failed to initialize: {result.error_message}")
        return
    
    print(f"✅ Initialized: {result.rendering_mode} mode")
    
    # Import PIL for saving images
    try:
        from PIL import Image
    except ImportError:
        print("❌ PIL not available. Install with: pip install Pillow")
        return
    
    # Create output directory
    output_dir = Path(__file__).parent / "avatar_samples"
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n2. Rendering and saving sample frames to: {output_dir}")
    
    # Different phonemes to demonstrate
    samples = [
        ('silence', 'Neutral/Silent'),
        ('A', 'Open mouth (ah)'),
        ('E', 'Smile (ee)'),
        ('O', 'Round mouth (oh)'),
        ('B', 'Closed lips (b/p/m)'),
        ('F', 'Lip bite (f/v)'),
        ('D', 'Teeth together (th)'),
        ('G', 'Open wide (g/k)'),
    ]
    
    for phoneme, description in samples:
        # Render frame
        frame, _ = renderer.render_frame(phoneme, intensity=1.0)
        
        # Convert to PIL Image
        img = Image.fromarray(frame)
        
        # Save
        filename = output_dir / f"avatar_{phoneme.lower()}.png"
        img.save(filename)
        
        print(f"   ✅ Saved: {filename.name} - {description}")
    
    print(f"\n✅ All samples saved to: {output_dir}")
    print(f"\nYou can now open these images to see what the avatar looks like!")
    print(f"The character is: crypko_00.png (anime-style character)")

if __name__ == "__main__":
    try:
        save_samples()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
