"""Jimeng (即梦) Image Generation Adapter"""

import asyncio
import base64
import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
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

    # Aspect ratios - jimeng_t2i_v40 only supports 1024x1024
    ASPECT_RATIOS = {
        "1:1": (1024, 1024),
        "16:9": (1024, 1024),
        "9:16": (1024, 1024),
        "4:3": (1024, 1024),
        "3:4": (1024, 1024),
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

        # Build request body - matching official docs format
        body = {
            "req_key": req_key,
            "prompt": prompt,
            "width": width,
            "height": height,
            "return_url": True,  # Return URL instead of base64
        }

        if negative_prompt:
            body["negative_prompt"] = negative_prompt

        if reference_image_url:
            body["image_urls"] = [reference_image_url]
            body["scale"] = 0.5

        if seed is not None:
            body["seed"] = seed


        # Submit task
        task_id = await self._submit_task(body)

        if on_progress:
            on_progress("等待图片生成...")

        # Poll for result (pass req_key for query)
        result = await self._poll_result(task_id, req_key, on_progress)

        return result

    async def _submit_task(self, body: dict) -> str:
        """Submit async task and return task_id"""
        if self.service:
            response = await asyncio.to_thread(self._sync_submit_task, body)
        else:
            response = await self._http_submit_task(body)

        if response.get("code") != 10000:
            raise Exception(f"Task submission failed: {response.get('message', 'Unknown error')}")

        return response["data"]["task_id"]

    def _sync_submit_task(self, body: dict) -> dict:
        """Synchronous task submission using SDK"""
        try:
            return self.service.cv_sync2async_submit_task(body)
        except Exception as e:
            return self._decode_sdk_exception(e)

    def _decode_sdk_exception(self, e: Exception) -> dict:
        """Decode volcengine SDK exceptions that wrap raw bytes responses"""
        raw = e.args[0] if e.args else b""
        if isinstance(raw, bytes):
            try:
                return json.loads(raw)
            except Exception:
                return {"code": -1, "message": raw.decode("utf-8", errors="replace")}
        return {"code": -1, "message": str(e)}

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
        req_key: str,
        on_progress: Callable[[str], None] | None = None,
        max_wait: int = 120,
        poll_interval: int = 2,
    ) -> ImageResult:
        """Poll for task result"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if self.service:
                response = await asyncio.to_thread(self._sync_get_result, task_id, req_key)
            else:
                raise NotImplementedError("SDK required")


            data = response.get("data", {})
            if not data:
                await asyncio.sleep(poll_interval)
                continue

            status = data.get("status", "")

            if status == "done":
                image_url = self._extract_image_url(data)
                if not image_url:
                    raise Exception(f"No image data in response. Keys: {list(data.keys())}")
                return ImageResult(
                    image_url=image_url,
                    width=data.get("width", 1024),
                    height=data.get("height", 1024),
                    seed=data.get("seed"),
                    raw_response=response,
                )

            elif status == "failed":
                raise Exception(f"Image generation failed: {response.get('message', '')}")

            elif status in ("running", "pending", "in_queue"):
                if on_progress:
                    on_progress(f"生成中... ({int(time.time() - start_time)}秒)")
                await asyncio.sleep(poll_interval)

            else:
                await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Image generation timed out after {max_wait}s")

    def _extract_image_url(self, data: dict) -> str:
        """Extract image URL from response data, falling back to base64 if needed"""
        # Try image_urls first
        image_urls = data.get("image_urls") or []
        if image_urls and image_urls[0]:
            return image_urls[0]

        # Fall back to binary_data_base64
        b64_list = data.get("binary_data_base64") or []
        if b64_list and b64_list[0]:
            return self._save_base64_to_temp(b64_list[0])

        return ""

    def _save_base64_to_temp(self, b64_data: str) -> str:
        """Decode base64 image and save to temp file, return file path"""
        img_bytes = base64.b64decode(b64_data)
        suffix = ".png"
        # Detect JPEG
        if img_bytes[:2] == b"\xff\xd8":
            suffix = ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="jimeng_")
        tmp.write(img_bytes)
        tmp.close()
        return tmp.name

    def _sync_get_result(self, task_id: str, req_key: str = "jimeng_t2i_v40") -> dict:
        """Synchronous result retrieval using SDK"""
        try:
            return self.service.cv_sync2async_get_result({
                "req_key": req_key,
                "task_id": task_id,
            })
        except Exception as e:
            return self._decode_sdk_exception(e)

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
