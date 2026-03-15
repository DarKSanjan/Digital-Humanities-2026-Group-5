#!/usr/bin/env python3
"""
Avatar expression showcase with CORRECT parameter indices.
Optionally use your own character image!

Usage:
  python demo_avatar_expressions.py                    # Use default character
  python demo_avatar_expressions.py path/to/image.png  # Use custom character
"""

import sys
import time
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_custom_character(renderer, image_path):
    """Load a custom character image."""
    from PIL import Image
    import torch
    
    print(f"   Loading custom character: {image_path}")
    
    try:
        pil_image = Image.open(image_path).convert('RGBA')
        
        # Resize to 512x512
        if pil_image.size != (512, 512):
            print(f"   Resizing from {pil_image.size} to (512, 512)")
            pil_image = pil_image.resize((512, 512), Image.Resampling.LANCZOS)
        
        # Convert to tensor
        image_array = np.array(pil_image).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_array).permute(2, 0, 1)
        renderer.character_image = image_tensor.to(renderer.device)
        
        print(f"   ✅ Custom character loaded!")
        return True
    except Exception as e:
        print(f"   ❌ Failed to load custom character: {e}")
        return False

def expressions_demo(custom_image_path=None):
    """Demo with correct parameter indices."""
    print("=" * 70)
    print("Avatar Expression Showcase (Correct Parameters)")
    print("=" * 70)
    
    # Initialize renderer
    print("\n1. Initializing avatar renderer...")
    from avatar_renderer import AvatarRenderer
    
    renderer = AvatarRenderer()
    result = renderer.initialize(use_gpu=True)
    
    if not result.success:
        print(f"❌ Failed to initialize: {result.error_message}")
        return
    
    print(f"✅ Initialized: {result.rendering_mode} mode")
    
    # Load custom character if provided
    if custom_image_path:
        if not load_custom_character(renderer, custom_image_path):
            print("   Falling back to default character")
    
    # Import visualization
    try:
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
    except ImportError:
        print("❌ matplotlib required")
        return
    
    print("\n2. Creating expression showcase...")
    
    # Parameter indices (from print_pose_params.py):
    # Eyebrows: 0-11
    # Eyes: 12-23
    # Iris: 24-25
    # Mouth: 26-36
    # Iris rotation: 37-38
    # Head rotation: 39-41 (head_x=pitch, head_y=yaw, neck_z=roll)
    # Body: 42-43
    # Breathing: 44
    
    # Create figure
    fig, ax = plt.subplots(figsize=(11, 11))
    fig.patch.set_facecolor('#1a1a1a')
    ax.set_title("Avatar Expression Showcase", fontsize=18, fontweight='bold', color='white')
    ax.axis('off')
    
    # Showcase sequence
    expressions = [
        (0, 2.0, "Neutral", [0]*45),
        
        (2.0, 3.0, "Happy Smile", lambda: set_params(
            eyebrow_happy=0.8, mouth_raised_corner=0.9, mouth_eee=0.3
        )),
        
        (3.0, 4.0, "Head Tilt Right", lambda: set_params(
            neck_z=0.5, eyebrow_happy=0.5, mouth_raised_corner=0.6
        )),
        
        (4.0, 5.0, "Head Tilt Left", lambda: set_params(
            neck_z=-0.5, eyebrow_raised=0.4, mouth_smirk=0.5
        )),
        
        (5.0, 6.0, "Look Up", lambda: set_params(
            head_x=0.6, eyebrow_raised=0.7, mouth_ooo=0.3
        )),
        
        (6.0, 7.0, "Look Down (Shy)", lambda: set_params(
            head_x=-0.5, eyebrow_happy=0.3, mouth_raised_corner=0.4, eye_happy_wink=0.2
        )),
        
        (7.0, 8.0, "Look Left", lambda: set_params(
            head_y=0.7, iris_rotation_x=0.8, eyebrow_raised=0.3
        )),
        
        (8.0, 9.0, "Look Right", lambda: set_params(
            head_y=-0.7, iris_rotation_x=-0.8, eyebrow_serious=0.2
        )),
        
        (9.0, 10.0, "Surprised", lambda: set_params(
            eyebrow_raised=1.0, eye_surprised=0.9, mouth_ooo=0.8, head_x=0.2
        )),
        
        (10.0, 11.0, "Angry", lambda: set_params(
            eyebrow_angry=0.9, eyebrow_lowered=0.6, mouth_lowered_corner=0.7, head_x=-0.1
        )),
        
        (11.0, 12.0, "Sad", lambda: set_params(
            eyebrow_troubled=0.8, mouth_lowered_corner=0.9, eye_relaxed=0.4, head_x=-0.3
        )),
        
        (12.0, 13.0, "Wink Left", lambda: set_params(
            eye_wink_left=1.0, mouth_raised_corner=0.7, eyebrow_happy=0.5
        )),
        
        (13.0, 14.0, "Wink Right", lambda: set_params(
            eye_wink_right=1.0, mouth_smirk=0.6, eyebrow_raised_right=0.4
        )),
        
        (14.0, 15.0, "Speaking Ah", lambda: set_params(
            mouth_aaa=1.0, head_y=0.1, breathing=0.6
        )),
        
        (15.0, 16.0, "Speaking Ee", lambda: set_params(
            mouth_eee=1.0, mouth_raised_corner=0.3, head_y=-0.1
        )),
        
        (16.0, 17.0, "Speaking Oh", lambda: set_params(
            mouth_ooo=1.0, eyebrow_raised=0.2, head_y=0.15
        )),
        
        (17.0, 18.0, "Thinking", lambda: set_params(
            eyebrow_serious=0.6, head_y=0.3, head_x=-0.2, iris_rotation_x=0.4, iris_rotation_y=0.3
        )),
        
        (18.0, 19.0, "Skeptical", lambda: set_params(
            eyebrow_lowered_left=0.7, eyebrow_raised_right=0.5, mouth_lowered_corner=0.4, head_y=-0.2
        )),
        
        (19.0, 20.0, "Determined", lambda: set_params(
            eyebrow_serious=0.9, mouth_delta=0.5, head_x=0.15, eye_unimpressed=0.3
        )),
        
        (20.0, 22.0, "Back to Neutral", [0]*45),
    ]
    
    def set_params(**kwargs):
        """Helper to set parameters by name."""
        params = [0.0] * 45
        
        # Eyebrows
        if 'eyebrow_troubled' in kwargs:
            params[0] = params[1] = kwargs['eyebrow_troubled']
        if 'eyebrow_angry' in kwargs:
            params[2] = params[3] = kwargs['eyebrow_angry']
        if 'eyebrow_lowered' in kwargs:
            params[4] = params[5] = kwargs['eyebrow_lowered']
        if 'eyebrow_lowered_left' in kwargs:
            params[4] = kwargs['eyebrow_lowered_left']
        if 'eyebrow_raised' in kwargs:
            params[6] = params[7] = kwargs['eyebrow_raised']
        if 'eyebrow_raised_right' in kwargs:
            params[7] = kwargs['eyebrow_raised_right']
        if 'eyebrow_happy' in kwargs:
            params[8] = params[9] = kwargs['eyebrow_happy']
        if 'eyebrow_serious' in kwargs:
            params[10] = params[11] = kwargs['eyebrow_serious']
        
        # Eyes
        if 'eye_wink_left' in kwargs:
            params[12] = kwargs['eye_wink_left']
        if 'eye_wink_right' in kwargs:
            params[13] = kwargs['eye_wink_right']
        if 'eye_happy_wink' in kwargs:
            params[14] = params[15] = kwargs['eye_happy_wink']
        if 'eye_surprised' in kwargs:
            params[16] = params[17] = kwargs['eye_surprised']
        if 'eye_relaxed' in kwargs:
            params[18] = params[19] = kwargs['eye_relaxed']
        if 'eye_unimpressed' in kwargs:
            params[20] = params[21] = kwargs['eye_unimpressed']
        
        # Mouth
        if 'mouth_aaa' in kwargs:
            params[26] = kwargs['mouth_aaa']
        if 'mouth_iii' in kwargs:
            params[27] = kwargs['mouth_iii']
        if 'mouth_uuu' in kwargs:
            params[28] = kwargs['mouth_uuu']
        if 'mouth_eee' in kwargs:
            params[29] = kwargs['mouth_eee']
        if 'mouth_ooo' in kwargs:
            params[30] = kwargs['mouth_ooo']
        if 'mouth_delta' in kwargs:
            params[31] = kwargs['mouth_delta']
        if 'mouth_lowered_corner' in kwargs:
            params[32] = params[33] = kwargs['mouth_lowered_corner']
        if 'mouth_raised_corner' in kwargs:
            params[34] = params[35] = kwargs['mouth_raised_corner']
        if 'mouth_smirk' in kwargs:
            params[36] = kwargs['mouth_smirk']
        
        # Iris
        if 'iris_rotation_x' in kwargs:
            params[37] = kwargs['iris_rotation_x']
        if 'iris_rotation_y' in kwargs:
            params[38] = kwargs['iris_rotation_y']
        
        # Head rotation
        if 'head_x' in kwargs:  # Pitch (up/down)
            params[39] = kwargs['head_x']
        if 'head_y' in kwargs:  # Yaw (left/right)
            params[40] = kwargs['head_y']
        if 'neck_z' in kwargs:  # Roll (tilt)
            params[41] = kwargs['neck_z']
        
        # Body
        if 'body_y' in kwargs:
            params[42] = kwargs['body_y']
        if 'body_z' in kwargs:
            params[43] = kwargs['body_z']
        
        # Breathing
        if 'breathing' in kwargs:
            params[44] = kwargs['breathing']
        
        return params
    
    # Convert lambda expressions to actual params
    expressions_resolved = []
    for start, end, name, params_or_func in expressions:
        if callable(params_or_func):
            params = params_or_func()
        else:
            params = params_or_func
        expressions_resolved.append((start, end, name, params))
    
    # Animation state
    state = {
        'current_params': expressions_resolved[0][3][:],
        'target_params': expressions_resolved[0][3][:],
        'current_name': expressions_resolved[0][2],
        'transition_progress': 1.0,
        'blink_timer': 0,
        'is_blinking': False,
        'blink_duration': 0,
    }
    
    def render_frame(renderer, params):
        """Render with given parameters."""
        import torch
        
        pose_tensor = torch.tensor([params], dtype=renderer.model.get_dtype()).to(renderer.device)
        
        if renderer.character_image.dim() == 3:
            input_image = renderer.character_image.unsqueeze(0)
        else:
            input_image = renderer.character_image
        
        with torch.no_grad():
            output_image = renderer.model.pose(input_image, pose_tensor)
        
        output_np = output_image[0].cpu().numpy()
        output_np = np.transpose(output_np, (1, 2, 0))
        output_np = np.clip(output_np, 0.0, 1.0)
        
        if output_np.shape[2] == 4:
            rgb = output_np[:, :, :3]
            alpha = output_np[:, :, 3:4]
            background = np.ones_like(rgb) * 0.95
            composited = rgb * alpha + background * (1.0 - alpha)
            frame = (composited * 255).astype(np.uint8)
        else:
            frame = (output_np * 255).astype(np.uint8)
        
        return frame
    
    # Initial frame
    frame_data = render_frame(renderer, state['current_params'])
    im = ax.imshow(frame_data, interpolation='bilinear')
    
    # UI elements
    name_text = ax.text(0.5, 0.98, '', transform=ax.transAxes,
                       ha='center', va='top', fontsize=14, fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.8),
                       color='cyan')
    
    fps_text = ax.text(0.02, 0.02, '', transform=ax.transAxes,
                      ha='left', va='bottom', fontsize=10,
                      bbox=dict(boxstyle='round', facecolor='black', alpha=0.7),
                      color='lime')
    
    frame_times = []
    
    def update_frame(frame_num):
        """Update animation."""
        start_time = time.time()
        
        current_time = frame_num / 30.0
        
        # Find current expression
        for start, end, name, params in expressions_resolved:
            if start <= current_time < end:
                if state['current_name'] != name:
                    state['current_name'] = name
                    state['target_params'] = params[:]
                    state['transition_progress'] = 0.0
                break
        
        # Smooth transition
        if state['transition_progress'] < 1.0:
            state['transition_progress'] = min(1.0, state['transition_progress'] + 0.1)
            t = state['transition_progress']
            t_smooth = t * t * (3.0 - 2.0 * t)
            
            for i in range(45):
                state['current_params'][i] = (
                    state['current_params'][i] * (1 - t_smooth) +
                    state['target_params'][i] * t_smooth
                )
        
        # Blinking
        state['blink_timer'] += 1/30.0
        if not state['is_blinking'] and state['blink_timer'] > np.random.uniform(3, 6):
            state['is_blinking'] = True
            state['blink_duration'] = 0
            state['blink_timer'] = 0
        
        # Start with current params
        render_params = state['current_params'][:]
        
        if state['is_blinking']:
            state['blink_duration'] += 1/30.0
            if state['blink_duration'] > 0.15:
                state['is_blinking'] = False
            else:
                # Apply blink
                blink_progress = state['blink_duration'] / 0.15
                if blink_progress < 0.5:
                    eye_close = blink_progress * 2.0
                else:
                    eye_close = (1.0 - blink_progress) * 2.0
                
                # Modify eye params
                render_params[12] = eye_close  # Left eye wink
                render_params[13] = eye_close  # Right eye wink
        
        # Render
        frame_data = render_frame(renderer, render_params)
        im.set_array(frame_data)
        
        # Update UI
        name_text.set_text(f'Expression: {state["current_name"]}')
        
        frame_time = time.time() - start_time
        frame_times.append(frame_time)
        if len(frame_times) > 30:
            frame_times.pop(0)
        avg_fps = 1.0 / (sum(frame_times) / len(frame_times)) if frame_times else 0
        fps_text.set_text(f'FPS: {avg_fps:.1f}')
        
        return [im, name_text, fps_text]
    
    total_frames = int(22.0 * 30)
    
    print(f"   Total expressions: {len(expressions_resolved)}")
    print(f"   Duration: 22 seconds")
    print(f"   Features: Head rotation, eye movement, expressions")
    
    anim = animation.FuncAnimation(
        fig, update_frame,
        frames=total_frames,
        interval=33,
        blit=True,
        repeat=True,
        cache_frame_data=False
    )
    
    print("\n✅ Showcase window opened!")
    print("   Close the window when done.\n")
    
    plt.tight_layout()
    plt.show()
    
    print("\n✅ Demo complete!")

if __name__ == "__main__":
    custom_image = sys.argv[1] if len(sys.argv) > 1 else None
    
    if custom_image:
        print(f"\nUsing custom character: {custom_image}\n")
    
    try:
        expressions_demo(custom_image)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
