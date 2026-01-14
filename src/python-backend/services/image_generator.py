import torch
import asyncio
import concurrent.futures
from diffusers import StableDiffusionXLPipeline, AutoPipelineForText2Image
from pathlib import Path
import os
from typing import List, Optional, AsyncGenerator, TYPE_CHECKING
from datetime import datetime

from models.request_models import LoraReference
from services.progress_callback import ProgressCallback, ProgressEvent

if TYPE_CHECKING:
    from services.model_manager import ModelManager


class ImageGenerator:
    def __init__(self, model_manager: Optional["ModelManager"] = None):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_manager = model_manager

        # Use absolute paths based on this file's location
        base_dir = Path(__file__).resolve().parent.parent.parent.parent  # LoraMint/
        self.outputs_base_path = base_dir / "data" / "outputs"
        self.loras_base_path = base_dir / "data" / "loras"

        # Create outputs directory if it doesn't exist
        self.outputs_base_path.mkdir(parents=True, exist_ok=True)

    def set_model_manager(self, model_manager: "ModelManager"):
        """Set the model manager for this generator."""
        self.model_manager = model_manager

    def is_gpu_available(self) -> bool:
        """Check if GPU is available"""
        return torch.cuda.is_available()

    @property
    def pipeline(self):
        """Get the current pipeline from model manager."""
        if self.model_manager:
            return self.model_manager.get_pipeline()
        return None

    def load_pipeline(self, model_id: Optional[str] = None):
        """Load the Stable Diffusion pipeline via model manager."""
        if self.model_manager is None:
            raise RuntimeError("ModelManager not set. Please configure a model first.")

        # If no model is loaded, we can't proceed
        if self.model_manager.get_pipeline() is None:
            if model_id:
                success = self.model_manager.load_model(model_id)
                if not success:
                    raise RuntimeError(f"Failed to load model: {model_id}")
            else:
                raise RuntimeError("No model loaded. Please select and download a model first.")

        print(f"Using model: {self.model_manager.get_current_model_id()}")

    def load_loras(self, user_id: str, loras: Optional[List[LoraReference]]) -> bool:
        """Load LoRA adapters into the pipeline. Returns True if any LoRA was loaded."""
        if not loras:
            return False

        # Check if current model supports LoRA
        if self.model_manager and not self.model_manager.supports_lora():
            print(f"Warning: Current model does not support LoRA. Skipping LoRA loading.")
            return False

        pipeline = self.pipeline
        if pipeline is None:
            print("Warning: No pipeline loaded, cannot load LoRAs")
            return False

        loaded_any = False
        for lora in loras:
            lora_path = self.loras_base_path / user_id / lora.file
            if lora_path.exists():
                try:
                    print(f"Loading LoRA: {lora.file} with strength {lora.strength}")
                    pipeline.load_lora_weights(
                        str(lora_path.parent),
                        weight_name=lora.file,
                        adapter_name=lora.file.replace('.safetensors', '')
                    )
                    # Set adapter strength
                    pipeline.set_adapters(
                        [lora.file.replace('.safetensors', '')],
                        adapter_weights=[lora.strength]
                    )
                    loaded_any = True
                except Exception as e:
                    print(f"Warning: Failed to load LoRA {lora.file}: {e}")
                    print("Continuing without this LoRA...")
            else:
                print(f"Warning: LoRA file not found: {lora_path}")

        return loaded_any

    def get_inference_steps(self) -> int:
        """Get the recommended inference steps for the current model."""
        if self.model_manager:
            return self.model_manager.get_inference_steps()
        return 30  # Default fallback

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

        pipeline = self.pipeline
        if pipeline is None:
            raise RuntimeError("No pipeline available")

        # Load LoRAs if specified
        loras_loaded = False
        if loras:
            loras_loaded = self.load_loras(user_id, loras)

        # Create user output directory
        user_output_dir = self.outputs_base_path / user_id
        user_output_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"generated_{timestamp}.png"
        output_path = user_output_dir / output_filename

        # Get inference steps from model config
        num_steps = self.get_inference_steps()

        print(f"Generating image with prompt: {prompt} ({num_steps} steps)")

        # Generate image
        image = pipeline(
            prompt=prompt,
            num_inference_steps=num_steps,
            guidance_scale=7.5,
        ).images[0]

        # Save image
        image.save(str(output_path))
        print(f"Image saved to: {output_path}")

        # Unload LoRAs for next generation
        if loras_loaded:
            try:
                pipeline.unload_lora_weights()
            except Exception as e:
                print(f"Warning: Failed to unload LoRA weights: {e}")

        return f"/outputs/{user_id}/{output_filename}"

    async def generate_with_progress(
        self,
        prompt: str,
        user_id: str,
        loras: Optional[List[LoraReference]] = None,
        num_inference_steps: Optional[int] = None
    ) -> AsyncGenerator[ProgressEvent, None]:
        """
        Generate an image with progress streaming via callback.
        Yields ProgressEvent objects for each inference step.

        Args:
            prompt: Text prompt for image generation
            user_id: User identifier for organizing outputs
            loras: Optional list of LoRA models to apply
            num_inference_steps: Number of inference steps (uses model default if not specified)

        Yields:
            ProgressEvent objects with progress updates
        """
        # Load pipeline if not already loaded
        self.load_pipeline()

        pipeline = self.pipeline
        if pipeline is None:
            raise RuntimeError("No pipeline available")

        # Get inference steps from model config if not specified
        if num_inference_steps is None:
            num_inference_steps = self.get_inference_steps()

        # Load LoRAs if specified
        loras_loaded = False
        if loras:
            loras_loaded = self.load_loras(user_id, loras)

        # Create user output directory
        user_output_dir = self.outputs_base_path / user_id
        user_output_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"generated_{timestamp}.png"
        output_path = user_output_dir / output_filename

        print(f"Generating image with prompt: {prompt} ({num_inference_steps} steps)")

        # Create progress callback
        callback = ProgressCallback(total_steps=num_inference_steps)
        loop = asyncio.get_event_loop()
        callback.set_loop(loop)

        # Capture pipeline in closure for thread safety
        active_pipeline = pipeline

        # Function to run pipeline (will be executed in thread pool)
        def run_pipeline():
            return active_pipeline(
                prompt=prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=7.5,
                callback=callback,
                callback_steps=1  # Call on every step
            ).images[0]

        # Run generation in thread pool to not block event loop
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = loop.run_in_executor(executor, run_pipeline)

            # Stream progress events while generation is running
            while not future.done():
                try:
                    # Wait for progress event with timeout
                    event = await asyncio.wait_for(
                        callback.queue.get(),
                        timeout=0.5
                    )
                    yield event
                except asyncio.TimeoutError:
                    # No event yet, continue waiting
                    continue

            # Drain any remaining queued events
            while not callback.queue.empty():
                try:
                    event = callback.queue.get_nowait()
                    yield event
                except asyncio.QueueEmpty:
                    break

            # Get result from future
            try:
                image = future.result()
                image.save(str(output_path))
                print(f"Image saved to: {output_path}")

                # Unload LoRAs for next generation
                if loras_loaded:
                    try:
                        active_pipeline.unload_lora_weights()
                    except Exception as e:
                        print(f"Warning: Failed to unload LoRA weights: {e}")

                # Yield completion event
                await callback.complete(f"/outputs/{user_id}/{output_filename}")
                yield await callback.queue.get()

            except Exception as e:
                print(f"Error during generation: {e}")
                await callback.error(str(e))
                yield await callback.queue.get()

    def cleanup(self):
        """Clean up resources via model manager."""
        if self.model_manager:
            self.model_manager.cleanup()
