#!/bin/bash

# Setup script for Thesis Defense Scheduler
echo "🚀 Setting up Thesis Defense Scheduler..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

echo "✅ Python and Node.js are installed"

# Create Python virtual environment for backend
echo "📦 Setting up Python backend..."
cd backend

# Remove existing virtual environment if it exists and had issues
if [ -d "venv" ]; then
    echo "🔄 Removing existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment
python3 -m venv venv
echo "✅ Created Python virtual environment"

# Activate virtual environment and install dependencies
source venv/bin/activate

# Upgrade pip first
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies with more lenient version requirements
echo "📦 Installing Python dependencies (this may take a few minutes)..."
pip install Flask Flask-CORS pandas numpy Werkzeug

if [ $? -eq 0 ]; then
    echo "✅ Installed Python dependencies successfully"
else
    echo "⚠️  Some dependencies failed to install, but continuing with basic setup"
    echo "📦 Installing minimal dependencies..."
    pip install Flask Flask-CORS Werkzeug
    pip install --no-deps pandas numpy || echo "⚠️  pandas/numpy installation failed - you may need to install these manually"
fi

# Go back to root directory
cd ..

# Install Node.js dependencies (should already be done)
echo "📦 Checking Node.js dependencies..."
if [ ! -d "node_modules" ]; then
    npm install
    echo "✅ Installed Node.js dependencies"
else
    echo "✅ Node.js dependencies already installed"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To run the application:"
echo "1. Start the Python backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "2. In a new terminal, start the React frontend:"
echo "   npm run dev"
echo ""
echo "3. Open your browser to the URL shown by the React dev server"
echo ""
echo "📝 Note: Make sure your Python scheduling code is in the parent directory"
echo "   (../../../src/main.py) for the integration to work properly."
echo ""
echo "⚠️  If you encounter any issues with pandas/numpy, try:"
echo "   cd backend && source venv/bin/activate && pip install pandas numpy"
