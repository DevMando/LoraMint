---
title: LoraMint
emoji: 🎨
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Train custom LoRAs and generate AI art with your own style
---

# LoraMint

**Train it once. Style it forever.**

A full-stack AI image generation app with custom LoRA training. Create your own visual style from just 1-5 reference images.

## Features

- **Image Generation**: SDXL Base, SDXL Turbo, or Z-Image Turbo
- **Custom LoRA Training**: DreamBooth-style PEFT training from your images
- **LoRA Stacking**: Combine multiple LoRAs with adjustable strength
- **Setup Wizard**: GPU detection and model recommendations
- **Cyberpunk UI**: Terminal-inspired dark theme with gradient accents

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Blazor Server (C#) |
| Backend | Python FastAPI |
| AI | diffusers, PEFT, PyTorch |
| Models | SDXL Base, SDXL Turbo, Z-Image Turbo |

## How It Works

1. **Setup**: Choose a model based on your GPU's VRAM
2. **Generate**: Enter a prompt to create AI images
3. **Train**: Upload 1-5 images to train a custom LoRA
4. **Apply**: Use your LoRA in future generations

## First Time Usage

1. Complete the setup wizard (auto-detects GPU)
2. Download your preferred model (~7-12GB)
3. Start generating!

## Tips

- **SDXL Turbo**: Fast (4 steps), good for quick iterations
- **SDXL Base**: Higher quality (30 steps), best LoRA compatibility
- **Z-Image Turbo**: Excellent quality, requires 16GB+ VRAM

## Source Code

Full source code available on [GitHub](https://github.com/DevMando/LoraMint)

## License

MIT License
