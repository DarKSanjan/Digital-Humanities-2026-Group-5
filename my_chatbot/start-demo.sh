#!/bin/bash
# Quick Start Script for Persuasive Chatbot Demo
# This script starts both the Python backend and Electron frontend

echo "🚀 Starting Persuasive Chatbot Demo..."
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check if .env exists
if [ ! -f "frontend/.env" ]; then
    echo "❌ Error: frontend/.env file not found"
    echo "Please create it with your API keys"
    exit 1
fi

echo "✅ Configuration found"
echo ""

# Start Python backend in background
echo "🐍 Starting Python backend..."
cd backend
python src/main.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to initialize
sleep 2

# Start frontend
echo "⚛️  Starting React frontend..."
cd frontend
npm run dev:react &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both services started!"
echo ""
echo "📝 Backend PID: $BACKEND_PID"
echo "📝 Frontend PID: $FRONTEND_PID"
echo ""
echo "🌐 Open your browser to: http://localhost:5173"
echo ""
echo "To stop the demo, press Ctrl+C or run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Wait for user interrupt
wait
