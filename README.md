# Always-On Memory Agent - Ollama Version

基于 Google 原始项目思路，使用本地 Ollama 模型实现的 always-on 记忆代理。

## 特性

- ✅ **本地运行** - 使用 Ollama + qwen3.5:9b，零 API 成本
- ✅ **持续记忆** - 24/7 后台运行，自动处理新信息
- ✅ **主动整合** - 定期 consolidating，发现记忆间的关联
- ✅ **智能查询** - 基于记忆合成答案，带引用
- ✅ **文件监控** - 自动读取 inbox 文件夹中的文本文件
- ✅ **HTTP API** - RESTful 接口，易于集成
- ✅ **SQLite 存储** - 轻量级持久化

## 快速开始

### 1. 环境要求

```bash
# 安装 Ollama
brew install ollama

# 启动 Ollama 服务
ollama serve

# 拉取模型（如果还没有）
ollama pull qwen3.5:9b-q4_K_M
ollama pull nomic-embed-text
```

### 2. 安装依赖

```bash
cd /Users/foxleoly/workspace/project/always-on-memory-ollama

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 启动 Agent

```bash
source venv/bin/activate
python agent.py
```

### 4. 测试

```bash
# 新终端
source venv/bin/activate
python test_agent.py
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 记忆统计 |
| `/memories` | GET | 列出所有记忆 |
| `/ingest` | POST | 录入新记忆 `{"text": "...", "source": "..."}` |
| `/query?q=...` | GET | 查询记忆 |
| `/consolidate` | POST | 手动触发整合 |
| `/delete` | POST | 删除记忆 `{"memory_id": 1}` |
| `/clear` | POST | 清空所有记忆 |

### 使用示例

```bash
# 录入记忆
curl -X POST http://localhost:8888/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "OpenClaw 是一个 AI 代理框架", "source": "test"}'

# 查询
curl "http://localhost:8888/query?q=OpenClaw 是什么"

# 查看状态
curl http://localhost:8888/status

# 列出记忆
curl http://localhost:8888/memories
```

## 文件监控

将文本文件放入 `./inbox/` 文件夹，Agent 会自动读取并录入：

```bash
# 支持的文件类型
echo "重要信息" > inbox/notes.txt
cp meeting-notes.md inbox/
cp data.json inbox/
```

## 配置

通过环境变量配置：

```bash
export MODEL="qwen3.5:9b"           # 主模型
export EMBED_MODEL="nomic-embed-text"  # 嵌入模型
export MEMORY_DB="memory.db"        # 数据库路径
export OLLAMA_HOST="http://localhost:11434"  # Ollama 地址
```

命令行参数：

```bash
python agent.py --watch ./inbox --port 8888 --consolidate-every 30
```

## 项目结构

```
always-on-memory-ollama/
├── agent.py           # 主程序
├── test_agent.py      # 测试脚本
├── requirements.txt   # Python 依赖
├── venv/              # 虚拟环境
├── inbox/             # 文件监控目录
├── memory.db          # SQLite 数据库（运行时创建）
└── README.md          # 本文档
```

## 与原始项目对比

| 特性 | Google 原版 | Ollama 版本 |
|------|------------|------------|
| 模型 | Gemini 3.1 Flash-Lite | qwen3.5:9b (本地) |
| 框架 | Google ADK | 自定义实现 |
| 多模态 | ✅ 图像/音频/视频 | ❌ 仅文本 |
| 成本 | 按 token 收费 | 免费 |
| 隐私 | 数据出网 | 本地运行 |

## 开发笔记

- 使用 `qwen3.5:9b` 模型，需要约 8GB RAM
- 整合间隔默认 30 分钟，可根据需要调整
- 文件监控每 5 秒轮询一次
- 单个文件最大 10KB（避免过长文本）

## 参考资料

1. **原始项目** - Google always-on-memory-agent  
   https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent

2. **Ollama** - 本地 LLM 运行  
   https://ollama.ai

3. **qwen3.5 模型**  
   https://ollama.ai/library/qwen3.5
