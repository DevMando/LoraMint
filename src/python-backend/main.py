from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import os
import json
from pathlib import Path

from models.request_models import GenerateRequest
from services.image_generator import ImageGenerator
from services.lora_trainer import LoraTrainer
from utils.file_handler import FileHandler

app = FastAPI(title="LoraMint Python Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
image_generator = ImageGenerator()
lora_trainer = LoraTrainer()
file_handler = FileHandler()

@app.get("/")
async def root():
    return {"message": "LoraMint Python Backend API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "gpu_available": image_generator.is_gpu_available()}

@app.post("/generate")
async def generate_image(request: GenerateRequest):
    """
    Generate an image using Stable Diffusion with optional LoRA models
    """
    try:
        print(f"Received generate request: prompt='{request.prompt}', userId='{request.userId}', loras={request.loras}")

        # Generate the image
        image_path = await image_generator.generate(
            prompt=request.prompt,
            user_id=request.userId,
            loras=request.loras
        )

        return JSONResponse(content={
            "success": True,
            "image_path": image_path,
            "message": "Image generated successfully"
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error generating image: {error_details}")
        raise HTTPException(status_code=500, detail=f"{str(e)}\n\nTraceback:\n{error_details}")


@app.post("/generate/stream")
async def generate_image_stream(request: GenerateRequest):
    """
    Generate an image with SSE progress streaming.
    Returns Server-Sent Events with progress updates.
    """
    async def event_generator():
        try:
            print(f"Received streaming generate request: prompt='{request.prompt}', userId='{request.userId}', loras={request.loras}")

            async for event in image_generator.generate_with_progress(
                prompt=request.prompt,
                user_id=request.userId,
                loras=request.loras
            ):
                # Format as SSE
                data = json.dumps(event.to_dict())
                yield f"data: {data}\n\n"

                # If complete or error, end stream
                if event.event in ("complete", "error"):
                    break

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in streaming generation: {error_details}")
            error_data = json.dumps({
                "event": "error",
                "success": False,
                "error": str(e),
                "message": "Unexpected error during generation"
            })
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.post("/train-lora")
async def train_lora(
    lora_name: str = Form(...),
    user_id: str = Form(...),
    images: List[UploadFile] = File(...)
):
    """
    Train a LoRA model using uploaded reference images
    """
    try:
        # Validate inputs
        if not images or len(images) == 0:
            raise HTTPException(status_code=400, detail="At least one image is required")

        if len(images) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 images allowed")

        # Save uploaded images temporarily
        temp_image_paths = await file_handler.save_temp_images(images)

        # Train the LoRA
        lora_path = await lora_trainer.train(
            lora_name=lora_name,
            user_id=user_id,
            image_paths=temp_image_paths
        )

        # Clean up temporary files
        file_handler.cleanup_temp_files(temp_image_paths)

        return JSONResponse(content={
            "success": True,
            "lora_path": lora_path,
            "message": f"LoRA '{lora_name}' trained successfully"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/loras/{user_id}")
async def list_user_loras(user_id: str):
    """
    List all LoRA models for a specific user
    """
    try:
        loras = file_handler.get_user_loras(user_id)
        return JSONResponse(content={
            "success": True,
            "loras": loras
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{user_id}")
async def list_user_images(user_id: str):
    """
    List all generated images for a specific user
    """
    try:
        images = file_handler.get_user_images(user_id)
        return JSONResponse(content={
            "success": True,
            "images": images
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
