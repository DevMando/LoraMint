"""
Core Training Loop for DreamBooth-LoRA SDXL Training

Optimized for RTX 3080 10GB with:
- Gradient checkpointing
- Mixed precision (FP16)
- 8-bit Adam optimizer
- LoRA (only training ~0.1% of parameters)
"""

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
import gc
import json

from diffusers import (
    AutoencoderKL,
    DDPMScheduler,
    StableDiffusionXLPipeline,
    UNet2DConditionModel,
)
from diffusers.optimization import get_scheduler
from transformers import AutoTokenizer, CLIPTextModel, CLIPTextModelWithProjection
from peft import LoraConfig, get_peft_model
from peft.utils import get_peft_model_state_dict
from safetensors.torch import save_file

from .training_config import LoraTrainingConfig
from .dreambooth_dataset import DreamBoothDataset, collate_fn


class LoraTrainingLoop:
    """
    Core training loop for DreamBooth-LoRA SDXL training.

    Uses PEFT library for efficient LoRA training with memory optimizations
    suitable for consumer GPUs (8-12GB VRAM).
    """

    def __init__(
        self,
        config: LoraTrainingConfig,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the training loop.

        Args:
            config: Training configuration
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.progress_callback = progress_callback
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # These will be set during training
        self.tokenizer_one = None
        self.tokenizer_two = None
        self.noise_scheduler = None
        self.text_encoder_one = None
        self.text_encoder_two = None
        self.vae = None
        self.unet = None

    def _report_progress(
        self,
        step: int,
        total_steps: int,
        loss: float,
        message: str,
        phase: str = "training"
    ):
        """Report training progress via callback"""
        if self.progress_callback:
            self.progress_callback({
                "event": "progress",
                "phase": phase,
                "step": step,
                "total_steps": total_steps,
                "loss": loss,
                "message": message,
                "percentage": (step / total_steps) * 100 if total_steps > 0 else 0
            })
        print(f"[{phase}] {message} - Step {step}/{total_steps}, Loss: {loss:.4f}")

    def _load_models(self):
        """Load and prepare models for training"""
        self._report_progress(0, 7, 0.0, "Loading tokenizers (1/7)...", "loading_models")
        print("Loading tokenizers...")
        self.tokenizer_one = AutoTokenizer.from_pretrained(
            self.config.pretrained_model_name,
            subfolder="tokenizer",
            use_fast=False,
        )
        self.tokenizer_two = AutoTokenizer.from_pretrained(
            self.config.pretrained_model_name,
            subfolder="tokenizer_2",
            use_fast=False,
        )

        self._report_progress(1, 7, 0.0, "Loading noise scheduler (2/7)...", "loading_models")
        print("Loading noise scheduler...")
        self.noise_scheduler = DDPMScheduler.from_pretrained(
            self.config.pretrained_model_name,
            subfolder="scheduler",
        )

        self._report_progress(2, 7, 0.0, "Loading text encoders (3/7)...", "loading_models")
        print("Loading text encoders...")
        self.text_encoder_one = CLIPTextModel.from_pretrained(
            self.config.pretrained_model_name,
            subfolder="text_encoder",
            torch_dtype=torch.float16,
        )
        self.text_encoder_two = CLIPTextModelWithProjection.from_pretrained(
            self.config.pretrained_model_name,
            subfolder="text_encoder_2",
            torch_dtype=torch.float16,
        )

        self._report_progress(3, 7, 0.0, "Loading VAE (4/7)...", "loading_models")
        print("Loading VAE...")
        # Use the fixed SDXL VAE for better stability
        if self.config.pretrained_vae_name:
            self.vae = AutoencoderKL.from_pretrained(
                self.config.pretrained_vae_name,
                torch_dtype=torch.float16,
            )
        else:
            self.vae = AutoencoderKL.from_pretrained(
                self.config.pretrained_model_name,
                subfolder="vae",
                torch_dtype=torch.float16,
            )

        self._report_progress(4, 7, 0.0, "Loading UNet (5/7)...", "loading_models")
        print("Loading UNet...")
        self.unet = UNet2DConditionModel.from_pretrained(
            self.config.pretrained_model_name,
            subfolder="unet",
            torch_dtype=torch.float16,
        )

        self._report_progress(5, 7, 0.0, "Moving models to GPU (6/7)...", "loading_models")
        # Freeze all base models
        self.text_encoder_one.requires_grad_(False)
        self.text_encoder_two.requires_grad_(False)
        self.vae.requires_grad_(False)
        self.unet.requires_grad_(False)

        # Move to device - UNet goes to GPU, others stay on CPU to save VRAM
        # Text encoders and VAE are only used for preprocessing, not during training loop
        print("Moving UNet to GPU (text encoders stay on CPU to save memory)...")
        # Text encoders on CPU need FP32 (CPU doesn't support FP16 LayerNorm)
        self.text_encoder_one.to("cpu", dtype=torch.float32)
        self.text_encoder_two.to("cpu", dtype=torch.float32)
        self.vae.to(self.device)  # VAE needed for encoding images
        self.unet.to(self.device)  # UNet is trained

        # Configure LoRA for UNet
        self._report_progress(6, 7, 0.0, "Applying LoRA configuration (7/7)...", "loading_models")
        print(f"Applying LoRA config (rank={self.config.lora_rank})...")
        lora_config = LoraConfig(
            r=self.config.lora_rank,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            init_lora_weights="gaussian",
            target_modules=self.config.target_modules,
        )

        # Apply LoRA to UNet
        self.unet = get_peft_model(self.unet, lora_config)
        self.unet.print_trainable_parameters()

        # Enable memory optimizations
        if self.config.gradient_checkpointing:
            self.unet.enable_gradient_checkpointing()
            print("Gradient checkpointing enabled")

        # Enable xformers if available
        if self.config.enable_xformers:
            try:
                self.unet.enable_xformers_memory_efficient_attention()
                print("xFormers memory efficient attention enabled")
            except Exception as e:
                print(f"xFormers not available: {e}")

    def _generate_class_images(self, class_data_dir: Path, num_images: int):
        """Generate class images for prior preservation"""
        class_data_dir.mkdir(parents=True, exist_ok=True)

        existing = list(class_data_dir.glob("*.png"))
        if len(existing) >= num_images:
            print(f"Class images already exist at {class_data_dir} ({len(existing)} images)")
            return

        num_to_generate = num_images - len(existing)
        print(f"Generating {num_to_generate} class images for prior preservation...")
        print("Loading image generation pipeline for class images (this may take 1-2 minutes)...")

        self._report_progress(
            step=0,
            total_steps=num_to_generate,
            loss=0.0,
            message="Loading pipeline for class image generation...",
            phase="class_generation"
        )

        # Create temporary pipeline for generation
        pipeline = StableDiffusionXLPipeline.from_pretrained(
            self.config.pretrained_model_name,
            torch_dtype=torch.float16,
            use_safetensors=True,
        ).to(self.device)

        pipeline.set_progress_bar_config(disable=True)

        # Enable memory optimizations
        if self.config.enable_xformers:
            try:
                pipeline.enable_xformers_memory_efficient_attention()
            except:
                pass

        for i in range(num_to_generate):
            self._report_progress(
                step=i + 1,
                total_steps=num_to_generate,
                loss=0.0,
                message=f"Generating class image {i + 1}/{num_to_generate}",
                phase="class_generation"
            )

            image = pipeline(
                self.config.class_prompt,
                num_inference_steps=25,
                guidance_scale=5.0,
            ).images[0]

            image.save(class_data_dir / f"class_{len(existing) + i:04d}.png")

        # Aggressive cleanup to free GPU memory before training
        del pipeline
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        gc.collect()
        torch.cuda.empty_cache()  # Second pass after gc

        # Force Python to release memory
        import time
        time.sleep(2)  # Give CUDA time to fully release memory

        print(f"Class images saved to {class_data_dir}")
        print(f"GPU memory freed. Ready for training model loading.")
        self._report_progress(
            step=num_to_generate,
            total_steps=num_to_generate,
            loss=0.0,
            message=f"Class images complete! Generated {num_to_generate} images.",
            phase="class_generation"
        )

    def _compute_text_embeddings(
        self,
        prompt_ids_one: torch.Tensor,
        prompt_ids_two: torch.Tensor
    ):
        """Compute text embeddings from both SDXL text encoders (on CPU to save GPU memory)"""
        with torch.no_grad():
            # Text encoders run on CPU to save GPU memory
            prompt_embeds_one = self.text_encoder_one(
                prompt_ids_one.to("cpu"),
                output_hidden_states=True,
            )
            pooled_prompt_embeds = prompt_embeds_one[0]
            prompt_embeds_one = prompt_embeds_one.hidden_states[-2]

            prompt_embeds_two = self.text_encoder_two(
                prompt_ids_two.to("cpu"),
                output_hidden_states=True,
            )
            pooled_prompt_embeds_two = prompt_embeds_two[0]
            prompt_embeds_two = prompt_embeds_two.hidden_states[-2]

        # Concatenate embeddings and move to GPU as FP16 (SDXL uses both encoders)
        prompt_embeds = torch.cat([prompt_embeds_one, prompt_embeds_two], dim=-1).to(self.device, dtype=torch.float16)

        return prompt_embeds, pooled_prompt_embeds_two.to(self.device, dtype=torch.float16)

    def train(self, instance_image_paths: List[str]) -> str:
        """
        Run the training loop.

        Args:
            instance_image_paths: Paths to training images

        Returns:
            Path to the saved LoRA weights file
        """
        print(f"\n{'='*60}")
        print(f"Starting LoRA Training: {self.config.lora_name}")
        print(f"Trigger word: {self.config.trigger_word}")
        print(f"Instance prompt: {self.config.instance_prompt}")
        print(f"Number of training images: {len(instance_image_paths)}")
        print(f"Device: {self.device}")
        print(f"{'='*60}\n")

        # Setup class images directory for prior preservation
        class_data_dir = None
        if self.config.with_prior_preservation:
            class_data_dir = self.config.output_dir / ".class_images"
            self._report_progress(0, 100, 0.0, "Generating class images...", "setup")
            self._generate_class_images(class_data_dir, self.config.num_class_images)

        # Load models
        print("\nLoading training models (this may take 1-2 minutes)...")
        self._report_progress(0, 100, 0.0, "Loading training models...", "setup")
        self._load_models()
        print("Training models loaded successfully!")

        # Create dataset
        print("Creating dataset...")
        train_dataset = DreamBoothDataset(
            instance_data_paths=instance_image_paths,
            instance_prompt=self.config.instance_prompt,
            tokenizer_one=self.tokenizer_one,
            tokenizer_two=self.tokenizer_two,
            size=self.config.resolution,
            center_crop=self.config.center_crop,
            class_data_dir=class_data_dir if self.config.with_prior_preservation else None,
            class_prompt=self.config.class_prompt,
            num_repeats=self.config.num_train_epochs,
        )

        train_dataloader = DataLoader(
            train_dataset,
            batch_size=self.config.train_batch_size,
            shuffle=True,
            collate_fn=collate_fn,
            num_workers=0,  # Avoid multiprocessing issues on Windows
        )

        # Setup optimizer
        print("Setting up optimizer...")
        optimizer_class = torch.optim.AdamW

        if self.config.use_8bit_adam:
            try:
                import bitsandbytes as bnb
                optimizer_class = bnb.optim.AdamW8bit
                print("Using 8-bit Adam optimizer")
            except ImportError:
                print("bitsandbytes not available, using standard AdamW")

        trainable_params = [p for p in self.unet.parameters() if p.requires_grad]
        optimizer = optimizer_class(
            trainable_params,
            lr=self.config.learning_rate,
            betas=(0.9, 0.999),
            weight_decay=1e-2,
            eps=1e-8,
        )

        # Calculate total steps
        num_update_steps_per_epoch = max(
            len(train_dataloader) // self.config.gradient_accumulation_steps, 1
        )

        if self.config.max_train_steps is None:
            total_steps = len(train_dataloader) // self.config.gradient_accumulation_steps
        else:
            total_steps = self.config.max_train_steps

        print(f"Total training steps: {total_steps}")

        # Setup learning rate scheduler
        lr_scheduler = get_scheduler(
            self.config.lr_scheduler,
            optimizer=optimizer,
            num_warmup_steps=self.config.lr_warmup_steps,
            num_training_steps=total_steps,
        )

        # Training loop
        self.unet.train()
        global_step = 0
        running_loss = 0.0

        self._report_progress(0, total_steps, 0.0, "Starting training...", "training")

        for step, batch in enumerate(train_dataloader):
            if global_step >= total_steps:
                break

            # Get latents from VAE
            with torch.no_grad():
                latents = self.vae.encode(
                    batch["instance_images"].to(self.device, dtype=torch.float16)
                ).latent_dist.sample()
                latents = latents * self.vae.config.scaling_factor

            # Sample noise
            noise = torch.randn_like(latents)
            bsz = latents.shape[0]

            # Sample random timesteps
            timesteps = torch.randint(
                0, self.noise_scheduler.config.num_train_timesteps,
                (bsz,), device=self.device
            ).long()

            # Add noise to latents
            noisy_latents = self.noise_scheduler.add_noise(latents, noise, timesteps)

            # Get text embeddings
            prompt_embeds, pooled_prompt_embeds = self._compute_text_embeddings(
                batch["instance_prompt_ids_one"],
                batch["instance_prompt_ids_two"]
            )

            # SDXL additional embeddings (original size, crop coords, target size)
            add_time_ids = torch.tensor([
                [self.config.resolution, self.config.resolution, 0, 0,
                 self.config.resolution, self.config.resolution]
            ], device=self.device, dtype=torch.float16).repeat(bsz, 1)

            added_cond_kwargs = {
                "text_embeds": pooled_prompt_embeds.to(dtype=torch.float16),
                "time_ids": add_time_ids,
            }

            # Predict noise residual
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                model_pred = self.unet(
                    noisy_latents,
                    timesteps,
                    encoder_hidden_states=prompt_embeds.to(dtype=torch.float16),
                    added_cond_kwargs=added_cond_kwargs,
                    return_dict=False,
                )[0]

            # Calculate loss
            target = noise
            loss = F.mse_loss(model_pred.float(), target.float(), reduction="mean")

            # Prior preservation loss
            if self.config.with_prior_preservation and "class_images" in batch:
                with torch.no_grad():
                    class_latents = self.vae.encode(
                        batch["class_images"].to(self.device, dtype=torch.float16)
                    ).latent_dist.sample()
                    class_latents = class_latents * self.vae.config.scaling_factor

                class_noise = torch.randn_like(class_latents)
                class_timesteps = torch.randint(
                    0, self.noise_scheduler.config.num_train_timesteps,
                    (bsz,), device=self.device
                ).long()
                noisy_class_latents = self.noise_scheduler.add_noise(
                    class_latents, class_noise, class_timesteps
                )

                class_prompt_embeds, class_pooled = self._compute_text_embeddings(
                    batch["class_prompt_ids_one"],
                    batch["class_prompt_ids_two"]
                )

                class_added_cond = {
                    "text_embeds": class_pooled.to(dtype=torch.float16),
                    "time_ids": add_time_ids,
                }

                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    class_pred = self.unet(
                        noisy_class_latents,
                        class_timesteps,
                        encoder_hidden_states=class_prompt_embeds.to(dtype=torch.float16),
                        added_cond_kwargs=class_added_cond,
                        return_dict=False,
                    )[0]

                prior_loss = F.mse_loss(class_pred.float(), class_noise.float())
                loss = loss + self.config.prior_loss_weight * prior_loss

            # Backward pass with gradient accumulation
            loss = loss / self.config.gradient_accumulation_steps
            loss.backward()

            running_loss += loss.item()

            # Update weights
            if (step + 1) % self.config.gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(trainable_params, 1.0)
                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()
                global_step += 1

                avg_loss = running_loss * self.config.gradient_accumulation_steps
                running_loss = 0.0

                # Report progress every 10 steps or at completion
                if global_step % 10 == 0 or global_step == total_steps:
                    self._report_progress(
                        step=global_step,
                        total_steps=total_steps,
                        loss=avg_loss,
                        message=f"Training step {global_step}/{total_steps}",
                        phase="training"
                    )

        # Save the trained LoRA
        self._report_progress(total_steps, total_steps, 0.0, "Saving LoRA weights...", "saving")
        output_path = self._save_lora_weights()

        # Cleanup
        self._cleanup()

        print(f"\n{'='*60}")
        print(f"Training complete!")
        print(f"LoRA saved to: {output_path}")
        print(f"Trigger word: {self.config.trigger_word}")
        print(f"{'='*60}\n")

        return output_path

    def _save_lora_weights(self) -> str:
        """Save LoRA weights in safetensors format compatible with load_lora_weights()"""
        # Get LoRA state dict
        unet_lora_state_dict = get_peft_model_state_dict(self.unet)

        # Convert to diffusers format for compatibility with load_lora_weights()
        converted_state_dict = {}
        for key, value in unet_lora_state_dict.items():
            # Remove the base_model.model. prefix from PEFT
            new_key = key.replace("base_model.model.", "")
            # Add unet. prefix for diffusers compatibility
            converted_state_dict[f"unet.{new_key}"] = value.to(torch.float16).contiguous()

        # Prepare metadata
        metadata = {
            "format": "pt",
            "trigger_word": self.config.trigger_word,
            "lora_name": self.config.lora_name,
            "instance_prompt": self.config.instance_prompt,
            "lora_rank": str(self.config.lora_rank),
            "lora_alpha": str(self.config.lora_alpha),
            "base_model": self.config.pretrained_model_name,
        }

        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Save as safetensors
        output_file = self.config.output_dir / f"{self.config.lora_name}.safetensors"
        save_file(converted_state_dict, str(output_file), metadata=metadata)

        # Also save a metadata JSON for easy reference
        metadata_file = self.config.output_dir / f"{self.config.lora_name}_metadata.json"
        full_metadata = {
            **metadata,
            "learning_rate": self.config.learning_rate,
            "num_train_epochs": self.config.num_train_epochs,
            "resolution": self.config.resolution,
            "with_prior_preservation": self.config.with_prior_preservation,
        }
        with open(metadata_file, "w") as f:
            json.dump(full_metadata, f, indent=2)

        print(f"LoRA weights saved to: {output_file}")
        print(f"Metadata saved to: {metadata_file}")

        return str(output_file)

    def _cleanup(self):
        """Free GPU memory"""
        print("Cleaning up GPU memory...")

        del self.unet
        del self.vae
        del self.text_encoder_one
        del self.text_encoder_two
        del self.noise_scheduler
        del self.tokenizer_one
        del self.tokenizer_two

        self.unet = None
        self.vae = None
        self.text_encoder_one = None
        self.text_encoder_two = None
        self.noise_scheduler = None
        self.tokenizer_one = None
        self.tokenizer_two = None

        torch.cuda.empty_cache()
        gc.collect()
        print("GPU memory cleaned up")
