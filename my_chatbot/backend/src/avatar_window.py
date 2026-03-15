"""
Avatar display window using tkinter.
Renders the talking-head-anime-3 avatar in a native Python window.
Receives phoneme data from the WebSocket server to animate lip sync.
"""

import threading
import time
import logging
import queue
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class AvatarWindow:
    """Native Python window for avatar display using tkinter."""

    def __init__(self, avatar_renderer):
        self.renderer = avatar_renderer
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.phoneme_queue: queue.Queue = queue.Queue()
        self.current_phoneme = "silence"
        self.target_phoneme = "silence"
        self.transition_progress = 1.0
        self.blink_timer = 0.0
        self.is_blinking = False
        self.blink_duration = 0.0
        self.idle_timer = 0.0
        self._tk_root = None
        self._tk_label = None
        self._photo_image = None

    def start(self):
        """Start the avatar window in a separate thread."""
        if self.running:
            return
        if not self.renderer.initialized:
            logger.warning("Avatar renderer not initialized, skipping window")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_window, daemon=True)
        self.thread.start()
        logger.info("Avatar window started")

    def stop(self):
        """Stop the avatar window."""
        self.running = False
        if self._tk_root:
            try:
                self._tk_root.quit()
            except Exception:
                pass
        logger.info("Avatar window stopped")

    def set_phoneme(self, phoneme: str):
        """Set the current phoneme for lip sync animation."""
        try:
            self.phoneme_queue.put_nowait(phoneme)
        except queue.Full:
            pass

    def set_phonemes(self, phonemes: list):
        """Queue a list of phonemes from the frontend."""
        for p in phonemes:
            ph = p.get("phoneme", "silence") if isinstance(p, dict) else str(p)
            self.set_phoneme(ph)

    def _run_window(self):
        """Main window loop running in its own thread."""
        try:
            import tkinter as tk
            from PIL import Image, ImageTk
        except ImportError as e:
            logger.error(f"Cannot open avatar window: {e}")
            logger.error("Install Pillow: pip install Pillow")
            self.running = False
            return

        root = tk.Tk()
        root.title("Persuasive Chatbot - Avatar")
        root.configure(bg="white")
        root.geometry("520x560")
        root.resizable(False, False)
        self._tk_root = root

        # Title label
        title = tk.Label(
            root, text="Avatar", font=("Segoe UI", 14, "bold"),
            bg="white", fg="#333"
        )
        title.pack(pady=(8, 0))

        # Status label
        self._status_label = tk.Label(
            root, text="Idle", font=("Segoe UI", 10),
            bg="white", fg="#888"
        )
        self._status_label.pack()

        # Image label for avatar frames
        self._tk_label = tk.Label(root, bg="white")
        self._tk_label.pack(padx=4, pady=4)

        # Render initial frame
        self._render_and_display(root)

        # Start update loop
        root.after(33, lambda: self._update_loop(root))

        def on_close():
            self.running = False
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)

        try:
            root.mainloop()
        except Exception:
            pass
        finally:
            self.running = False

    def _update_loop(self, root):
        """Called every ~33ms to update the avatar frame."""
        if not self.running:
            return

        # Drain phoneme queue
        new_phoneme = None
        while not self.phoneme_queue.empty():
            try:
                new_phoneme = self.phoneme_queue.get_nowait()
            except queue.Empty:
                break

        if new_phoneme and new_phoneme != self.target_phoneme:
            self.current_phoneme = self.target_phoneme
            self.target_phoneme = new_phoneme
            self.transition_progress = 0.0

        # Advance transition
        if self.transition_progress < 1.0:
            self.transition_progress = min(1.0, self.transition_progress + 0.18)

        # Blinking
        dt = 1.0 / 30.0
        self.blink_timer += dt
        if not self.is_blinking and self.blink_timer > 3.5:
            self.is_blinking = True
            self.blink_duration = 0.0
            self.blink_timer = 0.0
        if self.is_blinking:
            self.blink_duration += dt
            if self.blink_duration > 0.15:
                self.is_blinking = False

        # Idle sway
        self.idle_timer += dt

        # Render and display
        self._render_and_display(root)

        # Schedule next frame
        if self.running:
            root.after(33, lambda: self._update_loop(root))

    def _render_and_display(self, root):
        """Render current frame and display it in the tkinter window."""
        try:
            from PIL import Image, ImageTk
            import torch

            if not self.renderer.initialized or self.renderer.model is None:
                return
            if self.renderer.character_image is None:
                return

            # Interpolate pose between current and target phoneme
            cur_pose = self.renderer._phoneme_to_pose(self.current_phoneme, 1.0)
            tgt_pose = self.renderer._phoneme_to_pose(self.target_phoneme, 1.0)
            t = self.transition_progress
            t_smooth = t * t * (3.0 - 2.0 * t)  # ease-in-out
            pose = [
                cur_pose[i] * (1 - t_smooth) + tgt_pose[i] * t_smooth
                for i in range(len(cur_pose))
            ]

            # Apply blink
            if self.is_blinking and len(pose) > 15:
                bp = self.blink_duration / 0.15
                eye_close = (bp * 2.0) if bp < 0.5 else ((1.0 - bp) * 2.0)
                pose[14] = -eye_close * 0.8
                pose[15] = -eye_close * 0.8

            # Apply idle head sway
            if len(pose) > 21:
                pose[21] += np.sin(self.idle_timer * 0.5) * 0.03

            # Render
            pose_tensor = torch.tensor(
                [pose], dtype=self.renderer.model.get_dtype()
            ).to(self.renderer.device)

            img_in = self.renderer.character_image
            if img_in.dim() == 3:
                img_in = img_in.unsqueeze(0)

            with torch.no_grad():
                output = self.renderer.model.pose(img_in, pose_tensor)

            frame_np = output[0].cpu().numpy()
            frame_np = np.transpose(frame_np, (1, 2, 0))
            frame_np = np.clip(frame_np, 0.0, 1.0)

            # Alpha composite over white
            if frame_np.shape[2] == 4:
                rgb = frame_np[:, :, :3]
                alpha = frame_np[:, :, 3:4]
                bg = np.ones_like(rgb)
                frame_np = rgb * alpha + bg * (1.0 - alpha)

            frame_uint8 = (frame_np * 255).astype(np.uint8)
            pil_img = Image.fromarray(frame_uint8)
            self._photo_image = ImageTk.PhotoImage(pil_img)
            self._tk_label.configure(image=self._photo_image)

            # Update status
            ph_display = self.target_phoneme
            if self.transition_progress < 1.0:
                ph_display = f"{self.current_phoneme} → {self.target_phoneme}"
            blink_str = " 👁" if self.is_blinking else ""
            self._status_label.configure(text=f"Phoneme: {ph_display}{blink_str}")

        except Exception as e:
            logger.error(f"Avatar render error: {e}")
