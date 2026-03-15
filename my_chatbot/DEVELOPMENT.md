# Development Guide

This guide provides detailed information for developers working on the Persuasive Chatbot project.

## Project Structure

```
persuasive-chatbot/
├── backend/                    # Python backend service
│   ├── src/                   # Source code
│   │   ├── __init__.py
│   │   ├── main.py           # Entry point
│   │   ├── ipc_server.py     # IPC communication (Task 2.1)
│   │   ├── hardware_detection.py  # GPU/CPU detection (Task 2.3)
│   │   ├── path_utils.py     # Cross-platform paths (Task 2.5)
│   │   ├── avatar_renderer.py     # Avatar rendering (Task 4)
│   │   ├── lip_sync_controller.py # Lip sync (Task 5)
│   │   └── stream_coordinator.py  # Parallel processing (Task 6)
│   ├── tests/                # Test files
│   │   ├── unit/            # Unit tests
│   │   └── property/        # Property-based tests
│   ├── pyproject.toml       # Python project config
│   ├── requirements.txt     # Dependencies
│   └── .env.example         # Environment template
│
├── frontend/                 # Electron/React GUI
│   ├── electron/            # Electron main process
│   │   ├── main.ts         # Main process
│   │   └── preload.ts      # Preload script
│   ├── src/
│   │   ├── components/     # React components (Task 9)
│   │   │   ├── AvatarDisplay.tsx
│   │   │   ├── MicrophoneButton.tsx
│   │   │   ├── StatusIndicator.tsx
│   │   │   ├── TranscriptPanel.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   └── LoadingState.tsx
│   │   ├── hooks/          # Custom hooks (Tasks 12-14)
│   │   │   ├── useAudioRecording.ts
│   │   │   ├── useAvatarStream.ts
│   │   │   ├── useConversation.ts
│   │   │   └── useSpeechSynthesis.ts
│   │   ├── services/       # API services (Tasks 12-14)
│   │   │   ├── ipcService.ts
│   │   │   ├── whisperService.ts
│   │   │   ├── elevenLabsService.ts
│   │   │   └── llmService.ts
│   │   ├── store/          # State management (Task 8.2)
│   │   │   └── conversationStore.ts
│   │   ├── test/           # Test utilities
│   │   ├── App.tsx         # Root component
│   │   ├── main.tsx        # Entry point
│   │   └── index.css       # Global styles
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   └── .env.example
│
└── .kiro/specs/persuasive-chatbot/  # Specification files
    ├── requirements.md
    ├── design.md
    └── tasks.md
```

## Development Workflow

### 1. Initial Setup

Run the setup script for your platform:

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

### 2. Configure Environment

Edit the `.env` files:

**backend/.env:**
- `USE_GPU`: Enable/disable GPU acceleration
- `TARGET_FPS`: Target frame rate for GPU mode
- `AVATAR_MODEL_PATH`: Path to talking-head-anime-3 model

**frontend/.env:**
- `VITE_WHISPER_API_KEY`: OpenAI Whisper API key
- `VITE_ELEVENLABS_API_KEY`: ElevenLabs TTS API key
- `VITE_LLM_API_KEY`: LLM API key
- `VITE_LLM_API_URL`: LLM API endpoint
- `VITE_LLM_MODEL`: Model name (e.g., gpt-4)
- `VITE_CHATBOT_POSITION`: post-human or humanist

### 3. Running in Development

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python src/main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 4. Code Quality

**Before committing, run:**

```bash
# Backend
cd backend
black .                    # Format code
mypy src/                  # Type check
pylint src/                # Lint

# Frontend
cd frontend
npm run format             # Format code
npm run lint               # Lint
npm run type-check         # Type check
```

### 5. Testing

**Backend:**
```bash
cd backend
pytest                     # All tests
pytest tests/unit/         # Unit tests only
pytest tests/property/     # Property tests only
pytest -v                  # Verbose
pytest -k "test_name"      # Specific test
```

**Frontend:**
```bash
cd frontend
npm test                   # All tests
npm run test:watch         # Watch mode
npm test -- --coverage     # With coverage
```

## Implementation Tasks

The project is implemented following the task list in `.kiro/specs/persuasive-chatbot/tasks.md`.

### Current Status

- [x] Task 1: Project structure and development environment ✅
- [ ] Task 2: Python backend core infrastructure
- [ ] Task 3: Checkpoint - Verify infrastructure
- [ ] Task 4: Avatar Renderer component
- [ ] Task 5: Lip Sync Controller component
- [ ] Task 6: Stream Coordinator component
- [ ] Task 7: Checkpoint - Verify Python backend
- [ ] Task 8: Electron GUI core infrastructure
- [ ] Task 9: GUI components
- [ ] Task 10: Visual design and styling
- [ ] Task 11: Checkpoint - Verify GUI foundation
- [ ] Task 12: Speech Input Processor (Whisper)
- [ ] Task 13: Conversation Engine (LLM)
- [ ] Task 14: Speech Output Generator (ElevenLabs)
- [ ] Task 15: Checkpoint - Verify API integrations
- [ ] Task 16: Streaming pipeline integration
- [ ] Task 17: Error handling and recovery
- [ ] Task 18: Resource monitoring and optimization
- [ ] Task 19: Checkpoint - Verify error handling
- [ ] Task 20: Ethical transparency features
- [ ] Task 21: Cross-platform packaging
- [ ] Task 22: Final integration testing
- [ ] Task 23: Final checkpoint

### Task Dependencies

```
Task 1 (Setup)
  ↓
Task 2 (Backend Infrastructure)
  ↓
Task 3 (Checkpoint)
  ↓
Tasks 4-6 (Backend Components) - Can be done in parallel
  ↓
Task 7 (Checkpoint)
  ↓
Tasks 8-10 (GUI Foundation) - Sequential
  ↓
Task 11 (Checkpoint)
  ↓
Tasks 12-14 (API Integrations) - Can be done in parallel
  ↓
Task 15 (Checkpoint)
  ↓
Task 16 (Streaming Integration)
  ↓
Tasks 17-18 (Error Handling & Optimization) - Sequential
  ↓
Task 19 (Checkpoint)
  ↓
Tasks 20-21 (Transparency & Packaging) - Can be done in parallel
  ↓
Task 22 (Final Testing)
  ↓
Task 23 (Final Checkpoint)
```

## Testing Strategy

### Unit Tests

Focus on specific examples, edge cases, and integration points:

- Component initialization
- Error handling
- State transitions
- API integration
- Platform-specific behavior

### Property-Based Tests

Verify universal properties across randomized inputs:

- Use `hypothesis` for Python (100+ iterations)
- Use `fast-check` for TypeScript (100+ iterations)
- Each property test references design document property
- Tag format: `# Feature: persuasive-chatbot, Property {N}: {description}`

### Integration Tests

Test complete workflows:

- End-to-end speech-to-speech pipeline
- Streaming integration
- Cross-platform compatibility
- Error recovery scenarios

## Performance Targets

- **End-to-end response**: 2-3 seconds (max 5s)
- **Avatar FPS**: 30+ (GPU), 24+ (CPU)
- **Initialization**: <10 seconds
- **UI responsiveness**: <100ms feedback
- **Session stability**: 30+ minutes

## Debugging

### Backend Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG  # Windows: set LOG_LEVEL=DEBUG
python src/main.py

# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"
```

### Frontend Debugging

- Open DevTools in Electron: `Ctrl+Shift+I` (Windows) or `Cmd+Option+I` (macOS)
- Check console for errors
- Use React DevTools extension
- Monitor network requests in DevTools

### Common Issues

**GPU not detected:**
- Verify CUDA installation: `nvidia-smi`
- Check PyTorch CUDA support: `python -c "import torch; print(torch.version.cuda)"`
- Ensure CUDA version matches PyTorch requirements

**API errors:**
- Verify API keys in `.env`
- Check API rate limits
- Test API connectivity with curl/Postman

**IPC communication failures:**
- Check Python process is running
- Verify JSON-RPC message format
- Check for timeout issues (increase timeout if needed)

## Contributing

1. Create a feature branch: `git checkout -b feature/task-X`
2. Implement the task following the design document
3. Write tests (unit + property tests)
4. Run code quality checks
5. Commit with descriptive message: `git commit -m "Implement Task X: Description"`
6. Push and create pull request

## Resources

- [Specification](.kiro/specs/persuasive-chatbot/requirements.md)
- [Design Document](.kiro/specs/persuasive-chatbot/design.md)
- [Task List](.kiro/specs/persuasive-chatbot/tasks.md)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [Electron Documentation](https://www.electronjs.org/docs)
- [React Documentation](https://react.dev/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [fast-check Documentation](https://fast-check.dev/)
