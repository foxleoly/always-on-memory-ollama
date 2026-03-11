# Always-On Memory Agent with Ollama

**Ollama version based on Google always-on-memory-agent**

---

## Project Overview

This project is an Ollama-based implementation of Google's always-on-memory-agent. It replaces Google Gemini models with locally running Ollama models (qwen3.8b).

---

## Core Features

### 1. Memory Ingestion (Ingest)
- Automatically parses input text
- Extracts summary, entities, topic tags
- Evaluates importance
- Stores structured data to SQLite database

### 2. Memory Consolidation (Consolidate)
- Periodically scans unconsolidated memories
- Discovers patterns and associations between memories
- Generates comprehensive insights
- Automatically marks consolidated memories

### 3. Memory Query (Query)
- Answers questions based on stored memories
- Intelligent information retrieval
- References memory IDs for traceability

### 4. File Monitoring
- Monitors `inbox/` folder for new text files
- Automatically reads and processes new files
- Supports multiple text formats

### 5. HTTP API
- RESTful interface for complete CRUD operations
- Easy integration with other applications

---

## Technology Stack

- **Programming Language:** Python 3.12+
- **Async Framework:** asyncio
- **HTTP Framework:** aiohttp
- **Database:** SQLite3
- **LLM:** Ollama (via ollama-python)
- **Configuration:** Environment variables

---

## Project Structure

```
always-on-memory-ollama/
├── agent.py              # Main program
├── test_full.py          # Complete test suite
├── test_agent.py         # Quick test script
├── requirements.txt      # Python dependencies
├── README.md             # This documentation
├── CONFIG.md             # Configuration optimization guide
├── inbox/                # File monitoring directory
├── memory.db             # SQLite database (created at runtime)
└── venv/                 # Python virtual environment
```

---

## Quick Start

### Install Dependencies

```bash
cd /Users/foxleoly/workspace/project/always-on-memory-ollama
pip install -r requirements.txt
```

### Install Ollama

```bash
# macOS
brew install ollama

# Pull model
ollama pull qwen3:8b

# Start service
ollama serve
```

### Run Tests

```bash
# Make sure Ollama service is running
curl http://localhost:11434/api/tags

# Run complete test suite
python test_full.py
```

### Start Agent

```bash
source venv/bin/activate
python agent.py --port 8888 --consolidate-every 30
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Memory statistics |
| `/memories` | GET | List all memories |
| `/ingest` | POST | Ingest new memory `{"text": "...", "source": "..."}` |
| `/query?q=...` | GET | Query memories |
| `/consolidate` | POST | Manually trigger consolidation |
| `/delete` | POST | Delete memory `{"memory_id": 1}` |
| `/clear` | POST | Clear all memories |

### Usage Examples

```bash
# Ingest memory
curl -X POST http://localhost:8888/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "OpenClaw is an AI agent framework", "source": "test"}'

# Query
curl "http://localhost:8888/query?q=What is OpenClaw"

# Check status
curl http://localhost:8888/status

# List memories
curl http://localhost:8888/memories
```

---

## File Monitoring

Drop text files into `./inbox/` folder, Agent will automatically read and ingest them:

```bash
# Supported file types
echo "Important info" > inbox/notes.txt
cp meeting-notes.md inbox/
cp data.json inbox/
```

---

## Configuration

Configure via environment variables:

```bash
export MODEL="qwen3:8b"              # Main model
export EMBED_MODEL="nomic-embed-text" # Embedding model
export MEMORY_DB="memory.db"          # Database path
export OLLAMA_HOST="http://localhost:11434"  # Ollama address
```

Command line arguments:

```bash
python agent.py --watch ./inbox --port 8888 --consolidate-every 30
```

---

## Comparison with Original Project

| Feature | Google Original | Ollama Version |
|---------|----------------|----------------|
| Model | Gemini 3.1 Flash-Lite | qwen3.8b (local) |
| Framework | Google ADK | Custom implementation |
| Multi-modal | ✅ Image/Audio/Video | ❌ Text only |
| Cost | Per token | Free |
| Privacy | Data sent to cloud | Local running |

---

## Known Limitations

1. **Ollama Response Latency**
   - First load takes 10-30 seconds
   - Inference speed ~5-15 seconds/request
   - Suggest using faster models (e.g., qwen3:8b-q4_K_M)

2. **Local Running Requires Memory**
   - qwen3.5:9b-q4_K_M needs ~8GB RAM
   - qwen3:8b needs ~5GB RAM
   - Suggest periodic cleanup of unused memories

3. **Async Performance**
   - HTTP server uses async processing
   - But LLM calling is synchronous (ollama-python limitation)
   - May become performance bottleneck

---

## Future Improvements

1. **More Model Support**
   - Add Bailian, OpenAI API support
   - Implement model switching functionality

2. **Performance Optimization**
   - Use async LLM calling
   - Add caching mechanism
   - Implement streaming responses

3. **Feature Enhancements**
   - Add vector search (embedding)
   - Support multi-modal (image, audio, video)

---

## References

1. **Google always-on-memory-agent**  
   https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent

2. **Ollama Python Client**  
   https://github.com/ollama/ollama-python

3. **SQLite Documentation**  
   https://docs.python.org/3/library/sqlite3.html

4. **Ollama**  
   https://ollama.ai

---

*Last Updated: 2026-03-11*
