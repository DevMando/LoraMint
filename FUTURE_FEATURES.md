# LoraMint - Future Features Roadmap

This document tracks planned features and improvements for future development.

---

## System Configuration & Setup Page

**Priority:** High
**Status:** Planned

A dedicated configuration page to help users set up and troubleshoot their installation.

### Features

#### System Requirements Check
- [ ] .NET SDK version detection and validation
- [ ] Python version detection (3.10+ required)
- [ ] CUDA/GPU detection (NVIDIA GPU check)
- [ ] Available VRAM display
- [ ] Disk space check for AI models (~10GB required)
- [ ] PyTorch CUDA vs CPU detection

#### One-Click Setup Actions
- [ ] "Install CUDA PyTorch" button - automatically installs correct PyTorch version for user's GPU
- [ ] "Download SDXL Model" button - pre-cache the model to avoid first-run delays
- [ ] "Verify Installation" button - run diagnostics and report issues
- [ ] "Reinstall Dependencies" button - clean reinstall of Python packages

#### Status Dashboard
- [ ] Python backend status indicator (running/stopped/error)
- [ ] GPU status (available/not detected/VRAM usage)
- [ ] Model status (downloaded/not downloaded/loading)
- [ ] Current configuration display
- [ ] Real-time health monitoring

#### Configuration Options
- [ ] Select AI model (SDXL, SD Turbo, SDXL Lightning, etc.)
- [ ] Set generation defaults (inference steps, guidance scale, resolution)
- [ ] Configure storage paths (LoRAs, outputs)
- [ ] Adjust timeout settings
- [ ] Enable/disable auto-start Python backend

### Technical Notes

Issues encountered during initial setup that this page should help prevent:
1. PyTorch CPU-only installation (need CUDA version for GPU support)
2. Model download timeouts on first run
3. CUDA version compatibility with PyTorch
4. Insufficient VRAM for large models

---

## Real-Time Generation Progress

**Priority:** Medium
**Status:** Planned

Use SignalR for real-time updates during image generation.

### Features
- [ ] Progress bar showing inference steps (e.g., "Step 15/30")
- [ ] Estimated time remaining
- [ ] Live preview of image generation
- [ ] Cancel generation button
- [ ] Queue position indicator for multiple requests

---

## LoRA Training Improvements

**Priority:** High
**Status:** In Progress (currently placeholder implementation)

> **Note:** Current implementation creates placeholder .safetensors files that are not valid LoRAs.
> The image generator now gracefully skips invalid LoRAs, but real training needs to be implemented.

### Features
- [ ] Full Kohya LoRA trainer integration
- [ ] PEFT-based training as alternative
- [ ] Training progress with live updates
- [ ] Training configuration options (epochs, learning rate, rank, etc.)
- [ ] Training preview/samples during training
- [ ] Resume interrupted training
- [ ] Training queue management
- [ ] Validate LoRA files before listing in UI

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
**Status:** Planned

### Features
- [ ] Download/manage multiple base models
- [ ] Model switching without restart
- [ ] Custom model import (safetensors, ckpt)
- [ ] Model information display (size, type, capabilities)
- [ ] Automatic model recommendations based on VRAM

---

## Notes

- Features are listed in rough priority order within each section
- Check boxes indicate sub-feature completion status
- This document should be updated as features are implemented or priorities change
