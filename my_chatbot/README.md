# Persuasive Chatbot

An AI-powered persuasive debate chatbot with real-time avatar rendering, speech-to-text, text-to-speech, and lip-sync capabilities.

## Overview

This chatbot engages users in persuasive debates using a streaming pipeline that connects:

- **Speech-to-Text (STT)** — captures mic input and transcribes it
- **LLM** — generates persuasive responses using debate strategies (argument classification, analogy/example banks, strategy engine)
- **Text-to-Speech (TTS)** — streams audio output with sentence chunking
- **Avatar** — GPU-accelerated talking-head rendering with lip sync

## Project Structure

```
my_chatbot/
├── backend/
│   ├── src/                  # Core application source
│   │   ├── main.py           # Entry point (GUI + backend init)
│   │   ├── app_controller.py # GUI ↔ pipeline wiring
│   │   ├── app_gui.py        # CustomTkinter UI
│   │   ├── streaming_pipeline.py  # LLM → TTS → audio → lip sync
│   │   ├── mic_recorder.py   # Microphone capture
│   │   ├── stt_service.py    # Speech-to-text
│   │   ├── llm_service.py    # LLM integration
│   │   ├── audio_player.py   # Audio playback
│   │   ├── sentence_chunker.py
│   │   └── debate/           # Debate engine modules
│   │       ├── classifier.py
│   │       ├── prompt_builder.py
│   │       ├── strategy_engine.py
│   │       ├── argument_bank.py
│   │       ├── analogy_bank.py
│   │       └── persona.py
│   ├── tests/                # Unit, integration & property-based tests
│   ├── requirements.txt
│   └── pyproject.toml
└── .gitignore
```

## Setup

### Prerequisites

- Python 3.9+
- CUDA-capable GPU (optional, falls back to CPU rendering)

### Installation

```bash
cd my_chatbot/backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust settings as needed.

### Running

```bash
python -m src.main
```

### Running Tests

```bash
pytest
```

## Tech Stack

- Python, PyTorch, CustomTkinter
- Hypothesis (property-based testing)
- WebSocket IPC for frontend-backend communication
