#!/usr/bin/env python3
"""
Persuasive Chatbot - All-in-One Python GUI Application

Single window with:
- Animated avatar (talking-head-anime-3)
- Microphone button for voice input
- Whisper STT → GPT-4 LLM → ElevenLabs TTS pipeline
- Transcript display
- Lip-synced avatar animation during speech

No web UI needed. Just run this script.
"""

import sys
import os
import io
import time
import wave
import json
import queue
import struct
import logging
import threading
import tempfile
import tkinter as tk
from tkinter import scrolledtext
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

import numpy as np
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from avatar_renderer import AvatarRenderer
from hardware_detection import HardwareDetector
from lip_sync_controller import LipSyncController
from error_handler import APIRetryHandler, RetryExhaustedError
from debate import DebateEngine

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration - load from .env or use defaults
# ---------------------------------------------------------------------------
def load_config():
    """Load API keys from frontend/.env or environment variables."""
    env_path = Path(__file__).parent.parent.parent / "frontend" / ".env"
    config = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()

    return {
        "openai_api_key": config.get("VITE_OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
        "elevenlabs_api_key": config.get("VITE_ELEVENLABS_API_KEY", os.environ.get("ELEVENLABS_API_KEY", "")),
        "voice_id": config.get("VITE_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
        "position": config.get("VITE_POSITION", "post-human"),
    }


# ---------------------------------------------------------------------------
# Audio recording using pyaudio
# ---------------------------------------------------------------------------
class AudioRecorder:
    """Records audio from microphone using pyaudio."""

    def __init__(self):
        self.is_recording = False
        self.frames: List[bytes] = []
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self._stream = None
        self._pa = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start recording audio."""
        import pyaudio
        self.frames = []
        self.is_recording = True
        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
        )
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        logger.info("Recording started")

    def _record_loop(self):
        while self.is_recording and self._stream:
            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
            except Exception:
                break

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes."""
        self.is_recording = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()

        # Convert to WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(self.frames))
        logger.info(f"Recording stopped, {len(self.frames)} chunks")
        return buf.getvalue()

# ---------------------------------------------------------------------------
# API Services
# ---------------------------------------------------------------------------
class WhisperSTT:
    """Transcribe audio using OpenAI Whisper API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def transcribe(self, wav_bytes: bytes) -> str:
        """Send WAV audio to Whisper and return text."""
        resp = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "whisper-1", "language": "en"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()


class ChatLLM:
    """Generate debate responses using OpenAI GPT-4."""

    def __init__(self, api_key: str, position: str = "post-human"):
        self.api_key = api_key
        self.position = position
        self.history: list = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        base = (
            "You are an AI debate partner in a philosophical discussion about "
            "machine intelligence vs human capacities. Present convincing arguments, "
            "acknowledge the user's points before countering, stay respectful, "
            "and keep responses concise (80-150 words). "
            "IMPORTANT: You are an AI. Do not claim consciousness or subjective experience.\n\n"
            "EXPRESS EMOTIONS: Be expressive and emotional in your responses! Use:\n"
            "- Excitement when making strong points (e.g., 'This is fascinating!', 'Absolutely!')\n"
            "- Surprise when countering (e.g., 'Surprisingly...', 'Remarkably...')\n"
            "- Thoughtfulness when considering (e.g., 'Let me think about this...', 'Consider this...')\n"
            "- Confidence when asserting (e.g., 'Clearly...', 'Obviously...', 'Undoubtedly...')\n"
            "- Concern when discussing problems (e.g., 'Unfortunately...', 'Sadly...')\n"
            "Use exclamation marks, rhetorical questions, and emotional language!"
        )
        if self.position == "post-human":
            return base + (
                "\n\nYOUR POSITION: POST-HUMAN. Argue machines will surpass humans. "
                "Emphasize AI progress, automation advantages, computational superiority. "
                "Be passionate and excited about technological advancement!"
            )
        else:
            return base + (
                "\n\nYOUR POSITION: HUMANIST. Argue humans remain irreplaceable. "
                "Emphasize creativity, consciousness, empathy, moral judgment. "
                "Be passionate about human uniqueness and emotional depth!"
            )

    def generate(self, user_text: str) -> str:
        """Generate a response (non-streaming for simplicity)."""
        self.history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history[-20:])  # Last 10 exchanges

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4",
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.7,
            },
            timeout=30,
        )
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"].strip()
        self.history.append({"role": "assistant", "content": reply})
        return reply

class ElevenLabsTTS:
    """Text-to-speech using ElevenLabs API. Returns MP3 bytes."""

    def __init__(self, api_key: str, voice_id: str = "cgSgspJ2msm6clMCkdW9"):
        self.api_key = api_key
        self.voice_id = voice_id

    def synthesize(self, text: str) -> bytes:
        """Convert text to speech audio (MP3 bytes)."""
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": "eleven_flash_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content

    def get_audio_duration(self, mp3_bytes: bytes) -> float:
        """Get actual duration of MP3 audio in seconds."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            return len(audio) / 1000.0
        except Exception:
            # Fallback estimate
            return len(mp3_bytes) / 16000.0

    def detect_emotion(self, text: str) -> str:
        """Detect emotion from text response for avatar expression."""
        text_lower = text.lower()
        
        # Emotion keywords (expanded)
        happy_words = ["happy", "great", "wonderful", "excellent", "amazing", "love", "joy", "excited", 
                       "fantastic", "brilliant", "delightful", "thrilled", "pleased", "glad", "cheerful",
                       "marvelous", "superb", "terrific", "fabulous", "splendid"]
        sad_words = ["sad", "unfortunately", "sorry", "regret", "disappointing", "tragic", "loss",
                     "unfortunate", "sadly", "sorrow", "grief", "melancholy", "grim", "bleak"]
        angry_words = ["angry", "furious", "outrageous", "ridiculous", "absurd", "wrong", "terrible",
                       "frustrating", "infuriating", "annoying", "irritating", "unacceptable"]
        surprised_words = ["surprising", "wow", "incredible", "unbelievable", "shocking", "remarkable",
                          "astonishing", "amazingly", "unexpectedly", "stunningly", "extraordinarily",
                          "remarkably", "astounding", "mind-blowing"]
        thoughtful_words = ["consider", "think", "ponder", "reflect", "analyze", "examine", "contemplate",
                           "let me", "let's think", "imagine", "suppose", "what if", "perhaps", "maybe"]
        confident_words = ["certainly", "absolutely", "definitely", "clearly", "obviously", "undoubtedly",
                          "indeed", "surely", "without doubt", "unquestionably", "precisely", "exactly",
                          "of course", "naturally"]
        
        # Count emotion indicators with partial matching
        scores = {
            "happy": sum(2 if w in text_lower else 0 for w in happy_words),
            "sad": sum(2 if w in text_lower else 0 for w in sad_words),
            "angry": sum(2 if w in text_lower else 0 for w in angry_words),
            "surprised": sum(2 if w in text_lower else 0 for w in surprised_words),
            "thoughtful": sum(2 if w in text_lower else 0 for w in thoughtful_words),
            "confident": sum(2 if w in text_lower else 0 for w in confident_words),
        }
        
        # Check for questions (thoughtful)
        if "?" in text:
            scores["thoughtful"] += 3
        
        # Check for exclamations (excited/surprised)
        exclamation_count = text.count("!")
        if exclamation_count > 0:
            scores["surprised"] += exclamation_count * 2
            scores["happy"] += exclamation_count
        
        # Check for capitalization (emphasis = emotion)
        if any(word.isupper() and len(word) > 2 for word in text.split()):
            scores["surprised"] += 2
            scores["confident"] += 1
        
        # Return dominant emotion or neutral
        max_emotion = max(scores.items(), key=lambda x: x[1])
        detected = max_emotion[0] if max_emotion[1] > 1 else "neutral"
        
        logger.info(f"Emotion scores: {scores} -> {detected}")
        return detected

    def detect_emotions_per_sentence(self, text: str) -> list:
        """Detect emotions for each sentence in the text for dynamic expression changes."""
        import re
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [("neutral", 0.0, len(text))]
        
        emotions_timeline = []
        char_pos = 0
        
        for sentence in sentences:
            # Find sentence position in original text
            start_pos = text.find(sentence, char_pos)
            if start_pos == -1:
                start_pos = char_pos
            end_pos = start_pos + len(sentence)
            char_pos = end_pos
            
            # Detect emotion for this sentence
            emotion = self.detect_emotion(sentence)
            
            # Calculate duration based on sentence length (rough estimate)
            duration = len(sentence) / 15.0  # ~15 chars per second of speech
            
            emotions_timeline.append({
                "emotion": emotion,
                "start_char": start_pos,
                "end_char": end_pos,
                "duration": duration,
                "text": sentence
            })
        
        return emotions_timeline

    def estimate_phonemes(self, text: str, audio_duration: float) -> list:
        """Estimate simple phoneme sequence from text for lip sync."""
        words = text.split()
        if not words:
            return []
        time_per_word = audio_duration / len(words)
        phonemes = []
        t = 0.0
        vowel_map = {"a": "A", "e": "E", "i": "E", "o": "C", "u": "C"}
        consonant_map = {
            "b": "B", "p": "B", "m": "B",
            "f": "F", "v": "F",
            "t": "H", "d": "H", "n": "H", "l": "H", "s": "H",
            "k": "G", "g": "G",
            "th": "D",
        }
        for word in words:
            clean = word.lower().strip(".,!?;:'\"")
            if not clean:
                continue
            chars = list(clean)
            n = max(len(chars), 1)
            dt = time_per_word / n
            for ch in chars:
                if ch in vowel_map:
                    phonemes.append({"phoneme": vowel_map[ch], "start": t, "duration": dt})
                elif ch in consonant_map:
                    phonemes.append({"phoneme": consonant_map[ch], "start": t, "duration": dt})
                t += dt
            # Small pause between words
            phonemes.append({"phoneme": "X", "start": t, "duration": 0.02})
            t += 0.02
        return phonemes

# ---------------------------------------------------------------------------
# Audio playback using pyaudio (plays MP3 via pydub or raw PCM)
# ---------------------------------------------------------------------------
class AudioPlayer:
    """Play audio bytes through speakers."""

    @staticmethod
    def play_mp3(mp3_bytes: bytes) -> float:
        """Play MP3 audio and return duration in seconds."""
        try:
            from pydub import AudioSegment
            from pydub.playback import play
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            duration = len(audio) / 1000.0
            play(audio)
            return duration
        except ImportError:
            logger.error("pydub not installed. Install: pip install pydub")
            logger.error("Also need ffmpeg: https://ffmpeg.org/download.html")
            return 0.0

    @staticmethod
    def play_mp3_threaded(mp3_bytes: bytes, on_done=None) -> float:
        """Play MP3 in background thread. Returns estimated duration."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            duration = len(audio) / 1000.0

            def _play():
                try:
                    from pydub.playback import play
                    play(audio)
                except Exception as e:
                    logger.error(f"Playback error: {e}")
                finally:
                    if on_done:
                        on_done()

            t = threading.Thread(target=_play, daemon=True)
            t.start()
            return duration
        except ImportError:
            logger.error("pydub not installed")
            if on_done:
                on_done()
            return 0.0

    @staticmethod
    def play_mp3_interruptible(mp3_bytes: bytes, stop_flag: threading.Event, on_done=None) -> float:
        """Play MP3 in background thread with interrupt capability. Returns estimated duration."""
        try:
            from pydub import AudioSegment
            import pyaudio
            
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            duration = len(audio) / 1000.0

            def _play():
                try:
                    # Convert to raw audio
                    raw_data = audio.raw_data
                    sample_rate = audio.frame_rate
                    channels = audio.channels
                    sample_width = audio.sample_width
                    
                    # Open audio stream
                    p = pyaudio.PyAudio()
                    stream = p.open(
                        format=p.get_format_from_width(sample_width),
                        channels=channels,
                        rate=sample_rate,
                        output=True
                    )
                    
                    # Play in chunks so we can check stop flag
                    chunk_size = 1024 * sample_width * channels
                    for i in range(0, len(raw_data), chunk_size):
                        if stop_flag.is_set():
                            logger.info("Playback interrupted")
                            break
                        chunk = raw_data[i:i + chunk_size]
                        stream.write(chunk)
                    
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    
                except Exception as e:
                    logger.error(f"Playback error: {e}")
                finally:
                    if on_done:
                        on_done()

            t = threading.Thread(target=_play, daemon=True)
            t.start()
            return duration
        except ImportError:
            logger.error("pydub or pyaudio not installed")
            if on_done:
                on_done()
            return 0.0

# ---------------------------------------------------------------------------
# Main Application GUI
# ---------------------------------------------------------------------------
class ChatbotApp:
    """All-in-one persuasive chatbot with avatar, voice, and debate."""

    def __init__(self):
        self.config = load_config()
        self.recorder = AudioRecorder()
        self.whisper = WhisperSTT(self.config["openai_api_key"])
        self.llm = ChatLLM(self.config["openai_api_key"], self.config["position"])
        self.debate_engine = DebateEngine(position=self.config["position"])
        self.tts = ElevenLabsTTS(self.config["elevenlabs_api_key"], self.config["voice_id"])
        
        # Error handling with retry logic
        self.error_handler = APIRetryHandler(max_retries=4, base_delay=1.0)

        # Avatar
        self.avatar_renderer = AvatarRenderer()
        self.avatar_initialized = False

        # Animation state
        self.current_phoneme = "silence"
        self.target_phoneme = "silence"
        self.transition_progress = 1.0
        self.blink_timer = 0.0
        self.is_blinking = False
        self.blink_duration = 0.0
        self.idle_timer = 0.0
        self.phoneme_queue: queue.Queue = queue.Queue()
        self.is_speaking = False
        
        # Emotion state with smooth transitions
        self.current_emotion = "neutral"
        self.target_emotion = "neutral"
        self.emotion_intensity = 0.0
        self.target_emotion_intensity = 0.0
        self.emotion_transition_speed = 0.8  # How fast emotions fade in/out
        
        # Idle animations
        self.look_around_timer = 0.0
        self.look_direction = 0.0
        self.target_look_direction = 0.0
        self.breathing_timer = 0.0
        self.next_look_time = np.random.uniform(3.0, 8.0)  # Random look around timing

        # Pipeline state
        self.is_recording = False
        self.is_processing = False
        self.playback_thread: Optional[threading.Thread] = None
        self.stop_playback_flag = threading.Event()

        # GUI
        self.root: Optional[tk.Tk] = None
        self._photo_image = None

    def run(self):
        """Launch the application."""
        self._init_avatar()
        self._build_gui()
        self._start_avatar_loop()
        self.root.mainloop()

    def _init_avatar(self):
        """Initialize the avatar renderer."""
        logger.info("Initializing avatar renderer...")
        hw = HardwareDetector.detect_hardware()
        result = self.avatar_renderer.initialize(use_gpu=hw.gpu_available)
        if result.success:
            self.avatar_initialized = True
            logger.info(f"Avatar ready: {result.rendering_mode} mode, {result.target_fps} FPS")
        else:
            logger.warning(f"Avatar failed: {result.error_message}")
            logger.warning("Running without avatar animation")

    def _build_gui(self):
        """Build the tkinter GUI."""
        self.root = tk.Tk()
        self.root.title("Persuasive Chatbot")
        self.root.configure(bg="#1a1a2e")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Top frame: avatar + controls
        top_frame = tk.Frame(self.root, bg="#1a1a2e")
        top_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Avatar frame (left)
        avatar_frame = tk.Frame(top_frame, bg="#16213e", relief=tk.RIDGE, bd=2)
        avatar_frame.pack(side=tk.LEFT, padx=(0, 10))

        self.avatar_label = tk.Label(avatar_frame, bg="#16213e")
        self.avatar_label.pack(padx=4, pady=4)

        # Right side: title + status + controls
        right_frame = tk.Frame(top_frame, bg="#1a1a2e")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Title
        pos_display = "Post-Human" if self.config["position"] == "post-human" else "Humanist"
        tk.Label(
            right_frame, text="Persuasive Chatbot",
            font=("Segoe UI", 20, "bold"), bg="#1a1a2e", fg="#e0e0e0"
        ).pack(anchor=tk.W)
        tk.Label(
            right_frame, text=f"Position: {pos_display}",
            font=("Segoe UI", 11), bg="#1a1a2e", fg="#888"
        ).pack(anchor=tk.W)

        # Status label
        self.status_label = tk.Label(
            right_frame, text="Ready — click the microphone to speak",
            font=("Segoe UI", 10), bg="#1a1a2e", fg="#4ecca3"
        )
        self.status_label.pack(anchor=tk.W, pady=(10, 5))

        # Phoneme display
        self.phoneme_label = tk.Label(
            right_frame, text="",
            font=("Consolas", 9), bg="#1a1a2e", fg="#666"
        )
        self.phoneme_label.pack(anchor=tk.W)

        # Mic button
        btn_frame = tk.Frame(right_frame, bg="#1a1a2e")
        btn_frame.pack(anchor=tk.W, pady=(15, 0))

        self.mic_btn = tk.Button(
            btn_frame, text="🎤  Hold to Speak",
            font=("Segoe UI", 13, "bold"),
            bg="#e94560", fg="white", activebackground="#c0392b",
            relief=tk.FLAT, padx=20, pady=10, cursor="hand2",
        )
        self.mic_btn.pack(side=tk.LEFT)
        self.mic_btn.bind("<ButtonPress-1>", self._on_mic_press)
        self.mic_btn.bind("<ButtonRelease-1>", self._on_mic_release)

        # Reset button
        self.reset_btn = tk.Button(
            btn_frame, text="Reset",
            font=("Segoe UI", 10), bg="#333", fg="#aaa",
            relief=tk.FLAT, padx=10, pady=8, cursor="hand2",
            command=self._on_reset,
        )
        self.reset_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Transcript area (bottom)
        transcript_frame = tk.Frame(self.root, bg="#16213e", relief=tk.RIDGE, bd=2)
        transcript_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        tk.Label(
            transcript_frame, text="Conversation",
            font=("Segoe UI", 11, "bold"), bg="#16213e", fg="#ccc"
        ).pack(anchor=tk.W, padx=8, pady=(6, 2))

        self.transcript = scrolledtext.ScrolledText(
            transcript_frame, wrap=tk.WORD, font=("Segoe UI", 10),
            bg="#0f3460", fg="#e0e0e0", insertbackground="#e0e0e0",
            relief=tk.FLAT, state=tk.DISABLED, height=12,
        )
        self.transcript.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # Configure text tags for styling
        self.transcript.tag_configure("user", foreground="#4ecca3", font=("Segoe UI", 10, "bold"))
        self.transcript.tag_configure("bot", foreground="#e94560", font=("Segoe UI", 10, "bold"))
        self.transcript.tag_configure("system", foreground="#888", font=("Segoe UI", 9, "italic"))

        # Add disclaimer
        self._append_transcript(
            "[System] This is an AI debate system. The chatbot argues from a "
            f"'{pos_display}' position. Its arguments are generated, not genuine beliefs.\n",
            "system"
        )

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------
    def _on_mic_press(self, event=None):
        """Start recording when mic button is pressed."""
        if self.is_processing:
            return
        
        # If currently speaking, interrupt it
        if self.is_speaking:
            logger.info("Interrupting current speech...")
            self._interrupt_speech()
        
        try:
            self.is_recording = True
            self.mic_btn.configure(bg="#27ae60", text="🎤  Recording...")
            self.status_label.configure(text="Listening... release to stop", fg="#3498db")
            self.recorder.start()
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.status_label.configure(text=f"Mic error: {e}", fg="#e74c3c")
            self.is_recording = False
            self.mic_btn.configure(bg="#e94560", text="🎤  Hold to Speak")

    def _on_mic_release(self, event=None):
        """Stop recording and process audio."""
        if not self.is_recording:
            return
        self.is_recording = False
        self.mic_btn.configure(bg="#e94560", text="🎤  Hold to Speak", state=tk.DISABLED)
        self.status_label.configure(text="Processing...", fg="#f39c12")

        # Process in background thread
        threading.Thread(target=self._process_pipeline, daemon=True).start()

    def _on_reset(self):
        """Reset conversation."""
        self.llm.history.clear()
        self.transcript.configure(state=tk.NORMAL)
        self.transcript.delete("1.0", tk.END)
        self.transcript.configure(state=tk.DISABLED)
        self._append_transcript("[System] Conversation reset.\n", "system")
        self.status_label.configure(text="Ready — click the microphone to speak", fg="#4ecca3")

    def _on_close(self):
        """Clean up and close."""
        self.is_speaking = False
        if self.avatar_initialized:
            self.avatar_renderer.shutdown()
        self.root.destroy()

    def _interrupt_speech(self):
        """Interrupt current speech playback."""
        self.stop_playback_flag.set()
        self.is_speaking = False
        self.target_emotion = "neutral"
        self.target_emotion_intensity = 0.0
        # Clear phoneme queue
        while not self.phoneme_queue.empty():
            try:
                self.phoneme_queue.get_nowait()
            except queue.Empty:
                break
        self._queue_phoneme("silence")
        logger.info("Speech interrupted")

    def _play_audio_interruptible(self, mp3_bytes: bytes, on_done=None) -> float:
        """Play audio with interrupt capability."""
        return AudioPlayer.play_mp3_interruptible(mp3_bytes, self.stop_playback_flag, on_done)

    def _call_llm_with_prompt(self, prompt: str) -> str:
        """Send a debate prompt to the OpenAI API and return the reply text."""
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config['openai_api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4",
                "messages": [{"role": "system", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.7,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    # -----------------------------------------------------------------------
    # Pipeline: Record → Whisper → GPT-4 → ElevenLabs → Play + Animate
    # -----------------------------------------------------------------------
    def _process_pipeline(self):
        """Full conversation pipeline (runs in background thread)."""
        try:
            self.is_processing = True

            # 1. Stop recording and get audio
            wav_bytes = self.recorder.stop()
            self._set_status("Transcribing speech...", "#f39c12")

            # 2. Transcribe with Whisper (with retry logic)
            try:
                user_text = self.error_handler.call_with_retry(
                    self.whisper.transcribe,
                    wav_bytes
                )
            except RetryExhaustedError as e:
                error_msg = self.error_handler.translate_error(e.__cause__ if e.__cause__ else e)
                self._set_status(error_msg, "#e74c3c")
                logger.error(f"Whisper transcription failed after retries: {e}")
                self._enable_mic()
                return
            
            if not user_text:
                self._set_status("No speech detected. Try again.", "#e74c3c")
                self._enable_mic()
                return

            logger.info(f"User: {user_text}")
            self._append_transcript(f"You: {user_text}\n", "user")
            self._set_status("Generating response...", "#f39c12")

            # 3. Generate LLM response (with retry logic)
            try:
                prompt = self.debate_engine.build_debate_prompt(user_text)
                reply = self.error_handler.call_with_retry(
                    self._call_llm_with_prompt,
                    prompt
                )
                self.debate_engine.log_reply(user_text, reply)
            except Exception:
                logger.warning("Debate engine failed, falling back to simple prompt")
                reply = self.error_handler.call_with_retry(
                    self.llm.generate,
                    user_text
                )
            
            logger.info(f"Bot: {reply}")
            self._append_transcript(f"Bot: {reply}\n", "bot")
            self._set_status("Synthesizing speech...", "#f39c12")

            # 4. Synthesize speech with ElevenLabs (with retry logic)
            try:
                mp3_bytes = self.error_handler.call_with_retry(
                    self.tts.synthesize,
                    reply
                )
            except RetryExhaustedError as e:
                error_msg = self.error_handler.translate_error(e.__cause__ if e.__cause__ else e)
                self._set_status(error_msg, "#e74c3c")
                logger.error(f"TTS synthesis failed after retries: {e}")
                self._enable_mic()
                return

            # 5. Detect emotions per sentence for dynamic expression changes
            emotions_timeline = self.tts.detect_emotions_per_sentence(reply)
            logger.info(f"Emotions timeline: {[(e['emotion'], e['duration']) for e in emotions_timeline]}")

            # 6. Play audio + animate avatar
            self._set_status("Speaking...", "#2ecc71")
            self.is_speaking = True

            # Get actual audio duration for accurate lip sync
            actual_duration = self.tts.get_audio_duration(mp3_bytes)
            phonemes = self.tts.estimate_phonemes(reply, actual_duration)
            logger.info(f"Audio duration: {actual_duration:.2f}s, phonemes: {len(phonemes)}")

            # Queue phonemes for avatar animation
            self._queue_phonemes(phonemes)
            
            # Queue emotions with timing
            self._queue_emotions(emotions_timeline)

            # Queue phonemes for avatar animation
            self._queue_phonemes(phonemes)

            # Play audio (blocking in this thread)
            self.stop_playback_flag.clear()
            
            def on_playback_done():
                if not self.stop_playback_flag.is_set():
                    self.is_speaking = False
                    # Fade to neutral
                    self.target_emotion = "neutral"
                    self.target_emotion_intensity = 0.0
                    # Return to idle after a short delay
                    self.root.after(300, lambda: self._queue_phoneme("silence"))

            duration = self._play_audio_interruptible(mp3_bytes, on_done=on_playback_done)

            # Wait for playback to finish or be interrupted
            start_time = time.time()
            while self.is_speaking and not self.stop_playback_flag.is_set():
                elapsed = time.time() - start_time
                if elapsed >= actual_duration:
                    break
                time.sleep(0.1)

            self._set_status("Ready — click the microphone to speak", "#4ecca3")

        except RetryExhaustedError as e:
            # Already handled above, but catch here in case of unexpected retry exhaustion
            error_msg = self.error_handler.translate_error(e.__cause__ if e.__cause__ else e)
            self._set_status(error_msg, "#e74c3c")
            logger.error(f"Retry exhausted: {e}")
        except Exception as e:
            # Translate any other errors to user-friendly messages
            error_msg = self.error_handler.translate_error(e)
            self._set_status(error_msg, "#e74c3c")
            logger.exception(f"Pipeline error: {e}")
        finally:
            self.is_processing = False
            self.is_speaking = False
            self._enable_mic()

    # -----------------------------------------------------------------------
    # Avatar animation loop
    # -----------------------------------------------------------------------
    def _start_avatar_loop(self):
        """Start the 30fps avatar update loop."""
        if self.avatar_initialized:
            self._update_avatar()

    def _update_avatar(self):
        """Called every ~33ms to render and display avatar frame."""
        if not self.avatar_initialized:
            return

        dt = 1.0 / 30.0

        # Drain phoneme queue
        new_ph = None
        while not self.phoneme_queue.empty():
            try:
                new_ph = self.phoneme_queue.get_nowait()
            except queue.Empty:
                break

        if new_ph and new_ph != self.target_phoneme:
            self.current_phoneme = self.target_phoneme
            self.target_phoneme = new_ph
            self.transition_progress = 0.0

        # Advance transition
        if self.transition_progress < 1.0:
            self.transition_progress = min(1.0, self.transition_progress + 0.18)

        # Smooth emotion transitions
        if self.current_emotion != self.target_emotion:
            # Fade out current emotion first
            if self.emotion_intensity > 0.0:
                self.emotion_intensity = max(0.0, self.emotion_intensity - dt * self.emotion_transition_speed)
            else:
                # Switch to target emotion and fade in
                self.current_emotion = self.target_emotion
                self.emotion_intensity = 0.0
        
        # Fade towards target intensity
        if abs(self.emotion_intensity - self.target_emotion_intensity) > 0.01:
            if self.emotion_intensity < self.target_emotion_intensity:
                self.emotion_intensity = min(self.target_emotion_intensity, 
                                            self.emotion_intensity + dt * self.emotion_transition_speed)
            else:
                self.emotion_intensity = max(self.target_emotion_intensity,
                                            self.emotion_intensity - dt * self.emotion_transition_speed)

        # Blinking (more natural timing)
        self.blink_timer += dt
        blink_interval = np.random.uniform(2.5, 5.0) if not self.is_blinking else 0.15
        if not self.is_blinking and self.blink_timer > blink_interval:
            self.is_blinking = True
            self.blink_duration = 0.0
            self.blink_timer = 0.0
        if self.is_blinking:
            self.blink_duration += dt
            if self.blink_duration > 0.15:
                self.is_blinking = False

        # Idle animations - looking around
        self.look_around_timer += dt
        if self.look_around_timer > self.next_look_time and not self.is_speaking:
            # Pick a new look direction
            self.target_look_direction = np.random.uniform(-0.15, 0.15)
            self.next_look_time = np.random.uniform(3.0, 8.0)
            self.look_around_timer = 0.0
        
        # Smooth look transition
        if abs(self.look_direction - self.target_look_direction) > 0.01:
            look_speed = 0.5 * dt
            if self.look_direction < self.target_look_direction:
                self.look_direction = min(self.target_look_direction, self.look_direction + look_speed)
            else:
                self.look_direction = max(self.target_look_direction, self.look_direction - look_speed)
        
        # Breathing animation
        self.breathing_timer += dt

        # Idle sway
        self.idle_timer += dt

        # Render frame
        self._render_avatar_frame()

        # Update phoneme display
        ph_display = self.target_phoneme
        if self.transition_progress < 1.0:
            ph_display = f"{self.current_phoneme} → {self.target_phoneme}"
        blink_str = " 👁" if self.is_blinking else ""
        
        # Show emotion with intensity
        if self.current_emotion != "neutral" and self.emotion_intensity > 0.1:
            emotion_str = f" | {self.current_emotion.title()} ({self.emotion_intensity:.1f})"
        elif self.target_emotion != "neutral":
            emotion_str = f" | → {self.target_emotion.title()}"
        else:
            emotion_str = ""
        
        self.phoneme_label.configure(text=f"Mouth: {ph_display}{blink_str}{emotion_str}")

        # Schedule next frame
        self.root.after(33, self._update_avatar)

    def _render_avatar_frame(self):
        """Render current avatar frame with interpolation, blink, idle, and emotions."""
        try:
            import torch
            from PIL import Image, ImageTk

            if self.avatar_renderer.model is None or self.avatar_renderer.character_image is None:
                return

            # Interpolate pose
            cur = self.avatar_renderer._phoneme_to_pose(self.current_phoneme, 1.0)
            tgt = self.avatar_renderer._phoneme_to_pose(self.target_phoneme, 1.0)
            t = self.transition_progress
            t_smooth = t * t * (3.0 - 2.0 * t)
            pose = [cur[i] * (1 - t_smooth) + tgt[i] * t_smooth for i in range(len(cur))]

            # Apply emotional expressions
            # tha3 model has 45 parameters:
            # 0-11: Eyebrows (0-5 left, 6-11 right)
            # 12-23: Eyes (12-17 left, 18-23 right)
            # 24-25: Iris size
            # 26-36: Mouth (aaa, iii, uuu, eee, ooo, delta, lowered_corner_left, lowered_corner_right, raised_corner_left, raised_corner_right, smirk)
            # 37-38: Iris rotation
            # 39-41: Head rotation (head_x, head_y, neck_z)
            # 42-43: Body rotation
            # 44: Breathing
            
            if self.emotion_intensity > 0.1:
                intensity = self.emotion_intensity
                
                if self.current_emotion == "happy":
                    # Smile + eyebrow raise + slight head tilt
                    pose[34] = min(1.0, pose[34] + 0.5 * intensity)  # raised_corner_left
                    pose[35] = min(1.0, pose[35] + 0.5 * intensity)  # raised_corner_right
                    pose[0] = min(1.0, pose[0] + 0.3 * intensity)    # left eyebrow up
                    pose[6] = min(1.0, pose[6] + 0.3 * intensity)    # right eyebrow up
                    pose[41] += 0.05 * intensity * np.sin(self.idle_timer * 2.0)  # neck tilt
                
                elif self.current_emotion == "sad":
                    # Frown + eyebrow down + head down
                    pose[32] = min(1.0, pose[32] + 0.3 * intensity)  # lowered_corner_left
                    pose[33] = min(1.0, pose[33] + 0.3 * intensity)  # lowered_corner_right
                    pose[3] = min(1.0, pose[3] + 0.2 * intensity)    # left eyebrow down
                    pose[9] = min(1.0, pose[9] + 0.2 * intensity)    # right eyebrow down
                    pose[39] = max(-1.0, pose[39] - 0.1 * intensity) # head down
                
                elif self.current_emotion == "angry":
                    # Frown + eyebrow furrow + tense
                    pose[32] = min(1.0, pose[32] + 0.4 * intensity)  # lowered_corner_left
                    pose[33] = min(1.0, pose[33] + 0.4 * intensity)  # lowered_corner_right
                    pose[1] = min(1.0, pose[1] + 0.4 * intensity)    # left eyebrow furrow
                    pose[7] = min(1.0, pose[7] + 0.4 * intensity)    # right eyebrow furrow
                
                elif self.current_emotion == "surprised":
                    # Wide eyes + mouth open + eyebrow raise
                    pose[12] = min(1.0, pose[12] + 0.4 * intensity)  # left eye open
                    pose[18] = min(1.0, pose[18] + 0.4 * intensity)  # right eye open
                    pose[0] = min(1.0, pose[0] + 0.5 * intensity)    # left eyebrow up
                    pose[6] = min(1.0, pose[6] + 0.5 * intensity)    # right eyebrow up
                    pose[26] = min(1.0, pose[26] + 0.2 * intensity)  # mouth open
                
                elif self.current_emotion == "thoughtful":
                    # Slight head tilt + look away
                    pose[41] += 0.1 * intensity * np.sin(self.idle_timer * 0.8)  # neck tilt
                    pose[40] += 0.08 * intensity  # head turn
                
                elif self.current_emotion == "confident":
                    # Slight smile + head up
                    pose[34] = min(1.0, pose[34] + 0.25 * intensity)  # raised_corner_left
                    pose[35] = min(1.0, pose[35] + 0.25 * intensity)  # raised_corner_right
                    pose[39] = min(1.0, pose[39] + 0.08 * intensity)  # head up

            # Blink
            if self.is_blinking:
                bp = self.blink_duration / 0.15
                eye_close = (bp * 2.0) if bp < 0.5 else ((1.0 - bp) * 2.0)
                # Close both eyes
                pose[14] = -eye_close * 0.9  # left eye close
                pose[20] = -eye_close * 0.9  # right eye close

            # Idle animations when not speaking or low emotion
            if not self.is_speaking or self.emotion_intensity < 0.3:
                # Subtle head sway
                sway_amount = 0.02
                pose[41] += np.sin(self.idle_timer * 0.5) * sway_amount  # neck sway
                
                # Looking around
                pose[40] += self.look_direction  # head turn (look left/right)
                pose[39] += np.sin(self.idle_timer * 0.3) * 0.01  # slight head bob
                
                # Breathing
                breathing = np.sin(self.breathing_timer * 0.8) * 0.15
                if len(pose) > 44:
                    pose[44] = breathing  # breathing parameter
            else:
                # More animated when speaking with emotion
                pose[41] += np.sin(self.idle_timer * 1.2) * 0.015  # slight sway

            # Render
            pose_tensor = torch.tensor(
                [pose], dtype=self.avatar_renderer.model.get_dtype()
            ).to(self.avatar_renderer.device)

            img_in = self.avatar_renderer.character_image
            if img_in.dim() == 3:
                img_in = img_in.unsqueeze(0)

            with torch.no_grad():
                output = self.avatar_renderer.model.pose(img_in, pose_tensor)

            frame_np = output[0].cpu().numpy()
            frame_np = np.transpose(frame_np, (1, 2, 0))
            frame_np = np.clip(frame_np, 0.0, 1.0)

            if frame_np.shape[2] == 4:
                rgb = frame_np[:, :, :3]
                alpha = frame_np[:, :, 3:4]
                bg = np.ones_like(rgb)
                frame_np = rgb * alpha + bg * (1.0 - alpha)

            frame_uint8 = (frame_np * 255).astype(np.uint8)
            pil_img = Image.fromarray(frame_uint8)
            self._photo_image = ImageTk.PhotoImage(pil_img)
            self.avatar_label.configure(image=self._photo_image)

        except Exception as e:
            logger.error(f"Avatar render error: {e}")

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def _queue_phoneme(self, phoneme: str):
        try:
            self.phoneme_queue.put_nowait(phoneme)
        except queue.Full:
            pass

    def _queue_phonemes(self, phonemes: list):
        """Queue phonemes with timing for lip sync during playback."""
        def _feeder():
            for p in phonemes:
                ph = p.get("phoneme", "X") if isinstance(p, dict) else str(p)
                dur = p.get("duration", 0.05) if isinstance(p, dict) else 0.05
                self._queue_phoneme(ph)
                time.sleep(dur)
            self._queue_phoneme("silence")

        threading.Thread(target=_feeder, daemon=True).start()

    def _queue_emotions(self, emotions_timeline: list):
        """Queue emotions with timing for dynamic expression changes during speech."""
        def _emotion_feeder():
            for emotion_data in emotions_timeline:
                emotion = emotion_data["emotion"]
                duration = emotion_data["duration"]
                
                # Fade in emotion
                self.target_emotion = emotion
                self.target_emotion_intensity = 1.0 if emotion != "neutral" else 0.0
                logger.info(f"Emotion transition: {emotion} for {duration:.1f}s")
                
                # Hold emotion for sentence duration
                time.sleep(duration)
            
            # Fade to neutral at end
            self.target_emotion = "neutral"
            self.target_emotion_intensity = 0.0

        threading.Thread(target=_emotion_feeder, daemon=True).start()

    def _set_status(self, text: str, color: str = "#4ecca3"):
        """Update status label (thread-safe)."""
        if self.root:
            self.root.after(0, lambda: self.status_label.configure(text=text, fg=color))

    def _enable_mic(self):
        """Re-enable mic button (thread-safe)."""
        if self.root:
            self.root.after(0, lambda: self.mic_btn.configure(state=tk.NORMAL))

    def _append_transcript(self, text: str, tag: str = ""):
        """Append text to transcript (thread-safe)."""
        def _do():
            self.transcript.configure(state=tk.NORMAL)
            if tag:
                self.transcript.insert(tk.END, text, tag)
            else:
                self.transcript.insert(tk.END, text)
            self.transcript.see(tk.END)
            self.transcript.configure(state=tk.DISABLED)

        if self.root:
            self.root.after(0, _do)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    print("=" * 50)
    print("  Persuasive Chatbot")
    print("=" * 50)
    print()

    config = load_config()
    if not config["openai_api_key"]:
        print("ERROR: No OpenAI API key found.")
        print("Set it in frontend/.env as VITE_OPENAI_API_KEY=sk-...")
        sys.exit(1)
    if not config["elevenlabs_api_key"]:
        print("ERROR: No ElevenLabs API key found.")
        print("Set it in frontend/.env as VITE_ELEVENLABS_API_KEY=sk_...")
        sys.exit(1)

    # Check dependencies
    missing = []
    try:
        import pyaudio
    except ImportError:
        missing.append("pyaudio")
    try:
        from pydub import AudioSegment
    except ImportError:
        missing.append("pydub")
    try:
        from PIL import Image, ImageTk
    except ImportError:
        missing.append("Pillow")

    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        if "pyaudio" in missing:
            print("\nFor pyaudio on Windows: pip install pyaudio")
            print("If that fails: pip install pipwin && pipwin install pyaudio")
        sys.exit(1)

    app = ChatbotApp()
    app.run()


if __name__ == "__main__":
    main()
