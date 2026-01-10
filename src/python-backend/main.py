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
    num_train_epochs: Optional[int] = Form(default=None),
    learning_rate: float = Form(default=1e-4),
    lora_rank: int = Form(default=8),
    trigger_word: Optional[str] = Form(default=None),
    with_prior_preservation: bool = Form(default=True),
    fast_mode: bool = Form(default=False),
    images: List[UploadFile] = File(...)
):
    """
    Train a LoRA model using uploaded reference images.

    This endpoint performs real DreamBooth-style LoRA training using PEFT.
    Training can take several minutes depending on settings.

    Parameters:
    - lora_name: Name for the LoRA model
    - user_id: User identifier
    - num_train_epochs: Training epochs (auto-calculated based on image count if not specified)
    - learning_rate: Learning rate (default 1e-4)
    - lora_rank: LoRA rank, 4-32 (default 8)
    - trigger_word: Custom trigger word (auto-generated as sks_<name> if not specified)
    - with_prior_preservation: Use prior preservation to prevent overfitting (default True)
    - fast_mode: Enable fast mode for quicker training (fewer class images, reduced epochs)
    - images: 1-5 training images
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
            image_paths=temp_image_paths,
            num_train_epochs=num_train_epochs,
            learning_rate=learning_rate,
            lora_rank=lora_rank,
            trigger_word=trigger_word,
            with_prior_preservation=with_prior_preservation,
            fast_mode=fast_mode,
        )

        # Clean up temporary files
        file_handler.cleanup_temp_files(temp_image_paths)

        # Get trigger word from the trained config
        # The trainer generates it as sks_<lora_name> if not provided
        actual_trigger_word = trigger_word
        if not actual_trigger_word:
            safe_name = "".join(c for c in lora_name if c.isalnum())
            actual_trigger_word = f"sks_{safe_name.lower()}"

        return JSONResponse(content={
            "success": True,
            "lora_path": lora_path,
            "trigger_word": actual_trigger_word,
            "message": f"LoRA '{lora_name}' trained successfully. Use trigger word '{actual_trigger_word}' in your prompts."
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error training LoRA: {error_details}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/train-lora/stream")
async def train_lora_stream(
    lora_name: str = Form(...),
    user_id: str = Form(...),
    num_train_epochs: Optional[int] = Form(default=None),
    learning_rate: float = Form(default=1e-4),
    lora_rank: int = Form(default=8),
    trigger_word: Optional[str] = Form(default=None),
    with_prior_preservation: bool = Form(default=True),
    fast_mode: bool = Form(default=False),
    images: List[UploadFile] = File(...)
):
    """
    Train a LoRA model with SSE progress streaming.

    Same parameters as /train-lora but returns Server-Sent Events
    with progress updates during training. Includes fast_mode for quicker training.
    """
    import asyncio
    import queue
    import threading

    # Validate inputs first
    if not images or len(images) == 0:
        async def error_gen():
            yield f"data: {json.dumps({'event': 'error', 'success': False, 'error': 'At least one image is required'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    if len(images) > 5:
        async def error_gen():
            yield f"data: {json.dumps({'event': 'error', 'success': False, 'error': 'Maximum 5 images allowed'})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    # Save images before starting the generator
    temp_image_paths = await file_handler.save_temp_images(images)

    async def event_generator():
        progress_queue = queue.Queue()
        result_holder = {"path": None, "error": None, "trigger_word": None}

        def progress_callback(progress_data):
            """Callback to receive progress updates from training"""
            progress_queue.put(progress_data)

        def run_training():
            """Run training in a separate thread"""
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                result = loop.run_until_complete(lora_trainer.train(
                    lora_name=lora_name,
                    user_id=user_id,
                    image_paths=temp_image_paths,
                    num_train_epochs=num_train_epochs,
                    learning_rate=learning_rate,
                    lora_rank=lora_rank,
                    trigger_word=trigger_word,
                    with_prior_preservation=with_prior_preservation,
                    fast_mode=fast_mode,
                    progress_callback=progress_callback,
                ))
                result_holder["path"] = result

                # Calculate trigger word
                if trigger_word:
                    result_holder["trigger_word"] = trigger_word
                else:
                    safe_name = "".join(c for c in lora_name if c.isalnum())
                    result_holder["trigger_word"] = f"sks_{safe_name.lower()}"

                loop.close()
            except Exception as e:
                import traceback
                result_holder["error"] = str(e)
                print(f"Training error: {traceback.format_exc()}")
            finally:
                # Signal completion
                progress_queue.put(None)

        # Start training in background thread
        training_thread = threading.Thread(target=run_training)
        training_thread.start()

        try:
            # Stream progress events
            while True:
                try:
                    # Check for progress updates with timeout
                    event = progress_queue.get(timeout=1.0)

                    if event is None:
                        # Training completed
                        break

                    yield f"data: {json.dumps(event)}\n\n"

                except queue.Empty:
                    # No update, check if thread is still alive
                    if not training_thread.is_alive():
                        break
                    continue

            # Wait for thread to complete
            training_thread.join(timeout=5.0)

            # Send final result
            if result_holder["error"]:
                error_data = {
                    "event": "error",
                    "success": False,
                    "error": result_holder["error"],
                    "message": "Training failed"
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            else:
                complete_data = {
                    "event": "complete",
                    "success": True,
                    "lora_path": result_holder["path"],
                    "trigger_word": result_holder["trigger_word"],
                    "message": f"LoRA trained successfully. Use trigger word '{result_holder['trigger_word']}' in your prompts."
                }
                yield f"data: {json.dumps(complete_data)}\n\n"

        except Exception as e:
            import traceback
            print(f"Streaming error: {traceback.format_exc()}")
            error_data = {
                "event": "error",
                "success": False,
                "error": str(e),
                "message": "Unexpected error during training"
            }
            yield f"data: {json.dumps(error_data)}\n\n"

        finally:
            # Clean up temporary files
            file_handler.cleanup_temp_files(temp_image_paths)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

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
