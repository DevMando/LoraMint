# LoRA Mint

**Train it once. Style it forever.** Prompt, mint, and create with your own visual signature.

A full-stack web application that lets users:
- Generate images from text prompts using Stable Diffusion
- Upload reference images to train custom LoRA adapters
- Apply trained LoRAs to future image generations
- View and manage image outputs and LoRA files

---

## 🧱 Tech Stack

| Layer     | Technology                |
|-----------|---------------------------|
| Frontend  | Blazor Server (C#)         |
| Backend   | ASP.NET Core Minimal APIs  |
| AI Engine | Python (FastAPI)           |
| Models    | SDXL Base, SDXL Turbo, Z-Image Turbo |
| LoRA      | PEFT / Kohya Trainer       |
| Format    | `.safetensors`             |
| Storage   | Local File System          |

---

## 🚀 How It Works

1. **Setup**: First-time users are guided through a setup wizard to select and download a model
2. **Generate**: User enters a prompt → Python backend generates image using the selected model
3. **Train**: User uploads 1-5 reference images → LoRA model is trained and saved as `.safetensors`
4. **Apply**: User selects trained LoRA(s) → Generates stylized images with custom style
5. **Manage**: All LoRAs and images are organized per user for easy access

---

## 🤖 Supported Models

| Model | Speed | Quality | Min VRAM | LoRA Support |
|-------|-------|---------|----------|--------------|
| **SDXL Base 1.0** | Medium (30 steps) | High | 8GB | Yes |
| **SDXL Turbo** | Fast (4 steps) | Good | 8GB | Yes |
| **Z-Image Turbo** | Fast (8 steps) | Excellent | 16GB | No |

Models are downloaded on-demand through the setup wizard or settings page. Each model is ~7-12GB.

---

## 📁 Project Structure

```
LoraMint/
├── src/
│   ├── LoraMint.Web/              # Blazor Server application
│   │   ├── BackgroundServices/    # Hosted services
│   │   │   └── PythonBackendHostedService.cs
│   │   ├── Components/            # Blazor components
│   │   │   ├── Layout/            # MainLayout, NavMenu
│   │   │   └── Shared/            # Reusable components (ModelComparisonTable)
│   │   ├── Models/                # Data models (ModelConfig, GenerateRequest, etc.)
│   │   ├── Pages/                 # Razor pages
│   │   │   ├── Setup.razor        # First-time setup wizard
│   │   │   ├── Settings.razor     # Model management settings
│   │   │   ├── Generate.razor     # Image generation
│   │   │   ├── TrainLora.razor    # LoRA training
│   │   │   ├── MyImages.razor     # Image gallery
│   │   │   └── MyLoras.razor      # LoRA library
│   │   ├── Services/              # C# services
│   │   │   ├── PythonBackendService.cs
│   │   │   ├── FileStorageService.cs
│   │   │   └── ModelConfigurationService.cs
│   │   ├── wwwroot/css/           # Cyberpunk terminal theme
│   │   └── Program.cs             # Minimal API endpoints
│   │
│   └── python-backend/            # Python FastAPI backend
│       ├── models/                # Pydantic models
│       ├── services/              # AI services
│       │   ├── image_generator.py # SD image generation
│       │   ├── model_manager.py   # Model downloading/loading
│       │   └── training/          # LoRA training modules
│       ├── utils/                 # Utilities
│       └── main.py                # FastAPI application
│
├── data/                          # Storage (gitignored)
│   ├── models/                    # Downloaded AI models (~7-12GB each)
│   ├── loras/                     # User LoRA models
│   ├── outputs/                   # Generated images
│   └── model-settings.json        # Model preferences
│
├── QUICKSTART.md                  # Quick start guide
├── PROJECT_INSTRUCTIONS.md        # Detailed specifications
├── FUTURE_FEATURES.md             # Roadmap and planned features
├── docker-compose.yml             # Docker orchestration
└── README.md                      # This file
```

---

## 🔄 Local Development Setup

### Prerequisites

- .NET 8.0 SDK
- Python 3.10+
- CUDA-capable GPU (recommended)
- 16GB+ RAM

### Quick Start (Recommended)

The Blazor application **automatically sets up and starts the Python backend** for you!

**Linux/macOS:**
```bash
./start.sh
```

**Windows:**
```cmd
start.bat
```

That's it! The application will:
1. Stop any existing LoraMint instances (automatic cleanup)
2. Create Python virtual environment (if needed)
3. Install dependencies (if needed)
4. Start the Python backend
5. Start the Blazor web application

Access the app at `https://localhost:5001`

📖 **See [QUICKSTART.md](QUICKSTART.md) for detailed first-run instructions**

### Manual Setup (Optional)

If you prefer manual control:

#### 1. Setup Python Environment

**Linux/macOS:**
```bash
./setup-python.sh
```

**Windows:**
```cmd
setup-python.bat
```

Or manually:
```bash
cd src/python-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Start Applications

**Option A:** Use startup script (auto-starts Python backend)
```bash
./start.sh  # or start.bat on Windows
```

**Option B:** Start manually in separate terminals

Terminal 1 - Python Backend:
```bash
cd src/python-backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

Terminal 2 - Blazor Web:
```bash
cd src/LoraMint.Web
dotnet run
```

#### 3. Access the Application

Open your browser and navigate to:
- Web UI: `https://localhost:5001`
- Python API Docs: `http://localhost:8000/docs`

---

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Build and run all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:
- Web UI: `http://localhost:5001`
- Python API: `http://localhost:8000`

---

## 📖 API Documentation

### Blazor Minimal APIs

- `POST /api/generate` - Generate an image from a prompt
- `POST /api/train-lora` - Train a new LoRA model
- `GET /api/loras/{userId}` - List user's LoRA models
- `GET /api/images/{userId}` - List user's generated images

### Python FastAPI Endpoints

- `POST /generate` - Generate image using Stable Diffusion
- `POST /train-lora` - Train LoRA model
- `GET /loras/{user_id}` - Get user's LoRAs
- `GET /images/{user_id}` - Get user's images
- `GET /health` - Health check and GPU status
- `GET /models` - List available models with download status
- `POST /models/{id}/download` - Download a model (SSE progress stream)
- `POST /models/{id}/load` - Load model into GPU memory
- `POST /models/unload` - Unload current model
- `GET /models/current` - Get currently loaded model
- `GET /system/gpu` - Get GPU information (VRAM, CUDA version)

For detailed API documentation, visit `http://localhost:8000/docs` after starting the Python backend.

---

## 🎨 Features

### Model Selection & Setup
- First-time setup wizard with GPU detection and VRAM display
- Model comparison table with VRAM requirements and compatibility
- Color-coded compatibility indicators (green/yellow/red based on available VRAM)
- On-demand model downloading with SSE progress streaming
- Dynamic "Powered by [Model Name]" label in the UI
- Settings page for switching models without restart

### Cyberpunk Terminal Theme
- Dark theme with gradient mesh background
- Purple/pink/orange gradient accents with cyan highlights
- Terminal-style typography (JetBrains Mono)
- Animated loading states with pulsing dots and spinning rings
- Glowing UI elements and scanline effects
- Terminal prompt prefix (`>_`) on headings

### Image Generation
- Text-to-image using SDXL Base, SDXL Turbo, or Z-Image Turbo
- Optional LoRA model application with adjustable strength
- Multiple LoRAs can be combined
- Real-time generation feedback with animated progress
- Step counter with digital font display (Orbitron)
- Per-user image storage and organization

### LoRA Training
- Upload 1-5 reference images for training
- DreamBooth-style PEFT training with prior preservation
- Configurable training parameters (epochs, learning rate, LoRA rank)
- Fast mode option (~40% faster training)
- Real-time progress streaming with phase indicators
- Automatic trigger word generation (e.g., `sks_<name>`)
- Class image caching for faster retries
- Automatic .safetensors format output
- Per-user LoRA storage

### Gallery Management
- Browse all generated images per user
- View generation metadata
- Filter and organize by date
- Download images

### LoRA Library
- List all trained models per user
- View file information and creation dates
- Quick access for use in generation
- Delete unwanted models

---

## 🔧 Configuration

### Blazor Web (`src/LoraMint.Web/appsettings.json`)

```json
{
  "PythonBackend": {
    "BaseUrl": "http://localhost:8000",
    "Path": "../python-backend",
    "AutoStart": true,
    "AutoInstallDependencies": true
  },
  "Storage": {
    "LorasPath": "../../data/loras",
    "OutputsPath": "../../data/outputs"
  }
}
```

**Configuration Options:**
- `AutoStart`: Automatically start Python backend (default: `true`)
- `AutoInstallDependencies`: Auto-install Python packages (default: `true`)
- `Path`: Path to Python backend directory
- `BaseUrl`: Python backend API URL

### Python Backend (`src/python-backend/main.py`)

- Model selection (SDXL, SD Turbo, etc.)
- Generation parameters
- Storage paths
- GPU settings

---

## 🚧 Development Status

### ✅ Implemented

**Core Features**
- Blazor Server UI with all pages
- ASP.NET Core Minimal APIs
- FastAPI backend structure
- File storage system with per-user organization
- Docker support

**Image Generation**
- Image generation pipeline with real-time SSE progress streaming
- Animated loading states (pulsing dots, spinning rings, step counter)
- Per-user image management and gallery

**LoRA Training**
- Real LoRA training using DreamBooth-style PEFT (see Known Issues)
- Training UI with progress streaming and configurable settings
- Fast mode for quicker training (~40% faster)
- Automatic trigger word generation
- Class image caching for faster retries

**Model Management**
- Multi-model selection (SDXL Base, SDXL Turbo, Z-Image Turbo)
- Setup wizard for first-time users with GPU detection
- Model comparison table with VRAM compatibility indicators
- Settings page for model management
- Network-friendly model downloads (single-threaded to prevent saturation)

**Developer Experience**
- Automatic Python backend startup
- One-command setup and launch (`start.sh` / `start.bat`)
- Enhanced startup feedback with progress indicators
- Cross-platform startup scripts (Windows & Linux/macOS)
- Automated dependency installation and validation

**UI/UX**
- Cyberpunk terminal dark theme with gradient accents
- Terminal-style typography (JetBrains Mono)
- Glowing UI elements and scanline effects

### 🔨 In Progress
- LoRA training memory optimization for 10GB GPUs
- User authentication
- Image metadata persistence

### 📋 Planned
- LoRA stacking UI with sliders
- Azure Blob Storage support
- Batch generation
- LoRA marketplace
- Additional model support (SDXL Lightning, Playground v2.5, etc.)
- Custom model import (safetensors, ckpt)

---

## ⚠️ Known Issues

### LoRA Training Memory (10GB VRAM GPUs)

The current DreamBooth-style LoRA training implementation may experience out-of-memory (OOM) issues on GPUs with 10GB VRAM (e.g., RTX 3080). This occurs because:

1. **Class image generation** loads a full SDXL pipeline (~8GB)
2. **Training** loads UNet, VAE, and text encoders
3. CUDA memory fragmentation prevents efficient reuse

**Current mitigations implemented:**
- Text encoders run on CPU (FP32) instead of GPU
- Aggressive GPU memory cleanup between phases
- Gradient checkpointing enabled
- 8-bit Adam optimizer
- Mixed precision (FP16) training

**Workarounds for users:**
- Use GPUs with 12GB+ VRAM for reliable training
- Close other GPU-intensive applications during training
- If training fails, restart the app and try again (class images are cached)

**Future fixes planned:**
- Sequential model loading with offloading
- Lower resolution option for class image generation
- Memory-efficient attention (xFormers) when available

---

## 📚 Additional Documentation

- [Quick Start Guide](QUICKSTART.md) - Get up and running fast
- [Project Instructions](PROJECT_INSTRUCTIONS.md) - Detailed specifications
- [Future Features](FUTURE_FEATURES.md) - Roadmap and planned features
- [Python Backend README](src/python-backend/README.md) - Python setup guide
- [Blazor Web README](src/LoraMint.Web/README.md) - .NET setup guide

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Stable Diffusion by Stability AI
- diffusers library by Hugging Face
- PEFT for LoRA implementation
- Blazor framework by Microsoft

---

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review API documentation at `/docs`
