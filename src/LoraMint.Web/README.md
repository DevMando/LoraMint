# LoraMint Web Application

Blazor Server web interface for AI-powered image generation and LoRA training.

## 🚀 Quick Start

### Automatic Startup (Recommended)

The web application **automatically manages the Python backend** for you!

From the project root directory, run:

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
2. ✅ Check prerequisites (.NET SDK, Python)
3. ✅ Create Python virtual environment (if needed)
4. ✅ Install Python dependencies (if needed)
5. ✅ Start the Python backend automatically
6. ✅ Start the Blazor web application
7. 🌐 Open at `https://localhost:5001`

**No manual Python setup required!**

The startup process includes detailed progress feedback:
- **[STEP 1/3]** Virtual environment creation (~30-60 seconds)
- **[STEP 2/3]** Dependency installation (~2-5 minutes on first run)
  - Highlights major packages: PyTorch (~200MB), diffusers, transformers
- **[STEP 3/3]** Python backend startup
- Clear **[SUCCESS]** and **[FAILED]** status indicators

## Prerequisites

- .NET 8.0 SDK or higher
- Python 3.10+ (automatically detected)
- CUDA-capable GPU (recommended)

## Manual Running (Optional)

If you prefer to run the application manually:

### Installation

1. Navigate to this directory:
```bash
cd src/LoraMint.Web
```

2. Restore NuGet packages:
```bash
dotnet restore
```

### Running the Application

```bash
dotnet run
```

The application will:
- Start on `https://localhost:5001`
- Automatically start Python backend (if `AutoStart: true`)
- Connect to Python backend at `http://localhost:8000`

**Note:** The Python backend starts automatically by default. You don't need to run it separately!

## Features

### Cyberpunk Terminal Theme
- Dark theme with gradient mesh background (purple/pink/orange)
- Terminal-style typography using JetBrains Mono font
- Animated loading states with pulsing dots and spinning rings
- Glowing UI elements and gradient accent lines
- Cyan highlights for active states and links

### Generate Images
- Enter text prompts to generate images
- Select optional LoRA models to apply
- View generated images in real-time
- Multiple LoRAs with adjustable strength
- Animated progress with step counter display

### Train LoRA
- Upload 1-5 reference images
- Train custom LoRA adapters
- Name and organize your LoRAs
- Automatic .safetensors format

### My Images
- Browse all generated images
- View image metadata and prompts
- Organized by creation date
- Download images

### My LoRAs
- List all trained LoRA models
- View file sizes and creation dates
- Quick access to use in generation
- Per-user storage

## Configuration

### appsettings.json

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
- `Path`: Path to Python backend directory (relative to this project)
- `BaseUrl`: Python backend API URL

### Disable Auto-Start

To run Python backend manually, edit `appsettings.json`:

```json
{
  "PythonBackend": {
    "AutoStart": false
  }
}
```

Then start Python backend manually:
```bash
cd ../python-backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python main.py
```

## Architecture

### Automatic Backend Management

The application includes `PythonBackendHostedService`, a .NET `IHostedService` that:
- Detects Python installation
- Creates virtual environment
- Installs dependencies
- Starts Python backend as a child process
- Monitors the process
- Handles graceful shutdown

### Minimal APIs

ASP.NET Core Minimal APIs for backend endpoints:
- `POST /api/generate` - Generate images
- `POST /api/train-lora` - Train LoRA models
- `GET /api/loras/{userId}` - List user LoRAs
- `GET /api/images/{userId}` - List user images

### Static File Serving

Generated images and LoRA files are served from the `data/` directory:
- `/outputs/{userId}/{filename}` - Generated images from `data/outputs/`
- `/loras/{userId}/{filename}` - LoRA model files from `data/loras/`

### Services

- `PythonBackendService` - HTTP client for Python FastAPI backend
- `FileStorageService` - File system operations for LoRAs and images
- `PythonBackendHostedService` - Automatic Python backend lifecycle management

### Pages

- `/` - Home page with feature overview
- `/generate` - Image generation interface
- `/train-lora` - LoRA training interface
- `/my-images` - Image gallery
- `/my-loras` - LoRA management

## Project Structure

```
LoraMint.Web/
├── BackgroundServices/
│   └── PythonBackendHostedService.cs  # Auto-start service
├── Components/
│   ├── App.razor                      # HTML head with fonts & theme
│   ├── Routes.razor
│   └── Layout/
│       ├── MainLayout.razor           # Header, sidebar, body layout
│       └── NavMenu.razor
├── Models/
│   ├── GenerateRequest.cs
│   ├── LoraInfo.cs
│   └── ImageInfo.cs
├── Pages/
│   ├── Home.razor
│   ├── Generate.razor                 # With animated loading states
│   ├── TrainLora.razor
│   ├── MyImages.razor
│   └── MyLoras.razor
├── Services/
│   ├── PythonBackendService.cs
│   └── FileStorageService.cs
├── wwwroot/
│   └── css/
│       └── app.css                    # Cyberpunk terminal theme
├── Program.cs                         # Minimal APIs & service registration
├── appsettings.json                   # Configuration
└── appsettings.Development.json       # Dev configuration
```

## Development

### Running in Development Mode

```bash
dotnet run --environment Development
```

This uses `appsettings.Development.json` with enhanced logging for the Python backend service.

### Logs

The application logs include:
- Blazor application logs
- Python backend stdout/stderr
- Process management events
- Dependency installation progress

Check the console for `[Python]` prefixed logs from the backend.

## Troubleshooting

### Python not found
- Install Python 3.10+ from https://www.python.org/downloads/
- Ensure Python is in your system PATH

### .NET SDK not found
- Install .NET 8.0 SDK from https://dotnet.microsoft.com/download

### Port 8000 already in use
- Another process is using port 8000
- Change `BaseUrl` in `appsettings.json`
- Update port in `src/python-backend/main.py`

### Dependencies fail to install
- Check internet connection
- Try manual setup: `../../setup-python.sh`
- Check Python version compatibility

### Python backend won't start
- Check logs in the console
- Verify Python path in configuration
- Try disabling auto-start and running manually

## Notes

- Python backend starts automatically by default
- First run takes longer due to dependency installation and model downloads
- Default user ID is "user123" for testing
- File paths are relative to the project structure
- For production, implement proper user authentication
- Python process is terminated when the application stops

## Related Documentation

- [Project Root README](../../README.md) - Main project documentation
- [Python Backend README](../python-backend/README.md) - Python backend details
- [Quick Start Guide](../../QUICKSTART.md) - Getting started guide
