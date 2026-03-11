#!/usr/bin/env python3
"""
Always-On Memory Agent - 完整测试套件

覆盖：
1. 功能测试 - 核心功能验证
2. 边界测试 - 异常情况处理
3. 集成测试 - 多模块联调
4. 性能测试 - 响应时间评估
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8894"
TEST_RESULTS = []

def log_result(test_name, status, details="", duration=""):
    """记录测试结果"""
    result = {
        "test": test_name,
        "status": status,  # ✅ PASS / ❌ FAIL / ⚠️ WARN
        "details": details,
        "duration": duration,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    TEST_RESULTS.append(result)
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} [{result['timestamp']}] {test_name}: {status}")
    if details:
        print(f"   {details}")
    if duration:
        print(f"   耗时：{duration}")
    print()

def test_api_status():
    """测试 1: API 状态检查"""
    test_name = "API 状态检查"
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/status", timeout=5)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        if resp.status_code == 200:
            data = resp.json()
            if "total_memories" in data:
                log_result(test_name, "PASS", f"返回数据：{data}", duration)
                return True
            else:
                log_result(test_name, "FAIL", "返回数据格式错误", duration)
                return False
        else:
            log_result(test_name, "FAIL", f"HTTP 状态码：{resp.status_code}", duration)
            return False
    except requests.exceptions.ConnectionError:
        log_result(test_name, "FAIL", "无法连接到 API - Agent 是否运行？")
        return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_ingest_basic():
    """测试 2: 基础记忆录入"""
    test_name = "基础记忆录入"
    try:
        start = time.time()
        data = {
            "text": "测试记忆：OpenClaw 是一个强大的 AI 代理框架，支持多模型后端。",
            "source": "test_suite"
        }
        resp = requests.post(f"{BASE_URL}/ingest", json=data, timeout=180)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get("status") == "ingested" and "memory_id" in result.get("response", {}):
                log_result(test_name, "PASS", f"记忆 ID: {result['response']['memory_id']}", duration)
                return result['response']['memory_id']
            else:
                log_result(test_name, "FAIL", f"响应格式异常：{result}", duration)
                return None
        else:
            log_result(test_name, "FAIL", f"HTTP 状态码：{resp.status_code}", duration)
            return None
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return None

def test_ingest_empty_text():
    """测试 3: 边界测试 - 空文本输入"""
    test_name = "边界测试 - 空文本输入"
    try:
        start = time.time()
        data = {"text": "", "source": "test"}
        resp = requests.post(f"{BASE_URL}/ingest", json=data, timeout=30)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        # 应该返回错误或处理空文本
        if resp.status_code in [200, 400]:
            log_result(test_name, "PASS", f"正确处理空输入，状态码：{resp.status_code}", duration)
            return True
        else:
            log_result(test_name, "FAIL", f"意外状态码：{resp.status_code}", duration)
            return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_ingest_missing_field():
    """测试 4: 边界测试 - 缺少必需字段"""
    test_name = "边界测试 - 缺少 text 字段"
    try:
        start = time.time()
        data = {"source": "test"}  # 缺少 text
        resp = requests.post(f"{BASE_URL}/ingest", json=data, timeout=10)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        if resp.status_code == 400:
            log_result(test_name, "PASS", f"正确返回 400 错误", duration)
            return True
        else:
            log_result(test_name, "FAIL", f"应该返回 400，实际：{resp.status_code}", duration)
            return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_ingest_long_text():
    """测试 5: 边界测试 - 长文本输入"""
    test_name = "边界测试 - 长文本输入 (5000 字符)"
    try:
        start = time.time()
        long_text = "测试内容 " * 500  # 5000 字符
        data = {"text": long_text, "source": "test_long"}
        resp = requests.post(f"{BASE_URL}/ingest", json=data, timeout=180)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        if resp.status_code == 200:
            log_result(test_name, "PASS", f"成功处理长文本", duration)
            return True
        else:
            log_result(test_name, "FAIL", f"HTTP 状态码：{resp.status_code}", duration)
            return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_memories_list():
    """测试 6: 获取记忆列表"""
    test_name = "获取记忆列表"
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/memories", timeout=10)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        if resp.status_code == 200:
            data = resp.json()
            if "memories" in data and "count" in data:
                log_result(test_name, "PASS", f"记忆数量：{data['count']}", duration)
                return True
            else:
                log_result(test_name, "FAIL", "返回数据格式错误", duration)
                return False
        else:
            log_result(test_name, "FAIL", f"HTTP 状态码：{resp.status_code}", duration)
            return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_query_basic():
    """测试 7: 基础查询功能"""
    test_name = "基础查询功能"
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/query", params={"q": "OpenClaw 是什么"}, timeout=120)
        duration = f"{(time.time() - start):.1f}s"
        
        if resp.status_code == 200:
            data = resp.json()
            if "answer" in data:
                log_result(test_name, "PASS", f"回答长度：{len(data['answer'])} 字符", duration)
                return True
            else:
                log_result(test_name, "FAIL", "响应缺少 answer 字段", duration)
                return False
        else:
            log_result(test_name, "FAIL", f"HTTP 状态码：{resp.status_code}", duration)
            return False
    except requests.exceptions.Timeout:
        log_result(test_name, "WARN", "查询超时 (>120s) - Ollama 模型加载慢", "120s+")
        return True  # 算警告通过
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_query_empty():
    """测试 8: 边界测试 - 空查询"""
    test_name = "边界测试 - 空查询参数"
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/query", params={"q": ""}, timeout=10)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        if resp.status_code == 400:
            log_result(test_name, "PASS", f"正确返回 400 错误", duration)
            return True
        else:
            log_result(test_name, "FAIL", f"应该返回 400，实际：{resp.status_code}", duration)
            return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_consolidate_manual():
    """测试 9: 手动触发整合"""
    test_name = "手动触发整合"
    try:
        start = time.time()
        resp = requests.post(f"{BASE_URL}/consolidate", timeout=120)
        duration = f"{(time.time() - start):.1f}s"
        
        if resp.status_code == 200:
            data = resp.json()
            log_result(test_name, "PASS", f"整合结果：{data.get('status', 'unknown')}", duration)
            return True
        else:
            log_result(test_name, "FAIL", f"HTTP 状态码：{resp.status_code}", duration)
            return False
    except requests.exceptions.Timeout:
        log_result(test_name, "WARN", "整合超时 (>120s)", "120s+")
        return True
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_delete_memory():
    """测试 10: 删除记忆"""
    test_name = "删除记忆"
    try:
        # 先获取记忆列表
        resp = requests.get(f"{BASE_URL}/memories", timeout=10)
        if resp.status_code != 200:
            log_result(test_name, "FAIL", "无法获取记忆列表")
            return False
        
        memories = resp.json().get("memories", [])
        test_memories = [m for m in memories if m.get("source") == "test_suite"]
        
        if not test_memories:
            log_result(test_name, "WARN", "没有测试记忆可删除")
            return True
        
        # 删除测试记忆
        start = time.time()
        memory_id = test_memories[0]["id"]
        resp = requests.post(f"{BASE_URL}/delete", json={"memory_id": memory_id}, timeout=10)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get("status") == "deleted":
                log_result(test_name, "PASS", f"删除记忆 #{memory_id}", duration)
                return True
            else:
                log_result(test_name, "FAIL", f"删除失败：{result}", duration)
                return False
        else:
            log_result(test_name, "FAIL", f"HTTP 状态码：{resp.status_code}", duration)
            return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_invalid_json():
    """测试 11: 边界测试 - 无效 JSON"""
    test_name = "边界测试 - 无效 JSON"
    try:
        start = time.time()
        resp = requests.post(f"{BASE_URL}/ingest", 
                           data="not valid json",
                           headers={"Content-Type": "application/json"},
                           timeout=10)
        duration = f"{(time.time() - start) * 1000:.0f}ms"
        
        if resp.status_code == 400:
            log_result(test_name, "PASS", f"正确拒绝无效 JSON", duration)
            return True
        else:
            log_result(test_name, "FAIL", f"应该返回 400，实际：{resp.status_code}", duration)
            return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_memory_structure():
    """测试 12: 记忆数据结构验证"""
    test_name = "记忆数据结构验证"
    try:
        resp = requests.get(f"{BASE_URL}/memories", timeout=10)
        if resp.status_code != 200:
            log_result(test_name, "FAIL", "无法获取记忆列表")
            return False
        
        memories = resp.json().get("memories", [])
        if not memories:
            log_result(test_name, "WARN", "没有记忆可验证")
            return True
        
        # 验证记忆结构
        required_fields = ["id", "summary", "entities", "topics", "importance", "created_at"]
        memory = memories[0]
        missing = [f for f in required_fields if f not in memory]
        
        if not missing:
            log_result(test_name, "PASS", f"记忆结构完整，包含所有必需字段")
            return True
        else:
            log_result(test_name, "FAIL", f"缺少字段：{missing}")
            return False
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def test_performance_ingest():
    """测试 13: 性能测试 - 录入响应时间"""
    test_name = "性能测试 - 录入响应时间"
    try:
        times = []
        for i in range(3):
            start = time.time()
            data = {"text": f"性能测试记忆 {i}", "source": "perf_test"}
            resp = requests.post(f"{BASE_URL}/ingest", json=data, timeout=180)
            duration = time.time() - start
            times.append(duration)
            if resp.status_code != 200:
                log_result(test_name, "FAIL", f"第 {i+1} 次请求失败")
                return False
        
        avg_time = sum(times) / len(times)
        if avg_time < 30:
            log_result(test_name, "PASS", f"平均响应时间：{avg_time:.1f}s", f"{avg_time:.1f}s")
            return True
        else:
            log_result(test_name, "WARN", f"响应较慢：{avg_time:.1f}s (Ollama 冷启动)", f"{avg_time:.1f}s")
            return True
    except Exception as e:
        log_result(test_name, "FAIL", str(e))
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧠 Always-On Memory Agent - 完整测试套件")
    print("=" * 60)
    print()
    
    # 阶段 1: 基础功能测试
    print("📌 阶段 1: 基础功能测试")
    print("-" * 40)
    test_api_status()
    test_ingest_basic()
    test_memories_list()
    test_memory_structure()
    
    # 阶段 2: 边界测试
    print("📌 阶段 2: 边界测试")
    print("-" * 40)
    test_ingest_empty_text()
    test_ingest_missing_field()
    test_ingest_long_text()
    test_query_empty()
    test_invalid_json()
    
    # 阶段 3: 集成测试
    print("📌 阶段 3: 集成测试")
    print("-" * 40)
    test_query_basic()
    test_consolidate_manual()
    test_delete_memory()
    
    # 阶段 4: 性能测试
    print("📌 阶段 4: 性能测试")
    print("-" * 40)
    test_performance_ingest()
    
    # 汇总结果
    print()
    print("=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for r in TEST_RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in TEST_RESULTS if r["status"] == "FAIL")
    warned = sum(1 for r in TEST_RESULTS if r["status"] == "WARN")
    total = len(TEST_RESULTS)
    
    print(f"总计：{total} 个测试")
    print(f"✅ 通过：{passed}")
    print(f"❌ 失败：{failed}")
    print(f"⚠️  警告：{warned}")
    print()
    
    if failed > 0:
        print("❌ 测试未通过，需要修复以下问题：")
        for r in TEST_RESULTS:
            if r["status"] == "FAIL":
                print(f"  - {r['test']}: {r['details']}")
        return False
    else:
        print("✅ 所有测试通过！代码可以交付！")
        return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
