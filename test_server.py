#!/usr/bin/env python3
"""
Test TAU Server
"""
import requests
import json

print("=" * 60)
print("Testing TAU Server")
print("=" * 60)

base_url = "http://localhost:8000"

# Test 1: Health Check
print("\n[1] Health Check")
print("-" * 60)
try:
    response = requests.get(f"{base_url}/")
    data = response.json()
    print(f"✅ Status: {data['status']}")
    print(f"   Version: {data['version']}")
    print(f"   Anthropic Available: {data['anthropic_available']}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Verify Function
print("\n[2] Verify Function")
print("-" * 60)
try:
    response = requests.post(
        f"{base_url}/api/verify-function",
        json={
            "file_path": "examples/safe_functions.py",
            "function_name": "count_to"
        }
    )
    data = response.json()

    if data['success']:
        result = data['result']
        status = "✅" if result['verified'] else "❌"
        print(f"{status} Function: {result['name']}")
        print(f"   Verified: {result['verified']}")
        print(f"   Reason: {result['reason']}")
        print(f"   Duration: {result['duration']:.2f}s")
        if result['hash']:
            print(f"   Hash: #{result['hash'][:8]}")
    else:
        print(f"❌ Error: {data['error']}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Verify Entire File
print("\n[3] Verify File")
print("-" * 60)
try:
    response = requests.post(
        f"{base_url}/api/verify-file",
        json={"file_path": "examples/safe_functions.py"}
    )
    data = response.json()

    if data['success']:
        summary = data['result']
        print(f"✅ Total: {summary['total']}")
        print(f"   Passed: {summary['passed']}")
        print(f"   Failed: {summary['failed']}")

        print("\n   Results:")
        for result in summary['results']:
            status = "✅" if result['verified'] else "❌"
            print(f"   {status} {result['name']} - {result['reason']}")
    else:
        print(f"❌ Error: {data['error']}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Spec Generation (optional - requires API key)
print("\n[4] Spec Generation (requires ANTHROPIC_API_KEY)")
print("-" * 60)
try:
    response = requests.post(
        f"{base_url}/api/generate-specs",
        json={
            "function_source": """def multiply(x: int, n: int) -> int:
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result"""
        }
    )
    data = response.json()

    if data['success'] and data['specs']:
        specs = data['specs']
        print(f"✅ Specs generated!")
        print(f"   @requires: {specs['requires']}")
        print(f"   @ensures: {specs['ensures']}")
        if specs['suggested_invariants']:
            print(f"   Suggested invariants: {specs['suggested_invariants']}")
        print(f"   Confidence: {specs['confidence']*100:.0f}%")
    else:
        print(f"⚠️  {data.get('error', 'Spec generation not available (set ANTHROPIC_API_KEY)')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: API Docs
print("\n[5] API Documentation")
print("-" * 60)
print(f"📚 Interactive API docs: {base_url}/docs")
print(f"📖 OpenAPI schema: {base_url}/openapi.json")

print("\n" + "=" * 60)
print("Tests Complete!")
print("=" * 60)
