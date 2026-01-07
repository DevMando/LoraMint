#!/bin/bash

# LoraMint Python Backend Setup Script
# This script manually sets up the Python backend environment

echo "🔧 Setting up Python backend for LoraMint..."
echo ""

# Navigate to Python backend directory
cd src/python-backend

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.10 or higher."
    exit 1
fi

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

echo "✅ Using Python: $PYTHON_CMD"

# Create virtual environment
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping creation."
else
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
echo "   This may take several minutes..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "✅ Python backend setup complete!"
echo ""
echo "To start the Python backend manually:"
echo "  cd src/python-backend"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "Or simply run: ./start.sh"
