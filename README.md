**LoRA Mint** 
Train it once. Style it forever. Prompt, mint, and create with your own visual signature.

This a full-stack web application that lets users:
- Prompt a diffusion model to generate images
- Upload images to train custom LoRA adapters
- Apply trained LoRAs to future generations
- View and manage image outputs + LoRA files

---

## 🧱 Tech Stack

| Layer     | Tech                     |
|-----------|--------------------------|
| Frontend  | Blazor Server (C#)        |
| Backend   | Minimal API (C#)          |
| AI Engine | Python (FastAPI)          |
| Models    | Stable Diffusion, SDXL, Turbo |
| LoRA      | Kohya Trainer / PEFT     |
| Format    | `.safetensors`           |
| Storage   | Local or Azure Blob      |

---

## 🚀 How It Works

1. User enters a prompt → image is generated via Python
2. User uploads reference images → LoRA is trained and saved as `.safetensors`
3. Prompt + LoRA = stylized image generation
4. LoRA and images are saved per user

---

## 🔄 Local Dev Setup

### .NET + Blazor

```bash
cd LoRAMint.Blazor
dotnet run
