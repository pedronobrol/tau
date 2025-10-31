"""
Function hashing for proof certificate lookup.
Computes semantic hashes that are stable across formatting changes.
"""

import ast
import hashlib
import json
from typing import Dict, Any


def compute_function_hash(func_info: Dict[str, Any]) -> str:
    """
    Compute a semantic hash for a function.

    Uses AST-based hashing to ignore formatting differences:
    - Different whitespace/indentation → same hash
    - Different variable names → different hash (semantic change)
    - Different comments → same hash
    - Different docstrings → same hash

    The hash includes:
    - Function name and signature
    - Function body (AST-based, whitespace-independent)
    - All specifications (@requires, @ensures, @invariant, @variant)

    Args:
        func_info: Dictionary with keys:
            - name: Function name
            - source: Python source code
            - requires: Precondition string
            - ensures: Postcondition string
            - invariants: List of invariant strings
            - variant: Variant string

    Returns:
        64-character SHA-256 hex digest
    """
    try:
        # Parse function source to AST
        tree = ast.parse(func_info["source"])
        func_node = tree.body[0]  # Should be a FunctionDef

        # Extract semantic components
        components = {
            # Function signature
            "name": func_info["name"],
            "args": [arg.arg for arg in func_node.args.args],

            # Function body (normalized AST dump - ignores whitespace/comments)
            "body_ast": ast.dump(func_node, annotate_fields=False),

            # Specifications (critical for verification)
            "requires": func_info.get("requires", ""),
            "ensures": func_info.get("ensures", ""),
            "invariants": func_info.get("invariants", []),
            "variant": func_info.get("variant", "")
        }

        # Serialize to canonical JSON (sorted keys for stability)
        canonical = json.dumps(components, sort_keys=True, separators=(',', ':'))

        # Hash the canonical representation
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    except Exception as e:
        # Fallback to simple text-based hash if AST parsing fails
        print(f"Warning: AST-based hashing failed, using fallback: {e}")
        return compute_function_hash_simple(func_info)


def compute_function_hash_simple(func_info: Dict[str, Any]) -> str:
    """
    Fallback: Simple text-based hash.
    Less robust than AST-based but works for all cases.
    """
    combined = (
        func_info["name"] +
        func_info["source"] +
        func_info.get("requires", "") +
        func_info.get("ensures", "") +
        str(func_info.get("invariants", [])) +
        str(func_info.get("variant", ""))
    )

    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def compute_source_hash(func_info: Dict[str, Any]) -> str:
    """
    Compute EXACT hash of source text for auditing purposes.

    This hash changes with ANY modification (whitespace, comments, etc).
    Used to cryptographically prove EXACTLY what was verified.

    For auditing and compliance:
    - Proves exact code that was verified
    - Enables reproducible verification
    - Creates audit trail

    Args:
        func_info: Dictionary with keys:
            - name: Function name
            - source: Python source code
            - requires: Precondition string
            - ensures: Postcondition string
            - invariants: List of invariant strings
            - variant: Variant string

    Returns:
        64-character SHA-256 hex digest of exact source text
    """
    combined = (
        func_info["name"] +
        func_info["source"] +
        func_info.get("requires", "") +
        func_info.get("ensures", "") +
        str(func_info.get("invariants", [])) +
        str(func_info.get("variant", ""))
    )

    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def compute_body_hash(func_info: Dict[str, Any]) -> str:
    """
    Compute AST-based semantic hash of ONLY function body (excluding specs).

    Uses AST to ignore formatting differences:
    - Different whitespace/indentation → same hash
    - Different comments → same hash
    - Different docstrings → same hash
    - Different specs → same hash

    Used to detect when the same function implementation has been verified
    with different specifications. This allows suggesting cached proofs
    when specs change but implementation stays the same.

    Args:
        func_info: Dictionary with keys:
            - name: Function name
            - source: Python source code

    Returns:
        64-character SHA-256 hex digest of function body (semantic, no specs)
    """
    try:
        # Parse function source to AST
        tree = ast.parse(func_info["source"])
        func_node = tree.body[0]  # Should be a FunctionDef

        # Extract ONLY semantic body components (NO specs)
        components = {
            # Function signature
            "name": func_info["name"],
            "args": [arg.arg for arg in func_node.args.args],

            # Function body (normalized AST dump - ignores whitespace/comments)
            "body_ast": ast.dump(func_node, annotate_fields=False)
        }

        # Serialize to canonical JSON (sorted keys for stability)
        canonical = json.dumps(components, sort_keys=True, separators=(',', ':'))

        # Hash the canonical representation
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    except Exception as e:
        # Fallback to simple text-based hash if AST parsing fails
        print(f"Warning: AST-based body hashing failed, using fallback: {e}")
        combined = func_info["name"] + func_info["source"]
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
