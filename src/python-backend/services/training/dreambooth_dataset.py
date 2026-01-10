"""
DreamBooth Dataset for SDXL LoRA Training
"""

import torch
from torch.utils.data import Dataset
from PIL import Image
from pathlib import Path
from typing import List, Optional
import random
from torchvision import transforms


class DreamBoothDataset(Dataset):
    """
    Dataset for DreamBooth-style training with SDXL.

    Handles both instance images (the subject to learn) and optional
    class images (for prior preservation to prevent overfitting).
    """

    def __init__(
        self,
        instance_data_paths: List[str],
        instance_prompt: str,
        tokenizer_one,
        tokenizer_two,
        size: int = 1024,
        center_crop: bool = True,
        class_data_dir: Optional[Path] = None,
        class_prompt: Optional[str] = None,
        num_repeats: int = 100,
    ):
        """
        Initialize the dataset.

        Args:
            instance_data_paths: Paths to instance images (1-5 images)
            instance_prompt: The prompt with trigger word
            tokenizer_one: CLIP tokenizer for text encoder 1
            tokenizer_two: CLIP tokenizer for text encoder 2
            size: Image resolution (1024 for SDXL)
            center_crop: Whether to center crop images
            class_data_dir: Directory containing class images for prior preservation
            class_prompt: Prompt for class images
            num_repeats: Number of times to repeat the dataset per epoch
        """
        self.size = size
        self.center_crop = center_crop
        self.instance_prompt = instance_prompt
        self.class_prompt = class_prompt
        self.tokenizer_one = tokenizer_one
        self.tokenizer_two = tokenizer_two
        self.num_repeats = num_repeats

        # Load instance images
        self.instance_images = []
        for path in instance_data_paths:
            img = Image.open(path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            self.instance_images.append(img)

        self.num_instance_images = len(self.instance_images)

        # Load class images for prior preservation
        self.class_images = []
        if class_data_dir and Path(class_data_dir).exists():
            class_path = Path(class_data_dir)
            for img_path in sorted(class_path.glob("*.png"))[:100]:  # Limit to 100
                img = Image.open(img_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                self.class_images.append(img)

        self.num_class_images = len(self.class_images)

        # Image transforms
        self.image_transforms = transforms.Compose([
            transforms.Resize(size, interpolation=transforms.InterpolationMode.BILINEAR),
            transforms.CenterCrop(size) if center_crop else transforms.RandomCrop(size),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5]),
        ])

        # Pre-tokenize prompts for efficiency
        self._instance_tokens_one = self._tokenize(tokenizer_one, instance_prompt)
        self._instance_tokens_two = self._tokenize(tokenizer_two, instance_prompt)

        if class_prompt:
            self._class_tokens_one = self._tokenize(tokenizer_one, class_prompt)
            self._class_tokens_two = self._tokenize(tokenizer_two, class_prompt)
        else:
            self._class_tokens_one = None
            self._class_tokens_two = None

    def _tokenize(self, tokenizer, prompt: str) -> torch.Tensor:
        """Tokenize a prompt"""
        return tokenizer(
            prompt,
            truncation=True,
            padding="max_length",
            max_length=77,
            return_tensors="pt",
        ).input_ids.squeeze(0)

    def __len__(self):
        """Return dataset length (with repeats for small datasets)"""
        return self.num_instance_images * self.num_repeats

    def __getitem__(self, index):
        """Get a training example"""
        example = {}

        # Get instance image (cycle through if needed)
        instance_idx = index % self.num_instance_images
        instance_image = self.instance_images[instance_idx]

        # Apply transforms
        example["instance_images"] = self.image_transforms(instance_image)
        example["instance_prompt"] = self.instance_prompt
        example["instance_prompt_ids_one"] = self._instance_tokens_one
        example["instance_prompt_ids_two"] = self._instance_tokens_two

        # Add class image for prior preservation
        if self.class_images and self._class_tokens_one is not None:
            class_idx = random.randint(0, self.num_class_images - 1)
            class_image = self.class_images[class_idx]

            example["class_images"] = self.image_transforms(class_image)
            example["class_prompt"] = self.class_prompt
            example["class_prompt_ids_one"] = self._class_tokens_one
            example["class_prompt_ids_two"] = self._class_tokens_two

        return example


def collate_fn(examples):
    """
    Custom collate function for DataLoader.
    Handles variable presence of class images.
    """
    batch = {
        "instance_images": torch.stack([e["instance_images"] for e in examples]),
        "instance_prompt_ids_one": torch.stack([e["instance_prompt_ids_one"] for e in examples]),
        "instance_prompt_ids_two": torch.stack([e["instance_prompt_ids_two"] for e in examples]),
    }

    # Only add class data if present in all examples
    if all("class_images" in e for e in examples):
        batch["class_images"] = torch.stack([e["class_images"] for e in examples])
        batch["class_prompt_ids_one"] = torch.stack([e["class_prompt_ids_one"] for e in examples])
        batch["class_prompt_ids_two"] = torch.stack([e["class_prompt_ids_two"] for e in examples])

    return batch
