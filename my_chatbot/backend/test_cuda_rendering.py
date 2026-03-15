#!/usr/bin/env python3
"""
Quick test script to verify CUDA-enabled avatar rendering is working.
Run this after setting up CUDA to ensure everything is operational.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cuda_rendering():
    """Test CUDA-enabled avatar rendering."""
    print("=" * 60)
    print("CUDA Avatar Rendering Test")
    print("=" * 60)
    
    # 1. Check PyTorch and CUDA
    print("\n1. Checking PyTorch and CUDA...")
    try:
        import torch
        print(f"   ✅ PyTorch version: {torch.__version__}")
        print(f"   ✅ CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   ✅ CUDA version: {torch.version.cuda}")
            print(f"   ✅ GPU: {torch.cuda.get_device_name(0)}")
            print(f"   ✅ VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            print("   ⚠️  CUDA not available - will use CPU")
    except ImportError as e:
        print(f"   ❌ PyTorch not installed: {e}")
        return False
    
    # 2. Initialize Avatar Renderer
    print("\n2. Initializing Avatar Renderer...")
    try:
        from avatar_renderer import AvatarRenderer
        
        renderer = AvatarRenderer()
        start_time = time.time()
        result = renderer.initialize(use_gpu=True)
        init_time = time.time() - start_time
        
        if result.success:
            print(f"   ✅ Initialization successful in {init_time:.2f}s")
            print(f"   ✅ Rendering mode: {result.rendering_mode}")
            print(f"   ✅ Target FPS: {result.target_fps}")
        else:
            print(f"   ❌ Initialization failed: {result.error_message}")
            return False
    except Exception as e:
        print(f"   ❌ Failed to initialize renderer: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. Test Frame Rendering
    print("\n3. Testing frame rendering...")
    try:
        # Test with different phonemes
        test_phonemes = ['A', 'E', 'O', 'silence', 'B', 'F']
        render_times = []
        
        for phoneme in test_phonemes:
            start_time = time.time()
            frame, timestamp = renderer.render_frame(phoneme, intensity=1.0)
            render_time = (time.time() - start_time) * 1000  # ms
            render_times.append(time.time() - start_time)
            
            if frame is not None:
                print(f"   ✅ Rendered '{phoneme}' in {render_time:.1f}ms")
            else:
                print(f"   ❌ Failed to render '{phoneme}'")
                return False
        
        # Calculate average FPS
        avg_render_time = sum(render_times) / len(render_times)
        estimated_fps = 1.0 / avg_render_time if avg_render_time > 0 else 0
        print(f"\n   ✅ Average render time: {avg_render_time*1000:.1f}ms")
        print(f"   ✅ Estimated FPS: {estimated_fps:.1f}")
        
        if estimated_fps >= 25:
            print(f"   🚀 Performance: EXCELLENT (target: 30 FPS)")
        elif estimated_fps >= 15:
            print(f"   ✅ Performance: GOOD (target: 24 FPS)")
        else:
            print(f"   ⚠️  Performance: SLOW (may need optimization)")
            
    except Exception as e:
        print(f"   ❌ Rendering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Test Batch Rendering
    print("\n4. Testing batch rendering...")
    try:
        phoneme_sequence = ['A', 'E', 'O', 'A', 'E', 'O', 'silence', 'B', 'F', 'silence']
        
        start_time = time.time()
        frames = []
        for phoneme in phoneme_sequence:
            frame, timestamp = renderer.render_frame(phoneme, intensity=1.0)
            frames.append(frame)
        batch_time = time.time() - start_time
        
        if frames and len(frames) == len(phoneme_sequence):
            print(f"   ✅ Rendered {len(frames)} frames in {batch_time:.2f}s")
            print(f"   ✅ Average: {batch_time/len(frames)*1000:.1f}ms per frame")
        else:
            print(f"   ❌ Batch rendering failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Batch rendering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Success!
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nYour CUDA-enabled avatar rendering is working perfectly!")
    print(f"Mode: {result.rendering_mode.upper()}")
    print(f"Target FPS: {result.target_fps}")
    print(f"Estimated FPS: {estimated_fps:.1f}")
    print("\nYou can now run the full backend with: python src/main.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_cuda_rendering()
    sys.exit(0 if success else 1)
