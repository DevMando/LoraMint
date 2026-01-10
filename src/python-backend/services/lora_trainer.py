"""
LoRA Trainer Service

Provides DreamBooth-style LoRA training for SDXL using PEFT.
Creates valid .safetensors files compatible with diffusers load_lora_weights().
"""

import torch
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
import asyncio
import concurrent.futures

from .training import LoraTrainingConfig, LoraTrainingLoop


class LoraTrainer:
    """
    Service for training LoRA models using DreamBooth-style training.

    Uses PEFT library with memory optimizations for RTX 3080 10GB.
    """

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Use absolute paths based on this file's location
        base_dir = Path(__file__).resolve().parent.parent.parent.parent  # LoraMint/
        self.loras_base_path = base_dir / "data" / "loras"

        # Create loras directory if it doesn't exist
        self.loras_base_path.mkdir(parents=True, exist_ok=True)

        print(f"LoRA Trainer initialized")
        print(f"Device: {self.device}")
        print(f"LoRAs base path: {self.loras_base_path}")

    async def train(
        self,
        lora_name: str,
        user_id: str,
        image_paths: List[str],
        num_train_epochs: Optional[int] = None,
        learning_rate: float = 1e-4,
        lora_rank: int = 8,
        trigger_word: Optional[str] = None,
        with_prior_preservation: bool = True,
        fast_mode: bool = False,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> str:
        """
        Train a LoRA model using DreamBooth-style training.

        Args:
            lora_name: Name for the LoRA model
            user_id: User identifier for storage organization
            image_paths: Paths to training images (1-5 images)
            num_train_epochs: Training epochs (auto-calculated based on image count if None)
            learning_rate: Learning rate (default 1e-4)
            lora_rank: LoRA rank (default 8, higher = more capacity)
            trigger_word: Custom trigger word (auto-generated as sks_<name> if None)
            with_prior_preservation: Use prior preservation to prevent overfitting
            fast_mode: Enable fast mode (fewer class images, reduced epochs)
            progress_callback: Optional callback for progress updates

        Returns:
            Path to trained .safetensors file
        """
        # Validate inputs
        if not image_paths:
            raise ValueError("At least one training image is required")
        if len(image_paths) > 5:
            raise ValueError("Maximum 5 training images supported")

        # Create user lora directory
        user_lora_dir = self.loras_base_path / user_id
        user_lora_dir.mkdir(parents=True, exist_ok=True)

        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        lora_full_name = f"{lora_name}_{timestamp}"

        # Get recommended settings based on image count if epochs not specified
        if num_train_epochs is None:
            recommended = self.get_recommended_settings(len(image_paths))
            num_train_epochs = recommended["num_train_epochs"]
            if lora_rank == 8:  # Only override if using default
                lora_rank = recommended.get("lora_rank", 8)

        # Create training configuration
        config = LoraTrainingConfig(
            lora_name=lora_full_name,
            user_id=user_id,
            output_dir=user_lora_dir,
            original_name=lora_name,  # Use original name for trigger word
            num_train_epochs=num_train_epochs,
            learning_rate=learning_rate,
            lora_rank=lora_rank,
            trigger_word=trigger_word,
            with_prior_preservation=with_prior_preservation,
            fast_mode=fast_mode,
        )

        print(f"\n{'='*60}")
        print(f"Starting LoRA Training{'  [FAST MODE]' if fast_mode else ''}")
        print(f"{'='*60}")
        print(f"LoRA Name: {lora_name}")
        print(f"User ID: {user_id}")
        print(f"Trigger word: {config.trigger_word}")
        print(f"Number of images: {len(image_paths)}")
        print(f"Epochs: {config.num_train_epochs}")
        print(f"Learning rate: {learning_rate}")
        print(f"LoRA rank: {lora_rank}")
        print(f"Prior preservation: {with_prior_preservation}")
        print(f"Class images: {config.num_class_images}")
        print(f"Fast mode: {fast_mode}")
        print(f"Output directory: {user_lora_dir}")
        print(f"{'='*60}\n")

        # Run training in executor to not block event loop
        loop = asyncio.get_event_loop()

        def run_training():
            trainer = LoraTrainingLoop(config, progress_callback)
            return trainer.train(image_paths)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            output_path = await loop.run_in_executor(executor, run_training)

        print(f"\nTraining complete!")
        print(f"LoRA saved to: {output_path}")
        print(f"Use trigger word '{config.trigger_word}' in your prompts")

        return output_path

    def get_recommended_settings(self, num_images: int) -> dict:
        """
        Get recommended training settings based on image count.

        Args:
            num_images: Number of training images (1-5)

        Returns:
            Dictionary with recommended settings
        """
        if num_images <= 2:
            return {
                "num_train_epochs": 200,
                "learning_rate": 5e-5,
                "lora_rank": 4,
                "with_prior_preservation": True,
                "description": "Few images - using more epochs and lower learning rate"
            }
        elif num_images <= 4:
            return {
                "num_train_epochs": 150,
                "learning_rate": 1e-4,
                "lora_rank": 8,
                "with_prior_preservation": True,
                "description": "Medium dataset - balanced settings"
            }
        else:
            return {
                "num_train_epochs": 100,
                "learning_rate": 1e-4,
                "lora_rank": 8,
                "with_prior_preservation": True,
                "description": "Good dataset size - standard settings"
            }

    def get_user_loras(self, user_id: str) -> List[dict]:
        """
        Get list of LoRA models for a user.

        Args:
            user_id: User identifier

        Returns:
            List of LoRA info dictionaries
        """
        user_lora_dir = self.loras_base_path / user_id
        if not user_lora_dir.exists():
            return []

        loras = []
        for lora_file in user_lora_dir.glob("*.safetensors"):
            # Try to load metadata
            metadata_file = lora_file.with_suffix(".safetensors").with_name(
                lora_file.stem + "_metadata.json"
            )

            metadata = {}
            if metadata_file.exists():
                try:
                    import json
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                except:
                    pass

            loras.append({
                "filename": lora_file.name,
                "path": str(lora_file),
                "size_mb": lora_file.stat().st_size / (1024 * 1024),
                "created": datetime.fromtimestamp(
                    lora_file.stat().st_ctime
                ).isoformat(),
                "trigger_word": metadata.get("trigger_word", "unknown"),
                "lora_rank": metadata.get("lora_rank", "unknown"),
            })

        return sorted(loras, key=lambda x: x["created"], reverse=True)
