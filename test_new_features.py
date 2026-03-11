#!/usr/bin/env python3
"""
Test script for new features: User Isolation & Authentication
"""

import requests
import json
import time

BASE_URL = "http://localhost:8888"

def test_register_user():
    """Test user registration"""
    print("\n📝 Test 1: User Registration")
    print("-" * 40)
    
    # Register user1
    resp = requests.post(f"{BASE_URL}/auth/register", json={"username": "test_user1"})
    print(f"Register user1: {resp.status_code} - {resp.json()}")
    
    if resp.status_code == 200:
        data = resp.json()
        return data.get("token")
    return None

def test_ingest_with_auth(token):
    """Test memory ingestion with authentication"""
    print("\n📥 Test 2: Memory Ingestion with Auth")
    print("-" * 40)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Ingest private memory
    resp = requests.post(f"{BASE_URL}/ingest", 
                        json={"text": "This is my private memory", "is_shared": False},
                        headers=headers)
    print(f"Ingest private: {resp.status_code} - {resp.json()}")
    
    # Ingest shared memory
    resp = requests.post(f"{BASE_URL}/ingest",
                        json={"text": "This is a shared memory", "is_shared": True},
                        headers=headers)
    print(f"Ingest shared: {resp.status_code} - {resp.json()}")

def test_query_with_auth(token):
    """Test memory query with authentication"""
    print("\n🔍 Test 3: Memory Query with Auth")
    print("-" * 40)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{BASE_URL}/query", params={"q": "What memories do I have?"}, headers=headers)
    print(f"Query: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Answer: {data.get('answer', 'N/A')[:200]}...")

def test_list_memories_with_auth(token):
    """Test listing memories with authentication"""
    print("\n📋 Test 4: List Memories with Auth")
    print("-" * 40)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{BASE_URL}/memories", headers=headers)
    print(f"List memories: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total: {data.get('count', 0)} memories")
        for m in data.get('memories', [])[:3]:
            shared = "🔓 Shared" if m.get('is_shared') else "🔒 Private"
            print(f"  - #{m['id']}: {m['summary'][:50]}... [{shared}]")

def test_share_memory(token, memory_id):
    """Test sharing a memory"""
    print("\n🔓 Test 5: Share Memory")
    print("-" * 40)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.post(f"{BASE_URL}/share", json={"memory_id": memory_id}, headers=headers)
    print(f"Share memory #{memory_id}: {resp.status_code} - {resp.json()}")

def test_unauthorized_access():
    """Test unauthorized access"""
    print("\n🚫 Test 6: Unauthorized Access")
    print("-" * 40)
    
    # Try to access without token
    resp = requests.get(f"{BASE_URL}/memories")
    print(f"Access without token: {resp.status_code} - {resp.json()}")

def test_status(token):
    """Test status endpoint"""
    print("\n📊 Test 7: Status")
    print("-" * 40)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{BASE_URL}/status", headers=headers)
    print(f"Status: {resp.status_code} - {resp.json()}")

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Always-On Memory - New Features Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Register user
        token = test_register_user()
        if not token:
            print("❌ User registration failed!")
            return False
        
        time.sleep(1)
        
        # Test 2: Ingest with auth
        test_ingest_with_auth(token)
        time.sleep(1)
        
        # Test 3: Query with auth
        test_query_with_auth(token)
        time.sleep(1)
        
        # Test 4: List memories
        test_list_memories_with_auth(token)
        time.sleep(1)
        
        # Test 5: Share memory (get first private memory)
        resp = requests.get(f"{BASE_URL}/memories", headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 200:
            memories = resp.json().get('memories', [])
            private_memories = [m for m in memories if not m.get('is_shared')]
            if private_memories:
                test_share_memory(token, private_memories[0]['id'])
        
        time.sleep(1)
        
        # Test 6: Unauthorized access
        test_unauthorized_access()
        
        # Test 7: Status
        test_status(token)
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        return True
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error - is the agent running?")
        print("   Run: python agent_new.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
