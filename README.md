# PAVUI - AI视频创作平台

一个开源的AI视频创作工具，通过可视化界面串联多个AI服务，实现：
**文字 → 脚本/分镜 → 图片生成 → 视频合成** 的完整工作流。

## 当前版本：Phase 1 - 脚本生成模块

### 已实现功能

- **DeepSeek LLM集成**：支持DeepSeek API进行脚本生成
- **三阶段脚本生成**：
  1. 故事大纲生成（可跳过）
  2. 角色和场景提取
  3. 分镜脚本生成
- **可视化编辑**：角色、场景、分镜的可视化查看
- **项目管理**：自动保存项目到本地目录
- **中英文Prompt翻译**：自动将中文描述翻译为英文（用于图片生成）
- **智能重试**：根据错误类型智能处理API调用失败
- **多语言界面**：支持中文和英文

### 待实现功能（后续阶段）

- **Phase 2**：即梦图片生成、角色参考图、分镜图片
- **Phase 3**：Edge-TTS语音、即梦图生视频、字幕

## 快速开始

### 1. 安装依赖

```bash
cd pavui
pip install -r requirements.txt
```

### 2. 配置API密钥

方式一：环境变量
```bash
export DEEPSEEK_API_KEY=your-api-key
```

方式二：创建 `.env` 文件
```
DEEPSEEK_API_KEY=your-api-key
```

方式三：编辑 `config/settings.yaml`

### 3. 运行应用

```bash
python app.py
```

访问 http://localhost:7860

## 项目结构

```
pavui/
├── app.py                      # 主入口
├── requirements.txt
├── config/
│   └── settings.yaml           # 配置文件
├── locales/                    # 多语言
│   ├── zh.json
│   └── en.json
├── src/
│   ├── models/                 # 数据模型
│   │   ├── script.py           # Script, Character, Scene等
│   │   └── project.py          # Project项目管理
│   ├── services/               # 业务逻辑
│   │   ├── llm_service.py      # LLM调用服务
│   │   ├── script_service.py   # 脚本生成（三阶段）
│   │   ├── project_service.py  # 项目管理
│   │   └── translator.py       # 中英翻译
│   ├── adapters/               # API适配器
│   │   ├── base.py             # 基类
│   │   └── deepseek.py         # DeepSeek适配器
│   ├── ui/                     # Gradio界面
│   │   ├── app.py              # 主应用
│   │   ├── theme.py            # 主题样式
│   │   ├── components/         # UI组件
│   │   └── tabs/               # Tab页面
│   └── utils/
│       ├── config.py           # 配置加载
│       ├── i18n.py             # 国际化
│       └── retry.py            # 智能重试
└── tests/
```

## 工作流程

### 脚本生成流程

1. **输入主题**：描述想要创作的视频内容
2. **生成大纲**（可跳过）：AI生成故事大纲
3. **提取元素**：AI提取角色设定和场景设定
4. **生成分镜**：AI生成详细的分镜脚本
5. **翻译Prompt**：自动翻译为英文（用于图片生成）

### 脚本数据结构

```json
{
  "title": "视频标题",
  "summary": "一句话简介",
  "characters": [{
    "id": "char_001",
    "name": "小明",
    "role": "主角",
    "appearance": {
      "gender": "男",
      "age": "25岁",
      "clothing": "蓝色卫衣"
    }
  }],
  "locations": [{
    "id": "loc_001",
    "name": "咖啡厅",
    "time_of_day": "下午"
  }],
  "scenes": [{
    "scene_id": 1,
    "location_id": "loc_001",
    "character_ids": ["char_001"],
    "visual_description": "画面描述",
    "narration": "旁白",
    "image_prompt_zh": "中文prompt",
    "image_prompt_en": "English prompt"
  }]
}
```

## 开发

### 运行测试

```bash
pytest tests/
```

### 项目数据存储

项目默认保存在 `~/pavui_projects/` 目录，每个项目包含：
- `project.json` - 项目元数据
- `script.json` - 脚本数据
- `images/` - 图片文件（Phase 2）
- `audio/` - 音频文件（Phase 3）
- `output/` - 输出视频（Phase 3）

## License

MIT License
