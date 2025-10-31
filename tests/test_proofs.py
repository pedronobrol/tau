#!/usr/bin/env python3
"""
Test the proof certificate system.
"""

from tau.proofs import ProofCertificateManager, compute_function_hash


def test_hash_computation():
    """Test that hashing works and is stable."""
    print("=" * 60)
    print("Test 1: Hash Computation")
    print("=" * 60)

    func_info = {
        "name": "count_to",
        "source": """def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c""",
        "requires": "n >= 0",
        "ensures": "result = n",
        "invariants": ["0 <= !i <= n", "!c = !i"],
        "variant": "n - !i"
    }

    hash1 = compute_function_hash(func_info)
    print(f"Hash: {hash1}")
    print(f"Short hash: #{hash1[:8]}")

    # Compute again - should be identical
    hash2 = compute_function_hash(func_info)
    assert hash1 == hash2, "Hashes should be identical!"
    print("✅ Hash is stable across recomputation")

    # Change formatting - hash should still be same (AST-based)
    func_info_reformatted = func_info.copy()
    func_info_reformatted["source"] = """def count_to(n: int) -> int:
        c = 0
        i = 0
        while i < n:
            c = c + 1
            i = i + 1
        return c"""  # Different indentation

    hash3 = compute_function_hash(func_info_reformatted)
    assert hash1 == hash3, "Hash should ignore formatting changes!"
    print("✅ Hash is stable across formatting changes")

    # Change actual code - hash should change
    func_info_changed = func_info.copy()
    func_info_changed["source"] = func_info_changed["source"].replace("c = c + 1", "c = c + 2")

    hash4 = compute_function_hash(func_info_changed)
    assert hash1 != hash4, "Hash should change when code changes!"
    print("✅ Hash changes when code changes")

    print()


def test_proof_storage_and_lookup():
    """Test storing and retrieving proofs."""
    print("=" * 60)
    print("Test 2: Proof Storage and Lookup")
    print("=" * 60)

    manager = ProofCertificateManager()

    func_info = {
        "name": "count_to",
        "source": """def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c""",
        "requires": "n >= 0",
        "ensures": "result = n",
        "invariants": ["0 <= !i <= n", "!c = !i"],
        "variant": "n - !i"
    }

    # Store a proof
    print("Storing proof certificate...")
    func_hash = manager.store_proof(
        func_info=func_info,
        verified=True,
        whyml_code="let count_to (n: int) : int = ...",
        lean_code="def count_to (n : Int) : Int := ...",
        why3_output="Verification successful"
    )

    print(f"Stored with hash: {func_hash[:8]}")

    # Look it up
    print("Looking up proof...")
    certificate = manager.lookup_proof(func_info)

    assert certificate is not None, "Certificate should be found!"
    assert certificate["verified"] is True, "Should be verified!"
    assert certificate["hash"] == func_hash, "Hash should match!"
    print(f"✅ Found certificate: {certificate['function_name']}")
    print(f"   Verified: {certificate['verified']}")
    print(f"   Hash: #{certificate['hash'][:8]}")

    # Check stats
    stats = manager.get_stats()
    print(f"\nCache stats:")
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Cache misses: {stats['cache_misses']}")

    print()


def test_cache_miss():
    """Test that unknown functions return None."""
    print("=" * 60)
    print("Test 3: Cache Miss")
    print("=" * 60)

    manager = ProofCertificateManager()

    func_info = {
        "name": "unknown_function",
        "source": "def unknown_function(x: int) -> int:\n    return x + 1",
        "requires": "",
        "ensures": ""
    }

    print("Looking up non-existent function...")
    certificate = manager.lookup_proof(func_info)

    assert certificate is None, "Should not find certificate!"
    print("✅ Correctly returned None for cache miss")

    # Check stats
    stats = manager.get_stats()
    print(f"\nCache misses increased: {stats['cache_misses']}")

    print()


def test_list_proofs():
    """Test listing all proofs."""
    print("=" * 60)
    print("Test 4: List Proofs")
    print("=" * 60)

    manager = ProofCertificateManager()

    proofs = manager.list_proofs()
    print(f"Total proofs: {len(proofs)}")

    for proof in proofs:
        print(f"  - {proof['function_name']} (#{proof['hash'][:8]}) - "
              f"{'✅ Verified' if proof['verified'] else '❌ Failed'}")

    print()


if __name__ == "__main__":
    print("\n🧪 Testing TAU Proof Certificate System\n")

    try:
        test_hash_computation()
        test_proof_storage_and_lookup()
        test_cache_miss()
        test_list_proofs()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
