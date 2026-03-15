# Persuasive Chatbot

A speech-to-speech debate application that combines real-time conversational AI with animated avatar rendering. The chatbot engages users in philosophical debates about machine intelligence versus human capacities, maintaining a consistent argumentative position (either post-human or humanist).

## Architecture

The system consists of three main components:

1. **Python Backend** (`backend/`): Avatar rendering using talking-head-anime-3 with GPU acceleration
2. **Electron GUI** (`frontend/`): Cross-platform React-based user interface
3. **API Integration**: External services (Whisper STT, ElevenLabs TTS, LLM)

## Features

- 🎤 Speech-to-speech interaction with natural conversation flow
- 🎭 Animated avatar with lip-sync synchronized to speech
- 🧠 LLM-powered persuasive argumentation
- ⚡ GPU acceleration (CUDA on Windows) with CPU fallback
- 🖥️ Cross-platform support (Windows 10/11, macOS)
- 🎨 Professional UI with smooth animations
- 🔄 Streaming pipeline for low-latency responses (2-3s target)

## Quick Start

### Prerequisites

- **Python 3.12** (required for CUDA support)
- **Node.js 18+**
- **CUDA 12.1+** (optional, for GPU acceleration - highly recommended for RTX GPUs)

### Backend Setup

#### Option 1: With CUDA (Recommended for NVIDIA GPUs)

If you have an NVIDIA GPU (RTX 2060 or newer):

```powershell
cd backend
# Run automated setup (installs Python 3.12 + PyTorch with CUDA)
.\setup_cuda.bat

# Verify CUDA is working
.\venv_cuda\Scripts\python.exe check_cuda.py
```

You should see:
```
PyTorch: 2.5.1+cu121
CUDA available: True
GPU: NVIDIA GeForce RTX 3080 Laptop GPU
```

#### Option 2: CPU Only

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Note**: CPU rendering will be slower (10-15 FPS vs 30+ FPS on GPU)

### Frontend Setup

```bash
cd frontend
npm install
```

### Configuration

1. Copy `.env.example` to `.env` in both `backend/` and `frontend/` directories
2. Configure API keys:
   - Whisper API (OpenAI)
   - ElevenLabs API
   - LLM API (OpenAI GPT-4, Anthropic Claude, or compatible)
3. Set the chatbot's philosophical position (post-human or humanist)

### Running

#### With CUDA:
```powershell
# Terminal 1: Start Python backend with GPU
cd backend
.\venv_cuda\Scripts\activate
python src/main.py

# Terminal 2: Start Electron GUI
cd frontend
npm run dev
```

#### CPU Only:
```bash
# Terminal 1: Start Python backend
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python src/main.py

# Terminal 2: Start Electron GUI
cd frontend
npm run dev
```

### Performance

| Mode | FPS | Model | Init Time | Quality |
|------|-----|-------|-----------|---------|
| GPU (CUDA) | 30+ | standard_float | 0.8s | Excellent |
| CPU | 10-15 | separable_float | 5s | Good |

**GPU Requirements**: NVIDIA GPU with 4GB+ VRAM (tested on RTX 3080)

## Development

### Code Quality

```bash
# Backend
cd backend
black .                    # Format Python code
mypy src/                  # Type checking
pylint src/                # Linting

# Frontend
cd frontend
npm run format             # Format TypeScript/React code
npm run lint               # Linting
npm run type-check         # Type checking
```

### Testing

```bash
# Backend
cd backend
pytest                     # Run all tests
pytest -v                  # Verbose output
pytest -k property         # Run only property tests

# Frontend
cd frontend
npm test                   # Run all tests
npm run test:watch         # Watch mode
```

## Building

```bash
cd frontend

# Build for Windows
npm run build:win

# Build for macOS
npm run build:mac
```

## Project Structure

```
persuasive-chatbot/
├── backend/              # Python backend
│   ├── src/             # Source code
│   ├── tests/           # Tests
│   ├── pyproject.toml   # Python project config
│   └── requirements.txt # Python dependencies
├── frontend/            # Electron/React GUI
│   ├── electron/        # Electron main process
│   ├── src/            # React source code
│   ├── package.json    # Node.js dependencies
│   └── tsconfig.json   # TypeScript config
└── .kiro/              # Kiro specs
    └── specs/
        └── persuasive-chatbot/
```

## Technology Stack

### Backend
- Python 3.9+
- PyTorch (with CUDA support)
- talking-head-anime-3 (avatar rendering)
- hypothesis (property-based testing)

### Frontend
- Electron (desktop framework)
- React 18 (UI library)
- TypeScript (type safety)
- Tailwind CSS (styling)
- Framer Motion (animations)
- Zustand (state management)
- fast-check (property-based testing)

### External APIs
- OpenAI Whisper (speech-to-text)
- ElevenLabs (text-to-speech)
- LLM API (OpenAI GPT-4, Anthropic Claude, or compatible)

## Performance Targets

- End-to-end response time: 2-3 seconds
- Avatar rendering: 30+ FPS (GPU), 24+ FPS (CPU)
- Initialization time: <10 seconds
- Session duration: 30+ minutes stable operation

## License

MIT
