# Photo-Video UI

AI 视频创作工作流平台。输入文本主题或文章，自动生成视频脚本（角色 / 场景 / 分镜），并调用即梦 AI 批量生成参考图片。

## 分支说明

| 分支 | 平台 |
|------|------|
| `main` | Windows |
| `linux` | Linux / WSL |

## 依赖

- Python 3.10+
- DeepSeek API（脚本生成）
- 火山引擎即梦 API（图片生成，需开通 `jimeng_t2i_v40`）

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 并填入 API 密钥：

```bash
cp .env.example .env
```

```ini
DEEPSEEK_API_KEY=your-deepseek-api-key
JIMENG_ACCESS_KEY=your-access-key
JIMENG_SECRET_KEY=your-secret-key
```

## 运行

```bash
python app.py
```

## 功能

- **脚本生成**：输入主题或加载文本文件，由 DeepSeek 生成包含角色、场景、分镜的完整脚本
- **图片生成**：基于脚本内容调用即梦 API 批量生成角色参考图、场景参考图、分镜图
- **视频合成**：规划中

## 注意事项

- 即梦 `jimeng_t2i_v40` 目前仅支持 `1024×1024` 分辨率
- 生成的图片以临时文件形式缓存在本地，关闭程序后自动清理
