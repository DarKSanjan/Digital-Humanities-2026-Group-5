# Python Backend

Avatar rendering service using talking-head-anime-3 with GPU acceleration.

## Features

- Avatar rendering with talking-head-anime-3
- GPU acceleration via CUDA (Windows)
- CPU fallback for cross-platform compatibility
- IPC communication with Electron GUI
- Lip sync with phoneme-to-viseme mapping
- Parallel audio-visual processing

## Requirements

- Python 3.9 or higher
- CUDA 11.8+ (optional, for GPU acceleration on Windows)
- 8GB+ RAM (16GB recommended)
- 8GB+ VRAM for GPU mode (RTX 3080 or equivalent)

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Download talking-head-anime-3 Model

The talking-head-anime-3 model is required for avatar rendering:

1. Visit: https://github.com/pkhungurn/talking-head-anime-3-demo
2. Follow the repository instructions to download the pre-trained model
3. Place model files in the `models/` directory

### 4. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
- `USE_GPU=true` - Enable GPU acceleration (requires CUDA)
- `TARGET_FPS=30` - Target frame rate for GPU mode
- `FALLBACK_FPS=24` - Fallback frame rate for CPU mode
- `AVATAR_MODEL_PATH=models/talking-head-anime-3` - Path to model files

## Running

```bash
python src/main.py
```

The backend will:
1. Detect hardware capabilities (GPU/CPU)
2. Initialize the avatar renderer
3. Start the IPC server for communication with the GUI
4. Wait for rendering requests

## Development

### Code Quality

```bash
# Format code
black .

# Type checking
mypy src/

# Linting
pylint src/
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_ipc_server.py

# Run property tests only
pytest tests/property/

# Verbose output
pytest -v
```

### Project Structure

```
backend/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── ipc_server.py           # JSON-RPC IPC server
│   ├── hardware_detection.py   # GPU/CPU detection
│   ├── path_utils.py           # Cross-platform path handling
│   ├── avatar_renderer.py      # Avatar rendering with talking-head-anime-3
│   ├── lip_sync_controller.py  # Phoneme-to-viseme mapping
│   └── stream_coordinator.py   # Parallel audio-visual processing
├── tests/
│   ├── unit/                   # Unit tests
│   └── property/               # Property-based tests
├── models/                     # Model files (not in git)
├── logs/                       # Log files (not in git)
├── pyproject.toml             # Project configuration
└── requirements.txt           # Dependencies
```

## Hardware Detection

The backend automatically detects available hardware:

- **GPU Available**: Uses CUDA acceleration, targets 30+ FPS
- **GPU Unavailable**: Falls back to CPU rendering, targets 24+ FPS

Check GPU availability:
```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## Troubleshooting

### GPU Not Detected

1. Verify CUDA installation:
   ```bash
   nvidia-smi
   ```

2. Check PyTorch CUDA support:
   ```bash
   python -c "import torch; print(f'CUDA version: {torch.version.cuda}')"
   ```

3. Reinstall PyTorch with CUDA support:
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

### Model Loading Errors

- Ensure model files are in `models/` directory
- Check `AVATAR_MODEL_PATH` in `.env`
- Verify model files are not corrupted

### Memory Issues

- Reduce `TARGET_FPS` in `.env`
- Close other GPU-intensive applications
- Use CPU mode if VRAM is insufficient

## Performance

### Targets

- **Initialization**: <3 seconds for avatar renderer
- **Frame Rate**: 30+ FPS (GPU), 24+ FPS (CPU)
- **VRAM Usage**: <6GB (of 8GB available)
- **Latency**: <100ms per frame

### Monitoring

Enable debug logging to monitor performance:

```bash
export LOG_LEVEL=DEBUG  # Windows: set LOG_LEVEL=DEBUG
python src/main.py
```

## API Reference

### IPC Protocol

The backend communicates with the GUI via JSON-RPC over stdin/stdout.

**Message Format:**
```json
{
  "jsonrpc": "2.0",
  "method": "render_speech",
  "params": {
    "audio_data": "base64_encoded_audio",
    "phonemes": [
      {"phoneme": "AH", "start": 0.0, "duration": 0.1}
    ]
  },
  "id": 1
}
```

**Response Format:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "frames": ["base64_encoded_frame_1", "base64_encoded_frame_2"],
    "fps": 30.5
  },
  "id": 1
}
```

### Available Methods

- `initialize`: Initialize avatar renderer
- `render_frame`: Render single frame for phoneme
- `render_sequence`: Render frame sequence for phoneme list
- `get_hardware_info`: Get hardware capabilities
- `shutdown`: Clean up resources

## License

MIT
