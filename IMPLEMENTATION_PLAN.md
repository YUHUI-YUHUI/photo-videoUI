# PAVUI 实现计划

## Phase 1: 脚本生成模块 (MVP)

### 1.1 项目结构

```
pavui/
├── app.py                      # Gradio主入口
├── requirements.txt
├── .env.example
├── config/
│   └── settings.yaml           # 配置文件
├── src/
│   ├── __init__.py
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── script.py           # Script, Character, Location, Scene
│   │   └── project.py          # Project 项目管理
│   ├── services/               # 业务逻辑
│   │   ├── __init__.py
│   │   ├── llm_service.py      # LLM调用服务
│   │   ├── script_service.py   # 脚本生成服务
│   │   ├── project_service.py  # 项目管理服务
│   │   └── translator.py       # 中英文翻译服务
│   ├── adapters/               # API适配器
│   │   ├── __init__.py
│   │   ├── base.py             # 基类
│   │   └── deepseek.py         # DeepSeek适配器
│   ├── ui/                     # Gradio界面
│   │   ├── __init__.py
│   │   ├── app.py              # 主应用
│   │   ├── components/         # UI组件
│   │   │   ├── __init__.py
│   │   │   ├── header.py       # 头部组件
│   │   │   ├── project_list.py # 项目列表
│   │   │   ├── script_editor.py# 脚本编辑器
│   │   │   └── scene_card.py   # 场景卡片
│   │   ├── tabs/               # Tab页面
│   │   │   ├── __init__.py
│   │   │   ├── script_tab.py   # 脚本生成Tab
│   │   │   ├── images_tab.py   # 图片生成Tab (Phase 2)
│   │   │   └── video_tab.py    # 视频合成Tab (Phase 3)
│   │   ├── theme.py            # 主题配置
│   │   └── i18n.py             # 国际化
│   └── utils/
│       ├── __init__.py
│       ├── config.py           # 配置加载
│       ├── retry.py            # 智能重试
│       └── file_utils.py       # 文件操作
├── locales/                    # 多语言
│   ├── zh.json
│   └── en.json
├── assets/
│   └── css/
│       └── custom.css          # 自定义样式
└── tests/
    └── ...
```

### 1.2 数据模型设计

#### 1.2.1 Script 模型 (`src/models/script.py`)

```python
@dataclass
class Character:
    id: str                     # char_001
    name: str                   # 小明
    role: str                   # 主角/配角/群演
    appearance: CharacterAppearance
    personality: str
    voice_id: str | None        # TTS声音ID (Phase 3)

@dataclass
class CharacterAppearance:
    gender: str
    age: str
    height: str
    face: str                   # 脸型、五官
    hair: str                   # 发型、发色
    clothing: str
    accessories: str
    distinctive_features: str   # 标志性特征

@dataclass
class Location:
    id: str                     # loc_001
    name: str
    description: str
    time_of_day: str
    atmosphere: str
    reference_prompt_zh: str    # 中文prompt
    reference_prompt_en: str    # 英文prompt (翻译后)

@dataclass
class Scene:
    scene_id: int
    location_id: str
    character_ids: list[str]
    duration: str               # "5秒"
    shot_type: str              # 中景/近景/特写等
    camera_movement: str        # 固定/推进/平移等
    visual_description: str     # 中文画面描述
    narration: str | None       # 旁白
    dialogue: dict[str, str] | None  # {角色ID: 对话内容}
    mood: str
    image_prompt_zh: str        # 中文prompt
    image_prompt_en: str        # 英文prompt (翻译后)

@dataclass
class StyleGuide:
    visual_style: str           # 写实/动漫/3D等
    color_palette: list[str]
    aspect_ratio: str           # 16:9, 9:16, 1:1
    target_duration: str

@dataclass
class Script:
    title: str
    summary: str
    characters: list[Character]
    locations: list[Location]
    scenes: list[Scene]
    style_guide: StyleGuide
    created_at: datetime
    updated_at: datetime
```

#### 1.2.2 Project 模型 (`src/models/project.py`)

```python
@dataclass
class Project:
    id: str                     # UUID
    name: str                   # 项目名称
    path: Path                  # 项目目录路径
    script: Script | None
    status: ProjectStatus       # draft/generating/completed
    created_at: datetime
    updated_at: datetime

class ProjectStatus(Enum):
    DRAFT = "draft"
    SCRIPT_GENERATING = "script_generating"
    SCRIPT_READY = "script_ready"
    IMAGES_GENERATING = "images_generating"  # Phase 2
    IMAGES_READY = "images_ready"            # Phase 2
    VIDEO_GENERATING = "video_generating"    # Phase 3
    COMPLETED = "completed"                  # Phase 3

# 项目目录结构
# ~/pavui_projects/{project_id}/
#   ├── project.json            # 项目元数据
#   ├── script.json             # 脚本数据
#   ├── images/                 # Phase 2
#   │   ├── characters/         # 角色参考图
#   │   ├── locations/          # 场景参考图
#   │   └── scenes/             # 分镜图片
#   ├── audio/                  # Phase 3
#   └── output/                 # Phase 3
```

### 1.3 服务层设计

#### 1.3.1 LLM Service (`src/services/llm_service.py`)

```python
class LLMService:
    """统一的LLM调用服务"""

    def __init__(self, adapter: BaseLLMAdapter):
        self.adapter = adapter
        self.retry_handler = SmartRetryHandler()

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """普通文本生成"""

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        schema: dict | None = None,  # JSON Schema
    ) -> dict:
        """JSON模式生成，自动验证格式"""
```

#### 1.3.2 Script Service (`src/services/script_service.py`)

```python
class ScriptService:
    """脚本生成服务 - 三阶段生成"""

    def __init__(self, llm_service: LLMService, translator: Translator):
        self.llm = llm_service
        self.translator = translator

    # === 阶段1: 故事大纲 ===
    async def generate_outline(
        self,
        topic: str,
        style: str = "写实",
    ) -> str:
        """从主题生成故事大纲（可跳过）"""

    # === 阶段2: 角色与场景提取 ===
    async def extract_elements(
        self,
        outline_or_description: str,
        style: str,
    ) -> tuple[list[Character], list[Location]]:
        """从大纲/描述中提取角色和场景"""

    # === 阶段3: 分镜生成 ===
    async def generate_scenes(
        self,
        outline: str,
        characters: list[Character],
        locations: list[Location],
        style_guide: StyleGuide,
    ) -> list[Scene]:
        """生成详细分镜"""

    # === 完整流程 ===
    async def generate_full_script(
        self,
        input_text: str,
        skip_outline: bool = False,
        style: str = "写实",
        aspect_ratio: str = "16:9",
        on_progress: Callable | None = None,
    ) -> Script:
        """完整脚本生成流程"""

    # === Prompt翻译 ===
    async def translate_prompts(self, script: Script) -> Script:
        """将所有中文prompt翻译为英文"""
```

#### 1.3.3 Project Service (`src/services/project_service.py`)

```python
class ProjectService:
    """项目管理服务"""

    PROJECTS_DIR = Path.home() / "pavui_projects"

    def list_projects(self) -> list[ProjectSummary]:
        """列出所有项目"""

    def create_project(self, name: str) -> Project:
        """创建新项目"""

    def load_project(self, project_id: str) -> Project:
        """加载项目"""

    def save_project(self, project: Project) -> None:
        """保存项目（自动调用）"""

    def delete_project(self, project_id: str) -> None:
        """删除项目"""

    def export_script(self, project: Project, format: str = "json") -> Path:
        """导出脚本"""
```

#### 1.3.4 智能重试 (`src/utils/retry.py`)

```python
class SmartRetryHandler:
    """智能重试处理器"""

    MAX_RETRIES = 3

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        根据错误类型决定重试策略:
        - 网络错误: 指数退避重试
        - API限流(429): 等待后重试
        - 认证失败(401/403): 不重试，直接报错
        - 服务器错误(5xx): 重试
        - 内容审核: 不重试，报告原因
        """
```

### 1.4 UI组件设计

#### 1.4.1 主布局 (`src/ui/app.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│  PAVUI - AI视频创作平台              [项目: xxx ▼] [🌐中/EN] [⚙]│
├─────────────────────────────────────────────────────────────────┤
│  [📝 脚本生成]  [🎨 图片生成]  [🎬 视频合成]                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  (当前Tab内容)                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.4.2 脚本生成Tab (`src/ui/tabs/script_tab.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│ 左侧面板 (30%)                │ 右侧面板 (70%)                  │
├───────────────────────────────┼─────────────────────────────────┤
│ ┌───────────────────────────┐ │ ┌─────────────────────────────┐ │
│ │ 输入创意                  │ │ │ 角色列表                    │ │
│ │ ┌───────────────────────┐ │ │ │ ┌─────┐ ┌─────┐ ┌─────┐   │ │
│ │ │ 文本框                │ │ │ │ │角色1│ │角色2│ │+添加│   │ │
│ │ │ (支持粘贴大纲)        │ │ │ │ └─────┘ └─────┘ └─────┘   │ │
│ │ └───────────────────────┘ │ │ └─────────────────────────────┘ │
│ │                           │ │                                 │
│ │ 视觉风格: [写实 ▼]        │ │ ┌─────────────────────────────┐ │
│ │ 画面比例: [16:9 ▼]        │ │ │ 场景列表                    │ │
│ │                           │ │ │ ┌─────┐ ┌─────┐ ┌─────┐   │ │
│ │ ☐ 跳过大纲，直接生成分镜 │ │ │ │场景1│ │场景2│ │+添加│   │ │
│ │                           │ │ │ └─────┘ └─────┘ └─────┘   │ │
│ │ [▶ 生成脚本]              │ │ └─────────────────────────────┘ │
│ └───────────────────────────┘ │                                 │
│                               │ ┌─────────────────────────────┐ │
│ ┌───────────────────────────┐ │ │ 分镜列表                    │ │
│ │ 生成进度                  │ │ │ ┌─────────────────────────┐ │ │
│ │ ████████░░░░ 60%          │ │ │ │ 分镜1                   │ │ │
│ │ 正在生成角色设定...       │ │ │ │ 画面: xxx               │ │ │
│ └───────────────────────────┘ │ │ │ 旁白: xxx               │ │ │
│                               │ │ │ [编辑] [删除]           │ │ │
│                               │ │ └─────────────────────────┘ │ │
│                               │ │ ┌─────────────────────────┐ │ │
│                               │ │ │ 分镜2 ...               │ │ │
│                               │ │ └─────────────────────────┘ │ │
│                               │ └─────────────────────────────┘ │
└───────────────────────────────┴─────────────────────────────────┘
```

#### 1.4.3 可视化编辑组件

**角色编辑弹窗:**
```
┌─────────────────────────────────────┐
│ 编辑角色: 小明                   [X]│
├─────────────────────────────────────┤
│ 基本信息                            │
│ 名称: [小明        ]                │
│ 定位: [主角 ▼]                      │
│ 性格: [乐观开朗、有点冒失]          │
│                                     │
│ 外观设定                            │
│ 性别: [男 ▼]  年龄: [25岁左右  ]    │
│ 体型: [中等身材      ]              │
│ 脸型/五官: [圆脸、浓眉大眼    ]     │
│ 发型: [短发          ]              │
│ 服装: [蓝色卫衣、牛仔裤    ]        │
│ 配饰: [黑框眼镜      ]              │
│ 特征: [左脸有一颗小痣  ]            │
│                                     │
│         [取消]  [保存]              │
└─────────────────────────────────────┘
```

**分镜编辑弹窗:**
```
┌─────────────────────────────────────┐
│ 编辑分镜 #1                      [X]│
├─────────────────────────────────────┤
│ 场景: [咖啡厅 ▼]                    │
│ 出场角色: [☑小明 ☐小红 ▼]          │
│                                     │
│ 镜头设置                            │
│ 镜头类型: [中景 ▼]                  │
│ 镜头运动: [固定 ▼]                  │
│ 时长: [5秒 ▼]                       │
│                                     │
│ 画面描述:                           │
│ ┌─────────────────────────────────┐ │
│ │小明坐在咖啡厅靠窗的位置，阳光 │ │
│ │洒在他身上，他正低头看着手机    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 旁白:                               │
│ ┌─────────────────────────────────┐ │
│ │那天下午，我收到了一条改变人生 │ │
│ │的消息。                        │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 对话: (可选)                        │
│ ┌─────────────────────────────────┐ │
│ │                                │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 情绪氛围: [平静、期待    ]          │
│                                     │
│         [取消]  [保存]              │
└─────────────────────────────────────┘
```

### 1.5 Prompt模板设计

#### 1.5.1 大纲生成Prompt

```python
OUTLINE_SYSTEM_PROMPT = """你是一个专业的短视频脚本创作者。
根据用户的主题创作一个适合短视频的故事大纲。

要求：
1. 故事完整，有开头、发展、高潮、结尾
2. 控制在3-8个场景
3. 适合视觉呈现，包含具体的画面元素
4. 情节紧凑，适合1-2分钟短视频

输出格式：
## 标题
[视频标题]

## 简介
[一句话简介]

## 故事大纲
[详细的故事大纲，分段落描述]

## 主要角色
- 角色1：[简要描述外观和性格]
- 角色2：[简要描述外观和性格]

## 主要场景
- 场景1：[简要描述]
- 场景2：[简要描述]
"""
```

#### 1.5.2 角色场景提取Prompt

```python
EXTRACT_ELEMENTS_SYSTEM_PROMPT = """你是一个专业的视频分镜师。
从故事大纲中提取所有角色和场景的详细设定。

角色设定要求：
1. 外观描述要详细具体，便于AI图像生成保持一致性
2. 包含"DNA锚点"：脸型、发型/发色、标志性配饰、服装颜色
3. 特征描述使用固定词汇，避免同义词替换

场景设定要求：
1. 包含时间、光线、氛围
2. 描述具体的环境元素

输出JSON格式（严格遵循）：
{
  "characters": [...],
  "locations": [...]
}
"""
```

#### 1.5.3 分镜生成Prompt

```python
SCENES_SYSTEM_PROMPT = """你是一个专业的分镜脚本师。
根据故事大纲、角色设定和场景设定，生成详细的分镜脚本。

每个分镜包含：
1. 使用的场景和出场角色（引用ID）
2. 镜头类型和运动方式
3. 详细的画面描述（包含完整的角色外观描述）
4. 旁白或对话
5. 情绪氛围
6. 用于AI图像生成的prompt（中文）

输出JSON格式：
{
  "scenes": [...]
}
"""
```

### 1.6 配置文件

#### 1.6.1 settings.yaml

```yaml
# PAVUI 配置文件

# 语言设置
language: zh  # zh | en

# LLM服务配置
llm:
  default_provider: deepseek
  providers:
    deepseek:
      api_key: ""  # 或使用环境变量 DEEPSEEK_API_KEY
      base_url: "https://api.deepseek.com/v1"
      model: "deepseek-chat"

# 项目存储
storage:
  projects_dir: "~/pavui_projects"

# UI设置
ui:
  theme: dark  # dark | light
```

#### 1.6.2 .env.example

```
# DeepSeek API
DEEPSEEK_API_KEY=your-api-key

# 后续阶段使用
# JIMENG_API_KEY=
# JIMENG_SECRET_KEY=
```

### 1.7 国际化 (`locales/zh.json`)

```json
{
  "app": {
    "title": "PAVUI - AI视频创作平台",
    "project": "项目"
  },
  "tabs": {
    "script": "脚本生成",
    "images": "图片生成",
    "video": "视频合成"
  },
  "script": {
    "input_placeholder": "请描述你想创作的视频主题...",
    "style": "视觉风格",
    "aspect_ratio": "画面比例",
    "skip_outline": "跳过大纲，直接生成分镜",
    "generate": "生成脚本",
    "characters": "角色列表",
    "locations": "场景列表",
    "scenes": "分镜列表",
    "edit": "编辑",
    "delete": "删除",
    "add": "添加"
  },
  "styles": {
    "realistic": "写实",
    "anime": "动漫",
    "3d": "3D渲染",
    "illustration": "插画",
    "watercolor": "水彩"
  },
  "errors": {
    "api_key_missing": "请先配置API密钥",
    "generation_failed": "生成失败，请重试"
  }
}
```

### 1.8 依赖清单

```txt
# requirements.txt

# Web框架
gradio>=4.0.0

# HTTP客户端
httpx>=0.25.0

# 配置管理
python-dotenv>=1.0.0
pyyaml>=6.0

# 数据模型
pydantic>=2.0.0

# 工具
uuid

# 测试
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

### 1.9 开发步骤

#### Step 1: 基础框架 (Day 1)
- [ ] 创建项目结构
- [ ] 实现配置加载 (`config.py`)
- [ ] 实现国际化 (`i18n.py`)
- [ ] 创建数据模型 (`models/`)

#### Step 2: DeepSeek适配器 (Day 2)
- [ ] 实现 `BaseLLMAdapter`
- [ ] 实现 `DeepSeekAdapter`
- [ ] 实现智能重试 (`retry.py`)
- [ ] 编写单元测试

#### Step 3: 脚本服务 (Day 3-4)
- [ ] 实现 `LLMService`
- [ ] 实现 `ScriptService` 三阶段生成
- [ ] 实现 Prompt 模板
- [ ] 实现翻译服务（中→英）
- [ ] 编写单元测试

#### Step 4: 项目管理 (Day 5)
- [ ] 实现 `ProjectService`
- [ ] 自动保存逻辑
- [ ] 项目导入/导出

#### Step 5: Gradio界面 (Day 6-8)
- [ ] 实现主题和CSS
- [ ] 实现头部组件
- [ ] 实现项目列表组件
- [ ] 实现脚本生成Tab
- [ ] 实现可视化编辑组件
- [ ] 事件绑定和状态管理

#### Step 6: 测试和优化 (Day 9-10)
- [ ] 集成测试
- [ ] UI调优
- [ ] 错误处理完善
- [ ] 文档编写

---

## Phase 2: 图片生成模块 (待Phase 1完成后规划)

- 即梦API集成
- 角色参考图生成
- 分镜图片生成
- 图片选择和管理

## Phase 3: 视频合成模块 (待Phase 2完成后规划)

- Edge-TTS集成
- 多角色声音配置
- 即梦图生视频
- 字幕生成(SRT)
- 视频导出
