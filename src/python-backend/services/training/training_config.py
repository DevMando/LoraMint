"""
Training Configuration for LoRA DreamBooth Training
"""

from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


@dataclass
class LoraTrainingConfig:
    """Configuration for LoRA training with SDXL"""

    # Required parameters
    lora_name: str
    user_id: str
    output_dir: Path

    # Original name (without timestamp) for trigger word generation
    original_name: Optional[str] = None

    # Model settings
    pretrained_model_name: str = "stabilityai/stable-diffusion-xl-base-1.0"
    pretrained_vae_name: Optional[str] = "madebyollin/sdxl-vae-fp16-fix"

    # LoRA hyperparameters
    lora_rank: int = 8                    # LoRA rank (4-32, higher = more capacity)
    lora_alpha: int = 16                  # Usually 2x rank
    lora_dropout: float = 0.1
    target_modules: List[str] = field(default_factory=lambda: [
        "to_k", "to_q", "to_v", "to_out.0"  # Attention layers
    ])

    # Training hyperparameters
    num_train_epochs: int = 100           # For small datasets
    max_train_steps: Optional[int] = None # Override epochs if set
    learning_rate: float = 1e-4
    train_batch_size: int = 1
    gradient_accumulation_steps: int = 4  # Effective batch = 4

    # Trigger word
    instance_prompt_template: str = "a photo of {trigger_word}"
    trigger_word: Optional[str] = None    # Auto-generated if None

    # Prior preservation (prevent overfitting)
    with_prior_preservation: bool = True
    prior_loss_weight: float = 1.0
    class_prompt: str = "a photo"         # Generic class prompt
    num_class_images: int = 50            # Generated class images (reduced for speed)

    # Fast mode (reduces class images and epochs for quicker training)
    fast_mode: bool = False

    # Memory optimization for RTX 3080 10GB
    gradient_checkpointing: bool = True
    mixed_precision: str = "fp16"         # "no", "fp16", "bf16"
    use_8bit_adam: bool = True            # Requires bitsandbytes
    enable_xformers: bool = True

    # Scheduler
    lr_scheduler: str = "cosine"          # "constant", "cosine", "linear"
    lr_warmup_steps: int = 50

    # Validation (disabled by default for speed)
    validation_prompt: Optional[str] = None
    validation_steps: int = 50
    num_validation_images: int = 2

    # Resolution
    resolution: int = 1024                # SDXL native resolution
    center_crop: bool = True

    # Seeds
    seed: int = 42

    def __post_init__(self):
        """Generate trigger word and validation prompt if not provided"""
        # Apply fast mode optimizations
        if self.fast_mode:
            self.num_class_images = 25  # Reduced from 50
            # Reduce epochs by ~25% in fast mode
            self.num_train_epochs = max(50, int(self.num_train_epochs * 0.75))

        if self.trigger_word is None:
            # Use original_name if provided (without timestamp), otherwise use lora_name
            name_for_trigger = self.original_name if self.original_name else self.lora_name
            safe_name = "".join(c for c in name_for_trigger if c.isalnum())
            self.trigger_word = f"sks_{safe_name.lower()}"

        if self.validation_prompt is None:
            self.validation_prompt = self.instance_prompt_template.format(
                trigger_word=self.trigger_word
            )

        # Ensure output_dir is a Path
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

    @property
    def instance_prompt(self) -> str:
        """Get the full instance prompt with trigger word"""
        return self.instance_prompt_template.format(trigger_word=self.trigger_word)

    @classmethod
    def for_image_count(cls, num_images: int, **kwargs) -> "LoraTrainingConfig":
        """
        Create a config with recommended settings based on image count

        Args:
            num_images: Number of training images (1-5)
            **kwargs: Override any config parameters
        """
        if num_images <= 2:
            defaults = {
                "num_train_epochs": 200,
                "learning_rate": 5e-5,
                "lora_rank": 4,
                "with_prior_preservation": True,
            }
        elif num_images <= 4:
            defaults = {
                "num_train_epochs": 150,
                "learning_rate": 1e-4,
                "lora_rank": 8,
                "with_prior_preservation": True,
            }
        else:
            defaults = {
                "num_train_epochs": 100,
                "learning_rate": 1e-4,
                "lora_rank": 8,
                "with_prior_preservation": True,
            }

        # Merge defaults with provided kwargs
        defaults.update(kwargs)
        return cls(**defaults)
