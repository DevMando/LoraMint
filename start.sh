#!/bin/bash

# LoraMint Startup Script
# This script starts the Blazor application which will automatically
# set up and start the Python backend

echo "🚀 Starting LoraMint..."
echo ""

# Check if .NET SDK is installed
if ! command -v dotnet &> /dev/null; then
    echo "❌ .NET SDK not found. Please install .NET 8.0 SDK first."
    echo "   Visit: https://dotnet.microsoft.com/download"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.10 or higher."
    echo "   Visit: https://www.python.org/downloads/"
    exit 1
fi

# Navigate to Blazor app directory
cd src/LoraMint.Web

echo "✅ Starting Blazor application..."
echo "   The Python backend will start automatically."
echo ""
echo "📝 Note: First run may take a few minutes to:"
echo "   - Create Python virtual environment"
echo "   - Install dependencies"
echo "   - Download AI models (~6GB)"
echo ""

# Start the application
dotnet run

echo ""
echo "👋 LoraMint stopped."
