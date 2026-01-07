import torch
from diffusers import StableDiffusionXLPipeline, AutoPipelineForText2Image
from pathlib import Path
import os
from typing import List, Optional
from datetime import datetime

from models.request_models import LoraReference

class ImageGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipeline = None
        self.model_id = "stabilityai/stable-diffusion-xl-base-1.0"
        self.outputs_base_path = Path("../../../data/outputs")
        self.loras_base_path = Path("../../../data/loras")

        # Create outputs directory if it doesn't exist
        self.outputs_base_path.mkdir(parents=True, exist_ok=True)

    def is_gpu_available(self) -> bool:
        """Check if GPU is available"""
        return torch.cuda.is_available()

    def load_pipeline(self):
        """Load the Stable Diffusion pipeline"""
        if self.pipeline is None:
            print(f"Loading model: {self.model_id}")
            self.pipeline = AutoPipelineForText2Image.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True
            )
            self.pipeline = self.pipeline.to(self.device)
            print(f"Model loaded on {self.device}")

    def load_loras(self, user_id: str, loras: Optional[List[LoraReference]]):
        """Load LoRA adapters into the pipeline"""
        if not loras:
            return

        for lora in loras:
            lora_path = self.loras_base_path / user_id / lora.file
            if lora_path.exists():
                print(f"Loading LoRA: {lora.file} with strength {lora.strength}")
                self.pipeline.load_lora_weights(
                    str(lora_path.parent),
                    weight_name=lora.file,
                    adapter_name=lora.file.replace('.safetensors', '')
                )
                # Set adapter strength
                self.pipeline.set_adapters(
                    [lora.file.replace('.safetensors', '')],
                    adapter_weights=[lora.strength]
                )
            else:
                print(f"Warning: LoRA file not found: {lora_path}")

    async def generate(
        self,
        prompt: str,
        user_id: str,
        loras: Optional[List[LoraReference]] = None
    ) -> str:
        """
        Generate an image using Stable Diffusion

        Args:
            prompt: Text prompt for image generation
            user_id: User identifier for organizing outputs
            loras: Optional list of LoRA models to apply

        Returns:
            Path to the generated image
        """
        # Load pipeline if not already loaded
        self.load_pipeline()

        # Load LoRAs if specified
        if loras:
            self.load_loras(user_id, loras)

        # Create user output directory
        user_output_dir = self.outputs_base_path / user_id
        user_output_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"generated_{timestamp}.png"
        output_path = user_output_dir / output_filename

        print(f"Generating image with prompt: {prompt}")

        # Generate image
        image = self.pipeline(
            prompt=prompt,
            num_inference_steps=30,
            guidance_scale=7.5,
        ).images[0]

        # Save image
        image.save(str(output_path))
        print(f"Image saved to: {output_path}")

        # Unload LoRAs for next generation
        if loras:
            self.pipeline.unload_lora_weights()

        return f"/outputs/{user_id}/{output_filename}"

    def cleanup(self):
        """Clean up resources"""
        if self.pipeline is not None:
            del self.pipeline
            torch.cuda.empty_cache()
            self.pipeline = None
