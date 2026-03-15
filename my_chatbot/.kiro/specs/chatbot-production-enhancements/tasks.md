# Implementation Plan: Chatbot Production Enhancements

## Overview

This implementation plan transforms the persuasive chatbot MVP into a production-ready system with robust error handling, performance monitoring, ethical transparency, and a Full HD optimized UI. The tasks are organized to build incrementally, with each phase validating functionality before proceeding.

The system is a standalone Python application (`backend/src/chatbot_app.py`) with tkinter GUI, launched via `START_CHATBOT.bat`. Implementation will enhance the existing architecture while removing deprecated web-based components.

## Tasks

- [ ] 1. Set up error handling infrastructure
  - [x] 1.1 Create `APIRetryHandler` class with exponential backoff
    - Implement retry logic with delays: 1s, 2s, 4s, 8s (max 4 retries)
    - Add error translation method for user-friendly messages
    - Create `backend/src/error_handler.py`
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_
  
  - [ ]* 1.2 Write property test for API retry with exponential backoff
    - **Property 1: API Retry with Exponential Backoff**
    - **Validates: Requirements 1.1, 1.2, 1.4**
    - Test that any API failure triggers retries with correct delays
    - Verify conversation state preservation during retries
    - Create `backend/tests/test_error_handler_property.py`
  
  - [ ]* 1.3 Write unit tests for error message translation
    - Test network error messages (ConnectionError, Timeout)
    - Test API error messages (401, 429, 503)
    - Test system error messages (MemoryError, CUDA errors)
    - Create `backend/tests/test_error_handler.py`
    - _Requirements: 2.1, 2.2, 2.3, 2.5_

- [ ] 2. Implement network and process monitoring
  - [x] 2.1 Create `NetworkMonitor` class
    - Implement connectivity checking every 10 seconds
    - Add callback registration for connectivity changes
    - Implement reconnection handling
    - Add to `backend/src/error_handler.py`
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 2.2 Create `ProcessMonitor` class
    - Implement heartbeat mechanism
    - Add health check with 2-second timeout
    - Implement crash detection
    - Add to `backend/src/error_handler.py`
    - _Requirements: 4.1, 4.2, 4.5_
  
  - [ ]* 2.3 Write property test for network monitoring frequency
    - **Property 7: Network Connectivity Monitoring Frequency**
    - **Validates: Requirements 3.1**
    - Test that connectivity checks occur every 10 seconds
  
  - [ ]* 2.4 Write property test for network reconnection
    - **Property 8: Network Reconnection Round Trip**
    - **Validates: Requirements 3.3**
    - Test that losing then restoring connectivity resumes session

- [ ] 3. Implement resource monitoring system
  - [x] 3.1 Create `ResourceMonitor` class
    - Implement memory usage tracking (every 5 seconds)
    - Implement VRAM usage tracking for GPU mode
    - Add threshold checking (80% warning, 90% critical)
    - Create `backend/src/resource_monitor.py`
    - _Requirements: 5.1, 5.2, 5.3, 6.1, 6.3_
  
  - [x] 3.2 Implement garbage collection triggers
    - Add automatic GC every 10 minutes
    - Add threshold-based GC (>80% memory)
    - Add temporary file cleanup
    - Add GPU resource release
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ] 3.3 Implement session stability validation
    - Add session duration tracking
    - Add performance metrics collection (latency, FPS)
    - Add stability check for 30+ minute sessions
    - _Requirements: 7.1, 7.2, 7.4, 7.5_
  
  - [ ]* 3.4 Write property test for resource monitoring frequency
    - **Property 13: Resource Monitoring Frequency**
    - **Validates: Requirements 5.1, 6.1**
    - Test that memory and VRAM checks occur every 5 seconds
  
  - [ ]* 3.5 Write property test for memory usage limit
    - **Property 15: Memory Usage Limit**
    - **Validates: Requirements 5.5**
    - Test that memory usage remains below 2GB during normal operation
  
  - [ ]* 3.6 Write property test for VRAM usage limit
    - **Property 16: VRAM Usage Limit**
    - **Validates: Requirements 6.2**
    - Test that VRAM usage remains below 6GB during GPU rendering
  
  - [ ]* 3.7 Write property test for extended session stability
    - **Property 17: Extended Session Stability**
    - **Validates: Requirements 7.1**
    - Test that 30+ minute sessions maintain stable operation
  
  - [ ]* 3.8 Write property test for memory leak prevention
    - **Property 19: Memory Leak Prevention**
    - **Validates: Requirements 7.3**
    - Test that memory usage doesn't continuously increase over time

- [ ] 4. Checkpoint - Verify monitoring infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Integrate error handling into conversation pipeline
  - [x] 5.1 Enhance `ChatbotApp` with error handling
    - Integrate `APIRetryHandler` into Whisper STT calls
    - Integrate `APIRetryHandler` into GPT-4 LLM calls
    - Integrate `APIRetryHandler` into ElevenLabs TTS calls
    - Add error message display in UI
    - Modify `backend/src/chatbot_app.py`
    - _Requirements: 1.1, 1.2, 1.3, 2.4_
  
  - [ ] 5.2 Add network monitoring to application
    - Initialize `NetworkMonitor` in `ChatbotApp.__init__`
    - Register connectivity change callback
    - Implement input queuing during outages
    - Display reconnection notices in UI
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ] 5.3 Add process monitoring to application
    - Initialize `ProcessMonitor` in `ChatbotApp.__init__`
    - Add heartbeat calls in main loop
    - Implement crash recovery logic
    - Add crash logging
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ]* 5.4 Write property test for retry exhaustion error display
    - **Property 2: Retry Exhaustion Error Display**
    - **Validates: Requirements 1.3**
    - Test that exhausted retries show user-friendly error
  
  - [ ]* 5.5 Write property test for input queuing during outage
    - **Property 9: Input Queuing During Outage**
    - **Validates: Requirements 3.4**
    - Test that user inputs during outage are queued and processed after reconnection

- [ ] 6. Integrate resource monitoring into application
  - [ ] 6.1 Add `ResourceMonitor` to `ChatbotApp`
    - Initialize `ResourceMonitor` in `ChatbotApp.__init__`
    - Start monitoring thread
    - Add resource metrics display in developer console
    - Implement threshold warnings
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.3, 6.4, 6.5_
  
  - [ ] 6.2 Implement automatic garbage collection
    - Add periodic GC timer (10 minutes)
    - Add threshold-based GC trigger
    - Add GC logging with memory freed
    - Add temporary file cleanup after audio playback
    - _Requirements: 8.1, 8.2, 8.3, 8.5_
  
  - [ ] 6.3 Add session stability tracking
    - Track session start time
    - Log session duration at intervals
    - Validate performance metrics for extended sessions
    - _Requirements: 7.1, 7.2, 7.4, 7.5_
  
  - [ ]* 6.4 Write property test for periodic garbage collection
    - **Property 20: Periodic Garbage Collection**
    - **Validates: Requirements 8.1**
    - Test that GC is triggered every 10 minutes
  
  - [ ]* 6.5 Write property test for extended session performance
    - **Property 18: Extended Session Performance**
    - **Validates: Requirements 7.2, 7.5**
    - Test that 30+ minute sessions maintain consistent FPS and <3s latency

- [ ] 7. Checkpoint - Verify integrated monitoring
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement ethical transparency components
  - [ ] 8.1 Create disclaimer dialog
    - Design modal dialog with disclaimer text
    - Add position disclosure (post-human or humanist)
    - Add AI capabilities and limitations explanation
    - Require user acknowledgment (minimum 3 seconds)
    - Create `backend/src/disclaimer_dialog.py`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 10.1, 10.2, 10.3, 10.5_
  
  - [ ] 8.2 Add disclaimer to application startup
    - Show disclaimer at session start
    - Log acceptance with timestamp
    - Prevent interaction until acknowledged
    - Modify `backend/src/chatbot_app.py`
    - _Requirements: 9.1, 9.3, 9.4, 9.5_
  
  - [ ] 8.3 Create About section
    - List underlying AI models (Whisper, GPT-4, ElevenLabs, tha3)
    - Explain system capabilities
    - Document known limitations
    - Add version information and credits
    - Create accessible from main interface
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [ ] 8.4 Add position display to header
    - Show philosophical position in header
    - Keep visible throughout session
    - Update header styling
    - _Requirements: 10.1, 10.4_
  
  - [ ]* 8.5 Write unit tests for disclaimer dialog
    - Test disclaimer display at startup
    - Test 3-second minimum display time
    - Test acknowledgment requirement
    - Test acceptance logging
    - Create `backend/tests/test_disclaimer.py`
    - _Requirements: 9.1, 9.3, 9.4, 9.5_
  
  - [ ]* 8.6 Write property test for disclaimer display and acknowledgment
    - **Property 24: Disclaimer Display and Acknowledgment**
    - **Validates: Requirements 9.1, 9.3, 9.4, 9.5**
    - Test that any new session displays disclaimer for ≥3s and requires acknowledgment

- [ ] 9. Design Full HD UI layout
  - [ ] 9.1 Create design system configuration
    - Define color palette (dark theme)
    - Define typography (fonts, sizes, weights)
    - Define spacing scale
    - Define component styles (cards, buttons, shadows)
    - Create `backend/src/design_system.py`
    - _Requirements: 13.1, 13.2, 13.3, 16.1_
  
  - [ ] 9.2 Design Full HD window layout
    - Set window size to 1920x1080
    - Design header with title and position display
    - Design central avatar area (512x512)
    - Design control panel with microphone button
    - Design transcript area with scrolling
    - Design status indicator area
    - Create layout constants in `backend/src/ui_layout.py`
    - _Requirements: 12.1, 12.2, 12.3, 14.1_
  
  - [ ] 9.3 Design enhanced avatar display
    - Add framing effects around avatar
    - Add status indicators (speaking, listening, thinking)
    - Ensure avatar visibility and prominence
    - Design avatar container styling
    - _Requirements: 14.1, 14.3, 14.4, 14.5_
  
  - [ ]* 9.4 Write unit tests for Full HD layout
    - Test window dimensions (1920x1080)
    - Test avatar size (512x512)
    - Test component positioning
    - Test aspect ratio preservation
    - Create `backend/tests/test_ui_layout.py`
    - _Requirements: 12.1, 12.2, 12.4_

- [ ] 10. Implement Full HD UI components
  - [ ] 10.1 Refactor main window for Full HD
    - Apply design system colors and typography
    - Implement 1920x1080 layout
    - Add header with position display
    - Enhance avatar display with framing
    - Update control panel styling
    - Modify `backend/src/chatbot_app.py`
    - _Requirements: 12.1, 12.2, 12.3, 13.1, 13.2, 13.3, 14.1, 14.3_
  
  - [ ] 10.2 Implement enhanced status indicators
    - Add visual indicators for speaking/listening/thinking states
    - Add error message display area
    - Add retry button for recoverable errors
    - Add resource usage display (developer mode)
    - _Requirements: 2.4, 14.5, 15.2, 16.3_
  
  - [ ] 10.3 Implement smooth transitions
    - Add 300ms transitions between states
    - Use cubic-bezier easing functions
    - Implement fade-in/fade-out for messages
    - Add smooth avatar state transitions
    - _Requirements: 15.1, 15.3, 15.4_
  
  - [ ] 10.4 Add visual feedback for user actions
    - Provide <100ms feedback for button presses
    - Add hover effects to interactive elements
    - Add loading states with smooth animations
    - _Requirements: 15.2, 16.3_
  
  - [ ]* 10.5 Write property test for smooth animation transitions
    - **Property 33: Smooth Animation Transitions**
    - **Validates: Requirements 15.1, 15.3, 15.4**
    - Test that state transitions use 300ms duration with easing, without stuttering
  
  - [ ]* 10.6 Write property test for visual feedback responsiveness
    - **Property 34: Visual Feedback Responsiveness**
    - **Validates: Requirements 15.2**
    - Test that user actions receive feedback within 100ms
  
  - [ ]* 10.7 Write property test for UI resilience
    - **Property 35: UI Resilience**
    - **Validates: Requirements 16.3, 16.4, 16.5**
    - Test that errors and state changes maintain visual consistency

- [ ] 11. Enhance conversational experience
  - [ ] 11.1 Optimize conversation pacing
    - Minimize artificial delays in pipeline
    - Optimize API call sequencing
    - Implement parallel processing where possible
    - _Requirements: 17.1_
  
  - [ ] 11.2 Enhance conversational language
    - Update UI text to use conversational tone
    - Update error messages to be friendly
    - Update status messages to be natural
    - _Requirements: 17.2_
  
  - [ ] 11.3 Improve avatar feedback cues
    - Enhance idle animations (nodding, eye contact)
    - Improve emotional expressions
    - Add thinking animation during processing
    - _Requirements: 17.3_
  
  - [ ] 11.4 Implement conversation interruption
    - Allow user to interrupt ongoing bot speech
    - Stop audio playback on new mic press
    - Clear phoneme queue on interruption
    - Resume conversation flow naturally
    - _Requirements: 17.5_
  
  - [ ]* 11.5 Write property test for natural interaction
    - **Property 36: Natural Interaction**
    - **Validates: Requirements 17.1, 17.2, 17.3, 17.4**
    - Test that conversation minimizes delays, uses conversational language, and provides natural feedback
  
  - [ ]* 11.6 Write property test for conversation interruption
    - **Property 37: Conversation Interruption Support**
    - **Validates: Requirements 17.5**
    - Test that user can interrupt ongoing bot speech

- [ ] 12. Checkpoint - Verify UI and UX enhancements
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Clean up legacy system components
  - [x] 13.1 Remove Electron/React frontend
    - Delete `frontend/src/` directory (except `.env`)
    - Delete `frontend/package.json` and `node_modules/`
    - Delete `frontend/index.html` and `frontend/vite.config.ts`
    - Keep `frontend/.env` for API keys
    - _Requirements: 18.1_
  
  - [x] 13.2 Remove WebSocket IPC server
    - Delete `backend/src/websocket_server.py`
    - Delete `backend/src/ipc_server.py`
    - Remove WebSocket dependencies from requirements
    - _Requirements: 18.2_
  
  - [ ] 13.3 Remove TypeScript/JavaScript tests
    - Delete all `frontend/src/**/__tests__/` directories
    - Delete `frontend/src/**/*.test.ts` files
    - Delete `frontend/src/**/*.test.tsx` files
    - _Requirements: 18.3_
  
  - [ ] 13.4 Update documentation
    - Update README.md to reflect Python-only architecture
    - Remove web UI setup instructions
    - Update DEVELOPMENT.md with new architecture
    - Document new error handling and monitoring features
    - Document Full HD UI features
    - _Requirements: 18.4_
  
  - [ ] 13.5 Update launcher script
    - Remove frontend dependency checks from `START_CHATBOT.bat`
    - Update dependency list (remove Node.js, npm)
    - Add new Python dependencies (if any)
    - _Requirements: 18.5_

- [ ] 14. Production mode configuration
  - [ ] 14.1 Add production mode flag
    - Add `PRODUCTION_MODE` environment variable
    - Hide developer console in production mode
    - Hide debug information in production mode
    - Show only essential UI elements
    - _Requirements: 13.4, 16.2_
  
  - [ ] 14.2 Configure logging for production
    - Set log level to INFO in production
    - Disable debug logging
    - Configure log file rotation
    - Sanitize logs to remove sensitive data
    - _Requirements: 13.4_
  
  - [ ]* 14.3 Write unit tests for production mode
    - Test that debug info is hidden in production
    - Test that developer tools are disabled
    - Test that logs are sanitized
    - Create `backend/tests/test_production_mode.py`
    - _Requirements: 13.4, 16.2_

- [ ] 15. Integration testing and validation
  - [ ]* 15.1 Write integration test for full conversation flow
    - Test Record → Transcribe → Generate → Synthesize → Play
    - Verify all components work together
    - Create `backend/tests/test_integration.py`
  
  - [ ]* 15.2 Write integration test for error recovery flow
    - Test API failure → Retry → Success
    - Verify conversation state preservation
  
  - [ ]* 15.3 Write integration test for network outage flow
    - Test Disconnect → Queue inputs → Reconnect → Process
    - Verify input queuing and processing
  
  - [ ]* 15.4 Write integration test for resource management flow
    - Test Memory threshold → GC trigger → Memory freed
    - Verify resource monitoring and cleanup
  
  - [ ]* 15.5 Write performance test for extended sessions
    - Test 30-minute session stability
    - Verify response latency <3s throughout
    - Verify frame rate maintains 30+ FPS
    - Verify memory usage stays <2GB
    - Create `backend/tests/test_performance.py`

- [ ] 16. Final checkpoint and documentation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. Final polish and bug fixes
  - [ ] 17.1 Review and fix any remaining issues
    - Address any test failures
    - Fix any UI glitches
    - Optimize performance bottlenecks
  
  - [ ] 17.2 Update version information
    - Update version number in code
    - Update About section with new version
    - Update README with version history
  
  - [ ] 17.3 Create release notes
    - Document all new features
    - Document breaking changes
    - Document upgrade instructions

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end flows
- The implementation builds incrementally: infrastructure → integration → UI → cleanup → validation
- All code should be production-ready with proper error handling and logging
- Full HD UI should be tested at 1920x1080 resolution
- Extended session tests should run for at least 30 minutes
- Legacy cleanup removes all web-based architecture remnants
