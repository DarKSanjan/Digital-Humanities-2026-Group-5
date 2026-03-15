#!/usr/bin/env python3
"""
Smooth avatar animation demo with interpolation, blinking, and idle movements.
"""

import sys
import time
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def smooth_demo():
    """Demo with smooth interpolated animations."""
    print("=" * 60)
    print("Smooth Avatar Animation Demo")
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
    
    # Import visualization
    try:
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
    except ImportError:
        print("❌ matplotlib required. Install with: pip install matplotlib")
        return
    
    print("\n2. Creating smooth animation...")
    
    # Helper function to render smooth frames
    def render_smooth_frame(renderer, state, current_time):
        """Render a frame with smooth interpolation and animations."""
        import torch
        
        # Get base pose parameters for current and target phonemes
        current_pose = renderer._phoneme_to_pose(state['current_phoneme'], 1.0)
        target_pose = renderer._phoneme_to_pose(state['target_phoneme'], 1.0)
        
        # Interpolate between poses
        t = state['transition_progress']
        # Use ease-in-out for smoother transitions
        t_smooth = t * t * (3.0 - 2.0 * t)
        pose_params = [
            current_pose[i] * (1 - t_smooth) + target_pose[i] * t_smooth
            for i in range(len(current_pose))
        ]
        
        # Add blinking (modify eye parameters)
        if state['is_blinking']:
            # Blink animation: close -> open
            blink_progress = state['blink_duration'] / 0.15
            if blink_progress < 0.5:
                # Closing
                eye_close = blink_progress * 2.0
            else:
                # Opening
                eye_close = (1.0 - blink_progress) * 2.0
            
            # Eye parameters (indices 12-18 typically control eyes)
            if len(pose_params) > 15:
                pose_params[14] = -eye_close * 0.8  # Left eye close
                pose_params[15] = -eye_close * 0.8  # Right eye close
        
        # Add idle head rotation
        if len(pose_params) > 20:
            pose_params[21] += state['head_rotation']  # Yaw rotation
        
        # Render with modified parameters
        pose_tensor = torch.tensor([pose_params], dtype=renderer.model.get_dtype()).to(renderer.device)
        
        if renderer.character_image.dim() == 3:
            input_image = renderer.character_image.unsqueeze(0)
        else:
            input_image = renderer.character_image
        
        with torch.no_grad():
            output_image = renderer.model.pose(input_image, pose_tensor)
        
        # Convert to numpy
        output_np = output_image[0].cpu().numpy()
        output_np = np.transpose(output_np, (1, 2, 0))
        output_np = np.clip(output_np, 0.0, 1.0)
        
        # Alpha composite
        if output_np.shape[2] == 4:
            rgb = output_np[:, :, :3]
            alpha = output_np[:, :, 3:4]
            background = np.ones_like(rgb)
            composited = rgb * alpha + background * (1.0 - alpha)
            frame = (composited * 255).astype(np.uint8)
        else:
            frame = (output_np * 255).astype(np.uint8)
        
        return frame
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor('white')
    ax.set_title("Smooth Avatar Animation (30 FPS)", fontsize=16, fontweight='bold')
    ax.axis('off')
    
    # Animation state
    state = {
        'frame_num': 0,
        'blink_timer': 0,
        'blink_duration': 0,
        'is_blinking': False,
        'current_phoneme': 'silence',
        'target_phoneme': 'silence',
        'transition_progress': 1.0,
        'head_rotation': 0.0,
        'idle_timer': 0.0,
    }
    
    # Speech sequence with timing
    speech_sequence = [
        (0, 2.0, 'silence'),    # 0-2s: silence
        (2.0, 2.3, 'A'),        # "ah"
        (2.3, 2.6, 'E'),        # "ee"
        (2.6, 2.9, 'O'),        # "oh"
        (2.9, 3.2, 'silence'),  # pause
        (3.2, 3.4, 'B'),        # "b"
        (3.4, 3.6, 'A'),        # "ah"
        (3.6, 3.8, 'D'),        # "th"
        (3.8, 4.3, 'silence'),  # pause
        (4.3, 4.5, 'F'),        # "f"
        (4.5, 4.7, 'A'),        # "ah"
        (4.7, 4.9, 'silence'),  # pause
        (4.9, 5.2, 'E'),        # "ee"
        (5.2, 7.0, 'silence'),  # end silence
    ]
    
    # Initial frame
    import torch
    frame_data = render_smooth_frame(renderer, state, 0.0)
    im = ax.imshow(frame_data, interpolation='bilinear')
    
    # Info text
    info_text = ax.text(0.5, 0.98, '', transform=ax.transAxes,
                       ha='center', va='top', fontsize=12,
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                       color='white')
    
    fps_text = ax.text(0.02, 0.02, '', transform=ax.transAxes,
                      ha='left', va='bottom', fontsize=10,
                      bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                      color='lime')
    
    frame_times = []
    
    def update_frame(frame_num):
        """Update animation frame with smooth interpolation."""
        start_time = time.time()
        
        # Calculate time in seconds (30 FPS)
        current_time = frame_num / 30.0
        
        # Update phoneme based on speech sequence
        for start, end, phoneme in speech_sequence:
            if start <= current_time < end:
                if state['target_phoneme'] != phoneme:
                    state['current_phoneme'] = state['target_phoneme']
                    state['target_phoneme'] = phoneme
                    state['transition_progress'] = 0.0
                break
        
        # Smooth transition between phonemes
        if state['transition_progress'] < 1.0:
            state['transition_progress'] = min(1.0, state['transition_progress'] + 0.15)
        
        # Blinking logic (blink every 3-5 seconds)
        state['blink_timer'] += 1/30.0
        if not state['is_blinking'] and state['blink_timer'] > np.random.uniform(3, 5):
            state['is_blinking'] = True
            state['blink_duration'] = 0
            state['blink_timer'] = 0
        
        if state['is_blinking']:
            state['blink_duration'] += 1/30.0
            if state['blink_duration'] > 0.15:  # Blink lasts 150ms
                state['is_blinking'] = False
        
        # Idle head movement (subtle sway)
        state['idle_timer'] += 1/30.0
        state['head_rotation'] = np.sin(state['idle_timer'] * 0.5) * 0.05
        
        # Render frame with all animations
        frame_data = render_smooth_frame(renderer, state, current_time)
        im.set_array(frame_data)
        
        # Update info
        phoneme_display = state['target_phoneme']
        if state['transition_progress'] < 1.0:
            phoneme_display = f"{state['current_phoneme']}→{state['target_phoneme']}"
        
        blink_status = "👁️ BLINK" if state['is_blinking'] else ""
        info_text.set_text(f'Phoneme: {phoneme_display}  {blink_status}')
        
        # FPS calculation
        frame_time = time.time() - start_time
        frame_times.append(frame_time)
        if len(frame_times) > 30:
            frame_times.pop(0)
        avg_fps = 1.0 / (sum(frame_times) / len(frame_times)) if frame_times else 0
        fps_text.set_text(f'FPS: {avg_fps:.1f}')
        
        state['frame_num'] += 1
        
        return [im, info_text, fps_text]
    
    # Create animation at 30 FPS
    total_frames = int(7.0 * 30)  # 7 seconds at 30 FPS
    
    print(f"   Total frames: {total_frames}")
    print(f"   Duration: 7 seconds")
    print(f"   Features: Smooth interpolation, blinking, idle movement")
    
    anim = animation.FuncAnimation(
        fig, update_frame,
        frames=total_frames,
        interval=33,  # 33ms = ~30 FPS
        blit=True,
        repeat=True,
        cache_frame_data=False
    )
    
    print("\n✅ Animation window opened!")
    print("   Watch for:")
    print("   - Smooth mouth transitions between phonemes")
    print("   - Automatic eye blinking every 3-5 seconds")
    print("   - Subtle idle head movement")
    print("   - Real-time FPS counter")
    print("\n   Close the window when done.\n")
    
    plt.tight_layout()
    plt.show()
    
    print("\n✅ Demo complete!")

if __name__ == "__main__":
    try:
        smooth_demo()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
