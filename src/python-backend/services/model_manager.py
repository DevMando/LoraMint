"""
Model Manager for handling multiple diffusion models.

Manages model downloading, loading, unloading, and switching between
different models like SDXL Base, SDXL Turbo, and Z-Image Turbo.
"""
import torch
import gc
import json
import os
from pathlib import Path
from typing import Dict, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, asdict
from diffusers import AutoPipelineForText2Image
from huggingface_hub import snapshot_download, HfApi
from huggingface_hub.utils import RepositoryNotFoundError


@dataclass
class ModelConfig:
    """Configuration for a supported model."""
    id: str
    name: str
    huggingface_id: str
    description: str
    min_vram_gb: int
    recommended_vram_gb: int
    inference_steps: int
    speed_rating: str  # "Fast", "Medium"
    quality_rating: str  # "Excellent", "High", "Good"
    estimated_size_gb: int
    supports_lora: bool = True


@dataclass
class GpuInfo:
    """GPU information."""
    available: bool
    name: str = ""
    total_vram_gb: float = 0.0
    free_vram_gb: float = 0.0
    cuda_version: Optional[str] = None


@dataclass
class DownloadProgress:
    """Download progress event."""
    event: str  # "progress", "complete", "error"
    model_id: str
    percentage: float = 0.0
    downloaded_mb: float = 0.0
    total_mb: float = 0.0
    message: Optional[str] = None
    error: Optional[str] = None


# Default model configurations
DEFAULT_MODELS: Dict[str, ModelConfig] = {
    "sdxl-base": ModelConfig(
        id="sdxl-base",
        name="SDXL Base 1.0",
        huggingface_id="stabilityai/stable-diffusion-xl-base-1.0",
        description="The original Stable Diffusion XL model. Best quality and compatibility with LoRAs.",
        min_vram_gb=8,
        recommended_vram_gb=12,
        inference_steps=30,
        speed_rating="Medium",
        quality_rating="High",
        estimated_size_gb=7,
        supports_lora=True
    ),
    "sdxl-turbo": ModelConfig(
        id="sdxl-turbo",
        name="SDXL Turbo",
        huggingface_id="stabilityai/sdxl-turbo",
        description="Distilled SDXL for ultra-fast generation. 4 steps instead of 30.",
        min_vram_gb=8,
        recommended_vram_gb=10,
        inference_steps=4,
        speed_rating="Fast",
        quality_rating="Good",
        estimated_size_gb=7,
        supports_lora=True
    ),
    "z-image-turbo": ModelConfig(
        id="z-image-turbo",
        name="Z-Image Turbo",
        huggingface_id="Tongyi-MAI/Z-Image-Turbo",
        description="Alibaba's high-quality turbo model. Excellent quality with fast generation.",
        min_vram_gb=16,
        recommended_vram_gb=24,
        inference_steps=8,
        speed_rating="Fast",
        quality_rating="Excellent",
        estimated_size_gb=12,
        supports_lora=False
    )
}


class ModelManager:
    """
    Manages diffusion model lifecycle including downloading,
    loading, unloading, and switching between models.
    """

    def __init__(self, models_path: Optional[str] = None):
        """
        Initialize the model manager.

        Args:
            models_path: Custom path for storing models. Defaults to data/models.
        """
        base_dir = Path(__file__).resolve().parent.parent.parent.parent  # LoraMint/
        self.models_path = Path(models_path) if models_path else base_dir / "data" / "models"
        self.models_path.mkdir(parents=True, exist_ok=True)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.current_model_id: Optional[str] = None
        self.current_pipeline = None
        self.models = DEFAULT_MODELS.copy()

        print(f"ModelManager initialized. Models path: {self.models_path}")
        print(f"Device: {self.device}")

    def get_gpu_info(self) -> GpuInfo:
        """Get GPU information."""
        if not torch.cuda.is_available():
            return GpuInfo(available=False)

        try:
            gpu_name = torch.cuda.get_device_name(0)
            total_memory = torch.cuda.get_device_properties(0).total_memory
            free_memory = torch.cuda.memory_reserved(0) - torch.cuda.memory_allocated(0)

            # Get actual free memory (more accurate)
            torch.cuda.synchronize()
            free_memory = total_memory - torch.cuda.memory_allocated(0)

            cuda_version = torch.version.cuda

            return GpuInfo(
                available=True,
                name=gpu_name,
                total_vram_gb=total_memory / (1024**3),
                free_vram_gb=free_memory / (1024**3),
                cuda_version=cuda_version
            )
        except Exception as e:
            print(f"Error getting GPU info: {e}")
            return GpuInfo(available=True, name="Unknown GPU")

    def get_available_models(self) -> list:
        """Get list of available models with download status."""
        result = []
        for model in self.models.values():
            model_dict = asdict(model)
            model_dict["is_downloaded"] = self.is_model_downloaded(model.id)
            model_dict["local_path"] = str(self._get_model_path(model.id)) if model_dict["is_downloaded"] else None
            result.append(model_dict)
        return result

    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model."""
        return self.models.get(model_id)

    def _get_model_path(self, model_id: str) -> Path:
        """Get the local path for a model."""
        return self.models_path / model_id

    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if a model is downloaded locally."""
        model_path = self._get_model_path(model_id)
        if not model_path.exists():
            return False

        # Check for essential model files
        essential_files = ["model_index.json", "config.json"]
        for filename in essential_files:
            if (model_path / filename).exists():
                return True

        # Also check in subdirectories (some models have different structures)
        for subdir in model_path.iterdir():
            if subdir.is_dir():
                for filename in essential_files:
                    if (subdir / filename).exists():
                        return True

        return False

    async def download_model(
        self,
        model_id: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> AsyncGenerator[DownloadProgress, None]:
        """
        Download a model from HuggingFace Hub.

        Args:
            model_id: The model ID to download.
            progress_callback: Optional callback for progress updates.

        Yields:
            DownloadProgress events.
        """
        if model_id not in self.models:
            error = DownloadProgress(
                event="error",
                model_id=model_id,
                error=f"Unknown model: {model_id}"
            )
            yield error
            return

        config = self.models[model_id]
        model_path = self._get_model_path(model_id)

        try:
            # Initial progress
            yield DownloadProgress(
                event="progress",
                model_id=model_id,
                percentage=0,
                message=f"Starting download of {config.name}..."
            )

            # Create model directory
            model_path.mkdir(parents=True, exist_ok=True)

            # Download using huggingface_hub
            print(f"Downloading model {config.huggingface_id} to {model_path}")

            yield DownloadProgress(
                event="progress",
                model_id=model_id,
                percentage=5,
                message=f"Connecting to HuggingFace Hub..."
            )

            # Use snapshot_download for efficient downloading
            # This caches properly and handles resume
            # Limit max_workers to prevent overwhelming home networks
            downloaded_path = snapshot_download(
                repo_id=config.huggingface_id,
                local_dir=str(model_path),
                ignore_patterns=["*.md", "README.txt", "LICENSE.txt", "*.gitignore", "*.onnx", "*.onnx_data"],
                max_workers=1  # Single download at a time - gentlest on home networks
            )

            yield DownloadProgress(
                event="progress",
                model_id=model_id,
                percentage=95,
                message="Verifying download..."
            )

            # Verify download
            if self.is_model_downloaded(model_id):
                yield DownloadProgress(
                    event="complete",
                    model_id=model_id,
                    percentage=100,
                    message=f"{config.name} downloaded successfully!"
                )
            else:
                yield DownloadProgress(
                    event="error",
                    model_id=model_id,
                    error="Download completed but model files not found. Please try again."
                )

        except RepositoryNotFoundError:
            yield DownloadProgress(
                event="error",
                model_id=model_id,
                error=f"Model repository not found: {config.huggingface_id}"
            )
        except Exception as e:
            print(f"Error downloading model: {e}")
            yield DownloadProgress(
                event="error",
                model_id=model_id,
                error=str(e)
            )

    def load_model(self, model_id: str) -> bool:
        """
        Load a model into GPU memory.

        Args:
            model_id: The model ID to load.

        Returns:
            True if successful, False otherwise.
        """
        if model_id not in self.models:
            print(f"Unknown model: {model_id}")
            return False

        # Unload current model first
        if self.current_model_id and self.current_model_id != model_id:
            self.unload_model()

        if self.current_model_id == model_id and self.current_pipeline is not None:
            print(f"Model {model_id} already loaded")
            return True

        config = self.models[model_id]
        model_path = self._get_model_path(model_id)

        try:
            print(f"Loading model: {config.name}")

            # Determine source - local path or HuggingFace
            if self.is_model_downloaded(model_id):
                model_source = str(model_path)
                print(f"Loading from local path: {model_source}")
            else:
                model_source = config.huggingface_id
                print(f"Loading from HuggingFace: {model_source}")

            # Load the pipeline
            self.current_pipeline = AutoPipelineForText2Image.from_pretrained(
                model_source,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
            self.current_pipeline = self.current_pipeline.to(self.device)

            self.current_model_id = model_id
            print(f"Model {config.name} loaded successfully on {self.device}")
            return True

        except Exception as e:
            print(f"Error loading model: {e}")
            self.current_model_id = None
            self.current_pipeline = None
            return False

    def unload_model(self):
        """Unload the current model from GPU memory."""
        if self.current_pipeline is not None:
            print(f"Unloading model: {self.current_model_id}")
            del self.current_pipeline
            self.current_pipeline = None

            # Clean up GPU memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()

            print("Model unloaded, GPU memory cleared")

        self.current_model_id = None

    def get_pipeline(self):
        """Get the currently loaded pipeline."""
        return self.current_pipeline

    def get_current_model_id(self) -> Optional[str]:
        """Get the ID of the currently loaded model."""
        return self.current_model_id

    def get_current_model_config(self) -> Optional[ModelConfig]:
        """Get the configuration of the currently loaded model."""
        if self.current_model_id:
            return self.models.get(self.current_model_id)
        return None

    def get_inference_steps(self, model_id: Optional[str] = None) -> int:
        """Get the recommended inference steps for a model."""
        if model_id is None:
            model_id = self.current_model_id

        if model_id and model_id in self.models:
            return self.models[model_id].inference_steps

        return 30  # Default fallback

    def supports_lora(self, model_id: Optional[str] = None) -> bool:
        """Check if a model supports LoRA."""
        if model_id is None:
            model_id = self.current_model_id

        if model_id and model_id in self.models:
            return self.models[model_id].supports_lora

        return True  # Default assume yes

    def cleanup(self):
        """Clean up all resources."""
        self.unload_model()
