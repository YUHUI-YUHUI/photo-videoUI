"""Image generation service"""

import asyncio
from pathlib import Path
from typing import Callable
from dataclasses import dataclass

import httpx

from ..adapters.jimeng import JimengAdapter, ImageResult
from ..models import Script, Character, Location, Scene


@dataclass
class GeneratedImage:
    """Generated image with metadata"""
    url: str
    local_path: Path | None = None
    prompt: str = ""
    type: str = ""  # "character", "location", "scene"
    reference_id: str = ""  # char_001, loc_001, or scene_1


class ImageService:
    """Service for generating images for scripts"""

    def __init__(self, adapter: JimengAdapter):
        self.adapter = adapter

    async def generate_character_reference(
        self,
        character: Character,
        style: str = "写实",
        aspect_ratio: str = "3:4",  # Portrait orientation for characters
        on_progress: Callable[[str], None] | None = None,
    ) -> GeneratedImage:
        """Generate a reference image for a character

        Args:
            character: Character object with appearance details
            style: Visual style
            aspect_ratio: Image aspect ratio
            on_progress: Progress callback

        Returns:
            GeneratedImage with the character image
        """
        if on_progress:
            on_progress(f"生成角色图: {character.name}...")

        # Build detailed prompt from character appearance
        prompt = self._build_character_prompt(character, style)

        result = await self.adapter.generate_image(
            prompt=prompt,
            negative_prompt="低质量, 模糊, 变形, 丑陋, 多余的肢体",
            aspect_ratio=aspect_ratio,
            style=style,
            on_progress=on_progress,
        )

        return GeneratedImage(
            url=result.image_url,
            prompt=prompt,
            type="character",
            reference_id=character.id,
        )

    async def generate_location_reference(
        self,
        location: Location,
        style: str = "写实",
        aspect_ratio: str = "16:9",
        on_progress: Callable[[str], None] | None = None,
    ) -> GeneratedImage:
        """Generate a reference image for a location

        Args:
            location: Location object with description
            style: Visual style
            aspect_ratio: Image aspect ratio
            on_progress: Progress callback

        Returns:
            GeneratedImage with the location image
        """
        if on_progress:
            on_progress(f"生成场景图: {location.name}...")

        # Use the pre-generated prompt if available
        prompt = location.reference_prompt_en or location.reference_prompt_zh
        if not prompt:
            prompt = self._build_location_prompt(location, style)

        result = await self.adapter.generate_image(
            prompt=prompt,
            negative_prompt="人物, 低质量, 模糊",
            aspect_ratio=aspect_ratio,
            style=style,
            on_progress=on_progress,
        )

        return GeneratedImage(
            url=result.image_url,
            prompt=prompt,
            type="location",
            reference_id=location.id,
        )

    async def generate_scene_image(
        self,
        scene: Scene,
        characters: list[Character],
        locations: list[Location],
        style: str = "写实",
        aspect_ratio: str = "16:9",
        character_reference_urls: dict[str, str] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> GeneratedImage:
        """Generate an image for a scene

        Args:
            scene: Scene object with visual description
            characters: List of all characters (for reference)
            locations: List of all locations (for reference)
            style: Visual style
            aspect_ratio: Image aspect ratio
            character_reference_urls: Optional dict of character_id -> reference_image_url
            on_progress: Progress callback

        Returns:
            GeneratedImage with the scene image
        """
        if on_progress:
            on_progress(f"生成分镜{scene.scene_id}...")

        # Use the pre-generated English prompt if available
        prompt = scene.image_prompt_en or scene.image_prompt_zh
        if not prompt:
            prompt = self._build_scene_prompt(scene, characters, locations, style)

        # If we have character reference images, use the first one
        reference_url = None
        if character_reference_urls and scene.character_ids:
            for char_id in scene.character_ids:
                if char_id in character_reference_urls:
                    reference_url = character_reference_urls[char_id]
                    break

        result = await self.adapter.generate_image(
            prompt=prompt,
            negative_prompt="低质量, 模糊, 变形, 丑陋, 多余的肢体, 错误的手指",
            aspect_ratio=aspect_ratio,
            style=style,
            reference_image_url=reference_url,
            on_progress=on_progress,
        )

        return GeneratedImage(
            url=result.image_url,
            prompt=prompt,
            type="scene",
            reference_id=f"scene_{scene.scene_id}",
        )

    async def generate_all_images(
        self,
        script: Script,
        style: str = "写实",
        aspect_ratio: str = "16:9",
        generate_characters: bool = True,
        generate_locations: bool = True,
        generate_scenes: bool = True,
        on_progress: Callable[[str], None] | None = None,
    ) -> dict[str, list[GeneratedImage]]:
        """Generate all images for a script

        Args:
            script: Complete script object
            style: Visual style
            aspect_ratio: Image aspect ratio for scenes
            generate_characters: Whether to generate character references
            generate_locations: Whether to generate location references
            generate_scenes: Whether to generate scene images
            on_progress: Progress callback

        Returns:
            Dict with lists of generated images by type
        """
        results = {
            "characters": [],
            "locations": [],
            "scenes": [],
        }

        character_refs = {}

        # Generate character reference images
        if generate_characters:
            if on_progress:
                on_progress("开始生成角色参考图...")

            for char in script.characters:
                try:
                    image = await self.generate_character_reference(
                        char, style, "3:4", on_progress
                    )
                    results["characters"].append(image)
                    character_refs[char.id] = image.url
                except Exception as e:
                    if on_progress:
                        on_progress(f"角色 {char.name} 生成失败: {str(e)[:30]}")

        # Generate location reference images
        if generate_locations:
            if on_progress:
                on_progress("开始生成场景参考图...")

            for loc in script.locations:
                try:
                    image = await self.generate_location_reference(
                        loc, style, aspect_ratio, on_progress
                    )
                    results["locations"].append(image)
                except Exception as e:
                    if on_progress:
                        on_progress(f"场景 {loc.name} 生成失败: {str(e)[:30]}")

        # Generate scene images
        if generate_scenes:
            if on_progress:
                on_progress("开始生成分镜图...")

            for scene in script.scenes:
                try:
                    image = await self.generate_scene_image(
                        scene,
                        script.characters,
                        script.locations,
                        style,
                        aspect_ratio,
                        character_refs,
                        on_progress,
                    )
                    results["scenes"].append(image)
                except Exception as e:
                    if on_progress:
                        on_progress(f"分镜 {scene.scene_id} 生成失败: {str(e)[:30]}")

        if on_progress:
            on_progress("图片生成完成！")

        return results

    async def download_image(
        self,
        url: str,
        save_path: Path,
    ) -> Path:
        """Download an image from URL to local path

        Args:
            url: Image URL
            save_path: Local path to save the image

        Returns:
            Path to the saved image
        """
        save_path.parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

        return save_path

    def _build_character_prompt(self, character: Character, style: str) -> str:
        """Build a detailed prompt for character image generation"""
        app = character.appearance

        parts = [
            f"一个{app.gender}性角色",
            f"年龄{app.age}" if app.age else "",
            f"身材{app.height}" if app.height else "",
            f"脸型{app.face}" if app.face else "",
            f"发型{app.hair}" if app.hair else "",
            f"穿着{app.clothing}" if app.clothing else "",
            f"配饰{app.accessories}" if app.accessories else "",
            f"特征{app.distinctive_features}" if app.distinctive_features else "",
        ]

        # Filter empty parts
        parts = [p for p in parts if p]

        prompt = "，".join(parts)
        prompt += f"，{style}风格，高质量，精细，肖像照"

        return prompt

    def _build_location_prompt(self, location: Location, style: str) -> str:
        """Build a detailed prompt for location image generation"""
        parts = [
            location.name,
            location.description,
            f"时间: {location.time_of_day}" if location.time_of_day else "",
            f"氛围: {location.atmosphere}" if location.atmosphere else "",
        ]

        parts = [p for p in parts if p]
        prompt = "，".join(parts)
        prompt += f"，{style}风格，高质量，精细，场景图，无人物"

        return prompt

    def _build_scene_prompt(
        self,
        scene: Scene,
        characters: list[Character],
        locations: list[Location],
        style: str,
    ) -> str:
        """Build a detailed prompt for scene image generation"""
        # Get location info
        location = next((l for l in locations if l.id == scene.location_id), None)
        loc_desc = location.description if location else ""

        # Get character descriptions
        char_descs = []
        for char_id in scene.character_ids:
            char = next((c for c in characters if c.id == char_id), None)
            if char:
                char_descs.append(f"{char.name}: {char.get_description()}")

        prompt_parts = [
            scene.visual_description,
            loc_desc,
            f"场景中的人物: {'; '.join(char_descs)}" if char_descs else "",
            f"情绪氛围: {scene.mood}" if scene.mood else "",
        ]

        prompt_parts = [p for p in prompt_parts if p]
        prompt = "，".join(prompt_parts)
        prompt += f"，{style}风格，高质量，电影画面感"

        return prompt
