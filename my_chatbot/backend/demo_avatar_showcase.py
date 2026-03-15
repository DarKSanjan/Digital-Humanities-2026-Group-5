#!/usr/bin/env python3
"""
Avatar showcase demo - cycles through various expressions, movements, and emotions.
"""

import sys
import time
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def showcase_demo():
    """Showcase all avatar capabilities with expressions and movements."""
    print("=" * 60)
    print("Avatar Expression & Movement Showcase")
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
    
    print("\n2. Creating expression showcase...")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor('#1a1a1a')
    ax.set_title("Avatar Expression Showcase", fontsize=18, fontweight='bold', color='white')
    ax.axis('off')
    
    # Define showcase sequence with expressions and movements
    showcase_sequence = [
        # (start_time, duration, expression_name, params_dict)
        (0, 2.0, "Neutral Idle", {
            'mouth': 'silence', 'smile': 0.0, 'eyebrow': 0.0, 
            'head_pitch': 0.0, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': 0.0
        }),
        
        (2.0, 2.5, "Happy Smile", {
            'mouth': 'E', 'smile': 0.8, 'eyebrow': 0.3,
            'head_pitch': 0.0, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': 0.0
        }),
        
        (2.5, 3.0, "Big Smile + Head Tilt", {
            'mouth': 'E', 'smile': 1.0, 'eyebrow': 0.5,
            'head_pitch': 0.0, 'head_yaw': 0.0, 'head_roll': 0.15,
            'eye_wink': 0.0, 'iris_x': 0.1, 'iris_y': -0.1
        }),
        
        (3.0, 3.5, "Surprised", {
            'mouth': 'O', 'smile': 0.0, 'eyebrow': 0.8,
            'head_pitch': -0.1, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': -0.2
        }),
        
        (3.5, 4.0, "Thinking", {
            'mouth': 'silence', 'smile': -0.2, 'eyebrow': -0.3,
            'head_pitch': 0.1, 'head_yaw': 0.15, 'head_roll': 0.05,
            'eye_wink': 0.0, 'iris_x': 0.3, 'iris_y': 0.1
        }),
        
        (4.0, 4.5, "Skeptical", {
            'mouth': 'silence', 'smile': -0.3, 'eyebrow': -0.5,
            'head_pitch': 0.05, 'head_yaw': -0.1, 'head_roll': -0.08,
            'eye_wink': 0.0, 'iris_x': -0.2, 'iris_y': 0.0
        }),
        
        (4.5, 5.0, "Wink Left", {
            'mouth': 'E', 'smile': 0.6, 'eyebrow': 0.2,
            'head_pitch': 0.0, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 1.0, 'iris_x': 0.0, 'iris_y': 0.0
        }),
        
        (5.0, 5.5, "Speaking (Ah)", {
            'mouth': 'A', 'smile': 0.2, 'eyebrow': 0.1,
            'head_pitch': 0.0, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': 0.0
        }),
        
        (5.5, 6.0, "Speaking (Oh)", {
            'mouth': 'O', 'smile': 0.1, 'eyebrow': 0.0,
            'head_pitch': 0.0, 'head_yaw': 0.05, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.1, 'iris_y': 0.0
        }),
        
        (6.0, 6.5, "Speaking (Ee)", {
            'mouth': 'E', 'smile': 0.3, 'eyebrow': 0.2,
            'head_pitch': 0.0, 'head_yaw': -0.05, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': -0.1, 'iris_y': 0.0
        }),
        
        (6.5, 7.0, "Nodding Yes", {
            'mouth': 'silence', 'smile': 0.4, 'eyebrow': 0.2,
            'head_pitch': 0.2, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': 0.1
        }),
        
        (7.0, 7.5, "Nodding Yes (up)", {
            'mouth': 'silence', 'smile': 0.4, 'eyebrow': 0.2,
            'head_pitch': -0.15, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': -0.1
        }),
        
        (7.5, 8.0, "Shaking No", {
            'mouth': 'silence', 'smile': -0.2, 'eyebrow': -0.2,
            'head_pitch': 0.0, 'head_yaw': 0.25, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.3, 'iris_y': 0.0
        }),
        
        (8.0, 8.5, "Shaking No (other side)", {
            'mouth': 'silence', 'smile': -0.2, 'eyebrow': -0.2,
            'head_pitch': 0.0, 'head_yaw': -0.25, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': -0.3, 'iris_y': 0.0
        }),
        
        (8.5, 9.0, "Confused", {
            'mouth': 'silence', 'smile': -0.1, 'eyebrow': 0.6,
            'head_pitch': 0.0, 'head_yaw': 0.0, 'head_roll': 0.12,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': 0.0
        }),
        
        (9.0, 9.5, "Excited", {
            'mouth': 'A', 'smile': 0.9, 'eyebrow': 0.7,
            'head_pitch': -0.05, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': -0.15
        }),
        
        (9.5, 10.0, "Shy", {
            'mouth': 'silence', 'smile': 0.3, 'eyebrow': 0.1,
            'head_pitch': 0.15, 'head_yaw': 0.2, 'head_roll': 0.1,
            'eye_wink': 0.0, 'iris_x': 0.2, 'iris_y': 0.2
        }),
        
        (10.0, 10.5, "Determined", {
            'mouth': 'silence', 'smile': 0.0, 'eyebrow': -0.4,
            'head_pitch': -0.08, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': -0.1
        }),
        
        (10.5, 12.0, "Back to Neutral", {
            'mouth': 'silence', 'smile': 0.0, 'eyebrow': 0.0,
            'head_pitch': 0.0, 'head_yaw': 0.0, 'head_roll': 0.0,
            'eye_wink': 0.0, 'iris_x': 0.0, 'iris_y': 0.0
        }),
    ]
    
    # Animation state
    state = {
        'frame_num': 0,
        'current_expression': showcase_sequence[0][2],
        'current_params': showcase_sequence[0][3].copy(),
        'target_params': showcase_sequence[0][3].copy(),
        'transition_progress': 1.0,
        'blink_timer': 0,
        'is_blinking': False,
        'blink_duration': 0,
        'breathing_phase': 0.0,
    }
    
    # Helper function to render frames
    def render_showcase_frame(renderer, state):
        """Render frame with expression parameters."""
        import torch
        
        # Get base pose for mouth
        base_pose = renderer._phoneme_to_pose(state['current_params']['mouth'], 1.0)
        pose_params = list(base_pose)
        
        # Apply expression parameters
        params = state['current_params']
        
        # Eyebrow control (params 0-11)
        if len(pose_params) > 11:
            eyebrow_val = params['eyebrow']
            for i in range(12):
                pose_params[i] += eyebrow_val * 0.3
        
        # Mouth/smile control (params 12-26)
        if len(pose_params) > 26:
            smile_val = params['smile']
            # Adjust mouth corners for smile
            pose_params[18] += smile_val * 0.5  # Mouth corner left
            pose_params[19] += smile_val * 0.5  # Mouth corner right
        
        # Eye control (params 14-17)
        if len(pose_params) > 17:
            # Wink (close left eye)
            if params['eye_wink'] > 0:
                pose_params[14] = -params['eye_wink'] * 0.9
            
            # Blinking
            if state['is_blinking']:
                blink_progress = state['blink_duration'] / 0.15
                if blink_progress < 0.5:
                    eye_close = blink_progress * 2.0
                else:
                    eye_close = (1.0 - blink_progress) * 2.0
                pose_params[14] = -eye_close * 0.8
                pose_params[15] = -eye_close * 0.8
            
            # Iris position
            if len(pose_params) > 19:
                pose_params[16] += params['iris_x'] * 0.5  # Iris X
                pose_params[17] += params['iris_y'] * 0.5  # Iris Y
        
        # Head rotation (params 27-32 typically)
        if len(pose_params) > 32:
            pose_params[27] += params['head_pitch'] * 0.8  # Pitch (up/down)
            pose_params[28] += params['head_yaw'] * 0.8    # Yaw (left/right)
            pose_params[29] += params['head_roll'] * 0.8   # Roll (tilt)
        
        # Add subtle breathing motion
        breathing = np.sin(state['breathing_phase']) * 0.02
        if len(pose_params) > 27:
            pose_params[27] += breathing
        
        # Render
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
            background = np.ones_like(rgb) * 0.95  # Light gray background
            composited = rgb * alpha + background * (1.0 - alpha)
            frame = (composited * 255).astype(np.uint8)
        else:
            frame = (output_np * 255).astype(np.uint8)
        
        return frame
    
    # Initial frame
    frame_data = render_showcase_frame(renderer, state)
    im = ax.imshow(frame_data, interpolation='bilinear')
    
    # Info text
    expression_text = ax.text(0.5, 0.98, '', transform=ax.transAxes,
                             ha='center', va='top', fontsize=14, fontweight='bold',
                             bbox=dict(boxstyle='round', facecolor='black', alpha=0.8),
                             color='cyan')
    
    fps_text = ax.text(0.02, 0.02, '', transform=ax.transAxes,
                      ha='left', va='bottom', fontsize=10,
                      bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                      color='lime')
    
    progress_text = ax.text(0.98, 0.02, '', transform=ax.transAxes,
                           ha='right', va='bottom', fontsize=10,
                           bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                           color='yellow')
    
    frame_times = []
    
    def update_frame(frame_num):
        """Update animation frame."""
        start_time = time.time()
        
        # Calculate time
        current_time = frame_num / 30.0
        
        # Find current expression in sequence
        for i, (start, end, name, params) in enumerate(showcase_sequence):
            if start <= current_time < end:
                if state['current_expression'] != name:
                    # Start transition to new expression
                    state['current_expression'] = name
                    state['target_params'] = params.copy()
                    state['transition_progress'] = 0.0
                break
        
        # Smooth transition between expressions
        if state['transition_progress'] < 1.0:
            state['transition_progress'] = min(1.0, state['transition_progress'] + 0.08)
            t = state['transition_progress']
            t_smooth = t * t * (3.0 - 2.0 * t)  # Ease in-out
            
            # Interpolate all parameters
            for key in state['current_params']:
                current = state['current_params'][key]
                target = state['target_params'][key]
                if isinstance(current, (int, float)):
                    state['current_params'][key] = current * (1 - t_smooth) + target * t_smooth
                else:
                    state['current_params'][key] = target
        
        # Blinking logic
        state['blink_timer'] += 1/30.0
        if not state['is_blinking'] and state['blink_timer'] > np.random.uniform(3, 6):
            state['is_blinking'] = True
            state['blink_duration'] = 0
            state['blink_timer'] = 0
        
        if state['is_blinking']:
            state['blink_duration'] += 1/30.0
            if state['blink_duration'] > 0.15:
                state['is_blinking'] = False
        
        # Breathing animation
        state['breathing_phase'] += 0.05
        
        # Render frame
        frame_data = render_showcase_frame(renderer, state)
        im.set_array(frame_data)
        
        # Update text
        expression_text.set_text(f'Expression: {state["current_expression"]}')
        
        # FPS
        frame_time = time.time() - start_time
        frame_times.append(frame_time)
        if len(frame_times) > 30:
            frame_times.pop(0)
        avg_fps = 1.0 / (sum(frame_times) / len(frame_times)) if frame_times else 0
        fps_text.set_text(f'FPS: {avg_fps:.1f}')
        
        # Progress
        progress = (current_time / 12.0) * 100
        progress_text.set_text(f'Progress: {progress:.0f}%')
        
        state['frame_num'] += 1
        
        return [im, expression_text, fps_text, progress_text]
    
    # Create animation
    total_frames = int(12.0 * 30)  # 12 seconds at 30 FPS
    
    print(f"   Total expressions: {len(showcase_sequence)}")
    print(f"   Duration: 12 seconds")
    print(f"   Features:")
    print(f"   - 18 different expressions and movements")
    print(f"   - Smooth transitions between all states")
    print(f"   - Automatic blinking")
    print(f"   - Subtle breathing animation")
    print(f"   - Head movements (nod, shake, tilt)")
    print(f"   - Eye movements and winking")
    print(f"   - Various emotions (happy, sad, surprised, etc.)")
    
    anim = animation.FuncAnimation(
        fig, update_frame,
        frames=total_frames,
        interval=33,
        blit=True,
        repeat=True,
        cache_frame_data=False
    )
    
    print("\n✅ Showcase window opened!")
    print("   Watch the avatar cycle through various expressions!")
    print("   Close the window when done.\n")
    
    plt.tight_layout()
    plt.show()
    
    print("\n✅ Showcase complete!")

if __name__ == "__main__":
    try:
        showcase_demo()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
