"""Script generation service with multi-stage process for long text"""

from typing import Callable

from ..models import (
    Script,
    Character,
    CharacterAppearance,
    Location,
    Scene,
    StyleGuide,
)
from .llm_service import LLMService
from .translator import Translator


class ScriptService:
    """Script generation service - optimized for long text processing"""

    # ========== Prompt Templates ==========

    # Stage 1: Extract all characters and locations from full text
    EXTRACT_ELEMENTS_SYSTEM_PROMPT = """你是一个专业的文本分析师。
从用户提供的文本中提取所有角色和场景的详细设定，用于后续AI图像生成。

角色提取要求：
1. 提取所有有名字或重要的角色
2. 外观描述要详细具体，包含"DNA锚点"便于保持一致性
3. DNA锚点包括：脸型、发型/发色、标志性配饰、服装特征
4. 如果原文没有描述，根据角色性格和背景合理推断
5. 每个角色的appearance必须完整填写所有字段

场景提取要求：
1. 提取所有出现的场景/地点
2. 包含时间、光线、氛围
3. 描述具体的环境元素

输出严格的JSON格式：
{
  "characters": [
    {
      "id": "char_001",
      "name": "角色名",
      "role": "主角/配角/群演",
      "appearance": {
        "gender": "男/女",
        "age": "年龄描述",
        "height": "体型描述",
        "face": "脸型和五官",
        "hair": "发型和发色",
        "clothing": "服装描述",
        "accessories": "配饰",
        "distinctive_features": "标志性特征"
      },
      "personality": "性格描述"
    }
  ],
  "locations": [
    {
      "id": "loc_001",
      "name": "场景名称",
      "description": "详细描述",
      "time_of_day": "时间",
      "atmosphere": "氛围",
      "reference_prompt_zh": "用于AI图像生成的中文prompt"
    }
  ]
}"""

    # Stage 2: Generate scene splitting plan
    SCENE_SPLIT_SYSTEM_PROMPT = """你是一个专业的分镜规划师。
根据用户提供的文本内容，规划如何将其切分成适合短视频的场景。

要求：
1. 每个场景对应原文的一段内容
2. 标注每个场景在原文中的起始和结束位置（用原文中的关键句子标记）
3. 场景数量控制在5-15个
4. 每个场景应该有独立的画面感
5. 场景之间要有连贯性

输出严格的JSON格式：
{
  "total_scenes": 8,
  "scenes": [
    {
      "scene_id": 1,
      "title": "场景标题/概述",
      "start_marker": "原文中该场景开始的句子或关键词",
      "end_marker": "原文中该场景结束的句子或关键词",
      "location_id": "loc_001",
      "character_ids": ["char_001", "char_002"],
      "summary": "这个场景的简要描述"
    }
  ]
}

注意：start_marker和end_marker必须是原文中实际存在的文字片段，用于代码定位切割。"""

    # Stage 3: Generate detailed scene description for each segment
    SCENE_DETAIL_SYSTEM_PROMPT = """你是一个专业的分镜脚本师。
根据提供的文本片段、角色设定和场景设定，生成这个场景的详细分镜描述。

要求：
1. 镜头类型：远景/全景/中景/近景/特写
2. 镜头运动：固定/推进/拉远/平移/俯仰
3. 画面描述要详细，包含完整的角色外观描述
4. 生成用于AI图像生成的中文prompt
5. image_prompt_zh必须包含角色的完整外观特征

输出严格的JSON格式：
{
  "duration": "5秒",
  "shot_type": "中景",
  "camera_movement": "固定",
  "visual_description": "详细的画面描述",
  "narration": "旁白内容，如果没有则为null",
  "dialogue": {"char_001": "对话内容"},
  "mood": "情绪氛围",
  "image_prompt_zh": "用于AI图像生成的中文prompt，包含完整的角色外观描述和场景细节"
}"""

    def __init__(self, llm_service: LLMService, translator: Translator | None = None):
        self.llm = llm_service
        self.translator = translator

    async def extract_elements(
        self,
        full_text: str,
        on_progress: Callable[[str], None] | None = None,
    ) -> tuple[list[Character], list[Location]]:
        """Stage 1: Extract all characters and locations from full text"""
        if on_progress:
            on_progress("正在分析角色和场景...")

        # For very long text, we may need to summarize first
        text_to_analyze = full_text
        if len(full_text) > 30000:
            # Truncate but keep beginning and end for context
            text_to_analyze = full_text[:15000] + "\n\n...(中间内容省略)...\n\n" + full_text[-10000:]

        prompt = f"""请从以下文本中提取所有角色和场景的详细设定：

{text_to_analyze}

请确保：
1. 提取所有重要角色，包括主角和配角
2. 为每个角色生成详细的外观描述
3. 提取所有出现的场景/地点"""

        data = await self.llm.generate_json(
            prompt=prompt,
            system_prompt=self.EXTRACT_ELEMENTS_SYSTEM_PROMPT,
            temperature=0.7,
        )

        characters = []
        for char_data in data.get("characters", []):
            appearance_data = char_data.get("appearance", {})
            appearance = CharacterAppearance(
                gender=appearance_data.get("gender", ""),
                age=appearance_data.get("age", ""),
                height=appearance_data.get("height", ""),
                face=appearance_data.get("face", ""),
                hair=appearance_data.get("hair", ""),
                clothing=appearance_data.get("clothing", ""),
                accessories=appearance_data.get("accessories", ""),
                distinctive_features=appearance_data.get("distinctive_features", ""),
            )
            character = Character(
                id=char_data.get("id", f"char_{len(characters)+1:03d}"),
                name=char_data.get("name", ""),
                role=char_data.get("role", "配角"),
                appearance=appearance,
                personality=char_data.get("personality", ""),
            )
            characters.append(character)

        locations = []
        for loc_data in data.get("locations", []):
            location = Location(
                id=loc_data.get("id", f"loc_{len(locations)+1:03d}"),
                name=loc_data.get("name", ""),
                description=loc_data.get("description", ""),
                time_of_day=loc_data.get("time_of_day", ""),
                atmosphere=loc_data.get("atmosphere", ""),
                reference_prompt_zh=loc_data.get("reference_prompt_zh", ""),
            )
            locations.append(location)

        return characters, locations

    async def generate_split_plan(
        self,
        full_text: str,
        characters: list[Character],
        locations: list[Location],
        target_scenes: int = 8,
        on_progress: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """Stage 2: Generate scene splitting plan"""
        if on_progress:
            on_progress("正在规划分镜切割方案...")

        # Build context
        char_list = ", ".join([f"{c.name}({c.id})" for c in characters])
        loc_list = ", ".join([f"{l.name}({l.id})" for l in locations])

        # For long text, provide summary for planning
        text_for_planning = full_text
        if len(full_text) > 40000:
            text_for_planning = full_text[:20000] + "\n\n...(中间内容省略)...\n\n" + full_text[-15000:]

        prompt = f"""请为以下文本规划分镜切割方案：

{text_for_planning}

已提取的角色：{char_list}
已提取的场景：{loc_list}

要求：
- 将文本切分成约{target_scenes}个场景
- 每个场景的start_marker和end_marker必须是原文中实际存在的文字
- 确保场景之间有连贯性"""

        data = await self.llm.generate_json(
            prompt=prompt,
            system_prompt=self.SCENE_SPLIT_SYSTEM_PROMPT,
            temperature=0.7,
        )

        return data.get("scenes", [])

    def split_text_by_markers(
        self,
        full_text: str,
        split_plan: list[dict],
    ) -> list[tuple[dict, str]]:
        """Split text into segments based on markers

        Returns: List of (scene_plan, text_segment) tuples
        """
        segments = []

        for scene in split_plan:
            start_marker = scene.get("start_marker", "")
            end_marker = scene.get("end_marker", "")

            # Find start position
            start_pos = 0
            if start_marker:
                pos = full_text.find(start_marker)
                if pos != -1:
                    start_pos = pos

            # Find end position
            end_pos = len(full_text)
            if end_marker:
                pos = full_text.find(end_marker, start_pos)
                if pos != -1:
                    end_pos = pos + len(end_marker)

            # Extract segment
            segment = full_text[start_pos:end_pos].strip()

            # If segment is empty, use the summary as fallback
            if not segment:
                segment = scene.get("summary", "")

            segments.append((scene, segment))

        return segments

    async def generate_scene_detail(
        self,
        scene_plan: dict,
        text_segment: str,
        characters: list[Character],
        locations: list[Location],
        style: str = "写实",
        on_progress: Callable[[str], None] | None = None,
    ) -> Scene:
        """Stage 3: Generate detailed scene description for one segment"""
        scene_id = scene_plan.get("scene_id", 1)

        if on_progress:
            on_progress(f"正在生成第{scene_id}个分镜...")

        # Get relevant characters
        char_ids = scene_plan.get("character_ids", [])
        relevant_chars = [c for c in characters if c.id in char_ids]
        char_context = "\n".join([
            f"- {c.name}({c.id}): {c.get_description()}"
            for c in relevant_chars
        ]) or "无特定角色"

        # Get location
        loc_id = scene_plan.get("location_id", "")
        location = next((l for l in locations if l.id == loc_id), None)
        loc_context = f"{location.name}: {location.description}" if location else "未指定场景"

        prompt = f"""请为以下文本片段生成详细的分镜描述：

## 文本内容
{text_segment}

## 场景概述
{scene_plan.get("summary", "")}

## 出场角色
{char_context}

## 场景环境
{loc_context}

## 视觉风格
{style}

请生成这个场景的详细分镜描述，image_prompt_zh必须包含角色的完整外观特征。"""

        data = await self.llm.generate_json(
            prompt=prompt,
            system_prompt=self.SCENE_DETAIL_SYSTEM_PROMPT,
            temperature=0.7,
        )

        scene = Scene(
            scene_id=scene_id,
            location_id=loc_id,
            character_ids=char_ids,
            duration=data.get("duration", "5秒"),
            shot_type=data.get("shot_type", "中景"),
            camera_movement=data.get("camera_movement", "固定"),
            visual_description=data.get("visual_description", ""),
            narration=data.get("narration"),
            dialogue=data.get("dialogue"),
            mood=data.get("mood", ""),
            image_prompt_zh=data.get("image_prompt_zh", ""),
        )

        return scene

    async def translate_prompts(
        self,
        script: Script,
        on_progress: Callable[[str], None] | None = None,
    ) -> Script:
        """Translate all Chinese prompts to English"""
        if not self.translator:
            return script

        if on_progress:
            on_progress("正在翻译Prompt...")

        # Collect all prompts to translate
        prompts_to_translate = []

        # Location reference prompts
        for loc in script.locations:
            if loc.reference_prompt_zh:
                prompts_to_translate.append(loc.reference_prompt_zh)

        # Scene image prompts
        for scene in script.scenes:
            if scene.image_prompt_zh:
                prompts_to_translate.append(scene.image_prompt_zh)

        # Batch translate
        if prompts_to_translate:
            translations = await self.translator.translate_batch(prompts_to_translate)

            idx = 0

            # Apply translations to locations
            for loc in script.locations:
                if loc.reference_prompt_zh:
                    loc.reference_prompt_en = translations[idx]
                    idx += 1

            # Apply translations to scenes
            for scene in script.scenes:
                if scene.image_prompt_zh:
                    scene.image_prompt_en = translations[idx]
                    idx += 1

        return script

    async def generate_full_script(
        self,
        input_text: str,
        skip_outline: bool = False,
        style: str = "写实",
        aspect_ratio: str = "16:9",
        target_scenes: int = 8,
        on_progress: Callable[[str], None] | None = None,
    ) -> Script:
        """Complete script generation workflow for long text

        New workflow:
        1. Extract all characters and locations from full text
        2. Generate scene splitting plan
        3. Split text by markers using code
        4. Generate detailed scene for each segment
        5. Translate prompts

        Args:
            input_text: Full text content (e.g., novel chapter)
            skip_outline: Deprecated, kept for compatibility
            style: Visual style
            aspect_ratio: Aspect ratio
            target_scenes: Target number of scenes
            on_progress: Progress callback

        Returns:
            Complete Script object
        """
        # Stage 1: Extract characters and locations
        characters, locations = await self.extract_elements(input_text, on_progress)

        # Stage 2: Generate split plan
        split_plan = await self.generate_split_plan(
            input_text, characters, locations, target_scenes, on_progress
        )

        # Stage 3: Split text by markers (code, no LLM)
        if on_progress:
            on_progress("正在切割文本...")
        segments = self.split_text_by_markers(input_text, split_plan)

        # Stage 4: Generate detailed scenes one by one
        scenes = []
        for scene_plan, text_segment in segments:
            scene = await self.generate_scene_detail(
                scene_plan, text_segment, characters, locations, style, on_progress
            )
            scenes.append(scene)

        # Create style guide
        style_guide = StyleGuide(
            visual_style=style,
            color_palette=[],
            aspect_ratio=aspect_ratio,
            target_duration=f"{len(scenes) * 5}秒",
        )

        # Create script
        script = Script(
            title="",  # Will be set by user or derived
            summary="",
            characters=characters,
            locations=locations,
            scenes=scenes,
            style_guide=style_guide,
            outline=input_text[:500] + "..." if len(input_text) > 500 else input_text,
        )

        # Stage 5: Translate prompts
        script = await self.translate_prompts(script, on_progress)

        if on_progress:
            on_progress("脚本生成完成！")

        return script
