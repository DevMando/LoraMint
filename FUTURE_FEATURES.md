# LoraMint - Future Features Roadmap

This document tracks planned features and improvements for future development.

---

## System Configuration & Setup Page

**Priority:** High
**Status:** Implemented

A dedicated configuration page to help users set up and troubleshoot their installation.

### Features

#### System Requirements Check
- [x] CUDA/GPU detection (NVIDIA GPU check)
- [x] Available VRAM display
- [x] PyTorch CUDA vs CPU detection
- [ ] .NET SDK version detection and validation
- [ ] Python version detection (3.10+ required)
- [ ] Disk space check for AI models (~10GB required)

#### One-Click Setup Actions
- [x] "Download Model" button - download selected model with progress streaming
- [x] "Select/Load Model" button - load model into GPU memory
- [ ] "Install CUDA PyTorch" button - automatically installs correct PyTorch version for user's GPU
- [ ] "Verify Installation" button - run diagnostics and report issues
- [ ] "Reinstall Dependencies" button - clean reinstall of Python packages

#### Status Dashboard
- [x] GPU status (available/not detected/VRAM usage/CUDA version)
- [x] Model status (downloaded/not downloaded/loading)
- [x] Current model display with specs
- [ ] Python backend status indicator (running/stopped/error)
- [ ] Real-time health monitoring

#### Configuration Options
- [x] Select AI model (SDXL Base, SDXL Turbo, Z-Image Turbo)
- [x] Model comparison table with VRAM requirements
- [x] Color-coded compatibility indicators
- [ ] Set generation defaults (inference steps, guidance scale, resolution)
- [ ] Configure storage paths (LoRAs, outputs)
- [ ] Adjust timeout settings
- [ ] Enable/disable auto-start Python backend

### Technical Notes

Issues encountered during initial setup that this page should help prevent:
1. PyTorch CPU-only installation (need CUDA version for GPU support)
2. Model download timeouts on first run - **Fixed: 60-minute timeout**
3. CUDA version compatibility with PyTorch
4. Insufficient VRAM for large models - **Fixed: VRAM compatibility indicators**
5. Network saturation during downloads - **Fixed: Single-threaded downloads**

---

## UI Theme & Styling

**Priority:** Medium
**Status:** Implemented

A cyberpunk terminal-inspired dark theme with gradient accents.

### Implemented Features
- [x] Dark theme base (Radzen dark-base.css)
- [x] Cyberpunk gradient color palette (purple/pink/orange)
- [x] Cyan accent color for highlights
- [x] Terminal-style typography (JetBrains Mono font)
- [x] Gradient mesh background with scanline effect
- [x] Styled cards with gradient accent lines
- [x] Gradient buttons with glow effects
- [x] Custom scrollbar styling
- [x] Terminal prompt prefix (`>_`) on headings
- [x] Animated loading dots (pulsing gradient colors)
- [x] Spinning ring animation for generation progress
- [x] Step counter with digital font (Orbitron)
- [x] Glowing UI elements

### Remaining Features
- [ ] Theme switcher (light/dark modes)
- [ ] Custom color palette options
- [ ] Reduced motion accessibility option

---

## Real-Time Generation Progress

**Priority:** Medium
**Status:** Implemented (SSE-based)

Real-time progress updates are implemented using Server-Sent Events (SSE) instead of SignalR.

### Implemented Features
- [x] Progress bar showing inference steps (e.g., "Step 15/30")
- [x] Phase indicators for training (class_generation, loading_models, training, saving)
- [x] Loss value display during training
- [x] Percentage completion
- [x] Animated loading states (pulsing dots, spinning ring)
- [x] Digital step counter display

### Remaining Features
- [ ] Estimated time remaining
- [ ] Live preview of image generation
- [ ] Cancel generation button
- [ ] Queue position indicator for multiple requests

---

## LoRA Training Improvements

**Priority:** High
**Status:** Partially Implemented (memory optimization needed for 10GB GPUs)

> **Update:** DreamBooth-style LoRA training has been implemented using PEFT. Training works but may experience OOM issues on GPUs with 10GB VRAM due to CUDA memory fragmentation between class image generation and training phases.

### Implemented Features
- [x] PEFT-based DreamBooth LoRA training
- [x] Training progress with live SSE updates
- [x] Training configuration options (epochs, learning rate, rank, prior preservation)
- [x] Fast mode (~40% faster with reduced class images)
- [x] Visual pipeline progress indicator (4 phases)
- [x] Automatic trigger word generation (sks_<name>)
- [x] Class image caching (skips regeneration on retry)
- [x] Text encoders on CPU to save GPU memory

### Known Issues
- [ ] OOM on 10GB GPUs (RTX 3080) - needs sequential model loading
- [ ] CUDA memory fragmentation between class generation and training

### Remaining Features
- [ ] Full Kohya LoRA trainer integration (alternative approach)
- [ ] Training preview/samples during training
- [ ] Resume interrupted training
- [ ] Training queue management
- [ ] Validate LoRA files before listing in UI
- [ ] Lower VRAM mode (768px class images, model offloading)

---

## LoRA Management Enhancements

**Priority:** Medium
**Status:** Planned

### Features
- [ ] LoRA stacking UI with strength sliders
- [ ] LoRA preview images (auto-generate sample)
- [ ] LoRA metadata viewer (training params, trigger words)
- [ ] LoRA categories/tags
- [ ] Delete confirmation with undo
- [ ] LoRA export/import
- [ ] LoRA sharing/marketplace integration

---

## User Authentication

**Priority:** Medium
**Status:** Planned

### Features
- [ ] User registration and login
- [ ] Per-user LoRA and image storage
- [ ] User preferences/settings persistence
- [ ] OAuth integration (Google, GitHub)
- [ ] API key management for external access

---

## Image Gallery Improvements

**Priority:** Low
**Status:** Planned

### Features
- [ ] Image metadata persistence (prompt, settings, LoRAs used)
- [ ] Search and filter by prompt/date/LoRA
- [ ] Batch operations (delete, download, favorite)
- [ ] Image comparison view
- [ ] Regenerate with same settings
- [ ] Share image with prompt

---

## Batch Generation

**Priority:** Low
**Status:** Planned

### Features
- [ ] Generate multiple images from one prompt
- [ ] Prompt queue/batch processing
- [ ] Variation generation (same prompt, different seeds)
- [ ] Grid view of batch results

---

## Cloud Storage Support

**Priority:** Low
**Status:** Planned

### Features
- [ ] Azure Blob Storage integration
- [ ] AWS S3 support
- [ ] Google Cloud Storage support
- [ ] Configurable storage backend

---

## Model Management

**Priority:** Medium
**Status:** Implemented

### Implemented Features
- [x] Download/manage multiple base models (SDXL Base, SDXL Turbo, Z-Image Turbo)
- [x] Model switching without restart (load/unload via Settings page)
- [x] Model information display (size, speed rating, quality rating, VRAM requirements)
- [x] Automatic model recommendations based on VRAM (color-coded compatibility)
- [x] Setup wizard for first-time model selection
- [x] Progress streaming for model downloads
- [x] Network-friendly downloads (single-threaded to prevent saturation)

### Remaining Features
- [ ] Custom model import (safetensors, ckpt)
- [ ] Delete downloaded models
- [ ] Additional models (SDXL Lightning, Playground v2.5, RealVisXL, etc.)

---

## Notes

- Features are listed in rough priority order within each section
- Check boxes indicate sub-feature completion status
- This document should be updated as features are implemented or priorities change
