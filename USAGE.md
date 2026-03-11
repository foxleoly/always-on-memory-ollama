# Always-On Memory Agent - 使用指南

## 📋 目录

1. [快速开始](#快速开始)
2. [配置 Copilot 模型](#配置-copilot-模型)
3. [配置 Ollama 模型](#配置-ollama-模型)
4. [API 使用示例](#api-使用示例)
5. [文件监控](#文件监控)
6. [常见问题](#常见问题)

---

## 🚀 快速开始

### 步骤 1：克隆项目

```bash
cd ~/workspace/project
git clone https://github.com/foxleoly/always-on-memory-ollama.git
cd always-on-memory-ollama
```

### 步骤 2：安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤 3：选择模型提供者

**选项 A：使用 GitHub Copilot（推荐，有订阅）**
- 需要 GitHub Copilot 订阅
- 支持 GPT-4o, Claude, Gemini 等模型
- 速度快，质量高

**选项 B：使用 Ollama（免费，本地）**
- 无需订阅
- 本地运行，隐私好
- 速度较慢，需要内存

---

## 🔧 配置 Copilot 模型

### 前提条件

1. **GitHub Copilot 订阅**
   - 访问 https://github.com/settings/copilot
   - 确保订阅有效

2. **GitHub CLI 认证**
   ```bash
   # 安装 gh CLI（如果还没有）
   brew install gh
   
   # 登录 GitHub
   gh auth login
   # 选择：GitHub.com → HTTPS → Login with browser
   # 复制设备代码，浏览器打开 https://github.com/login/device
   # 输入代码，授权完成
   ```

3. **验证认证**
   ```bash
   gh auth status
   # 应该显示：✓ Logged in to github.com account foxleoly
   ```

### 启动 Agent

```bash
cd ~/workspace/project/always-on-memory-ollama
source venv/bin/activate

# 设置环境变量
export PROVIDER=copilot
export MODEL=gpt-4o  # 可选：gpt-4o, claude-3.7-sonnet, gemini-2.5-pro 等

# 启动 Agent
python agent.py --port 8888 --consolidate-every 30
```

### 支持的 Copilot 模型

| 模型名称 | 环境变量值 | 提供商 | 特点 |
|---------|-----------|--------|------|
| GPT-4o | `gpt-4o` | OpenAI | 默认，平衡速度与质量 |
| GPT-4o Mini | `gpt-4o-mini` | OpenAI | 快速，低成本 |
| GPT-4.1 | `gpt-4.1` | OpenAI | 最新 GPT-4 |
| Claude 3.5 Sonnet | `claude-3.5-sonnet` | Anthropic | 代码能力强 |
| Claude 3.7 Sonnet | `claude-3.7-sonnet` | Anthropic | 最新 Claude |
| Claude Sonnet 4 | `claude-sonnet-4` | Anthropic | Claude 4 |
| O1 | `o1` | OpenAI | 推理模型 |
| O3 Mini | `o3-mini` | OpenAI | 快速推理 |
| Gemini 2.0 Flash | `gemini-2.0-flash` | Google | Gemini 系列 |
| Gemini 2.5 Pro | `gemini-2.5-pro` | Google | 最强 Gemini |

---

## 🦙 配置 Ollama 模型

### 前提条件

1. **安装 Ollama**
   ```bash
   # macOS
   brew install ollama
   
   # 启动服务
   ollama serve
   ```

2. **拉取模型**
   ```bash
   # 推荐模型（5GB RAM）
   ollama pull qwen3:8b
   
   # 或更大模型（8GB RAM）
   ollama pull qwen3.5:9b-q4_K_M
   ```

### 启动 Agent

```bash
cd ~/workspace/project/always-on-memory-ollama
source venv/bin/activate

# 设置环境变量
export PROVIDER=ollama
export MODEL=qwen3:8b  # 或 qwen3.5:9b-q4_K_M

# 启动 Agent
python agent.py --port 8888 --consolidate-every 30
```

---

## 🌐 API 使用示例

### 1. 录入记忆

```bash
# 简单录入
curl -X POST http://localhost:8888/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "text": "OpenClaw 是一个 AI 代理框架，支持多模型后端",
    "source": "工作笔记"
  }'

# 响应示例
{
  "status": "ingested",
  "response": {
    "memory_id": 1,
    "status": "stored",
    "summary": "OpenClaw 是一个 AI 代理框架"
  }
}
```

### 2. 查询记忆

```bash
# 查询问题
curl "http://localhost:8888/query?q=OpenClaw 是什么"

# 响应示例
{
  "question": "OpenClaw 是什么",
  "answer": "OpenClaw 是一个 AI 代理框架，支持多模型后端（Ollama、Bailian 等）[记忆 1]..."
}
```

### 3. 查看状态

```bash
curl http://localhost:8888/status

# 响应示例
{
  "total_memories": 10,
  "unconsolidated": 5,
  "consolidations": 2
}
```

### 4. 列出所有记忆

```bash
curl http://localhost:8888/memories

# 响应示例
{
  "memories": [
    {
      "id": 1,
      "summary": "OpenClaw 是一个 AI 代理框架",
      "entities": ["OpenClaw", "AI", "框架"],
      "topics": ["技术", "AI"],
      "importance": 0.8,
      "created_at": "2026-03-11T10:00:00Z"
    }
  ],
  "count": 10
}
```

### 5. 手动触发整合

```bash
curl -X POST http://localhost:8888/consolidate

# 响应示例
{
  "status": "done",
  "response": {
    "status": "consolidated",
    "memories_processed": 5,
    "insight": "OpenClaw 项目包含多个子模块..."
  }
}
```

### 6. 删除记忆

```bash
curl -X POST http://localhost:8888/delete \
  -H "Content-Type: application/json" \
  -d '{"memory_id": 1}'
```

### 7. 清空所有记忆

```bash
curl -X POST http://localhost:8888/clear
```

---

## 📁 文件监控

### 自动录入文件

将文本文件放入 `inbox/` 目录，Agent 会自动读取并录入：

```bash
# 创建笔记
echo "今天完成了用户登录功能的开发" > inbox/notes.md

# 复制会议纪要
cp ~/Downloads/meeting-notes.txt inbox/

# 复制数据文件
cp data.json inbox/
```

### 支持的文件类型

- `.txt` - 纯文本
- `.md` - Markdown
- `.json` - JSON
- `.csv` - CSV
- `.log` - 日志文件
- `.xml` - XML
- `.yaml` / `.yml` - YAML
- `.py` - Python 代码
- `.js` / `.ts` - JavaScript/TypeScript

### 监控频率

- 每 5 秒检查一次新文件
- 已处理文件会被记录，不会重复处理
- 单个文件最大 10KB

---

## ⚙️ 高级配置

### 环境变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `PROVIDER` | 模型提供者 | `ollama` | `copilot`, `ollama` |
| `MODEL` | 模型名称 | `qwen3:8b` | `gpt-4o`, `claude-3.7-sonnet` |
| `MEMORY_DB` | 数据库路径 | `memory.db` | `/path/to/memory.db` |
| `OLLAMA_HOST` | Ollama 地址 | `http://localhost:11434` | - |
| `GITHUB_TOKEN` | GitHub Token（Copilot） | 自动获取 | `ghp_xxx` |

### 命令行参数

```bash
python agent.py \
  --watch ./inbox \          # 监控目录
  --port 8888 \              # HTTP 端口
  --consolidate-every 30     # 整合间隔（分钟）
```

### 配置文件（可选）

创建 `~/.always-on-memory.json`：

```json
{
  "provider": "copilot",
  "model": "gpt-4o",
  "copilot": {
    "apiKey": ""  // 留空自动从 gh CLI 加载
  },
  "consolidate_every": 30,
  "port": 8888
}
```

---

## 🔍 常见问题

### Q1: Copilot Token 加载失败

**错误信息：** `GitHub token not found`

**解决方案：**
```bash
# 1. 确保已登录 GitHub
gh auth status

# 2. 如果没有登录，执行
gh auth login

# 3. 或手动设置 Token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### Q2: Token 交换失败

**错误信息：** `Token exchange failed with status 401`

**解决方案：**
1. 确认有 GitHub Copilot 订阅
2. 访问 https://github.com/settings/copilot 检查订阅状态
3. 重新登录：`gh auth logout && gh auth login`

### Q3: Ollama 响应太慢

**解决方案：**
1. 使用更小的模型：`ollama pull qwen3:8b`
2. 确保 Ollama 服务在运行：`ollama serve`
3. 检查内存使用：`ps aux | grep ollama`

### Q4: 记忆整合失败

**错误信息：** `Consolidate parse error`

**解决方案：**
1. 检查 Ollama/Copilot 服务是否正常
2. 查看日志输出
3. 尝试手动触发整合：`curl -X POST http://localhost:8888/consolidate`

### Q5: 端口被占用

**错误信息：** `Address already in use`

**解决方案：**
```bash
# 查找占用端口的进程
lsof -ti:8888 | xargs kill -9

# 或使用其他端口
python agent.py --port 8889
```

---

## 📚 参考资料

1. **GitHub 仓库** - https://github.com/foxleoly/always-on-memory-ollama
2. **Google 原项目** - https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent
3. **Ollama** - https://ollama.ai
4. **GitHub Copilot** - https://github.com/features/copilot

---

*Last Updated: 2026-03-11*
