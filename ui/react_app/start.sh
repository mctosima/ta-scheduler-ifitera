#!/bin/bash

# Start script for Thesis Defense Scheduler
echo "🚀 Starting Thesis Defense Scheduler..."

# Function to start backend
start_backend() {
    echo "📡 Starting Python backend..."
    cd backend
    source venv/bin/activate
    python app.py &
    BACKEND_PID=$!
    cd ..
    echo "✅ Backend started (PID: $BACKEND_PID)"
}

# Function to start frontend
start_frontend() {
    echo "🌐 Starting React frontend..."
    npm run dev &
    FRONTEND_PID=$!
    echo "✅ Frontend started (PID: $FRONTEND_PID)"
}

# Check if backend virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "❌ Backend not set up. Please run ./setup.sh first."
    exit 1
fi

# Start both services
start_backend
sleep 3  # Give backend time to start
start_frontend

echo ""
echo "🎉 Both services are starting!"
echo ""
echo "📡 Backend: http://localhost:5000"
echo "🌐 Frontend: http://localhost:5173 (or check terminal output)"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for user to stop
trap 'echo "Stopping services..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT
wait
