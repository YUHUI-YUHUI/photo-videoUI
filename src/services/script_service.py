"""Script generation service with three-stage process"""

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
    """Script generation service - three-stage generation"""

    # ========== Prompt Templates ==========

    OUTLINE_SYSTEM_PROMPT = """你是一个专业的短视频脚本创作者。
根据用户的主题创作一个适合短视频的故事大纲。

要求：
1. 故事完整，有开头、发展、高潮、结尾
2. 控制在3-8个场景
3. 适合视觉呈现，包含具体的画面元素
4. 情节紧凑，适合1-2分钟短视频
5. 角色设定要有特点，易于识别

输出格式：
## 标题
[视频标题]

## 简介
[一句话简介]

## 故事大纲
[详细的故事大纲，分段落描述主要情节]

## 主要角色
- 角色1（名字）：[外观特征、性格特点]
- 角色2（名字）：[外观特征、性格特点]
（如有更多角色继续列出）

## 主要场景
- 场景1：[场景名称和描述]
- 场景2：[场景名称和描述]
（如有更多场景继续列出）"""

    EXTRACT_ELEMENTS_SYSTEM_PROMPT = """你是一个专业的视频分镜师。
从故事大纲中提取所有角色和场景的详细设定，用于AI图像生成。

角色设定要求：
1. 外观描述要详细具体，包含"DNA锚点"便于保持一致性
2. DNA锚点包括：脸型、发型/发色、标志性配饰、服装颜色
3. 特征描述使用固定词汇，避免同义词替换
4. 每个角色的appearance必须完整填写所有字段

场景设定要求：
1. 包含时间、光线、氛围
2. 描述具体的环境元素
3. 生成用于AI图像的参考prompt

输出严格的JSON格式：
{
  "characters": [
    {
      "id": "char_001",
      "name": "角色名",
      "role": "主角/配角/群演",
      "appearance": {
        "gender": "男/女",
        "age": "年龄描述，如25岁左右",
        "height": "体型描述，如中等身材",
        "face": "脸型和五官，如圆脸、浓眉大眼",
        "hair": "发型和发色，如黑色短发",
        "clothing": "服装描述，如蓝色卫衣、牛仔裤",
        "accessories": "配饰，如黑框眼镜",
        "distinctive_features": "标志性特征，如左脸有一颗小痣"
      },
      "personality": "性格描述"
    }
  ],
  "locations": [
    {
      "id": "loc_001",
      "name": "场景名称",
      "description": "详细描述",
      "time_of_day": "时间，如下午",
      "atmosphere": "氛围，如温馨、安静",
      "reference_prompt_zh": "用于AI图像生成的中文prompt"
    }
  ]
}"""

    SCENES_SYSTEM_PROMPT = """你是一个专业的分镜脚本师。
根据故事大纲、角色设定和场景设定，生成详细的分镜脚本。

每个分镜要求：
1. 使用已定义的场景和角色（通过ID引用）
2. 镜头类型：远景/全景/中景/近景/特写
3. 镜头运动：固定/推进/拉远/平移/俯仰
4. 画面描述要详细，包含完整的角色外观描述
5. 旁白或对话要与画面配合
6. 生成用于AI图像生成的中文prompt

输出严格的JSON格式：
{
  "title": "视频标题",
  "summary": "一句话简介",
  "scenes": [
    {
      "scene_id": 1,
      "location_id": "loc_001",
      "character_ids": ["char_001"],
      "duration": "5秒",
      "shot_type": "中景",
      "camera_movement": "固定",
      "visual_description": "详细的画面描述",
      "narration": "旁白内容，如果没有则为null",
      "dialogue": {"char_001": "对话内容"},
      "mood": "情绪氛围",
      "image_prompt_zh": "用于AI图像生成的中文prompt，包含完整的角色外观描述和场景细节"
    }
  ],
  "style_guide": {
    "visual_style": "写实/动漫/3D等",
    "color_palette": ["主色调1", "主色调2"],
    "aspect_ratio": "16:9",
    "target_duration": "总时长，如60秒"
  }
}"""

    def __init__(self, llm_service: LLMService, translator: Translator | None = None):
        self.llm = llm_service
        self.translator = translator

    async def generate_outline(
        self,
        topic: str,
        style: str = "写实",
        on_progress: Callable[[str], None] | None = None,
    ) -> str:
        """Stage 1: Generate story outline from topic"""
        if on_progress:
            on_progress("正在生成故事大纲...")

        prompt = f"""请根据以下主题创作一个短视频故事大纲：

主题：{topic}

视觉风格：{style}

要求：
- 故事长度控制在3-8个场景
- 适合1-2分钟的短视频
- 有清晰的故事线和情感弧度
- 角色设定要有识别度"""

        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=self.OUTLINE_SYSTEM_PROMPT,
            temperature=0.8,
        )

        return response.content

    async def extract_elements(
        self,
        outline: str,
        style: str = "写实",
        on_progress: Callable[[str], None] | None = None,
    ) -> tuple[list[Character], list[Location]]:
        """Stage 2: Extract characters and locations from outline"""
        if on_progress:
            on_progress("正在提取角色和场景...")

        prompt = f"""请从以下故事大纲中提取所有角色和场景的详细设定：

{outline}

视觉风格：{style}

请确保：
1. 每个角色的外观描述完整详细
2. 每个场景的环境描述具体
3. 生成适合AI图像生成的prompt"""

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

    async def generate_scenes(
        self,
        outline: str,
        characters: list[Character],
        locations: list[Location],
        style: str = "写实",
        aspect_ratio: str = "16:9",
        on_progress: Callable[[str], None] | None = None,
    ) -> tuple[list[Scene], StyleGuide, str, str]:
        """Stage 3: Generate detailed scenes/storyboard

        Returns: (scenes, style_guide, title, summary)
        """
        if on_progress:
            on_progress("正在生成分镜脚本...")

        # Build character and location context
        char_context = "\n".join([
            f"- {c.id}: {c.name}（{c.role}）- {c.get_description()}"
            for c in characters
        ])

        loc_context = "\n".join([
            f"- {l.id}: {l.name} - {l.description}（{l.time_of_day}，{l.atmosphere}）"
            for l in locations
        ])

        prompt = f"""请根据以下信息生成详细的分镜脚本：

## 故事大纲
{outline}

## 已定义的角色
{char_context}

## 已定义的场景
{loc_context}

## 视觉设定
- 风格：{style}
- 画面比例：{aspect_ratio}

请生成完整的分镜脚本，每个分镜的image_prompt_zh要包含完整的角色外观描述。"""

        data = await self.llm.generate_json(
            prompt=prompt,
            system_prompt=self.SCENES_SYSTEM_PROMPT,
            temperature=0.7,
        )

        scenes = []
        for scene_data in data.get("scenes", []):
            scene = Scene(
                scene_id=scene_data.get("scene_id", len(scenes) + 1),
                location_id=scene_data.get("location_id", ""),
                character_ids=scene_data.get("character_ids", []),
                duration=scene_data.get("duration", "5秒"),
                shot_type=scene_data.get("shot_type", "中景"),
                camera_movement=scene_data.get("camera_movement", "固定"),
                visual_description=scene_data.get("visual_description", ""),
                narration=scene_data.get("narration"),
                dialogue=scene_data.get("dialogue"),
                mood=scene_data.get("mood", ""),
                image_prompt_zh=scene_data.get("image_prompt_zh", ""),
            )
            scenes.append(scene)

        style_data = data.get("style_guide", {})
        style_guide = StyleGuide(
            visual_style=style_data.get("visual_style", style),
            color_palette=style_data.get("color_palette", []),
            aspect_ratio=style_data.get("aspect_ratio", aspect_ratio),
            target_duration=style_data.get("target_duration", "60秒"),
        )

        title = data.get("title", "")
        summary = data.get("summary", "")

        return scenes, style_guide, title, summary

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
        on_progress: Callable[[str], None] | None = None,
    ) -> Script:
        """Complete script generation workflow

        Args:
            input_text: Topic or detailed description
            skip_outline: If True, treat input_text as outline and skip stage 1
            style: Visual style
            aspect_ratio: Aspect ratio
            on_progress: Progress callback

        Returns:
            Complete Script object
        """
        # Stage 1: Generate outline (or use input directly)
        if skip_outline:
            outline = input_text
        else:
            outline = await self.generate_outline(input_text, style, on_progress)

        # Stage 2: Extract characters and locations
        characters, locations = await self.extract_elements(outline, style, on_progress)

        # Stage 3: Generate scenes
        scenes, style_guide, title, summary = await self.generate_scenes(
            outline, characters, locations, style, aspect_ratio, on_progress
        )

        # Create script
        script = Script(
            title=title,
            summary=summary,
            characters=characters,
            locations=locations,
            scenes=scenes,
            style_guide=style_guide,
            outline=outline,
        )

        # Translate prompts
        script = await self.translate_prompts(script, on_progress)

        if on_progress:
            on_progress("脚本生成完成！")

        return script
