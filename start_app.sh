#!/bin/bash

# Clinical Consultation Analyzer - Startup Script
# This script starts both the FastAPI backend and React frontend

set -e

echo "🏥 Clinical Consultation Analyzer"
echo "=================================="
echo ""

# Check if backend and frontend directories exist
if [ ! -d "backend" ]; then
    echo "❌ Error: 'backend' directory not found"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo "❌ Error: 'frontend' directory not found"
    exit 1
fi

# Setup backend
echo "📦 Setting up backend..."
cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "  Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "  Installing dependencies..."
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Warning: .env file not found in backend/"
    echo "  Please create backend/.env with your API key:"
    echo "  LANGEXTRACT_API_KEY=your-gemini-api-key-here"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit..."
fi

# Start backend in background
echo "  Starting FastAPI server on port 8000..."
python -m uvicorn main:app --reload --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "  ✓ Backend started (PID: $BACKEND_PID)"

cd ..

# Setup frontend
echo ""
echo "📦 Setting up frontend..."
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "  Installing npm dependencies..."
    npm install -q
fi

# Start frontend
echo "  Starting React app on port 3000..."
export REACT_APP_API_URL=http://localhost:8000
npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  ✓ Frontend starting (PID: $FRONTEND_PID)"

cd ..

echo ""
echo "=================================="
echo "✓ Application started!"
echo ""
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend:  http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Logs:"
echo "   Backend:  backend/backend.log"
echo "   Frontend: frontend/frontend.log"
echo ""
echo "To stop the application:"
echo "  kill $BACKEND_PID  # Stop backend"
echo "  kill $FRONTEND_PID # Stop frontend"
echo ""
echo "=================================="
