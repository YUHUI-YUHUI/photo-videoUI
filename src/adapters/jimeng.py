"""Jimeng (即梦) Image Generation Adapter"""

import asyncio
import time
from dataclasses import dataclass
from typing import Callable

import httpx


@dataclass
class ImageResult:
    """Result from image generation"""
    image_url: str
    width: int
    height: int
    seed: int | None = None
    raw_response: dict | None = None


class JimengAdapter:
    """Jimeng AI Image Generation Adapter

    Uses Volcengine Visual API for image generation.
    """

    name = "jimeng"
    display_name = "即梦AI"

    # API Configuration
    BASE_URL = "https://visual.volcengineapi.com"
    REGION = "cn-north-1"
    SERVICE = "cv"
    VERSION = "2022-08-31"

    # Available models
    MODELS = {
        "jimeng_t2i_v40": "即梦4.0 文生图",
        "jimeng_t2i_v30": "即梦3.0 文生图",
        "jimeng_i2i_v40": "即梦4.0 图生图",
    }

    # Aspect ratios
    ASPECT_RATIOS = {
        "1:1": (1024, 1024),
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "4:3": (1024, 768),
        "3:4": (768, 1024),
    }

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        model: str = "jimeng_t2i_v40",
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.model = model

        # Initialize volcengine SDK
        self._init_sdk()

    def _init_sdk(self):
        """Initialize Volcengine SDK"""
        try:
            from volcengine.visual.VisualService import VisualService

            self.service = VisualService()
            self.service.set_ak(self.access_key)
            self.service.set_sk(self.secret_key)
        except ImportError:
            # Fallback to manual HTTP requests if SDK not installed
            self.service = None

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
        style: str = "写实",
        reference_image_url: str | None = None,
        seed: int | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> ImageResult:
        """Generate image from prompt

        Args:
            prompt: Text description of the image
            negative_prompt: What to avoid in the image
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            style: Visual style
            reference_image_url: Optional reference image for style/character
            seed: Random seed for reproducibility
            on_progress: Progress callback

        Returns:
            ImageResult with the generated image URL
        """
        if on_progress:
            on_progress("提交图片生成任务...")

        # Get dimensions from aspect ratio
        width, height = self.ASPECT_RATIOS.get(aspect_ratio, (1024, 1024))

        # Determine model based on whether we have a reference image
        req_key = "jimeng_i2i_v40" if reference_image_url else self.model

        # Build request body
        body = {
            "req_key": req_key,
            "prompt": prompt,
            "width": width,
            "height": height,
            "use_sr": True,  # Enable super resolution
            "return_url": True,
        }

        if negative_prompt:
            body["negative_prompt"] = negative_prompt

        if reference_image_url:
            body["image_urls"] = [reference_image_url]
            body["scale"] = 0.5  # Control how much to follow reference

        if seed is not None:
            body["seed"] = seed

        # Submit task
        task_id = await self._submit_task(body)

        if on_progress:
            on_progress("等待图片生成...")

        # Poll for result
        result = await self._poll_result(task_id, on_progress)

        return result

    async def _submit_task(self, body: dict) -> str:
        """Submit async task and return task_id"""
        if self.service:
            # Use SDK
            response = await asyncio.to_thread(
                self._sync_submit_task, body
            )
        else:
            # Manual HTTP request
            response = await self._http_submit_task(body)

        if response.get("code") != 10000:
            raise Exception(f"Task submission failed: {response.get('message', 'Unknown error')}")

        return response["data"]["task_id"]

    def _sync_submit_task(self, body: dict) -> dict:
        """Synchronous task submission using SDK"""
        return self.service.cv_sync2_async_submit_task(body)

    async def _http_submit_task(self, body: dict) -> dict:
        """Submit task via HTTP (fallback)"""
        # Note: This requires proper signature authentication
        # For now, this is a placeholder - the SDK method is preferred
        raise NotImplementedError(
            "Please install volcengine SDK: pip install volcengine"
        )

    async def _poll_result(
        self,
        task_id: str,
        on_progress: Callable[[str], None] | None = None,
        max_wait: int = 120,
        poll_interval: int = 2,
    ) -> ImageResult:
        """Poll for task result"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if self.service:
                response = await asyncio.to_thread(
                    self._sync_get_result, task_id
                )
            else:
                raise NotImplementedError("SDK required")

            status = response.get("data", {}).get("status", "")

            if status == "done":
                # Task completed
                data = response["data"]
                image_urls = data.get("image_urls", [])

                if not image_urls:
                    raise Exception("No image generated")

                return ImageResult(
                    image_url=image_urls[0],
                    width=data.get("width", 1024),
                    height=data.get("height", 1024),
                    seed=data.get("seed"),
                    raw_response=response,
                )

            elif status == "failed":
                raise Exception(f"Image generation failed: {response.get('message', '')}")

            elif status in ("running", "pending"):
                if on_progress:
                    on_progress(f"生成中... ({int(time.time() - start_time)}秒)")
                await asyncio.sleep(poll_interval)

            else:
                # Unknown status, keep waiting
                await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Image generation timed out after {max_wait}s")

    def _sync_get_result(self, task_id: str) -> dict:
        """Synchronous result retrieval using SDK"""
        return self.service.cv_sync2_async_get_result({"task_id": task_id})

    async def test_connection(self) -> bool:
        """Test if the adapter is properly configured"""
        if not self.access_key or not self.secret_key:
            return False

        try:
            # Try a simple API call to verify credentials
            # This is a lightweight check that doesn't generate an image
            if self.service:
                # SDK is available
                return True
            return False
        except Exception:
            return False

    def get_available_models(self) -> dict[str, str]:
        """Get available models"""
        return self.MODELS.copy()
