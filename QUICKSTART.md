# LoraMint Quick Start Guide

Get LoraMint up and running in just a few steps!

## 🎯 One-Command Start

### Option 1: Automatic Setup (Recommended)

The Blazor application will automatically set up and start the Python backend for you.

**Linux/macOS:**
```bash
./start.sh
```

**Windows:**
```cmd
start.bat
```

That's it! The application will:
1. 🧹 Stop any existing LoraMint instances (automatic cleanup)
2. ✅ Check for .NET SDK and Python
3. 📦 Create Python virtual environment (if needed)
4. 📥 Install all dependencies (if needed)
5. 🚀 Start both the Blazor web app and Python backend
6. 🌐 Open the app at `https://localhost:5001`

**Note:** The startup process now includes detailed progress indicators:
- `[STEP 1/3]` Virtual environment creation
- `[STEP 2/3]` Dependency installation (highlights PyTorch, diffusers, transformers)
- `[STEP 3/3]` Backend startup
- Clear `[SUCCESS]` and `[FAILED]` status messages

## 🔧 Manual Setup (Optional)

If you prefer to set up the Python environment manually first:

**Linux/macOS:**
```bash
./setup-python.sh
./start.sh
```

**Windows:**
```cmd
setup-python.bat
start.bat
```

## 📋 What Happens on First Run?

The first time you run LoraMint, it will:

1. **Create Virtual Environment** (~30 seconds)
   - Creates an isolated Python environment

2. **Install Dependencies** (~2-5 minutes)
   - Installs PyTorch, diffusers, FastAPI, etc.

3. **Setup Wizard** (first launch)
   - Detects your GPU and available VRAM
   - Shows model comparison table with compatibility indicators
   - Lets you choose a model (SDXL Base, SDXL Turbo, or Z-Image Turbo)
   - Downloads the selected model (~7-12GB depending on model)

**Total first-run time:** ~3-5 minutes + model download time

## 🎨 Using the Application

Once started, open your browser to `https://localhost:5001`

### Complete the Setup Wizard (First Time Only)

1. **Welcome** - Introduction to LoraMint
2. **System Check** - View your GPU info and available VRAM
3. **Model Selection** - Choose from:
   - **SDXL Turbo** (Recommended) - Fast, 4 steps, good quality
   - **SDXL Base 1.0** - Medium speed, 30 steps, high quality
   - **Z-Image Turbo** - Fast, excellent quality (requires 16GB VRAM)
4. **Download** - Wait for model download (progress shown)
5. **Complete** - You're ready to generate!

### Generate Your First Image

1. Go to **Generate** page
2. Enter a prompt (e.g., "a serene mountain landscape at sunset")
3. Click **Generate Image**
4. Wait ~5-60 seconds depending on model (Turbo models are faster)
5. View your image!

### Train Your First LoRA

1. Go to **Train LoRA** page
2. Enter a name (e.g., "my_style")
3. Upload 1-5 reference images
4. Click **Start Training**
5. Wait for training to complete
6. Use your LoRA in future generations!

## ⚙️ Configuration

### Change Model

After initial setup, you can change models via the **Settings** page:

1. Click the **Settings** icon in the navigation
2. Go to the **Models** tab
3. Download additional models if needed
4. Click **Select** to switch models or **Reload** to reload the current model

### Disable Auto-Start

Edit `src/LoraMint.Web/appsettings.json`:

```json
{
  "PythonBackend": {
    "AutoStart": false
  }
}
```

Then start Python manually:
```bash
cd src/python-backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

### Change Python Backend Path

Edit `src/LoraMint.Web/appsettings.json`:

```json
{
  "PythonBackend": {
    "Path": "/path/to/your/python-backend"
  }
}
```

### Disable Auto-Install Dependencies

Edit `src/LoraMint.Web/appsettings.json`:

```json
{
  "PythonBackend": {
    "AutoInstallDependencies": false
  }
}
```

## 🐳 Using Docker Instead

If you prefer Docker:

```bash
docker-compose up --build
```

Access the app at `http://localhost:5001`

## 🚨 Troubleshooting

### Python not found
- Install Python 3.10+ from https://www.python.org/downloads/
- Make sure it's in your PATH

### .NET SDK not found
- Install .NET 8.0 SDK from https://dotnet.microsoft.com/download

### Port 8000 already in use
- The startup scripts automatically kill existing processes on port 8000
- If you still have issues, manually kill the process:
  - **Windows:** `taskkill /F /IM python.exe` or check Task Manager
  - **Linux/macOS:** `lsof -ti:8000 | xargs kill -9`
- Or change the port in `src/python-backend/main.py`:
  ```python
  uvicorn.run(app, host="0.0.0.0", port=8001)  # Change to 8001
  ```
- And update `appsettings.json`:
  ```json
  {
    "PythonBackend": {
      "BaseUrl": "http://localhost:8001"
    }
  }
  ```

### GPU not detected
- Install CUDA toolkit if you have an NVIDIA GPU
- Otherwise, CPU will be used (much slower)
- Check GPU status at `http://localhost:8000/health`

### Dependencies fail to install
- Check your internet connection
- Try manual setup: `./setup-python.sh` or `setup-python.bat`
- Check Python version: `python --version` (should be 3.10+)

## 📚 Next Steps

- Read the full [README.md](README.md)
- Check [PROJECT_INSTRUCTIONS.md](PROJECT_INSTRUCTIONS.md) for details
- Explore the API docs at `http://localhost:8000/docs`
- View Python backend README at `src/python-backend/README.md`
- View Blazor web README at `src/LoraMint.Web/README.md`

## 🎉 Enjoy!

You're all set to start generating amazing AI images with custom LoRAs!
