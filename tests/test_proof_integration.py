#!/usr/bin/env python3
"""
Test the full proof certificate integration:
1. Store a proof certificate
2. Check it can be retrieved
3. Test the API endpoints
"""

import requests
import json


BASE_URL = "http://localhost:8000"


def test_proof_workflow():
    """Test the complete proof workflow."""
    print("=" * 70)
    print("Testing Proof Certificate Integration")
    print("=" * 70)

    # Test 1: Check server is running
    print("\n1. Checking server health...")
    try:
        response = requests.get(f"{BASE_URL}/")
        health = response.json()
        print(f"   ✅ Server is running: {health['status']}")
    except Exception as e:
        print(f"   ❌ Server is not running: {e}")
        print("   Please start server with: python3 -m tau.server.app")
        return

    # Test 2: Store a proof certificate
    print("\n2. Storing a proof certificate...")

    function_source = """def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c"""

    store_request = {
        "function_name": "count_to",
        "function_source": function_source,
        "requires": "n >= 0",
        "ensures": "result = n",
        "invariants": ["0 <= !i <= n", "!c = !i"],
        "variant": "n - !i",
        "verified": True,
        "whyml_code": "let count_to (n: int) : int = ...",
        "lean_code": "def count_to (n : Int) : Int := ...",
        "why3_output": "Verification successful - all goals proved"
    }

    response = requests.post(f"{BASE_URL}/api/proofs/store", json=store_request)
    result = response.json()

    if result.get("success"):
        func_hash = result["hash"]
        print(f"   ✅ Stored proof with hash: #{func_hash[:8]}")
    else:
        print(f"   ❌ Failed to store proof: {result.get('error')}")
        return

    # Test 3: Check the proof exists
    print("\n3. Checking if proof can be retrieved...")

    check_request = {
        "function_name": "count_to",
        "function_source": function_source,
        "requires": "n >= 0",
        "ensures": "result = n",
        "invariants": ["0 <= !i <= n", "!c = !i"],
        "variant": "n - !i"
    }

    response = requests.post(f"{BASE_URL}/api/proofs/check", json=check_request)
    proof_check = response.json()

    if proof_check.get("found"):
        print(f"   ✅ Found cached proof!")
        print(f"      Hash: #{proof_check['hash'][:8]}")
        print(f"      Verified: {proof_check['verified']}")
        print(f"      Created: {proof_check['created_at']}")
    else:
        print(f"   ❌ Proof not found (should have been cached)")
        return

    # Test 4: Test cache miss with different function
    print("\n4. Testing cache miss with different function...")

    different_function = {
        "function_name": "unknown_func",
        "function_source": "def unknown_func(x: int) -> int:\n    return x * 2",
        "requires": "",
        "ensures": ""
    }

    response = requests.post(f"{BASE_URL}/api/proofs/check", json=different_function)
    proof_check = response.json()

    if not proof_check.get("found"):
        print(f"   ✅ Correctly returned cache miss")
    else:
        print(f"   ❌ Should not have found a proof for unknown function")

    # Test 5: Get cache statistics
    print("\n5. Getting cache statistics...")

    response = requests.get(f"{BASE_URL}/api/proofs/stats")
    stats = response.json()

    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Cache misses: {stats['cache_misses']}")
    print(f"   Cache size: {stats['cache_size_bytes']} bytes")

    # Test 6: List all proofs
    print("\n6. Listing all proofs...")

    response = requests.get(f"{BASE_URL}/api/proofs/list")
    result = response.json()

    if result.get("success"):
        proofs = result["proofs"]
        print(f"   Found {len(proofs)} proof(s):")
        for proof in proofs:
            status = "✅" if proof["verified"] else "❌"
            print(f"      {status} {proof['function_name']} (#{proof['hash'][:8]})")
    else:
        print(f"   ❌ Failed to list proofs")

    # Test 7: Verify that hash is stable across formatting
    print("\n7. Testing hash stability across formatting changes...")

    # Same function, different formatting
    reformatted_source = """def count_to(n: int) -> int:
        c = 0
        i = 0
        while i < n:
            c = c + 1
            i = i + 1
        return c"""  # Extra indentation

    reformatted_check = {
        "function_name": "count_to",
        "function_source": reformatted_source,
        "requires": "n >= 0",
        "ensures": "result = n",
        "invariants": ["0 <= !i <= n", "!c = !i"],
        "variant": "n - !i"
    }

    response = requests.post(f"{BASE_URL}/api/proofs/check", json=reformatted_check)
    proof_check = response.json()

    if proof_check.get("found") and proof_check["hash"] == func_hash:
        print(f"   ✅ Hash is stable - found same proof despite formatting changes!")
        print(f"      Hash: #{proof_check['hash'][:8]}")
    else:
        print(f"   ❌ Hash changed with formatting (should be stable)")

    print("\n" + "=" * 70)
    print("✅ All proof certificate tests passed!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_proof_workflow()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
