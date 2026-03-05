"""Main DearPyGui application"""

import asyncio
import threading
from pathlib import Path

import dearpygui.dearpygui as dpg

from ..adapters import DeepSeekAdapter
from ..services import LLMService, ScriptService, ProjectService, Translator
from ..models import Script
from ..utils.config import Config
from ..utils.i18n import I18n


class PAVUIApp:
    """PAVUI Desktop Application using DearPyGui"""

    def __init__(self):
        # Load config
        self.config = Config()

        # Initialize i18n
        self.i18n = I18n()
        self.i18n.set_language("zh")

        # Initialize services
        self.adapter = DeepSeekAdapter(
            api_key=self.config.deepseek_api_key,
            base_url=self.config.deepseek_base_url,
            model=self.config.deepseek_model,
        )
        self.llm_service = LLMService(self.adapter)
        self.translator = Translator(self.llm_service)
        self.script_service = ScriptService(self.llm_service, self.translator)
        self.project_service = ProjectService()

        # State
        self.current_script: Script | None = None
        self.is_generating = False
        self.loaded_file_content: str | None = None

    def run(self):
        """Run the application"""
        dpg.create_context()

        # Load Chinese font
        self._setup_chinese_font()

        # Create main window
        with dpg.window(tag="main_window"):
            self._create_ui()

        # Setup and show
        dpg.create_viewport(
            title="PAVUI - AI Video Creation Platform",
            width=1400,
            height=900,
        )
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)
        dpg.start_dearpygui()
        dpg.destroy_context()

    def _setup_chinese_font(self):
        """Setup Chinese font for proper display"""
        # Try to find a Chinese font
        font_paths = [
            # WSL - Windows fonts
            "/mnt/c/Windows/Fonts/msyh.ttc",      # 微软雅黑
            "/mnt/c/Windows/Fonts/simsun.ttc",    # 宋体
            "/mnt/c/Windows/Fonts/simhei.ttf",    # 黑体
            # Linux common paths
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            # Project local font
            str(Path(__file__).parent.parent.parent / "assets/fonts/NotoSansSC.otf"),
        ]

        font_path = None
        for path in font_paths:
            if Path(path).exists():
                font_path = path
                break

        if font_path:
            with dpg.font_registry():
                with dpg.font(font_path, 18) as chinese_font:
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
                dpg.bind_font(chinese_font)

    def _create_ui(self):
        """Create the main UI"""
        # Header
        with dpg.group(horizontal=True):
            dpg.add_text("PAVUI - AI视频创作平台", color=(100, 180, 255))
            dpg.add_spacer(width=20)
            dpg.add_text("文本 → 脚本 → 图片 → 视频", color=(150, 150, 150))

        dpg.add_separator()
        dpg.add_spacer(height=10)

        # Main content with tabs
        with dpg.tab_bar():
            # Script Generation Tab
            with dpg.tab(label="脚本生成"):
                self._create_script_tab()

            # Images Tab (placeholder)
            with dpg.tab(label="图片生成"):
                dpg.add_text("即将在第二阶段推出", color=(150, 150, 150))
                dpg.add_spacer(height=10)
                dpg.add_text("功能预览:")
                dpg.add_text("  - 即梦API集成")
                dpg.add_text("  - 角色参考图生成")
                dpg.add_text("  - 场景图片生成")

            # Video Tab (placeholder)
            with dpg.tab(label="视频合成"):
                dpg.add_text("即将在第三阶段推出", color=(150, 150, 150))
                dpg.add_spacer(height=10)
                dpg.add_text("功能预览:")
                dpg.add_text("  - Edge-TTS语音合成")
                dpg.add_text("  - 即梦图生视频")
                dpg.add_text("  - 字幕生成")

            # Settings Tab
            with dpg.tab(label="设置"):
                self._create_settings_tab()

    def _create_script_tab(self):
        """Create script generation tab"""
        with dpg.group(horizontal=True):
            # Left panel - Input
            with dpg.child_window(width=450, height=-1):
                dpg.add_text("输入来源", color=(100, 180, 255))
                dpg.add_separator()
                dpg.add_spacer(height=5)

                # Input mode selection
                with dpg.group(horizontal=True):
                    dpg.add_radio_button(
                        tag="input_mode",
                        items=["直接输入", "加载文件"],
                        default_value="直接输入",
                        horizontal=True,
                        callback=self._on_input_mode_change,
                    )

                dpg.add_spacer(height=5)

                # Direct input panel
                with dpg.group(tag="direct_input_panel"):
                    dpg.add_text("描述你想要的视频内容:")
                    dpg.add_input_text(
                        tag="topic_input",
                        multiline=True,
                        height=120,
                        width=-1,
                        hint="例如: 一个程序员加班后发现咖啡机坏了的搞笑短片",
                    )

                # File input panel (hidden by default)
                with dpg.group(tag="file_input_panel", show=False):
                    # Option 1: Browse button
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="浏览...",
                            callback=self._on_select_file,
                            width=80,
                        )
                        dpg.add_text(tag="file_name_text", default_value="未选择文件", color=(150, 150, 150))

                    dpg.add_spacer(height=5)

                    # Option 2: Paste path directly
                    dpg.add_text("或直接粘贴文件路径:", color=(150, 150, 150))
                    with dpg.group(horizontal=True):
                        dpg.add_input_text(
                            tag="file_path_input",
                            width=-80,
                            hint="/path/to/your/file.txt",
                        )
                        dpg.add_button(
                            label="加载",
                            callback=self._on_load_path,
                            width=70,
                        )

                    dpg.add_spacer(height=5)
                    dpg.add_text("文件预览 (前500字):")
                    dpg.add_input_text(
                        tag="file_preview",
                        multiline=True,
                        height=80,
                        width=-1,
                        readonly=True,
                        default_value="",
                    )

                    dpg.add_spacer(height=5)
                    dpg.add_text("给AI的指令:")
                    dpg.add_input_text(
                        tag="file_instructions",
                        multiline=True,
                        height=60,
                        width=-1,
                        default_value="请总结这篇内容，生成一个包含5-8个场景的视频脚本。",
                    )

                dpg.add_spacer(height=10)

                with dpg.group(horizontal=True):
                    dpg.add_text("视觉风格:")
                    dpg.add_combo(
                        tag="style_select",
                        items=["写实", "动漫", "3D渲染", "插画", "水彩"],
                        default_value="写实",
                        width=100,
                    )
                    dpg.add_spacer(width=20)
                    dpg.add_text("画面比例:")
                    dpg.add_combo(
                        tag="aspect_ratio",
                        items=["16:9", "9:16", "1:1", "4:3"],
                        default_value="16:9",
                        width=80,
                    )

                dpg.add_spacer(height=5)
                dpg.add_checkbox(tag="skip_outline", label="跳过大纲，直接生成分镜")

                dpg.add_spacer(height=15)
                dpg.add_button(
                    tag="generate_btn",
                    label="生成脚本",
                    width=-1,
                    height=40,
                    callback=self._on_generate_click,
                )

                dpg.add_spacer(height=10)
                dpg.add_text(tag="progress_text", default_value="", color=(255, 200, 100))

            dpg.add_spacer(width=10)

            # Right panel - Results
            with dpg.child_window(width=-1, height=-1):
                with dpg.tab_bar():
                    # Characters tab
                    with dpg.tab(label="角色"):
                        with dpg.child_window(tag="characters_panel", height=-1):
                            dpg.add_text(
                                "暂无角色，请先生成脚本",
                                tag="no_characters_text",
                                color=(150, 150, 150),
                            )

                    # Locations tab
                    with dpg.tab(label="场景"):
                        with dpg.child_window(tag="locations_panel", height=-1):
                            dpg.add_text(
                                "暂无场景，请先生成脚本",
                                tag="no_locations_text",
                                color=(150, 150, 150),
                            )

                    # Scenes tab
                    with dpg.tab(label="分镜"):
                        with dpg.child_window(tag="scenes_panel", height=-1):
                            dpg.add_text(
                                "暂无分镜，请先生成脚本",
                                tag="no_scenes_text",
                                color=(150, 150, 150),
                            )

    def _create_settings_tab(self):
        """Create settings tab"""
        dpg.add_text("API配置", color=(100, 180, 255))
        dpg.add_separator()
        dpg.add_spacer(height=10)

        # DeepSeek settings
        dpg.add_text("DeepSeek")
        with dpg.group(horizontal=True):
            dpg.add_text("API密钥:")
            dpg.add_input_text(
                tag="deepseek_key_input",
                password=True,
                width=300,
                hint="输入你的DeepSeek API密钥",
                default_value=self.config.deepseek_api_key or "",
            )
            dpg.add_button(label="测试连接", callback=self._on_test_connection)
            dpg.add_text(tag="test_result", default_value="")

        with dpg.group(horizontal=True):
            dpg.add_text("接口地址:")
            dpg.add_input_text(
                tag="deepseek_url_input",
                width=300,
                default_value=self.config.deepseek_base_url,
            )

        dpg.add_spacer(height=20)
        dpg.add_separator()
        dpg.add_spacer(height=10)

        dpg.add_text("项目存储", color=(100, 180, 255))
        with dpg.group(horizontal=True):
            dpg.add_text("项目目录:")
            dpg.add_input_text(
                width=400,
                default_value=str(self.config.projects_dir),
                enabled=False,
            )

    def _on_input_mode_change(self, sender, app_data):
        """Handle input mode change"""
        if app_data == "直接输入":
            dpg.configure_item("direct_input_panel", show=True)
            dpg.configure_item("file_input_panel", show=False)
        else:
            dpg.configure_item("direct_input_panel", show=False)
            dpg.configure_item("file_input_panel", show=True)

    def _on_load_path(self, sender, app_data):
        """Load file from pasted path"""
        file_path = dpg.get_value("file_path_input").strip()
        if not file_path:
            dpg.set_value("file_name_text", "请输入文件路径")
            dpg.configure_item("file_name_text", color=(255, 100, 100))
            return

        # Expand ~ to home directory
        file_path = str(Path(file_path).expanduser())

        if not Path(file_path).exists():
            dpg.set_value("file_name_text", "文件不存在")
            dpg.configure_item("file_name_text", color=(255, 100, 100))
            return

        self._load_file(file_path)

    def _load_file(self, file_path: str):
        """Load a text file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            file_name = Path(file_path).name
            file_size = len(content)

            # Check file size (roughly 1 token = 1.5 chars for Chinese, limit ~60k tokens)
            MAX_CHARS = 80000
            if file_size > MAX_CHARS:
                content = content[:MAX_CHARS]
                dpg.set_value("file_name_text", f"{file_name} ({file_size:,}字符 - 已截断至{MAX_CHARS:,})")
                dpg.configure_item("file_name_text", color=(255, 200, 100))
            else:
                dpg.set_value("file_name_text", f"{file_name} ({file_size:,}字符)")
                dpg.configure_item("file_name_text", color=(100, 255, 100))

            self.loaded_file_content = content

            # Show preview (first 500 chars)
            preview = content[:500]
            if len(content) > 500:
                preview += "\n... (已截断)"
            dpg.set_value("file_preview", preview)

        except Exception as e:
            dpg.set_value("file_name_text", f"错误: {str(e)[:30]}")
            dpg.configure_item("file_name_text", color=(255, 100, 100))
            self.loaded_file_content = None

    def _on_select_file(self, sender, app_data):
        """Open file dialog using tkinter (more user-friendly)"""
        import tkinter as tk
        from tkinter import filedialog

        # Create hidden tkinter root
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Open native file dialog
        file_path = filedialog.askopenfilename(
            title="Select a text file",
            filetypes=[
                ("Text files", "*.txt"),
                ("Markdown files", "*.md"),
                ("All files", "*.*"),
            ],
        )

        root.destroy()

        if file_path:
            self._load_file(file_path)


    def _on_generate_click(self, sender, app_data):
        """Handle generate button click"""
        if self.is_generating:
            return

        # Get input based on mode
        input_mode = dpg.get_value("input_mode")
        if input_mode == "直接输入":
            topic = dpg.get_value("topic_input")
            if not topic.strip():
                dpg.set_value("progress_text", "请输入视频主题")
                return
            input_text = topic
        else:
            if not self.loaded_file_content:
                dpg.set_value("progress_text", "请先选择文件")
                return
            instructions = dpg.get_value("file_instructions")
            # Combine file content with instructions
            input_text = f"{instructions}\n\n---\n内容:\n{self.loaded_file_content}"

        if not self.adapter.api_key:
            dpg.set_value("progress_text", "请在设置中配置 DeepSeek API Key")
            return

        # Start generation in background thread
        self.is_generating = True
        dpg.configure_item("generate_btn", enabled=False)
        dpg.set_value("progress_text", "正在生成...")

        thread = threading.Thread(target=self._generate_script_thread, args=(input_text,))
        thread.daemon = True
        thread.start()

    def _generate_script_thread(self, topic: str):
        """Generate script in background thread"""
        try:
            style = dpg.get_value("style_select")
            aspect_ratio = dpg.get_value("aspect_ratio")
            skip_outline = dpg.get_value("skip_outline")

            # Map English style to Chinese for the API
            style_map = {
                "Realistic": "写实",
                "Anime": "动漫",
                "3D Render": "3D渲染",
                "Illustration": "插画",
                "Watercolor": "水彩",
            }
            style_zh = style_map.get(style, "写实")

            def on_progress(msg):
                # Map Chinese progress messages to English
                msg_map = {
                    "正在生成故事大纲...": "Generating story outline...",
                    "正在提取角色和场景...": "Extracting characters and locations...",
                    "正在生成分镜脚本...": "Generating storyboard...",
                    "正在翻译Prompt...": "Translating prompts...",
                    "脚本生成完成！": "Script generation complete!",
                }
                dpg.set_value("progress_text", msg_map.get(msg, msg))

            # Run async generation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            script = loop.run_until_complete(
                self.script_service.generate_full_script(
                    input_text=topic,
                    skip_outline=skip_outline,
                    style=style_zh,
                    aspect_ratio=aspect_ratio,
                    on_progress=on_progress,
                )
            )
            loop.close()

            self.current_script = script
            self._update_script_display()
            dpg.set_value("progress_text", "Script generation complete!")

        except Exception as e:
            dpg.set_value("progress_text", f"Error: {str(e)[:50]}")

        finally:
            self.is_generating = False
            dpg.configure_item("generate_btn", enabled=True)

    def _update_script_display(self):
        """Update the UI to display the generated script"""
        if not self.current_script:
            return

        # Update characters panel
        dpg.delete_item("characters_panel", children_only=True)
        if self.current_script.characters:
            for char in self.current_script.characters:
                with dpg.group(parent="characters_panel"):
                    dpg.add_text(f"* {char.name} ({char.role})", color=(100, 200, 150))
                    dpg.add_text(f"  Personality: {char.personality}", color=(150, 150, 150))
                    if char.appearance:
                        appearance_text = char.appearance.to_prompt()[:80]
                        if len(char.appearance.to_prompt()) > 80:
                            appearance_text += "..."
                        dpg.add_text(f"  Appearance: {appearance_text}", color=(120, 120, 120))
                    dpg.add_separator()
        else:
            dpg.add_text("No characters", parent="characters_panel", color=(150, 150, 150))

        # Update locations panel
        dpg.delete_item("locations_panel", children_only=True)
        if self.current_script.locations:
            for loc in self.current_script.locations:
                with dpg.group(parent="locations_panel"):
                    dpg.add_text(f"* {loc.name}", color=(100, 200, 150))
                    dpg.add_text(f"  Time: {loc.time_of_day} | Mood: {loc.atmosphere}", color=(150, 150, 150))
                    desc_text = loc.description[:60]
                    if len(loc.description) > 60:
                        desc_text += "..."
                    dpg.add_text(f"  {desc_text}", color=(120, 120, 120))
                    dpg.add_separator()
        else:
            dpg.add_text("No locations", parent="locations_panel", color=(150, 150, 150))

        # Update scenes panel
        dpg.delete_item("scenes_panel", children_only=True)
        if self.current_script.scenes:
            # Build lookup maps
            char_map = {c.id: c.name for c in self.current_script.characters}
            loc_map = {l.id: l.name for l in self.current_script.locations}

            for scene in self.current_script.scenes:
                with dpg.group(parent="scenes_panel"):
                    loc_name = loc_map.get(scene.location_id, "Unknown")
                    char_names = [char_map.get(cid, cid) for cid in scene.character_ids]

                    dpg.add_text(f"Scene {scene.scene_id}", color=(100, 180, 255))
                    dpg.add_text(
                        f"  {scene.shot_type} | {scene.camera_movement} | {scene.duration}",
                        color=(150, 150, 150)
                    )
                    dpg.add_text(
                        f"  Location: {loc_name} | Characters: {', '.join(char_names) or 'None'}",
                        color=(120, 120, 120)
                    )
                    desc_text = scene.visual_description[:80]
                    if len(scene.visual_description) > 80:
                        desc_text += "..."
                    dpg.add_text(f"  {desc_text}", color=(180, 180, 180))
                    if scene.narration:
                        narr_text = scene.narration[:50]
                        if len(scene.narration) > 50:
                            narr_text += "..."
                        dpg.add_text(f"  Narration: {narr_text}", color=(200, 180, 100))
                    dpg.add_separator()
        else:
            dpg.add_text("No scenes", parent="scenes_panel", color=(150, 150, 150))

    def _on_test_connection(self, sender, app_data):
        """Test API connection"""
        # Get the API key from input field
        api_key = dpg.get_value("deepseek_key_input")
        base_url = dpg.get_value("deepseek_url_input")

        if not api_key or api_key.endswith("..."):
            dpg.set_value("test_result", "请输入完整API密钥")
            return

        dpg.set_value("test_result", "测试中...")

        def test_thread():
            try:
                # Create a new adapter with the entered API key
                test_adapter = DeepSeekAdapter(
                    api_key=api_key,
                    base_url=base_url,
                    model=self.config.deepseek_model,
                )

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(test_adapter.test_connection())
                loop.close()

                if success:
                    # Update the adapter in the service
                    self.adapter = test_adapter
                    self.llm_service.adapter = test_adapter
                    dpg.set_value("test_result", "成功 - 已连接!")
                else:
                    dpg.set_value("test_result", "失败 - 检查API密钥")
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg:
                    dpg.set_value("test_result", "失败 - API密钥无效")
                elif "timeout" in error_msg.lower():
                    dpg.set_value("test_result", "失败 - 连接超时")
                else:
                    dpg.set_value("test_result", f"错误: {error_msg[:40]}")

        thread = threading.Thread(target=test_thread)
        thread.daemon = True
        thread.start()


def create_app():
    """Create and return the app instance"""
    return PAVUIApp()
