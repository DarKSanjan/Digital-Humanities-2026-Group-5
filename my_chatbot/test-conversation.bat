@echo off
REM Simple Test - Just the conversation (no avatar needed)
REM This tests microphone, Whisper, GPT-4, and ElevenLabs

echo.
echo 🎤 Testing Conversation System (No Backend Needed!)
echo.
echo This will test:
echo  ✅ Microphone recording
echo  ✅ Whisper transcription
echo  ✅ GPT-4 responses
echo  ✅ ElevenLabs speech
echo.
echo The avatar will show "Audio-only mode" - that's OK!
echo.

cd frontend
echo Starting frontend...
echo.
npm run dev:react

pause
