#!/usr/bin/env python3
"""Quick test script for the memory agent."""

import requests
import json

BASE_URL = "http://localhost:8889"

def test_status():
    print("📊 Testing /status...")
    resp = requests.get(f"{BASE_URL}/status")
    print(f"   Status: {resp.json()}")

def test_ingest():
    print("\n📥 Testing /ingest...")
    data = {
        "text": "OpenClaw 是一个强大的 AI 代理框架，支持多模型后端（Ollama、Bailian 等）。主要特性包括 subagent 系统、技能系统、记忆系统。Leo 哥哥是主要开发者。",
        "source": "test"
    }
    resp = requests.post(f"{BASE_URL}/ingest", json=data)
    print(f"   Response: {resp.json()}")

def test_query():
    print("\n🔍 Testing /query...")
    resp = requests.get(f"{BASE_URL}/query", params={"q": "OpenClaw 是什么？"})
    print(f"   Answer: {resp.json()['answer'][:200]}...")

def test_memories():
    print("\n📚 Testing /memories...")
    resp = requests.get(f"{BASE_URL}/memories")
    data = resp.json()
    print(f"   Total memories: {data['count']}")
    for m in data['memories'][:3]:
        print(f"   - #{m['id']}: {m['summary'][:50]}...")

if __name__ == "__main__":
    print("🧠 Memory Agent Test Suite\n")
    print("=" * 50)
    
    try:
        test_status()
        test_ingest()
        test_ingest()  # Add another memory for consolidation
        test_query()
        test_memories()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the agent running?")
        print("   Run: python agent.py")
    except Exception as e:
        print(f"❌ Error: {e}")
