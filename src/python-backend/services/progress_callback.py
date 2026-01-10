import asyncio
from dataclasses import dataclass, asdict
from typing import Optional
import threading


@dataclass
class ProgressEvent:
    """Event data for SSE progress streaming"""
    event: str  # "progress", "complete", "error"
    step: Optional[int] = None
    total_steps: Optional[int] = None
    percentage: Optional[float] = None
    message: Optional[str] = None
    image_path: Optional[str] = None
    error: Optional[str] = None
    success: bool = True

    def to_dict(self):
        return asdict(self)


class ProgressCallback:
    """
    Callback for diffusers pipeline that captures progress and pushes to a queue.
    Thread-safe for use with synchronous pipeline callbacks.
    """

    def __init__(self, total_steps: int = 30):
        self.total_steps = total_steps
        self.queue: asyncio.Queue = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop for thread-safe queue operations"""
        with self._lock:
            self._loop = loop

    def __call__(self, step: int, timestep: int, latents):
        """
        Diffusers callback - called on each inference step.
        This runs in a separate thread, so we need thread-safe queue access.
        """
        percentage = ((step + 1) / self.total_steps) * 100
        event = ProgressEvent(
            event="progress",
            step=step + 1,
            total_steps=self.total_steps,
            percentage=round(percentage, 2),
            message=f"Generating... Step {step + 1}/{self.total_steps}"
        )

        # Thread-safe put into async queue
        with self._lock:
            if self._loop is not None:
                self._loop.call_soon_threadsafe(
                    lambda: self.queue.put_nowait(event)
                )

    async def complete(self, image_path: str):
        """Send completion event"""
        await self.queue.put(ProgressEvent(
            event="complete",
            success=True,
            image_path=image_path,
            message="Image generated successfully",
            percentage=100.0,
            step=self.total_steps,
            total_steps=self.total_steps
        ))

    async def error(self, error_message: str):
        """Send error event"""
        await self.queue.put(ProgressEvent(
            event="error",
            success=False,
            error=error_message,
            message="Failed to generate image"
        ))
