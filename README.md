# 音频人工评估实验平台

## 项目介绍

音频人工评估实验平台是一个用于AI音频生成模型质量评估的在线Web应用。平台支持通过配置文件快速部署评估实验，允许被试（测试人员）在线完成音频质量打分，并为管理者提供数据收集与分析工具。

### 核心特性

- **快速实验部署**：通过编写 `manifest.jsonl` 和 `metric_defination.json` 文件，即可定义和上线一套新的评估实验
- **简洁的实验流程**：被试通过简单的验证码即可参与实验，无需复杂的注册登录流程
- **多样化题型支持**：支持多种音频任务评估（TTS、SVS、TTM、SR、SE、VTA等）
- **多系统打分**：支持对每个样本的多个系统进行评分，自动计算各系统的最终分数统计
- **无数据库设计**：所有实验数据和被试进度都以文件形式存储在服务器上，简化了部署和维护
- **内置数据分析**：提供管理后台，用于查看实验进度和分析基本的统计数据（均值、标准差、分数分布等）
- **音频可视化**：支持音频Mel频谱图显示
- **视频支持**：支持视频播放用于视音频同步评估
- **实验文件管理**：支持将音频文件直接放在实验目录中，便于实验管理

### 技术栈

- **后端**：Flask 2.3.3
- **数据处理**：Pandas 2.1.1
- **数据可视化**：Matplotlib 3.7.2, Seaborn 0.12.2
- **音频处理**：Librosa 0.10.1, SoundFile 0.12.1
- **前端**：原生JavaScript + Bootstrap

## 项目结构

```
uniaudio/
├── app/                                # 应用核心代码目录
│   ├── __init__.py                     # 应用工厂函数，初始化Flask App
│   ├── main/                           # 核心实验流程蓝图
│   │   ├── __init__.py                 # 蓝图定义
│   │   ├── routes.py                   # 实验相关路由
│   │   ├── utils.py                    # 实验相关辅助函数
│   │   ├── audio_utils.py              # 音频处理工具
│   │   └── video_utils.py              # 视频处理工具
│   ├── admin/                          # 管理后台蓝图
│   │   ├── __init__.py                 # 蓝图定义
│   │   ├── routes.py                   # 管理后台路由
│   │   ├── analysis_tools.py           # 数据分析核心逻辑
│   │   └── chart_cache.py              # 图表缓存管理
│   ├── static/                         # 静态文件
│   │   ├── css/                        # 样式文件
│   │   ├── js/                         # JavaScript脚本
│   │   ├── audio/                      # 音频文件
│   │   ├── video/                      # 视频文件
│   │   └── cache/                      # 运行时缓存（已在 .gitignore 中）
│   │       ├── mel/                    # Mel频谱图缓存
│   │       ├── charts/                 # 图表缓存
│   │       └── videos/                 # 合成视频缓存（VTA任务）
│   └── templates/                      # Jinja2模板文件
│       ├── main/                       # 实验流程页面
│       └── admin/                      # 管理后台页面
├── experiments/                        # 实验配置文件和数据目录（已在 .gitignore 中）
│   └── tts_experiment_1/               # 实验示例
│       ├── manifest.jsonl              # 题库文件
│       ├── metric_defination.json      # 指标定义文件
│       ├── task_defination.json        # 任务定义文件
│       ├── audio/                      # 实验音频文件（可选）
│       └── results/                    # 存储该实验的被试数据
├── config.py                          # 配置文件
├── run.py                             # 项目启动脚本
├── requirements.txt                   # Python依赖列表
└── README.md                          # 项目说明文档
```

## 快速开始

### 1. 环境准备

```bash
# 克隆或下载项目代码
git clone <repository-url>
cd star_mos

# 安装Python依赖
pip install -r requirements.txt

# 安装ffmpeg（用于VTA任务的视频处理）
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt-get install ffmpeg
# Windows: 从 https://ffmpeg.org/download.html 下载
```

### 2. 配置文件设置

推荐使用 `.env` 文件管理敏感配置（`.env` 已在 `.gitignore` 中，不会被提交）：

```bash
# 复制示例配置
cp .env.example .env
# 编辑 .env 填入实际值
```

或直接修改 `config.py`：

```python
class Config:
    SECRET_KEY = 'your-secret-key-change-in-production'  # 修改为安全的随机密钥
  
    # 实验验证码配置
    EXPERIMENT_CODES = {
        'your_experiment_name': 'your_verification_code'
    }
  
    # 管理员验证码
    ADMIN_VERIFICATION_CODE = 'your_admin_code'
```

### 3. 启动应用

```bash
python run.py
```

应用将在 `http://localhost:5000` 启动。

## 实验配置

### 1. 创建实验目录

在 `experiments/` 目录下创建新的实验目录：

```bash
mkdir experiments/my_experiment
```

### 2. 配置文件说明

#### `manifest.jsonl` - 题库文件

每行一个JSON对象，定义一道题目：

```json
{
  "sample_id": "sample_001",
  "task_type": "tts",
  "metrics": ["MOS", "SMOS"],
  "systems": [
    {
      "system_id": "system_A",
      "system_name": "系统A",
      "audio_path": "audio/system_a_output.wav"
    },
    {
      "system_id": "system_B", 
      "system_name": "系统B",
      "audio_path": "audio/system_b_output.wav"
    }
  ],
  "gt_audio_path": "audio/reference.wav",
  "prompt": "Hello, this is a sample text for text-to-speech evaluation.",
  "show_gt_audio": true,
  "show_prompt": true,
  "show_gt_audio_mel": false,
  "show_prompt_mel": false
}
```

**字段说明**：
- `sample_id`: 样本唯一标识
- `task_type`: 任务类型（tts, svs, ttm, sr, se, vta）
- `metrics`: 评估指标列表
- `systems`: 系统列表，每个系统包含：
  - `system_id`: 系统唯一标识（用于数据存储）
  - `system_name`: 系统显示名称（用户看到的名称）
  - `audio_path`: 系统生成的音频文件路径
- `gt_audio_path`: 参考音频路径（可选）
- `prompt`: 提示内容（文本或音频/视频路径）
- `show_*`: 控制界面显示选项

#### `metric_defination.json` - 指标定义文件

定义评估指标的详细说明：

```json
{
  "MOS": {
    "题目描述": "平均主观意见分 - 请评估音频的整体质量",
    "评分范围": [1, 5],
    "评分示例": {
      "1": "质量很差，无法理解",
      "2": "质量较差，理解困难",
      "3": "质量一般，基本可理解",
      "4": "质量良好，清晰可理解",
      "5": "质量优秀，自然流畅"
    }
  },
  "SMOS": {
    "题目描述": "说话人一致性评分 - 请评估音频与说话人声音的相似度",
    "评分范围": [1, 5],
    "评分示例": {
      "1": "完全不像目标说话人",
      "2": "不太像目标说话人",
      "3": "一般相似",
      "4": "比较像目标说话人",
      "5": "非常像目标说话人"
    }
  }
}
```

#### `task_defination.json` - 任务定义文件

定义任务类型的描述：

```json
{
  "tts": {
    "description": "Text-to-Speech: 将输入的文本转换为自然流畅的人类语音。"
  },
  "svs": {
    "description": "Singing Voice Synthesis: 根据歌词和旋律生成歌唱声音。"
  }
}
```

### 3. 音频文件管理

#### 方式一：使用实验目录（推荐）

将音频文件直接放在实验目录中：

```
experiments/my_experiment/
├── manifest.jsonl
├── metric_defination.json
├── task_defination.json
├── audio/
│   ├── system_a_output.wav
│   ├── system_b_output.wav
│   └── reference.wav
└── results/
```

在manifest中使用相对路径：

```json
"audio_path": "audio/system_a_output.wav"
```

#### 方式二：使用静态目录

将音频文件放在 `app/static/audio/` 目录中，在manifest中使用绝对路径：

```json
"audio_path": "/static/audio/samples/system_a_output.wav"
```

## 使用方法

### 被试使用方法

1. **访问欢迎页面**
   - 打开浏览器访问系统地址
   - 选择要参与的实验

2. **输入验证码**
   - 输入实验管理员提供的验证码
   - 系统验证通过后自动生成唯一用户ID

3. **完成评估任务**
   - 系统会逐一展示评估题目
   - 每个题目可能包含：
     - 生成音频（必听）
     - 参考音频（对比用）
     - 文本提示
     - Mel频谱图
     - 视频内容（VTA任务）

4. **提交评分**
   - 根据题目要求对不同指标进行评分（通常1-5分）
   - 点击"下一题"提交当前评分并进入下一题
   - 可以点击"上一题"返回修改之前的答案
   - 完成所有题目后自动跳转到感谢页面

### 管理员使用方法

1. **访问管理后台**
   - 访问 `/admin/login`
   - 输入管理员验证码

2. **查看实验进度**
   - 在实验列表中查看各实验的完成情况
   - 查看已完成用户数量和基本统计信息

3. **数据分析**
   - 点击实验查看详细分析结果
   - 查看各系统的分数统计和分布
   - 导出数据用于进一步分析

## 数据存储说明

### 实验结果存储

- **用户响应数据**：`experiments/{experiment_name}/results/user_{user_id}.jsonl`
- **已完成用户记录**：`experiments/{experiment_name}/results/completed_users.log`
- **系统分数统计**：`experiments/{experiment_name}/results/system_scores.json`

### 缓存文件

所有缓存文件统一存储在 `app/static/cache/` 目录下：

- **Mel频谱图缓存**：`app/static/cache/mel/`
- **图表缓存**：`app/static/cache/charts/`
- **合成视频缓存**：`app/static/cache/videos/`（VTA任务专用）

## 功能特性详解

### 多系统打分功能

- **系统随机化**：用户看到"系统1、系统2..."，但实际对应的模型顺序随机化，避免顺序偏差
- **滑动条打分**：提供更直观的评分体验，实时显示当前选择的分数
- **导航功能**：支持返回上一题修改答案，进度自动保存
- **键盘快捷键**：Ctrl+Enter提交，Ctrl+←返回上一题

### 音频文件路由

- **实验目录支持**：可以直接在实验目录中组织音频文件
- **路径自动处理**：系统自动处理相对路径和绝对路径
- **安全检查**：防止目录遍历攻击，确保文件访问安全

### 数据完整性

- **统一保存**：所有答案在实验完成后统一保存，确保数据完整性
- **Session管理**：用户会话期间答案状态保持一致
- **错误处理**：完善的错误处理和日志记录

## 部署说明

### 生产环境部署

1. **修改配置**
   - 更新 `config.py` 中的密钥和验证码
   - 设置适当的文件权限

2. **使用生产服务器**
   ```bash
   # 使用gunicorn
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 run:app
   
   # 或使用uwsgi
   pip install uwsgi
   uwsgi --http :5000 --module run:app
   ```

3. **反向代理**
   - 使用Nginx作为反向代理
   - 配置SSL证书

### 数据备份

- 定期备份 `experiments/` 目录
- 备份 `app/static/cache/` 目录（可选）

## 故障排除

### 常见问题

1. **音频文件无法播放**
   - 检查文件路径是否正确
   - 确认文件格式支持（WAV, MP3, FLAC）
   - 检查文件权限

2. **Mel频谱图生成失败**
   - 确认librosa库安装正确
   - 检查音频文件是否损坏
   - 查看应用日志

3. **实验无法访问**
   - 检查实验目录结构是否正确
   - 确认manifest.jsonl格式正确
   - 验证实验验证码配置

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。

## 许可证

本项目采用MIT许可证。
