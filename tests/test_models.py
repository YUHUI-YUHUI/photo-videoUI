"""Tests for data models"""

import pytest
from datetime import datetime

from src.models import (
    Script,
    Character,
    CharacterAppearance,
    Location,
    Scene,
    StyleGuide,
)


class TestCharacter:
    def test_create_character(self):
        char = Character(
            id="char_001",
            name="小明",
            role="主角",
            personality="乐观开朗",
        )
        assert char.id == "char_001"
        assert char.name == "小明"
        assert char.role == "主角"

    def test_character_appearance(self):
        appearance = CharacterAppearance(
            gender="男",
            age="25岁",
            height="中等身材",
            face="圆脸、浓眉大眼",
            hair="黑色短发",
            clothing="蓝色卫衣",
            accessories="黑框眼镜",
            distinctive_features="左脸有痣",
        )
        prompt = appearance.to_prompt()
        assert "男" in prompt
        assert "25岁" in prompt
        assert "蓝色卫衣" in prompt

    def test_character_description(self):
        char = Character(
            id="char_001",
            name="小明",
            role="主角",
            appearance=CharacterAppearance(
                gender="男",
                clothing="蓝色卫衣",
            ),
        )
        desc = char.get_description()
        assert "小明" in desc
        assert "蓝色卫衣" in desc


class TestLocation:
    def test_create_location(self):
        loc = Location(
            id="loc_001",
            name="咖啡厅",
            description="现代简约风格",
            time_of_day="下午",
            atmosphere="温馨",
        )
        assert loc.id == "loc_001"
        assert loc.name == "咖啡厅"


class TestScene:
    def test_create_scene(self):
        scene = Scene(
            scene_id=1,
            location_id="loc_001",
            character_ids=["char_001"],
            duration="5秒",
            shot_type="中景",
            visual_description="小明坐在咖啡厅",
            narration="那天下午...",
            mood="平静",
        )
        assert scene.scene_id == 1
        assert "char_001" in scene.character_ids


class TestScript:
    def test_create_empty_script(self):
        script = Script(title="测试视频", summary="测试")
        assert script.title == "测试视频"
        assert len(script.characters) == 0
        assert len(script.scenes) == 0

    def test_add_character(self):
        script = Script(title="测试")
        char = Character(id="char_001", name="小明", role="主角")
        script.add_character(char)
        assert len(script.characters) == 1
        assert script.get_character_by_id("char_001") is not None

    def test_add_location(self):
        script = Script(title="测试")
        loc = Location(id="loc_001", name="咖啡厅")
        script.add_location(loc)
        assert len(script.locations) == 1
        assert script.get_location_by_id("loc_001") is not None

    def test_add_scene(self):
        script = Script(title="测试")
        scene = Scene(scene_id=0, visual_description="测试场景")
        script.add_scene(scene)
        assert len(script.scenes) == 1
        assert script.scenes[0].scene_id == 1  # Auto-assigned

    def test_remove_character(self):
        script = Script(title="测试")
        char = Character(id="char_001", name="小明", role="主角")
        script.add_character(char)
        assert script.remove_character("char_001")
        assert len(script.characters) == 0

    def test_to_json(self):
        script = Script(
            title="测试视频",
            summary="测试",
            characters=[Character(id="char_001", name="小明", role="主角")],
        )
        json_str = script.to_json()
        assert "测试视频" in json_str
        assert "小明" in json_str

    def test_from_json(self):
        original = Script(
            title="测试视频",
            summary="测试",
            characters=[Character(id="char_001", name="小明", role="主角")],
        )
        json_str = original.to_json()
        restored = Script.from_json(json_str)
        assert restored.title == original.title
        assert len(restored.characters) == 1
        assert restored.characters[0].name == "小明"
