from pathlib import Path
from typing import List
import shutil
import uuid
from fastapi import UploadFile
import os

class FileHandler:
    def __init__(self):
        # Use absolute paths based on this file's location
        base_dir = Path(__file__).resolve().parent.parent.parent.parent  # LoraMint/
        self.loras_base_path = base_dir / "data" / "loras"
        self.outputs_base_path = base_dir / "data" / "outputs"
        self.temp_base_path = base_dir / "data" / "temp"

        # Create directories if they don't exist
        self.loras_base_path.mkdir(parents=True, exist_ok=True)
        self.outputs_base_path.mkdir(parents=True, exist_ok=True)
        self.temp_base_path.mkdir(parents=True, exist_ok=True)

    async def save_temp_images(self, images: List[UploadFile]) -> List[str]:
        """
        Save uploaded images to temporary directory

        Args:
            images: List of uploaded files

        Returns:
            List of paths to saved temporary files
        """
        temp_paths = []
        temp_dir = self.temp_base_path / str(uuid.uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)

        for idx, image in enumerate(images):
            # Generate temporary filename
            file_extension = Path(image.filename).suffix if image.filename else ".jpg"
            temp_filename = f"image_{idx}{file_extension}"
            temp_path = temp_dir / temp_filename

            # Save file
            with open(temp_path, "wb") as f:
                content = await image.read()
                f.write(content)

            temp_paths.append(str(temp_path))

        return temp_paths

    def cleanup_temp_files(self, temp_paths: List[str]):
        """
        Clean up temporary files

        Args:
            temp_paths: List of temporary file paths to delete
        """
        if not temp_paths:
            return

        # Get the parent directory of the first temp file
        temp_dir = Path(temp_paths[0]).parent

        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")

    def get_user_loras(self, user_id: str) -> List[dict]:
        """
        Get list of LoRA files for a user

        Args:
            user_id: User identifier

        Returns:
            List of LoRA file information
        """
        user_lora_dir = self.loras_base_path / user_id

        if not user_lora_dir.exists():
            return []

        loras = []
        for lora_file in user_lora_dir.glob("*.safetensors"):
            loras.append({
                "name": lora_file.stem,
                "fileName": lora_file.name,
                "filePath": str(lora_file),
                "fileSize": lora_file.stat().st_size,
                "createdAt": lora_file.stat().st_ctime
            })

        return sorted(loras, key=lambda x: x["createdAt"], reverse=True)

    def get_user_images(self, user_id: str) -> List[dict]:
        """
        Get list of generated images for a user

        Args:
            user_id: User identifier

        Returns:
            List of image file information
        """
        user_output_dir = self.outputs_base_path / user_id

        if not user_output_dir.exists():
            return []

        images = []
        image_extensions = {".png", ".jpg", ".jpeg"}

        for image_file in user_output_dir.iterdir():
            if image_file.suffix.lower() in image_extensions:
                images.append({
                    "fileName": image_file.name,
                    "filePath": str(image_file),
                    "url": f"/outputs/{user_id}/{image_file.name}",
                    "createdAt": image_file.stat().st_ctime
                })

        return sorted(images, key=lambda x: x["createdAt"], reverse=True)

    def get_lora_path(self, user_id: str, lora_filename: str) -> Path:
        """Get full path to a LoRA file"""
        return self.loras_base_path / user_id / lora_filename

    def get_output_path(self, user_id: str, filename: str) -> Path:
        """Get full path to an output image file"""
        return self.outputs_base_path / user_id / filename
