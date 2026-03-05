"""Script data models for PAVUI"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CharacterAppearance(BaseModel):
    """Character appearance details"""
    gender: str = ""
    age: str = ""
    height: str = ""
    face: str = ""          # 脸型、五官
    hair: str = ""          # 发型、发色
    clothing: str = ""
    accessories: str = ""
    distinctive_features: str = ""  # 标志性特征

    def to_prompt(self) -> str:
        """Convert appearance to prompt string"""
        parts = []
        if self.gender:
            parts.append(self.gender)
        if self.age:
            parts.append(self.age)
        if self.height:
            parts.append(self.height)
        if self.face:
            parts.append(self.face)
        if self.hair:
            parts.append(self.hair)
        if self.clothing:
            parts.append(self.clothing)
        if self.accessories:
            parts.append(self.accessories)
        if self.distinctive_features:
            parts.append(self.distinctive_features)
        return ", ".join(parts)


class Character(BaseModel):
    """Character definition"""
    id: str                     # char_001
    name: str
    role: str = "配角"          # 主角/配角/群演
    appearance: CharacterAppearance = Field(default_factory=CharacterAppearance)
    personality: str = ""
    voice_id: str | None = None  # TTS voice ID (Phase 3)

    def get_description(self) -> str:
        """Get full character description for prompts"""
        parts = [f"{self.name}"]
        if self.appearance:
            appearance_str = self.appearance.to_prompt()
            if appearance_str:
                parts.append(appearance_str)
        return ", ".join(parts)


class Location(BaseModel):
    """Location/scene setting"""
    id: str                     # loc_001
    name: str
    description: str = ""
    time_of_day: str = ""
    atmosphere: str = ""
    reference_prompt_zh: str = ""    # Chinese prompt
    reference_prompt_en: str = ""    # English prompt (translated)


class Scene(BaseModel):
    """Scene/shot definition"""
    scene_id: int
    location_id: str = ""
    character_ids: list[str] = Field(default_factory=list)
    duration: str = "5秒"
    shot_type: str = "中景"           # 远景/全景/中景/近景/特写
    camera_movement: str = "固定"     # 固定/推进/拉远/平移/俯仰
    visual_description: str = ""      # 画面描述
    narration: str | None = None      # 旁白
    dialogue: dict[str, str] | None = None  # {角色ID: 对话内容}
    mood: str = ""
    image_prompt_zh: str = ""         # Chinese prompt
    image_prompt_en: str = ""         # English prompt (translated)


class StyleGuide(BaseModel):
    """Visual style guide"""
    visual_style: str = "写实"        # 写实/动漫/3D/插画/水彩
    color_palette: list[str] = Field(default_factory=list)
    aspect_ratio: str = "16:9"
    target_duration: str = "60秒"


class Script(BaseModel):
    """Complete script structure"""
    title: str = ""
    summary: str = ""
    characters: list[Character] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    style_guide: StyleGuide = Field(default_factory=StyleGuide)
    outline: str = ""                 # Original outline text
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_character_by_id(self, char_id: str) -> Character | None:
        """Get character by ID"""
        for char in self.characters:
            if char.id == char_id:
                return char
        return None

    def get_location_by_id(self, loc_id: str) -> Location | None:
        """Get location by ID"""
        for loc in self.locations:
            if loc.id == loc_id:
                return loc
        return None

    def add_character(self, character: Character) -> None:
        """Add a character"""
        # Ensure unique ID
        existing_ids = {c.id for c in self.characters}
        if character.id in existing_ids:
            # Generate new ID
            i = 1
            while f"char_{i:03d}" in existing_ids:
                i += 1
            character.id = f"char_{i:03d}"
        self.characters.append(character)
        self.updated_at = datetime.now()

    def add_location(self, location: Location) -> None:
        """Add a location"""
        existing_ids = {l.id for l in self.locations}
        if location.id in existing_ids:
            i = 1
            while f"loc_{i:03d}" in existing_ids:
                i += 1
            location.id = f"loc_{i:03d}"
        self.locations.append(location)
        self.updated_at = datetime.now()

    def add_scene(self, scene: Scene) -> None:
        """Add a scene"""
        # Set scene_id
        if self.scenes:
            scene.scene_id = max(s.scene_id for s in self.scenes) + 1
        else:
            scene.scene_id = 1
        self.scenes.append(scene)
        self.updated_at = datetime.now()

    def remove_character(self, char_id: str) -> bool:
        """Remove a character by ID"""
        for i, char in enumerate(self.characters):
            if char.id == char_id:
                self.characters.pop(i)
                # Also remove from scenes
                for scene in self.scenes:
                    if char_id in scene.character_ids:
                        scene.character_ids.remove(char_id)
                self.updated_at = datetime.now()
                return True
        return False

    def remove_location(self, loc_id: str) -> bool:
        """Remove a location by ID"""
        for i, loc in enumerate(self.locations):
            if loc.id == loc_id:
                self.locations.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def remove_scene(self, scene_id: int) -> bool:
        """Remove a scene by ID"""
        for i, scene in enumerate(self.scenes):
            if scene.scene_id == scene_id:
                self.scenes.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def update_character(self, char_id: str, data: dict) -> bool:
        """Update a character"""
        for char in self.characters:
            if char.id == char_id:
                for key, value in data.items():
                    if hasattr(char, key):
                        setattr(char, key, value)
                self.updated_at = datetime.now()
                return True
        return False

    def update_location(self, loc_id: str, data: dict) -> bool:
        """Update a location"""
        for loc in self.locations:
            if loc.id == loc_id:
                for key, value in data.items():
                    if hasattr(loc, key):
                        setattr(loc, key, value)
                self.updated_at = datetime.now()
                return True
        return False

    def update_scene(self, scene_id: int, data: dict) -> bool:
        """Update a scene"""
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                for key, value in data.items():
                    if hasattr(scene, key):
                        setattr(scene, key, value)
                self.updated_at = datetime.now()
                return True
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "Script":
        """Create from dictionary"""
        return cls.model_validate(data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Script":
        """Create from JSON string"""
        return cls.model_validate_json(json_str)
