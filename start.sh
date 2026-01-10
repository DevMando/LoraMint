#!/bin/bash

# LoraMint Startup Script
# This script starts the Blazor application which will automatically
# set up and start the Python backend

echo ""
echo "========================================"
echo "   LoraMint - AI Image Generation"
echo "========================================"
echo ""

# Kill any existing instances
echo "[CHECK] Checking for existing instances..."

# Kill existing LoraMint.Web process if running
if pgrep -f "LoraMint.Web" > /dev/null 2>&1; then
    echo "[CLEANUP] Stopping existing LoraMint.Web instance..."
    pkill -f "LoraMint.Web" 2>/dev/null
    sleep 2
fi

# Kill Python process on port 8000 if running
PORT_8000_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$PORT_8000_PID" ]; then
    echo "[CLEANUP] Stopping existing Python backend on port 8000 (PID: $PORT_8000_PID)..."
    kill -9 $PORT_8000_PID 2>/dev/null
    sleep 1
fi

echo "[OK] No conflicting instances running"

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

# Function to wait for server and open browser (runs in background)
wait_and_open_browser() {
    echo "[BROWSER] Waiting for server to be ready..."
    MAX_WAIT=300  # 5 minutes max wait
    WAITED=0
    while [ $WAITED -lt $MAX_WAIT ]; do
        # Try to connect to the server (ignore SSL cert issues for localhost)
        if curl -sk --connect-timeout 2 https://localhost:5001 > /dev/null 2>&1; then
            echo "[BROWSER] Server is ready! Opening browser..."
            sleep 1
            xdg-open https://localhost:5001 2>/dev/null || open https://localhost:5001 2>/dev/null
            return 0
        fi
        sleep 2
        WAITED=$((WAITED + 2))
    done
    echo "[BROWSER] Timeout waiting for server. Please open https://localhost:5001 manually."
}

# Clean build cache to avoid file lock issues
echo "[BUILD] Cleaning build cache..."
dotnet clean -v q > /dev/null 2>&1
rm -f obj/Debug/net8.0/rpswa.dswa.cache.json 2>/dev/null

# Start browser wait in background
wait_and_open_browser &

# Start the application
dotnet run

echo ""
echo "👋 LoraMint stopped."
