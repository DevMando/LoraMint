# Project Instructions: AI-Powered Image Generation + LoRA Training Web App

## OVERVIEW

Build a full-stack web application that allows users to:
1. Enter a prompt to generate images using a diffusion-based model (e.g. SDXL or Turbo)
2. Upload 1–5 reference images to train a LoRA adapter
3. Use previously trained LoRAs in future generations
4. View and manage generated images and LoRA files

## TECH STACK

- **Frontend & Orchestration**: Blazor Server (C#) with Minimal APIs
- **UI Rendering**: Blazor .razor components
- **API Layer**: Minimal APIs in Program.cs
- **Backend (AI Engine)**: Python (FastAPI)
- **Image Generation**: Stable Diffusion (SDXL or Turbo) via diffusers
- **LoRA Training**: Kohya LoRA trainer or PEFT
- **File Format**: .safetensors for all LoRAs
- **Storage**: Local disk or Azure Blob
- **Process Management**: .NET Hosted Service for automatic Python backend startup
- **Queueing (Optional)**: Hangfire (.NET) or Celery (Python)

## ARCHITECTURE

```
[Blazor UI]
   │
   ├── POST /generate-prompt → Minimal API → Python SD Engine → Return Image
   ├── POST /train-lora      → Minimal API → Python Trainer → Save .safetensors
   ├── GET /loras            → Return LoRA list
   └── GET /images           → Return user generations
```

## PYTHON BACKEND RESPONSIBILITIES

### Endpoints

**POST /generate**
- Accept prompt + LoRA info, run SDXL/Turbo with loaded LoRA(s), return image

**POST /train-lora**
- Accept image upload + LoRA name, run training pipeline, save .safetensors

**File Management**
- Serve .safetensors and image files for listing
- Save outputs to: `/outputs/{userId}/`
- Save LoRAs to: `/loras/{userId}/`

### Dependencies

```bash
pip install fastapi==0.109.0 uvicorn[standard]==0.27.0 python-multipart==0.0.6
pip install torch==2.2.0 torchvision==0.17.0
pip install diffusers==0.30.0 transformers==4.44.0 accelerate==0.34.0
pip install safetensors==0.4.5 peft==0.13.0 pillow==10.4.0 numpy==1.26.4
```

**Note:** These versions are tested and compatible. The application automatically installs them via `requirements.txt`.

## BLAZOR SERVER RESPONSIBILITIES

### UI Pages

- **/generate**: Prompt input, optional LoRA selector, generate button
- **/train-lora**: Upload images, name LoRA, start training
- **/my-images**: Gallery of generated images
- **/my-loras**: List and preview LoRA files

### Minimal API Endpoints

- `POST /generate`
- `POST /train-lora`
- `GET /loras`
- `GET /images`

### Example Minimal API in Program.cs

```csharp
app.MapPost("/generate", async (PromptInput input) => {
   // Forward to Python via HttpClient
});

app.MapPost("/train-lora", async (HttpRequest req) => {
   // Upload images to Python, trigger training
});

app.MapGet("/loras", () => {
   // Return list of available LoRAs
});
```

## DATA STORAGE STRUCTURE

```
/loras/
   └── user123/
       └── anime_style_v1.safetensors

/outputs/
   └── user123/
       └── sequoia-sonic.png
```

## PROMPT EXAMPLE (With LoRA Usage)

```json
{
  "prompt": "fox in pixel art style",
  "loras": [
    { "file": "anime_style_v1.safetensors", "strength": 0.75 }
  ]
}
```

## OPTIONAL FEATURES (STRETCH GOALS)

- Real-time image preview with SignalR
- Training progress bar / polling
- LoRA metadata viewer
- LoRA stacking with sliders
- Hugging Face Space integration for preview-only mode

## AUTOMATIC STARTUP & DEPLOYMENT

### Hosted Service Architecture

The application uses a .NET `IHostedService` (`PythonBackendHostedService`) to automatically manage the Python backend lifecycle:

**Features:**
- Automatic Python virtual environment creation
- Automatic dependency installation from `requirements.txt`
- Python backend process management (start/stop)
- Cross-platform support (Windows, Linux, macOS)
- Configurable auto-start behavior

**Configuration (appsettings.json):**
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

### Startup Flow

1. User runs `./start.sh` (or `start.bat` on Windows)
2. Script executes `dotnet run` in `src/LoraMint.Web/`
3. `PythonBackendHostedService.StartAsync()` is called
4. Service checks for Python installation
5. Service creates virtual environment (if not exists)
6. Service installs dependencies (if `AutoInstallDependencies: true`)
7. Service starts `python main.py` as a child process
8. Blazor app starts and connects to Python backend at port 8000
9. Application ready at `https://localhost:5001`

### Deployment Scripts

**Linux/macOS:**
- `start.sh` - One-command startup
- `setup-python.sh` - Manual Python environment setup

**Windows:**
- `start.bat` - One-command startup
- `setup-python.bat` - Manual Python environment setup

**Docker:**
- `docker-compose.yml` - Multi-container deployment

## NOTES FOR AI AGENT / DEVELOPER

- All LoRA files must be saved and used in .safetensors format only
- Python model engine should support dynamic LoRA loading
- Training and generation must be async-compatible
- GPU environment assumed (e.g. T4 or A10G)
- Clean separation between .NET orchestration and Python model logic
- Blazor Minimal API layer manages orchestration and UI only
- Python backend is managed as a child process of the Blazor application
- On application shutdown, Python process is automatically terminated
