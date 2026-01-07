#!/bin/bash

# LoraMint Startup Script
# This script starts the Blazor application which will automatically
# set up and start the Python backend

echo ""
echo "========================================"
echo "   LoraMint - AI Image Generation"
echo "========================================"
echo ""

# Check if .NET SDK is installed
echo "[CHECK] Verifying .NET SDK installation..."
if ! command -v dotnet &> /dev/null; then
    echo "[FAILED] .NET SDK not found. Please install .NET 8.0 SDK first."
    echo "         Visit: https://dotnet.microsoft.com/download"
    exit 1
fi
echo "[OK] .NET SDK found"

# Check if Python is installed
echo "[CHECK] Verifying Python installation..."
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[FAILED] Python not found. Please install Python 3.10 or higher."
    echo "         Visit: https://www.python.org/downloads/"
    exit 1
fi
echo "[OK] Python found"

# Navigate to Blazor app directory
cd src/LoraMint.Web

echo ""
echo "========================================"
echo "Starting Application..."
echo "========================================"
echo ""
echo "The Python backend will start automatically."
echo ""
echo "On first run, the following will happen:"
echo "  [STEP 1/3] Create Python virtual environment (~30-60 seconds)"
echo "  [STEP 2/3] Install AI dependencies (~2-5 minutes)"
echo "             - PyTorch (~200MB)"
echo "             - diffusers, transformers, and more"
echo "  [STEP 3/3] Start Python FastAPI backend"
echo ""
echo "When you generate your first image:"
echo "  - Stable Diffusion model will download (~6GB)"
echo "  - This happens only once"
echo ""
echo "========================================"
echo ""

# Start the application
dotnet run

echo ""
echo "👋 LoraMint stopped."
