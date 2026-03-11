# Ollama 配置优化

## 内存占用对比

| 模型 | 内存占用 | 推理速度 | 适用场景 |
|------|----------|----------|----------|
| qwen3.5:9b-q4_K_M | ~8 GB | 中等 | 高质量需求 |
| qwen3:8b | ~5 GB | 较快 | 日常使用 ✅ |

## 优化配置

### 1. 使用更小的模型

```bash
# 拉取 qwen3:8b（已存在）
ollama pull qwen3:8b

# 修改 agent.py 中的 MODEL 配置
MODEL = os.getenv("MODEL", "qwen3:8b")  # 从 9b 改为 8b
```

### 2. 配置 Ollama 自动卸载（空闲时释放内存）

```bash
# 设置环境变量（~/.zshrc）
export OLLAMA_KEEP_ALIVE=5m  # 空闲 5 分钟后卸载模型

# 或者临时设置
launchctl setenv OLLAMA_KEEP_ALIVE 5m
```

### 3. 手动控制模型加载

```bash
# 停止 Ollama 服务（释放内存）
ollama serve stop

# 需要时再启动
ollama serve
```

### 4. 使用更低精度的量化版本

```bash
# Q4_K_M (推荐，平衡质量和大小)
ollama pull qwen3:8b

# Q3_K_S (更小，质量略降)
ollama pull qwen3:8b-q3_K_S  # ~4GB

# Q2_K (最小，质量明显下降)
ollama pull qwen3:8b-q2_K  # ~3GB
```

## 推荐配置

**日常使用：**
- 模型：`qwen3:8b`（5GB）
- OLLAMA_KEEP_ALIVE: `5m`
- 内存占用：空闲时 ~100MB，使用时 ~5GB

**高质量需求：**
- 模型：`qwen3.5:9b-q4_K_M`（8GB）
- OLLAMA_KEEP_ALIVE: `1m`
- 内存占用：空闲时 ~100MB，使用时 ~8GB

## 快速切换脚本

```bash
#!/bin/bash
# switch-model.sh

if [ "$1" == "small" ]; then
    echo "切换到 qwen3:8b (5GB)"
    export MODEL="qwen3:8b"
elif [ "$1" == "large" ]; then
    echo "切换到 qwen3.5:9b (8GB)"
    export MODEL="qwen3.5:9b-q4_K_M"
else
    echo "用法：./switch-model.sh [small|large]"
    exit 1
fi

echo "MODEL=$MODEL" > .env
echo "已切换模型：$MODEL"
```

## 监控内存

```bash
# 查看 Ollama 内存占用
ps aux | grep ollama | grep -v grep

# 查看系统内存
memory_pressure

# 实时监测
top -l 1 | grep ollama
```
