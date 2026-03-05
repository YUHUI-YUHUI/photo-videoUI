"""Script generation tab"""

import asyncio
import json
from typing import Any

import gradio as gr

from ...models import Script, Character, CharacterAppearance, Location, Scene, ProjectStatus
from ...services import ScriptService, ProjectService
from ...utils.i18n import t


def create_script_tab(
    script_service: ScriptService,
    project_service: ProjectService,
) -> dict:
    """Create the script generation tab"""

    # State
    current_script = gr.State(None)
    current_project_id = gr.State(None)

    with gr.Row():
        # Left panel - Input
        with gr.Column(scale=1):
            gr.Markdown(f"### {t('script.input_title')}")

            topic_input = gr.Textbox(
                label="",
                placeholder=t("script.input_placeholder"),
                lines=6,
                max_lines=10,
            )

            with gr.Row():
                style_select = gr.Dropdown(
                    choices=[
                        ("写实", "写实"),
                        ("动漫", "动漫"),
                        ("3D渲染", "3D渲染"),
                        ("插画", "插画"),
                        ("水彩", "水彩"),
                    ],
                    value="写实",
                    label=t("script.style"),
                    scale=1,
                )
                aspect_ratio = gr.Dropdown(
                    choices=["16:9", "9:16", "1:1", "4:3"],
                    value="16:9",
                    label=t("script.aspect_ratio"),
                    scale=1,
                )

            skip_outline = gr.Checkbox(
                label=t("script.skip_outline"),
                value=False,
            )

            generate_btn = gr.Button(
                t("script.generate"),
                variant="primary",
                size="lg",
            )

            # Progress
            progress_box = gr.Markdown(
                "",
                visible=False,
                elem_classes="progress-container",
            )

        # Right panel - Script display
        with gr.Column(scale=2):
            with gr.Tabs():
                # Characters tab
                with gr.Tab(t("script.characters")):
                    characters_list = gr.HTML(
                        _render_empty_state("script.no_characters"),
                        elem_id="characters-list",
                    )

                # Locations tab
                with gr.Tab(t("script.locations")):
                    locations_list = gr.HTML(
                        _render_empty_state("script.no_locations"),
                        elem_id="locations-list",
                    )

                # Scenes tab
                with gr.Tab(t("script.scenes")):
                    scenes_list = gr.HTML(
                        _render_empty_state("script.no_scenes"),
                        elem_id="scenes-list",
                    )

    # Character editor (hidden by default)
    with gr.Row(visible=False) as character_editor:
        with gr.Column(elem_classes="editor-panel"):
            gr.Markdown(f"### {t('character.title')}")

            edit_char_id = gr.Textbox(visible=False)

            with gr.Row():
                edit_char_name = gr.Textbox(label=t("character.name"), scale=2)
                edit_char_role = gr.Dropdown(
                    choices=[
                        (t("character.role_protagonist"), "主角"),
                        (t("character.role_supporting"), "配角"),
                        (t("character.role_extra"), "群演"),
                    ],
                    label=t("character.role"),
                    scale=1,
                )

            edit_char_personality = gr.Textbox(label=t("character.personality"), lines=2)

            gr.Markdown(f"**{t('character.title')} - 外观设定**")

            with gr.Row():
                edit_char_gender = gr.Dropdown(
                    choices=[
                        (t("character.gender_male"), "男"),
                        (t("character.gender_female"), "女"),
                    ],
                    label=t("character.gender"),
                    scale=1,
                )
                edit_char_age = gr.Textbox(label=t("character.age"), scale=2)

            edit_char_height = gr.Textbox(label=t("character.height"))
            edit_char_face = gr.Textbox(label=t("character.face"))
            edit_char_hair = gr.Textbox(label=t("character.hair"))
            edit_char_clothing = gr.Textbox(label=t("character.clothing"))
            edit_char_accessories = gr.Textbox(label=t("character.accessories"))
            edit_char_features = gr.Textbox(label=t("character.distinctive_features"))

            with gr.Row():
                cancel_char_btn = gr.Button(t("app.cancel"))
                save_char_btn = gr.Button(t("app.save"), variant="primary")

    # Scene editor (hidden by default)
    with gr.Row(visible=False) as scene_editor:
        with gr.Column(elem_classes="editor-panel"):
            gr.Markdown(f"### {t('scene.title')}")

            edit_scene_id = gr.Number(visible=False)

            with gr.Row():
                edit_scene_location = gr.Dropdown(
                    choices=[],
                    label=t("scene.location"),
                    scale=2,
                )
                edit_scene_duration = gr.Dropdown(
                    choices=["3秒", "5秒", "8秒", "10秒", "15秒"],
                    value="5秒",
                    label=t("scene.duration"),
                    scale=1,
                )

            edit_scene_characters = gr.CheckboxGroup(
                choices=[],
                label=t("scene.characters"),
            )

            with gr.Row():
                edit_scene_shot = gr.Dropdown(
                    choices=[
                        (t("scene.shot_wide"), "远景"),
                        (t("scene.shot_full"), "全景"),
                        (t("scene.shot_medium"), "中景"),
                        (t("scene.shot_close"), "近景"),
                        (t("scene.shot_closeup"), "特写"),
                    ],
                    value="中景",
                    label=t("scene.shot_type"),
                    scale=1,
                )
                edit_scene_camera = gr.Dropdown(
                    choices=[
                        (t("scene.camera_static"), "固定"),
                        (t("scene.camera_push"), "推进"),
                        (t("scene.camera_pull"), "拉远"),
                        (t("scene.camera_pan"), "平移"),
                        (t("scene.camera_tilt"), "俯仰"),
                    ],
                    value="固定",
                    label=t("scene.camera_movement"),
                    scale=1,
                )

            edit_scene_visual = gr.Textbox(
                label=t("scene.visual_description"),
                lines=3,
            )
            edit_scene_narration = gr.Textbox(
                label=t("scene.narration"),
                lines=2,
            )
            edit_scene_mood = gr.Textbox(label=t("scene.mood"))

            with gr.Row():
                cancel_scene_btn = gr.Button(t("app.cancel"))
                save_scene_btn = gr.Button(t("app.save"), variant="primary")

    # Event handlers
    def generate_script(topic, style, ratio, skip, project_id, progress=gr.Progress()):
        """Generate script from topic"""
        if not topic.strip():
            return (
                gr.update(),  # current_script
                gr.update(visible=True, value="请输入视频主题"),  # progress
                gr.update(),  # characters
                gr.update(),  # locations
                gr.update(),  # scenes
            )

        progress_messages = []

        def on_progress(msg):
            progress_messages.append(msg)

        try:
            # Run async generation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            script = loop.run_until_complete(
                script_service.generate_full_script(
                    input_text=topic,
                    skip_outline=skip,
                    style=style,
                    aspect_ratio=ratio,
                    on_progress=on_progress,
                )
            )
            loop.close()

            # Save to project if we have one
            if project_id:
                project_service.update_script(project_id, script)

            # Render UI
            return (
                script,  # current_script
                gr.update(visible=False),  # progress
                _render_characters(script.characters),
                _render_locations(script.locations),
                _render_scenes(script.scenes, script.characters, script.locations),
            )

        except Exception as e:
            return (
                gr.update(),
                gr.update(visible=True, value=f"生成失败: {str(e)}"),
                gr.update(),
                gr.update(),
                gr.update(),
            )

    generate_btn.click(
        fn=generate_script,
        inputs=[topic_input, style_select, aspect_ratio, skip_outline, current_project_id],
        outputs=[current_script, progress_box, characters_list, locations_list, scenes_list],
    )

    return {
        "current_script": current_script,
        "current_project_id": current_project_id,
        "topic_input": topic_input,
        "generate_btn": generate_btn,
        "characters_list": characters_list,
        "locations_list": locations_list,
        "scenes_list": scenes_list,
    }


def _render_empty_state(text_key: str) -> str:
    """Render empty state HTML"""
    return f"""
    <div class="empty-state">
        <div class="empty-state-icon">📝</div>
        <p>{t(text_key)}</p>
    </div>
    """


def _render_characters(characters: list[Character]) -> str:
    """Render characters list as HTML"""
    if not characters:
        return _render_empty_state("script.no_characters")

    html = '<div class="scrollable-list">'
    for char in characters:
        role_badge = {
            "主角": "🌟",
            "配角": "👤",
            "群演": "👥",
        }.get(char.role, "👤")

        html += f"""
        <div class="card">
            <div class="card-title">{role_badge} {char.name}</div>
            <div class="card-subtitle">{char.role} · {char.personality}</div>
            <div style="margin-top: 0.5rem; font-size: 0.85rem; color: var(--neutral-400);">
                {char.appearance.to_prompt() if char.appearance else ''}
            </div>
        </div>
        """
    html += "</div>"
    return html


def _render_locations(locations: list[Location]) -> str:
    """Render locations list as HTML"""
    if not locations:
        return _render_empty_state("script.no_locations")

    html = '<div class="scrollable-list">'
    for loc in locations:
        html += f"""
        <div class="card">
            <div class="card-title">📍 {loc.name}</div>
            <div class="card-subtitle">{loc.time_of_day} · {loc.atmosphere}</div>
            <div style="margin-top: 0.5rem; font-size: 0.85rem; color: var(--neutral-400);">
                {loc.description}
            </div>
        </div>
        """
    html += "</div>"
    return html


def _render_scenes(
    scenes: list[Scene],
    characters: list[Character],
    locations: list[Location],
) -> str:
    """Render scenes list as HTML"""
    if not scenes:
        return _render_empty_state("script.no_scenes")

    # Build lookup maps
    char_map = {c.id: c.name for c in characters}
    loc_map = {l.id: l.name for l in locations}

    html = '<div class="scrollable-list">'
    for scene in scenes:
        loc_name = loc_map.get(scene.location_id, "未知场景")
        char_names = [char_map.get(cid, cid) for cid in scene.character_ids]

        html += f"""
        <div class="scene-card">
            <div class="scene-header">
                <span class="scene-number">场景 {scene.scene_id}</span>
                <span class="scene-meta">{scene.shot_type} · {scene.camera_movement} · {scene.duration}</span>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <span style="color: var(--neutral-400);">📍</span> {loc_name}
                <span style="margin-left: 1rem; color: var(--neutral-400);">👥</span> {', '.join(char_names) or '无'}
            </div>
            <div style="font-size: 0.9rem; margin-bottom: 0.5rem;">
                {scene.visual_description}
            </div>
            {"<div style='font-style: italic; color: var(--neutral-300);'>🎙 " + scene.narration + "</div>" if scene.narration else ""}
            <div style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--neutral-500);">
                情绪: {scene.mood}
            </div>
        </div>
        """
    html += "</div>"
    return html
