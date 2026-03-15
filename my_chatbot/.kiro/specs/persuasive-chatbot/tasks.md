# Implementation Plan: Persuasive Chatbot

## Overview

This implementation plan breaks down the persuasive chatbot system into discrete coding tasks. The system combines Python backend (avatar rendering with talking-head-anime-3), Electron/React GUI, and external API integrations (Whisper STT, ElevenLabs TTS, LLM) to create a speech-to-speech debate application with animated avatar.

The implementation follows an incremental approach: establish core infrastructure, implement individual components with testing, integrate components through IPC, add streaming and parallel processing, implement error handling, optimize performance, implement ethical transparency features, and finalize with cross-platform packaging.

## Tasks

- [x] 1. Set up project structure and development environment
  - Create directory structure for Python backend and Electron GUI
  - Initialize Python project with virtual environment and dependencies (PyTorch, talking-head-anime-3, hypothesis)
  - Initialize Electron/React project with TypeScript, Tailwind CSS, Framer Motion, Zustand, fast-check
  - Set up configuration files for both platforms (package.json, pyproject.toml, tsconfig.json)
  - Create .env.example files for API keys (Whisper, ElevenLabs, LLM)
  - Set up ESLint, Prettier, Black, mypy for code quality
  - _Requirements: 5.5, 14.1, 14.6_

- [x] 2. Implement Python backend core infrastructure
  - [x] 2.1 Create IPC server with JSON-RPC protocol
    - Implement bidirectional communication over stdin/stdout
    - Add message serialization/deserialization with error handling
    - Implement request-response pattern with timeout mechanism (5s default)
    - Add message validation and error propagation
    - _Requirements: 5.5, 9.3_
  
  - [x] 2.2 Write unit tests for IPC server
    - Test message serialization/deserialization
    - Test timeout handling
    - Test error propagation
    - _Requirements: 5.5_
  
  - [x] 2.3 Create hardware detection and configuration module
    - Detect CUDA availability using torch.cuda.is_available()
    - Detect GPU name, VRAM, CUDA version
    - Determine rendering mode (GPU/CPU) based on capabilities
    - Create HardwareInfo data structure
    - _Requirements: 2.6, 13.3, 13.4, 13.5_
  
  - [x] 2.4 Write property test for hardware detection
    - **Property 29: Hardware Capability Detection**
    - **Validates: Requirements 13.5**
  
  - [x] 2.5 Implement cross-platform path handling utilities
    - Use pathlib for all file system operations
    - Create helper functions for temp file management
    - Handle platform-specific differences transparently
    - _Requirements: 13.2, 13.8_
  
  - [x] 2.6 Write property test for path handling
    - **Property 28: Cross-Platform Path Handling**
    - **Validates: Requirements 13.2, 13.8**

- [x] 3. Checkpoint - Verify infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Avatar Renderer component
  - [x] 4.1 Create AvatarRenderer class with initialization
    - Load talking-head-anime-3 model
    - Implement GPU initialization with CUDA
    - Implement CPU fallback on GPU failure
    - Add model loading with error handling
    - Track current FPS and rendering mode
    - _Requirements: 2.1, 2.6, 2.8, 13.3, 13.4_
  
  - [x] 4.2 Write unit tests for AvatarRenderer initialization
    - Test GPU initialization success path
    - Test CPU fallback when GPU unavailable
    - Test model loading errors
    - _Requirements: 2.6, 2.8_
  
  - [x] 4.3 Implement frame rendering methods
    - Implement render_frame() for single phoneme
    - Implement render_sequence() for phoneme stream
    - Add frame batching for GPU efficiency
    - Monitor VRAM usage (<6GB target)
    - Return frames as numpy arrays with timestamps
    - _Requirements: 2.1, 2.4, 2.7_
  
  - [x] 4.4 Write property test for frame rate performance
    - **Property 4: Frame Rate Performance Thresholds**
    - **Validates: Requirements 2.4, 2.7, 10.2, 10.3**
  
  - [x] 4.5 Write property test for initialization time
    - **Property 5: Initialization Time Constraint**
    - **Validates: Requirements 2.5, 10.6**

- [ ] 5. Implement Lip Sync Controller component
  - [x] 5.1 Create phoneme-to-viseme mapping
    - Define standard viseme set (A, B, C, D, E, F, G, H, X)
    - Map IPA phonemes to visemes
    - Implement map_phoneme_to_viseme() method
    - _Requirements: 8.3_
  
  - [x] 5.2 Write property test for phoneme-to-viseme mapping
    - **Property 18: Phoneme-to-Viseme Mapping**
    - **Validates: Requirements 8.3**
  
  - [x] 5.3 Implement animation sequence generation
    - Convert phoneme timeline to frame-by-frame visemes
    - Handle pauses with neutral mouth positions
    - Implement interpolation for smooth transitions
    - Maintain 100ms synchronization tolerance
    - _Requirements: 8.1, 8.2, 8.4_
  
  - [x] 5.4 Write property test for pause handling
    - **Property 19: Pause Handling in Lip Sync**
    - **Validates: Requirements 8.4**
  
  - [x] 5.5 Write property test for lip sync consistency
    - **Property 20: Lip Sync Round-Trip Consistency**
    - **Validates: Requirements 8.5**
  
  - [x] 5.6 Write property test for audio-visual synchronization
    - **Property 3: Audio-Visual Synchronization**
    - **Validates: Requirements 2.2, 7.4, 8.1, 8.2**

- [ ] 6. Implement Stream Coordinator component
  - [x] 6.1 Create StreamCoordinator class with asyncio
    - Implement process_speech_stream() for parallel processing
    - Implement play_audio() for audio playback
    - Implement render_avatar() for frame generation
    - Add synchronization monitoring (100ms tolerance)
    - _Requirements: 10.8_
  
  - [x] 6.2 Write property test for parallel processing
    - **Property 25: Parallel Audio-Visual Processing**
    - **Validates: Requirements 10.8**
  
  - [x] 6.3 Integrate AvatarRenderer and LipSyncController
    - Wire components together in StreamCoordinator
    - Implement frame buffering (2-3 frames ahead)
    - Add frame dropping if rendering falls behind
    - Monitor and log A/V sync drift
    - _Requirements: 2.2, 8.1, 8.2_

- [x] 7. Checkpoint - Verify Python backend
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement Electron GUI core infrastructure
  - [x] 8.1 Create React project structure and routing
    - Set up component directory structure
    - Create main App component
    - Set up Tailwind CSS configuration
    - Configure Framer Motion for animations
    - _Requirements: 5.5, 5.7, 12.1, 12.2_
  
  - [x] 8.2 Implement state management with Zustand
    - Create conversationStore with AppState interface
    - Define state: sessionStatus, position, conversationHistory, currentTranscript, errorMessage, hardwareCapabilities
    - Implement state actions for session lifecycle
    - _Requirements: 1.4, 5.3_
  
  - [x] 8.3 Write unit tests for state management
    - Test state transitions
    - Test conversation history updates
    - Test error state handling
    - _Requirements: 5.3_
  
  - [x] 8.4 Create IPC service for Python backend communication
    - Implement IPCService class with message sending
    - Add timeout handling (5s default)
    - Implement message queue for reconnection
    - Add process crash detection and restart logic
    - _Requirements: 5.5, 10.1_
  
  - [-] 8.5 Write unit tests for IPC service
    - Test message serialization
    - Test timeout handling
    - Test process crash recovery
    - _Requirements: 5.5, 10.1_

- [ ] 9. Implement GUI components
  - [x] 9.1 Create AvatarDisplay component
    - Display video stream from Python backend
    - Handle frame updates via IPC
    - Show loading state during initialization
    - Display fallback message in audio-only mode
    - _Requirements: 5.1, 5.8, 10.2_
  
  - [x] 9.2 Create MicrophoneButton component
    - Implement recording control with visual states
    - Add pulsing animation during listening
    - Provide responsive feedback within 100ms
    - _Requirements: 5.2, 5.9, 13.4_
  
  - [x] 9.3 Create StatusIndicator component
    - Display current session status (idle, listening, processing, speaking, error)
    - Use color coding (blue=listening, yellow=processing, green=speaking)
    - Implement smooth state transitions (300ms)
    - _Requirements: 5.2, 5.7, 12.2_
  
  - [ ] 9.4 Write property test for state transitions
    - **Property 11: State Transition Animations**
    - **Validates: Requirements 5.7**
  
  - [x] 9.5 Create TranscriptPanel component (optional display)
    - Display conversation history as text
    - Auto-scroll to latest message
    - Toggle visibility based on user preference
    - _Requirements: 5.4_
  
  - [ ] 9.6 Create ErrorBoundary and error display components
    - Catch and display React errors gracefully
    - Show user-friendly error messages
    - Provide Retry button for recoverable errors
    - Display error codes for support reference
    - _Requirements: 9.1, 12.6_
  
  - [x] 9.7 Create LoadingState component
    - Display loading indicators for operations >200ms
    - Show progress for initialization
    - Implement smooth animations
    - _Requirements: 5.8, 12.5_
  
  - [ ] 9.8 Write property test for loading state display
    - **Property 27: Loading State Display**
    - **Validates: Requirements 12.5**

- [ ] 10. Implement visual design and styling
  - [ ] 10.1 Create design system with Tailwind
    - Define color scheme (dark theme)
    - Set up typography system (Inter font family)
    - Create spacing and layout utilities
    - Define animation presets
    - _Requirements: 5.10, 5.11, 12.1, 12.7_
  
  - [ ] 10.2 Apply professional styling to all components
    - Implement clean, minimal layout
    - Add smooth transitions and animations
    - Establish clear visual hierarchy
    - Ensure consistent spacing and alignment
    - _Requirements: 12.1, 12.2, 12.3, 12.7_
  
  - [ ] 10.3 Write property test for UI responsiveness
    - **Property 13: UI Responsiveness**
    - **Validates: Requirements 5.9, 10.4, 12.4**

- [ ] 11. Checkpoint - Verify GUI foundation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement Speech Input Processor (Whisper integration)
  - [x] 12.1 Create useAudioRecording hook
    - Use browser MediaRecorder API
    - Capture audio in WebM or WAV format
    - Implement start/stop recording
    - Handle microphone permissions
    - _Requirements: 1.1, 6.1_
  
  - [x] 12.2 Create whisperService for API integration
    - Send audio to Whisper API
    - Parse transcription response
    - Extract confidence score
    - Target 1-2 second latency
    - _Requirements: 1.1, 6.1, 6.2_
  
  - [ ] 12.3 Write unit tests for Whisper integration
    - Test API call success
    - Test error handling (network failure, invalid audio)
    - Test confidence score extraction
    - _Requirements: 6.1, 6.2_
  
  - [ ] 12.4 Implement transcription accuracy and clarification
    - Check confidence threshold (0.9)
    - Request clarification on low confidence
    - Handle background noise with retry prompt
    - Support natural speech patterns (pauses, filler words)
    - _Requirements: 1.5, 6.2, 6.3, 6.5_
  
  - [ ] 12.5 Write property test for transcription accuracy
    - **Property 14: Transcription Accuracy**
    - **Validates: Requirements 6.2**
  
  - [ ] 12.6 Write property test for natural speech handling
    - **Property 15: Natural Speech Pattern Handling**
    - **Validates: Requirements 6.5**

- [ ] 13. Implement Conversation Engine (LLM integration)
  - [x] 13.1 Create ConversationEngine interface
    - Define initialize() with position parameter
    - Implement generateResponse() with streaming
    - Add getPosition() and resetSession() methods
    - _Requirements: 1.2, 3.1_
  
  - [x] 13.2 Create llmService for API integration
    - Integrate with LLM API (OpenAI GPT-4 or similar)
    - Implement streaming response handling
    - Parse token-by-token output
    - Handle API errors with retry logic
    - _Requirements: 1.2, 10.7_
  
  - [ ] 13.3 Write unit tests for LLM integration
    - Test API call success
    - Test streaming response parsing
    - Test error handling and retry
    - _Requirements: 1.2_
  
  - [ ] 13.4 Implement prompt engineering for philosophical positions
    - Create system prompts for post-human position
    - Create system prompts for humanist position
    - Include conversation history (last 10 exchanges)
    - Add rhetorical strategy instructions
    - Constrain response length (100-200 words)
    - _Requirements: 3.1, 3.2, 3.5, 4.1_
  
  - [ ] 13.5 Write property test for position consistency
    - **Property 6: Philosophical Position Consistency**
    - **Validates: Requirements 3.2, 3.4, 3.5**
  
  - [ ] 13.6 Write property test for counterargument defense
    - **Property 7: Counterargument Defense**
    - **Validates: Requirements 3.3**
  
  - [ ] 13.7 Write property test for rhetorical strategies
    - **Property 8: Rhetorical Strategy Employment**
    - **Validates: Requirements 4.1, 4.3, 4.4**
  
  - [ ] 13.8 Write property test for argument acknowledgment
    - **Property 9: Argument Acknowledgment**
    - **Validates: Requirements 4.2**
  
  - [ ] 13.9 Write property test for respectful tone
    - **Property 10: Respectful Tone Maintenance**
    - **Validates: Requirements 4.5**
  
  - [ ] 13.10 Write property test for consciousness claim prohibition
    - **Property 26: Consciousness Claim Prohibition**
    - **Validates: Requirements 11.4**
  
  - [ ] 13.11 Implement conversational context preservation
    - Maintain conversation history in state
    - Pass context to LLM with each request
    - Reference earlier exchanges in responses
    - _Requirements: 1.4_
  
  - [ ] 13.12 Write property test for context preservation
    - **Property 2: Conversational Context Preservation**
    - **Validates: Requirements 1.4**

- [ ] 14. Implement Speech Output Generator (ElevenLabs integration)
  - [x] 14.1 Create elevenLabsService for TTS API
    - Integrate with ElevenLabs API
    - Implement streaming text-to-speech
    - Parse audio chunks and phoneme data
    - Target 500ms for first audio chunk
    - _Requirements: 1.3, 7.1, 7.2, 10.7_
  
  - [ ] 14.2 Write property test for TTS conversion completeness
    - **Property 1: Text-to-Speech Conversion Completeness**
    - **Validates: Requirements 1.3**
  
  - [ ] 14.3 Write unit tests for ElevenLabs integration
    - Test API call success
    - Test streaming audio parsing
    - Test phoneme data extraction
    - Test error handling
    - _Requirements: 7.1_
  
  - [ ] 14.2 Implement voice configuration and consistency
    - Set voice ID for consistent character
    - Configure prosody and emphasis settings
    - Maintain voice characteristics across session
    - Ensure 22kHz+ sample rate
    - _Requirements: 7.2, 7.3, 7.5_
  
  - [ ] 14.4 Write property test for voice consistency
    - **Property 16: Voice Consistency**
    - **Validates: Requirements 7.3**
  
  - [ ] 14.5 Write property test for audio quality
    - **Property 17: Audio Quality Standard**
    - **Validates: Requirements 7.5**
  
  - [ ] 14.3 Create useSpeechSynthesis hook
    - Accept text stream from LLM
    - Forward to ElevenLabs streaming endpoint
    - Receive and buffer audio chunks
    - Extract phoneme timing data
    - _Requirements: 7.4, 10.7_

- [ ] 15. Checkpoint - Verify API integrations
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Implement streaming pipeline integration
  - [-] 16.1 Create useConversation hook for end-to-end flow
    - Orchestrate speech input → LLM → TTS → avatar pipeline
    - Implement streaming from LLM to TTS
    - Forward audio and phonemes to Python backend via IPC
    - Update UI state throughout pipeline
    - _Requirements: 1.1, 1.2, 1.3, 10.7_
  
  - [ ] 16.2 Implement parallel processing coordination
    - Start TTS while LLM is still generating
    - Play audio while rendering avatar in parallel
    - Buffer audio chunks for smooth playback
    - _Requirements: 10.7, 10.8_
  
  - [ ] 16.3 Write property test for streaming TTS
    - **Property 24: Streaming Text-to-Speech**
    - **Validates: Requirements 10.7**
  
  - [ ] 16.3 Optimize end-to-end response time
    - Minimize latency at each pipeline stage
    - Target 2-3 seconds total response time
    - Implement performance monitoring
    - _Requirements: 1.1, 1.2, 10.1_
  
  - [ ] 16.4 Write property test for response time
    - **Property 22: End-to-End Response Time**
    - **Validates: Requirements 1.1, 1.2, 10.1**

- [ ] 17. Implement error handling and recovery
  - [ ] 17.1 Add API failure handling with retry logic
    - Implement exponential backoff (1s, 2s, 4s, 8s)
    - Display user-friendly error messages
    - Provide Retry button
    - Maintain conversation state for recovery
    - _Requirements: 9.1_
  
  - [ ] 17.2 Write unit tests for API error handling
    - Test retry logic
    - Test error message display
    - Test state preservation
    - _Requirements: 9.1_
  
  - [ ] 17.3 Implement avatar rendering fallback hierarchy
    - Attempt GPU rendering first
    - Fall back to CPU on GPU failure
    - Fall back to audio-only on rendering failure
    - Display visual indicator for degraded mode
    - _Requirements: 2.8, 9.2_
  
  - [ ] 17.4 Write unit tests for rendering fallback
    - Test GPU to CPU fallback
    - Test audio-only mode activation
    - Test visual indicator display
    - _Requirements: 2.8, 9.2_
  
  - [ ] 17.5 Implement network connectivity monitoring
    - Detect network loss with periodic health checks
    - Pause session when network lost
    - Display reconnection notification
    - Attempt automatic reconnection every 5 seconds
    - Resume session when connectivity restored
    - _Requirements: 9.4_
  
  - [ ] 17.6 Write unit tests for network monitoring
    - Test disconnection detection
    - Test reconnection logic
    - Test session pause/resume
    - _Requirements: 9.4_
  
  - [ ] 17.7 Implement IPC error handling and process recovery
    - Handle Python process crashes
    - Attempt process restart
    - Queue messages during reconnection
    - Display fatal error if restart fails
    - _Requirements: 9.1, 9.5_
  
  - [ ] 17.8 Add comprehensive error logging
    - Log all errors with timestamps
    - Include component identifier
    - Log to console and rotating files
    - Implement log rotation (100MB max)
    - _Requirements: 9.3_
  
  - [ ] 17.9 Write property test for error logging
    - **Property 21: Error Logging Completeness**
    - **Validates: Requirements 9.3**

- [ ] 18. Implement resource monitoring and optimization
  - [ ] 18.1 Create ResourceMonitor for Python backend
    - Monitor memory usage (warn at 80%)
    - Monitor disk space (warn at 90%)
    - Monitor VRAM usage (<6GB target)
    - Trigger garbage collection when needed
    - Clean up temporary files
    - _Requirements: 10.5_
  
  - [ ] 18.2 Optimize avatar rendering performance
    - Implement frame batching for GPU
    - Monitor and maintain target FPS
    - Reduce quality if CPU overloaded
    - Clear CUDA cache periodically
    - _Requirements: 2.4, 2.7, 10.2, 10.3_
  
  - [ ] 18.3 Ensure extended session stability
    - Test 30-minute continuous operation
    - Monitor for memory leaks
    - Verify stable FPS over time
    - Check for latency degradation
    - _Requirements: 10.5_
  
  - [ ] 18.4 Write property test for extended session stability
    - **Property 23: Extended Session Stability**
    - **Validates: Requirements 10.5**

- [ ] 19. Checkpoint - Verify error handling and performance
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 20. Implement ethical transparency features
  - [ ] 20.1 Create session start disclaimer
    - Display AI system disclaimer at session start
    - Disclose philosophical position
    - Show disclaimer before first interaction
    - _Requirements: 11.1, 11.2_
  
  - [ ] 20.2 Add technology information display
    - Provide "About" section with technology details
    - Document underlying AI models
    - Explain system capabilities and limitations
    - _Requirements: 11.3_
  
  - [ ] 20.3 Write unit tests for disclaimer display
    - Test disclaimer shown at session start
    - Test position disclosure
    - _Requirements: 11.1, 11.2_

- [ ] 21. Implement cross-platform packaging and deployment
  - [ ] 21.1 Configure Electron Builder for both platforms
    - Set up build configuration for Windows
    - Set up build configuration for macOS
    - Configure app icons and metadata
    - Set up code signing (if available)
    - _Requirements: 5.5, 5.6, 13.1, 13.6_
  
  - [ ] 21.2 Bundle Python backend with Electron app
    - Package Python dependencies with PyInstaller or similar
    - Include talking-head-anime-3 model files
    - Configure IPC to launch bundled Python process
    - Handle platform-specific executable paths
    - _Requirements: 5.5, 13.1, 13.6_
  
  - [ ] 21.3 Build and test Windows executable
    - Build Windows installer/portable app
    - Test on Windows 10 and Windows 11
    - Verify GPU acceleration with CUDA
    - Test CPU fallback
    - _Requirements: 5.5, 5.6, 13.1, 13.3_
  
  - [ ] 21.4 Build and test macOS executable
    - Build macOS .app bundle
    - Test on macOS Monterey and Ventura
    - Verify CPU rendering performance
    - Test app signing and notarization (if configured)
    - _Requirements: 5.5, 5.6, 13.1_
  
  - [ ] 21.5 Write integration tests for cross-platform compatibility
    - Test file path handling on both platforms
    - Test executable building
    - Test hardware detection on both platforms
    - _Requirements: 13.1, 13.2, 13.5, 13.8_

- [ ] 22. Final integration testing and polish
  - [ ] 22.1 Conduct end-to-end testing
    - Complete full debate session (5+ exchanges)
    - Verify all components working together
    - Test error recovery scenarios
    - Measure performance metrics
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ] 22.2 Write integration tests for end-to-end flow
    - Test complete speech-to-speech pipeline
    - Test streaming integration
    - Test state management throughout flow
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ] 22.3 Perform UI/UX polish pass
    - Review visual design quality
    - Verify animation smoothness
    - Check loading state clarity
    - Ensure error messages are helpful
    - Verify responsive feedback timing
    - Test cross-platform UI consistency
    - _Requirements: 5.7, 5.8, 5.9, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_
  
  - [ ] 22.4 Conduct performance testing
    - Measure end-to-end response time (target: 2-3s)
    - Measure avatar FPS (GPU: 30+, CPU: 24+)
    - Measure initialization time (target: <10s)
    - Monitor memory usage over 30-minute session
    - Verify UI responsiveness (<100ms feedback)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_
  
  - [ ] 22.5 Write property test for processing feedback
    - **Property 12: Processing Feedback Display**
    - **Validates: Requirements 5.8**

- [ ] 23. Final checkpoint - Complete system verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples, edge cases, and integration points
- The implementation uses Python for backend (avatar rendering, lip sync, IPC server) and TypeScript/React for GUI
- Cross-platform compatibility is maintained throughout with platform-agnostic code
- Performance optimization focuses on streaming, parallel processing, and GPU acceleration
- Error handling includes graceful degradation and recovery mechanisms
