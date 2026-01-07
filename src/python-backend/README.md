# LoraMint Python Backend

AI-powered image generation backend using FastAPI and Stable Diffusion.

## 🚀 Quick Start

### Automatic Startup (Recommended)

The Python backend is **automatically started** by the Blazor application!

From the project root, simply run:

**Linux/macOS:**
```bash
./start.sh
```

**Windows:**
```cmd
start.bat
```

The Blazor application will automatically:
1. Create the Python virtual environment
2. Install all dependencies
3. Start the Python backend
4. Connect everything together

No manual Python setup required!

## 🔧 Manual Setup (Optional)

If you need to run the Python backend independently:

### Prerequisites

- Python 3.10 or higher
- CUDA-capable GPU (recommended)
- 16GB+ RAM
- 10GB+ free disk space for models

### Installation

**Option 1: Use setup script**

From project root:
```bash
./setup-python.sh  # Linux/macOS
# or
setup-python.bat   # Windows
```

**Option 2: Manual setup**

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Server Manually

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the server
python main.py
```

The server will start on `http://localhost:8000`

**Note:** When using automatic startup, you don't need to run this manually!

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### POST /generate
Generate an image from a text prompt with optional LoRA models.

**Request Body:**
```json
{
  "prompt": "a fox in pixel art style",
  "userId": "user123",
  "loras": [
    {
      "file": "anime_style_v1.safetensors",
      "strength": 0.75
    }
  ]
}
```

### POST /train-lora
Train a new LoRA model using uploaded reference images.

**Form Data:**
- `lora_name`: Name for the LoRA model
- `user_id`: User identifier
- `images`: 1-5 image files

### GET /loras/{user_id}
Get list of all LoRA models for a user.

### GET /images/{user_id}
Get list of all generated images for a user.

## Configuration

Edit `main.py` to configure:
- Model selection (SDXL, SD Turbo, etc.)
- Default generation parameters
- File storage paths
- GPU settings

## Automatic Process Management

This Python backend is designed to be **automatically managed** by the Blazor application through `PythonBackendHostedService`.

When the Blazor app starts:
- ✅ Virtual environment is created automatically (if needed)
- ✅ Dependencies are installed automatically (if needed)
- ✅ This Python process is started as a child process
- ✅ Process is monitored and logs are captured
- ✅ Process is cleanly terminated when Blazor stops

**Configuration in Blazor's `appsettings.json`:**
```json
{
  "PythonBackend": {
    "BaseUrl": "http://localhost:8000",
    "Path": "../python-backend",
    "AutoStart": true,
    "AutoInstallDependencies": true
  }
}
```

To disable automatic startup, set `AutoStart: false` and run this backend manually.

## Dependencies

The following packages are automatically installed:
- **FastAPI** (0.109.0) - Web framework
- **Uvicorn** (0.27.0) - ASGI server
- **PyTorch** (2.2.0) - Deep learning framework (~200MB)
- **Torchvision** (0.17.0) - Computer vision models
- **Diffusers** (0.30.0) - Stable Diffusion pipeline
- **Transformers** (4.44.0) - AI model library
- **Accelerate** (0.34.0) - Training acceleration
- **Safetensors** (0.4.5) - LoRA file format
- **PEFT** (0.13.0) - Parameter-Efficient Fine-Tuning
- **Pillow** (10.4.0) - Image processing
- **NumPy** (1.26.4) - Numerical computing

## Notes

- First run will download the Stable Diffusion model (~6GB)
- GPU is highly recommended for acceptable generation speed
- LoRA training is currently a placeholder implementation
- For production LoRA training, integrate kohya_ss or PEFT
- When using automatic startup, the virtual environment is at `venv/`
- Python process logs are forwarded to the Blazor application console
- Dependencies are automatically updated to compatible versions
