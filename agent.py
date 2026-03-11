#!/usr/bin/env python3
"""
Always-On Memory Agent - Ollama/Copilot Version

A lightweight background agent that continuously processes, consolidates, and serves memory.
Runs 24/7 with local Ollama models or GitHub Copilot models.

Usage:
    python agent.py                          # watch ./inbox, serve on :8888
    python agent.py --watch ./docs --port 9000
    python agent.py --consolidate-every 15   # consolidate every 15 min

Query:
    curl "http://localhost:8888/query?q=what+do+you+know"
    curl -X POST http://localhost:8888/ingest -d '{"text": "some info"}'
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import signal
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ollama
from aiohttp import web

from copilot_provider import CopilotProvider

# ─── Config ────────────────────────────────────────────────────

PROVIDER = os.getenv("PROVIDER", "ollama")  # 模型提供者：ollama 或 copilot
MODEL = os.getenv("MODEL", "qwen3:8b")  # 优化：使用 8b 模型，内存占用从 8GB 降到 5GB
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
DB_PATH = os.getenv("MEMORY_DB", "memory.db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Text file extensions
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log", ".xml", ".yaml", ".yml", ".py", ".js", ".ts"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="[%H:%M:%S]",
)
log = logging.getLogger("memory-agent")

# ─── Ollama Client ─────────────────────────────────────────────

class OllamaClient:
    def __init__(self, host=OLLAMA_HOST, model=MODEL):
        self.host = host
        self.model = model
        self.client = ollama.Client(host=host)
    
    def _chat_sync(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        """Synchronous chat request (runs in thread)."""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                options={"temperature": temperature}
            )
            return response["message"]["content"]
        except Exception as e:
            log.error(f"Ollama chat error: {e}")
            return f"Error: {e}"
    
    async def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        """Send a chat request to Ollama (async, non-blocking)."""
        return await asyncio.to_thread(
            self._chat_sync, system_prompt, user_message, temperature
        )
    
    def _generate_json_sync(self, system_prompt: str, user_message: str) -> dict:
        """Synchronous JSON generation (runs in thread)."""
        response_text = self._chat_sync(system_prompt, user_message, temperature=0.1)
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            return {"error": "No JSON found", "raw": response_text}
        except json.JSONDecodeError as e:
            log.error(f"JSON parse error: {e}\nResponse: {response_text[:200]}")
            return {"error": f"JSON parse error: {e}", "raw": response_text}
    
    async def generate_json(self, system_prompt: str, user_message: str) -> dict:
        """Send a request and parse response as JSON (async, non-blocking)."""
        return await asyncio.to_thread(
            self._generate_json_sync, system_prompt, user_message
        )


# ─── Database ──────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL,
            summary TEXT NOT NULL,
            entities TEXT NOT NULL DEFAULT '[]',
            topics TEXT NOT NULL DEFAULT '[]',
            connections TEXT NOT NULL DEFAULT '[]',
            importance REAL NOT NULL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            consolidated INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS consolidations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_ids TEXT NOT NULL,
            summary TEXT NOT NULL,
            insight TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS processed_files (
            path TEXT PRIMARY KEY,
            processed_at TEXT NOT NULL
        );
    """)
    return db


# ─── Tools ─────────────────────────────────────────────────────

def store_memory(
    raw_text: str,
    summary: str,
    entities: list,
    topics: list,
    importance: float,
    source: str = "",
) -> dict:
    """Store a processed memory in the database."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        """INSERT INTO memories (source, raw_text, summary, entities, topics, importance, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (source, raw_text, summary, json.dumps(entities), json.dumps(topics), importance, now),
    )
    db.commit()
    mid = cursor.lastrowid
    db.close()
    log.info(f"📥 Stored memory #{mid}: {summary[:60]}...")
    return {"memory_id": mid, "status": "stored", "summary": summary}


def read_all_memories() -> dict:
    """Read all stored memories from the database, most recent first."""
    db = get_db()
    rows = db.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT 50").fetchall()
    memories = []
    for r in rows:
        memories.append({
            "id": r["id"], "source": r["source"], "summary": r["summary"],
            "entities": json.loads(r["entities"]), "topics": json.loads(r["topics"]),
            "importance": r["importance"], "connections": json.loads(r["connections"]),
            "created_at": r["created_at"], "consolidated": bool(r["consolidated"]),
        })
    db.close()
    return {"memories": memories, "count": len(memories)}


def read_unconsolidated_memories() -> dict:
    """Read memories that haven't been consolidated yet."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM memories WHERE consolidated = 0 ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    memories = []
    for r in rows:
        memories.append({
            "id": r["id"], "summary": r["summary"],
            "entities": json.loads(r["entities"]), "topics": json.loads(r["topics"]),
            "importance": r["importance"], "created_at": r["created_at"],
        })
    db.close()
    return {"memories": memories, "count": len(memories)}


def store_consolidation(
    source_ids: list,
    summary: str,
    insight: str,
    connections: list,
) -> dict:
    """Store a consolidation result and mark source memories as consolidated."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO consolidations (source_ids, summary, insight, created_at) VALUES (?, ?, ?, ?)",
        (json.dumps(source_ids), summary, insight, now),
    )
    for conn in connections:
        from_id, to_id = conn.get("from_id"), conn.get("to_id")
        rel = conn.get("relationship", "")
        if from_id and to_id:
            for mid in [from_id, to_id]:
                row = db.execute("SELECT connections FROM memories WHERE id = ?", (mid,)).fetchone()
                if row:
                    existing = json.loads(row["connections"])
                    existing.append({"linked_to": to_id if mid == from_id else from_id, "relationship": rel})
                    db.execute("UPDATE memories SET connections = ? WHERE id = ?", (json.dumps(existing), mid))
    placeholders = ",".join("?" * len(source_ids))
    db.execute(f"UPDATE memories SET consolidated = 1 WHERE id IN ({placeholders})", source_ids)
    db.commit()
    db.close()
    log.info(f"🔄 Consolidated {len(source_ids)} memories. Insight: {insight[:80]}...")
    return {"status": "consolidated", "memories_processed": len(source_ids), "insight": insight}


def read_consolidation_history() -> dict:
    """Read past consolidation insights."""
    db = get_db()
    rows = db.execute("SELECT * FROM consolidations ORDER BY created_at DESC LIMIT 10").fetchall()
    result = [{"summary": r["summary"], "insight": r["insight"], "source_ids": r["source_ids"]} for r in rows]
    db.close()
    return {"consolidations": result, "count": len(result)}


def get_memory_stats() -> dict:
    """Get current memory statistics."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) as c FROM memories").fetchone()["c"]
    unconsolidated = db.execute("SELECT COUNT(*) as c FROM memories WHERE consolidated = 0").fetchone()["c"]
    consolidations = db.execute("SELECT COUNT(*) as c FROM consolidations").fetchone()["c"]
    db.close()
    return {
        "total_memories": total,
        "unconsolidated": unconsolidated,
        "consolidations": consolidations,
    }


def delete_memory(memory_id: int) -> dict:
    """Delete a memory by ID."""
    db = get_db()
    row = db.execute("SELECT 1 FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if not row:
        db.close()
        return {"status": "not_found", "memory_id": memory_id}
    db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    db.commit()
    db.close()
    log.info(f"🗑️  Deleted memory #{memory_id}")
    return {"status": "deleted", "memory_id": memory_id}


def clear_all_memories(inbox_path: str = None) -> dict:
    """Delete all memories, consolidations, and inbox files. Full reset."""
    db = get_db()
    mem_count = db.execute("SELECT COUNT(*) as c FROM memories").fetchone()["c"]
    db.execute("DELETE FROM memories")
    db.execute("DELETE FROM consolidations")
    db.execute("DELETE FROM processed_files")
    db.commit()
    db.close()

    files_deleted = 0
    if inbox_path:
        folder = Path(inbox_path)
        if folder.is_dir():
            for f in folder.iterdir():
                if f.name.startswith("."):
                    continue
                try:
                    if f.is_file():
                        f.unlink()
                        files_deleted += 1
                    elif f.is_dir():
                        shutil.rmtree(f)
                        files_deleted += 1
                except OSError as e:
                    log.error(f"Failed to delete {f.name}: {e}")

    log.info(f"🗑️  Cleared all {mem_count} memories, deleted {files_deleted} inbox files")
    return {"status": "cleared", "memories_deleted": mem_count, "files_deleted": files_deleted}


# ─── Agent Prompts ─────────────────────────────────────────────

INGEST_PROMPT = """
你是一个记忆录入专家。你的任务是将用户提供的信息转化为结构化记忆。

处理步骤：
1. 仔细阅读输入内容
2. 生成 1-2 句简洁摘要（中文）
3. 提取 3-8 个关键实体（人名、公司、产品、概念等）
4. 分配 2-4 个主题标签
5. 评估重要性（0.0-1.0）

输出格式（严格 JSON，不要其他内容）：
{
    "summary": "摘要内容",
    "entities": ["实体 1", "实体 2"],
    "topics": ["主题 1", "主题 2"],
    "importance": 0.8
}
"""

def build_consolidate_prompt(memories_list: str) -> str:
    """Build consolidate prompt with memories."""
    return f"""
你是一个记忆整合专家。你有以下未整合的记忆：

【未整合的记忆列表】
{memories_list}

任务：
1. 找出这些记忆之间的关联和模式
2. 生成一个综合摘要（2-3 句，中文）
3. 提炼一个核心洞察（1 句，中文）
4. 列出记忆间的连接关系

输出格式（严格 JSON，不要其他内容）：
{{
    "summary": "综合摘要",
    "insight": "核心洞察",
    "connections": [
        {{"from_id": 1, "to_id": 2, "relationship": "因果关系"}},
        {{"from_id": 2, "to_id": 3, "relationship": "相关"}}
    ]
}}
"""

def build_query_prompt(memories_list: str, consolidations_list: str, question: str) -> str:
    """Build query prompt with memories and question."""
    return f"""
你是一个记忆查询专家。基于以下记忆回答问题。

【所有记忆】
{memories_list}

【整合洞察】
{consolidations_list}

【问题】
{question}

要求：
1. 只基于提供的记忆回答
2. 引用记忆 ID，如 [记忆 1], [记忆 2]
3. 如果没有相关信息，诚实说明
4. 回答要简洁有条理（中文）
"""


# ─── Memory Agent ──────────────────────────────────────────────

class MemoryAgent:
    def __init__(self, model=MODEL, provider=PROVIDER):
        self.model = model
        self.provider = provider
        
        # 根据 PROVIDER 选择客户端
        if provider.lower() == "copilot":
            copilot_api_url = os.getenv("COPILOT_API_URL", "https://api.githubcopilot.com")
            log.info(f"🚀 Using GitHub Copilot provider with model: {model}, API URL: {copilot_api_url}")
            self.client = CopilotProvider(model=model, api_url=copilot_api_url)
        else:
            log.info(f"🦙 Using Ollama provider with model: {model}")
            self.client = OllamaClient(host=OLLAMA_HOST, model=model)
    
    async def ingest(self, text: str, source: str = "") -> dict:
        """Ingest new text and store as memory."""
        user_message = f"来源：{source}\n\n内容：\n{text}" if source else f"内容：\n{text}"
        
        result = await self.client.generate_json(INGEST_PROMPT, user_message)
        
        if "error" in result:
            log.error(f"Ingest parse error: {result}")
            # Fallback: store raw
            return store_memory(
                raw_text=text,
                summary=text[:200],
                entities=[],
                topics=["general"],
                importance=0.5,
                source=source
            )
        
        return store_memory(
            raw_text=text,
            summary=result.get("summary", text[:200]),
            entities=result.get("entities", []),
            topics=result.get("topics", []),
            importance=result.get("importance", 0.5),
            source=source
        )
    
    async def consolidate(self) -> dict:
        """Consolidate unconsolidated memories."""
        unconsolidated = read_unconsolidated_memories()
        
        if unconsolidated["count"] < 2:
            return {"status": "skipped", "reason": f"Only {unconsolidated['count']} unconsolidated memories"}
        
        # Convert memories to readable format
        memories_list = "\n".join([
            f"记忆 #{m['id']}: {m['summary']}\n  实体: {', '.join(m['entities'])}\n  主题: {', '.join(m['topics'])}\n  重要性: {m['importance']}"
            for m in unconsolidated["memories"]
        ])
        
        prompt = build_consolidate_prompt(memories_list)
        result = await self.client.generate_json(
            "你是一个 JSON 格式化的助手。只输出 JSON，不要其他内容。",
            prompt
        )
        
        if "error" in result:
            log.error(f"Consolidate parse error: {result}")
            return {"status": "error", "reason": result["error"]}
        
        source_ids = [m["id"] for m in unconsolidated["memories"]]
        return store_consolidation(
            source_ids=source_ids,
            summary=result.get("summary", ""),
            insight=result.get("insight", ""),
            connections=result.get("connections", [])
        )
    
    async def query(self, question: str) -> str:
        """Answer a question based on memories."""
        all_memories = read_all_memories()
        consolidations = read_consolidation_history()
        
        memories_list = "\n".join([
            f"记忆 #{m['id']}: {m['summary']}"
            for m in all_memories["memories"]
        ])
        
        consolidations_list = "\n".join([
            f"洞察 {i+1}: {c['insight']}"
            for i, c in enumerate(consolidations["consolidations"])
        ])
        
        prompt = build_query_prompt(memories_list, consolidations_list, question)
        response = await self.client.chat(
            "",
            prompt
        )
        return response
    
    async def status(self) -> dict:
        """Get memory system status."""
        return get_memory_stats()


# ─── File Watcher ──────────────────────────────────────────────

async def watch_folder(agent: MemoryAgent, folder: Path, poll_interval: int = 5):
    """Watch a folder for new text files and ingest them."""
    folder.mkdir(parents=True, exist_ok=True)
    db = get_db()
    log.info(f"👁️  Watching: {folder}/  (text files only)")

    while True:
        try:
            for f in sorted(folder.iterdir()):
                if f.name.startswith("."):
                    continue
                suffix = f.suffix.lower()
                if suffix not in TEXT_EXTENSIONS:
                    continue
                row = db.execute("SELECT 1 FROM processed_files WHERE path = ?", (str(f),)).fetchone()
                if row:
                    continue

                try:
                    log.info(f"📄 New text file: {f.name}")
                    text = f.read_text(encoding="utf-8", errors="replace")[:10000]
                    if text.strip():
                        await agent.ingest(text, source=f.name)
                except Exception as file_err:
                    log.error(f"Error ingesting {f.name}: {file_err}")

                db.execute(
                    "INSERT INTO processed_files (path, processed_at) VALUES (?, ?)",
                    (str(f), datetime.now(timezone.utc).isoformat()),
                )
                db.commit()
        except Exception as e:
            log.error(f"Watch error: {e}")

        await asyncio.sleep(poll_interval)


# ─── Consolidation Timer ──────────────────────────────────────

async def consolidation_loop(agent: MemoryAgent, interval_minutes: int = 30):
    """Run consolidation periodically, like sleep cycles."""
    log.info(f"🔄 Consolidation: every {interval_minutes} minutes")
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            db = get_db()
            count = db.execute("SELECT COUNT(*) as c FROM memories WHERE consolidated = 0").fetchone()["c"]
            db.close()
            if count >= 2:
                log.info(f"🔄 Running consolidation ({count} unconsolidated memories)...")
                result = await agent.consolidate()
                log.info(f"🔄 {result}")
            else:
                log.info(f"🔄 Skipping consolidation ({count} unconsolidated memories)")
        except Exception as e:
            log.error(f"Consolidation error: {e}")


# ─── HTTP API ──────────────────────────────────────────────────

def build_http(agent: MemoryAgent, watch_path: str = "./inbox"):
    app = web.Application()

    async def handle_query(request: web.Request):
        q = request.query.get("q", "").strip()
        if not q:
            return web.json_response({"error": "missing ?q= parameter"}, status=400)
        answer = await agent.query(q)
        return web.json_response({"question": q, "answer": answer})

    async def handle_ingest(request: web.Request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid JSON"}, status=400)
        text = data.get("text", "").strip()
        if not text:
            return web.json_response({"error": "missing 'text' field"}, status=400)
        source = data.get("source", "api")
        result = await agent.ingest(text, source=source)
        return web.json_response({"status": "ingested", "response": result})

    async def handle_consolidate(request: web.Request):
        try:
            result = await agent.consolidate()
            return web.json_response({"status": "success", "response": result})
        except Exception as e:
            log.error(f"Consolidate error: {e}")
            return web.json_response({"status": "error", "error": str(e)}, status=500)

    async def handle_status(request: web.Request):
        stats = await agent.status()
        return web.json_response(stats)

    async def handle_memories(request: web.Request):
        data = read_all_memories()
        return web.json_response(data)

    async def handle_delete(request: web.Request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid JSON"}, status=400)
        memory_id = data.get("memory_id")
        if not memory_id:
            return web.json_response({"error": "missing 'memory_id' field"}, status=400)
        result = delete_memory(int(memory_id))
        return web.json_response(result)

    async def handle_clear(request: web.Request):
        result = clear_all_memories(inbox_path=watch_path)
        return web.json_response(result)

    app.router.add_get("/query", handle_query)
    app.router.add_post("/ingest", handle_ingest)
    app.router.add_post("/consolidate", handle_consolidate)
    app.router.add_get("/status", handle_status)
    app.router.add_get("/memories", handle_memories)
    app.router.add_post("/delete", handle_delete)
    app.router.add_post("/clear", handle_clear)

    return app


# ─── Main ──────────────────────────────────────────────────────

async def main_async(args):
    agent = MemoryAgent(model=MODEL)

    log.info("🧠 Agent Memory Layer starting (Ollama Version)")
    log.info(f"   Model: {MODEL}")
    log.info(f"   Ollama Host: {OLLAMA_HOST}")
    log.info(f"   Database: {DB_PATH}")
    log.info(f"   Watch: {args.watch}")
    log.info(f"   Consolidate: every {args.consolidate_every}m")
    log.info(f"   API: http://localhost:{args.port}")
    log.info("")

    # Start background tasks
    tasks = [
        asyncio.create_task(watch_folder(agent, Path(args.watch))),
        asyncio.create_task(consolidation_loop(agent, args.consolidate_every)),
    ]

    # Start HTTP server
    app = build_http(agent, watch_path=args.watch)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", args.port)
    await site.start()

    log.info(f"✅ Agent running. Drop files in {args.watch}/ or POST to http://localhost:{args.port}/ingest")
    log.info("")

    # Wait forever
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()


def main():
    parser = argparse.ArgumentParser(description="Agent Memory Layer - Ollama Version")
    parser.add_argument("--watch", default="./inbox", help="Folder to watch (default: ./inbox)")
    parser.add_argument("--port", type=int, default=8893, help="HTTP API port (default: 8893)")
    parser.add_argument("--consolidate-every", type=int, default=30, help="Consolidation interval (default: 30m)")
    args = parser.parse_args()

    # Handle graceful shutdown
    loop = asyncio.new_event_loop()

    def shutdown(sig):
        log.info(f"\n👋 Shutting down (signal {sig})...")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown, sig)

    try:
        loop.run_until_complete(main_async(args))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        loop.close()
        log.info("🧠 Agent stopped.")


if __name__ == "__main__":
    main()
