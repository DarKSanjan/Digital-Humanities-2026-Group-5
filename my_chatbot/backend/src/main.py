"""Main entry point for the Python backend.

Launches the customtkinter GUI alongside the existing backend
components (AvatarRenderer, LipSyncController, StreamCoordinator,
AvatarWindow).  The StreamingPipeline, AudioPlayer, and AppController
are wired together so that mic input flows through STT → LLM → TTS →
audio playback → lip sync.
"""

import sys
import logging
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from websocket_server import WebSocketIPCServer
from hardware_detection import HardwareDetector
from avatar_renderer import AvatarRenderer
from lip_sync_controller import LipSyncController
from stream_coordinator import StreamCoordinator
from avatar_window import AvatarWindow

from src.app_gui import AppGUI
from src.audio_player import AudioPlayer
from src.streaming_pipeline import StreamingPipeline
from src.app_controller import AppController
from src.mic_recorder import MicRecorder

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class BackendService:
    """Main backend service coordinating all components."""

    def __init__(self):
        self.ipc_server = WebSocketIPCServer(host="127.0.0.1", port=8765)
        self.avatar_renderer = AvatarRenderer()
        self.lip_sync_controller = LipSyncController()
        self.stream_coordinator = None
        self.hardware_info = None
        self.avatar_window = None

    async def initialize(self) -> None:
        """Initialize all backend components."""
        logger.info("Initializing backend service...")

        # Detect hardware
        self.hardware_info = HardwareDetector.detect_hardware()
        logger.info(
            f"Hardware: {self.hardware_info.platform}, "
            f"GPU: {self.hardware_info.gpu_available}"
        )

        # Initialize avatar renderer
        init_result = self.avatar_renderer.initialize(
            use_gpu=self.hardware_info.gpu_available
        )

        if not init_result.success:
            logger.error(f"Avatar init failed: {init_result.error_message}")
            logger.warning("Continuing in audio-only mode")
        else:
            logger.info(
                f"Avatar initialized: mode={init_result.rendering_mode}, "
                f"fps={init_result.target_fps}"
            )
            # Start the avatar display window
            self.avatar_window = AvatarWindow(self.avatar_renderer)
            self.avatar_window.start()
            logger.info("Avatar display window launched")

        # Initialize stream coordinator
        self.stream_coordinator = StreamCoordinator(
            avatar_renderer=self.avatar_renderer,
            lip_sync_controller=self.lip_sync_controller,
            sync_tolerance_ms=100.0,
            frame_buffer_size=3
        )

        self._register_ipc_handlers()
        logger.info("Backend service initialized successfully")

    def _register_ipc_handlers(self) -> None:
        """Register JSON-RPC method handlers with IPC server."""

        async def handle_get_hardware_info(params: dict) -> dict:
            if self.hardware_info is None:
                return {"error": "Hardware not detected"}
            return {
                "platform": self.hardware_info.platform,
                "gpuAvailable": self.hardware_info.gpu_available,
                "gpuName": self.hardware_info.gpu_name,
                "cudaVersion": self.hardware_info.cuda_version,
                "renderingMode": self.hardware_info.rendering_mode,
                "targetFPS": self.hardware_info.target_fps,
            }

        async def handle_get_renderer_status(params: dict) -> dict:
            return {
                "initialized": self.avatar_renderer.initialized,
                "renderingMode": self.avatar_renderer.get_rendering_mode(),
                "targetFPS": self.avatar_renderer.get_target_fps(),
                "currentFPS": self.avatar_renderer.get_fps(),
                "vramUsageGB": self.avatar_renderer.get_vram_usage(),
            }

        async def handle_render_frame(params: dict) -> dict:
            phoneme = params.get("phoneme", "X")
            intensity = params.get("intensity", 1.0)
            try:
                frame, timestamp = self.avatar_renderer.render_frame(phoneme, intensity)
                import base64
                frame_b64 = base64.b64encode(frame.tobytes()).decode("utf-8")
                return {
                    "success": True,
                    "frame": frame_b64,
                    "timestamp": timestamp,
                    "shape": list(frame.shape),
                    "fps": self.avatar_renderer.get_fps(),
                }
            except Exception as e:
                logger.error(f"Frame rendering failed: {e}")
                return {"success": False, "error": str(e)}

        async def handle_render_speech(params: dict) -> dict:
            """Receive phonemes from frontend and push to avatar window."""
            phonemes = params.get("phonemes", [])
            try:
                if self.avatar_window and self.avatar_window.running:
                    self.avatar_window.set_phonemes(phonemes)
                    return {"success": True, "queued": len(phonemes)}
                return {"success": True, "message": "Avatar window not running"}
            except Exception as e:
                logger.error(f"render_speech failed: {e}")
                return {"success": False, "error": str(e)}

        async def handle_ping(params: dict) -> dict:
            return {"status": "ok", "timestamp": asyncio.get_event_loop().time()}

        self.ipc_server.register_handler("getHardwareInfo", handle_get_hardware_info)
        self.ipc_server.register_handler("getRendererStatus", handle_get_renderer_status)
        self.ipc_server.register_handler("renderFrame", handle_render_frame)
        self.ipc_server.register_handler("render_speech", handle_render_speech)
        self.ipc_server.register_handler("ping", handle_ping)
        logger.info("IPC handlers registered")

    async def run(self) -> None:
        """Run the backend service."""
        await self.initialize()
        logger.info("Backend ready, starting WebSocket server...")
        await self.ipc_server.start()

    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down backend service...")
        if self.avatar_window:
            self.avatar_window.stop()
        self.ipc_server.stop()
        if self.avatar_renderer.initialized:
            self.avatar_renderer.shutdown()
        logger.info("Backend service shutdown complete")


def _build_lip_sync_callbacks(avatar_window):
    """Return (on_lip_sync_start, on_lip_sync_end) wired to *avatar_window*.

    If *avatar_window* is ``None`` (e.g. GPU init failed), the callbacks
    are harmless no-ops.
    """

    def on_lip_sync_start(phonemes) -> None:
        if avatar_window is not None and avatar_window.running:
            avatar_window.set_phonemes(phonemes)

    def on_lip_sync_end() -> None:
        if avatar_window is not None and avatar_window.running:
            avatar_window.set_phoneme("silence")

    return on_lip_sync_start, on_lip_sync_end


def launch_gui(backend_service: BackendService) -> None:
    """Create and run the customtkinter GUI with the streaming pipeline.

    This wires together:
    * :class:`AppGUI` — the customtkinter window
    * :class:`AudioPlayer` — sounddevice playback
    * :class:`StreamingPipeline` — LLM → TTS → playback → lip sync
    * :class:`AppController` — GUI ↔ mic ↔ STT ↔ pipeline
    * :class:`MicRecorder` — pyaudio capture

    The controller's background asyncio loop is started before the
    blocking ``gui.mainloop()`` call.
    """
    gui = AppGUI()

    audio_player = AudioPlayer()

    on_start, on_end = _build_lip_sync_callbacks(backend_service.avatar_window)

    pipeline = StreamingPipeline(
        audio_player=audio_player,
        on_lip_sync_start=on_start,
        on_lip_sync_end=on_end,
    )

    mic = MicRecorder()

    controller = AppController(
        gui=gui,
        pipeline=pipeline,
        mic_recorder=mic,
    )

    controller.start()
    logger.info("AppController background loop started")

    try:
        gui.mainloop()
    except KeyboardInterrupt:
        logger.info("GUI interrupted")
    finally:
        controller.stop()
        logger.info("AppController stopped")


async def main() -> None:
    """Main entry point."""
    logger.info("Persuasive Chatbot Backend starting...")
    service = BackendService()
    try:
        await service.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        service.shutdown()


def main_with_gui() -> None:
    """Entry point that initialises the backend then launches the GUI.

    BackendService.initialize() is awaited in a one-shot event loop,
    then the blocking customtkinter mainloop takes over.
    """
    logger.info("Persuasive Chatbot starting (GUI mode)...")
    service = BackendService()
    try:
        asyncio.run(service.initialize())
        launch_gui(service)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        service.shutdown()


if __name__ == "__main__":
    try:
        main_with_gui()
    except KeyboardInterrupt:
        logger.info("Exiting...")
