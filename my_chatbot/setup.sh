#!/bin/bash
# Setup script for Persuasive Chatbot project

set -e

echo "🚀 Setting up Persuasive Chatbot project..."

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Setup backend
echo ""
echo "🐍 Setting up Python backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env and configure your settings"
fi

cd ..

# Setup frontend
echo ""
echo "⚛️  Setting up Electron/React frontend..."
cd frontend

echo "Installing Node.js dependencies..."
npm install

if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit frontend/.env and add your API keys"
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit backend/.env with your configuration"
echo "2. Edit frontend/.env with your API keys:"
echo "   - VITE_WHISPER_API_KEY"
echo "   - VITE_ELEVENLABS_API_KEY"
echo "   - VITE_LLM_API_KEY"
echo "3. Download talking-head-anime-3 model (see backend/README.md)"
echo ""
echo "🏃 To run the application:"
echo "   Terminal 1: cd backend && source venv/bin/activate && python src/main.py"
echo "   Terminal 2: cd frontend && npm run dev"
