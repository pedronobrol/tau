"""
Integration tests for the full transpiler
"""

import pytest
import os
from tau import transpile, ExternalFunctionContract


def test_simple_function():
    """Test transpiling a simple function"""
    source = '''
def add(a: int, b: int) -> int:
    return a + b
'''

    meta = {
        "add": {
            "requires": "true",
            "ensures": "result = a + b"
        }
    }

    result = transpile(source, meta, base_name="test_add")

    # Check files were created
    assert os.path.exists(result["why_file"])
    assert os.path.exists(result["lean_file"])

    # Check WhyML content
    whyml = result["whyml_source"]
    assert "module M_add" in whyml
    assert "let add (a:int) (b:int) : int =" in whyml
    assert "requires { true }" in whyml
    assert "ensures  { result = a + b }" in whyml
    assert "(a + b)" in whyml


def test_function_with_if_else():
    """Test transpiling function with conditionals"""
    source = '''
def max2(a: int, b: int) -> int:
    if a > b:
        return a
    else:
        return b
'''

    meta = {
        "max2": {
            "requires": "true",
            "ensures": "(a > b -> result = a) /\\\\ (a <= b -> result = b)"
        }
    }

    result = transpile(source, meta, base_name="test_max2")

    whyml = result["whyml_source"]
    assert "if (a > b) then" in whyml
    assert "else" in whyml


def test_function_with_loop():
    """Test transpiling function with loop"""
    source = '''
def sum_to(n: int) -> int:
    s = 0
    i = 0
    while i <= n:
        s = s + i
        i = i + 1
    return s
'''

    meta = {
        "sum_to": {
            "requires": "n >= 0",
            "ensures": "result = n * (n + 1) / 2",
            "invariants": [
                "0 <= !i",
                "!i <= n + 1",
                "!s = !i * (!i - 1) / 2"
            ],
            "variant": "n - !i"
        }
    }

    result = transpile(source, meta, base_name="test_sum_to")

    whyml = result["whyml_source"]
    assert "let s = ref 0 in" in whyml
    assert "let i = ref 0 in" in whyml
    assert "while" in whyml
    assert "invariant { 0 <= !i }" in whyml
    assert "variant { n - !i }" in whyml
    assert "do" in whyml
    assert "done;" in whyml


def test_external_function():
    """Test function with external contract"""
    source = '''
def norm1(x: int) -> int:
    return abs(x) + 1
'''

    external_contracts = {
        "abs": ExternalFunctionContract(
            args=[("x", "int")],
            return_type="int",
            requires="true",
            ensures="result >= 0"
        )
    }

    meta = {
        "norm1": {
            "requires": "true",
            "ensures": "result >= 1"
        }
    }

    result = transpile(source, meta, external_contracts=external_contracts, base_name="test_norm1")

    whyml = result["whyml_source"]
    assert "val abs (x:int) : int" in whyml
    assert "requires { true }" in whyml
    assert "ensures  { result >= 0 }" in whyml


def test_lean_generation():
    """Test Lean theorem generation"""
    source = '''
def inc(x: int) -> int:
    return x + 1
'''

    meta = {
        "inc": {
            "requires": "true",
            "ensures": "result = x + 1"
        }
    }

    result = transpile(source, meta, base_name="test_inc")

    lean = result["lean_source"]
    assert "theorem inc_correct" in lean
    assert "(x : Int)" in lean
    assert "-- requires: true" in lean
    assert "-- ensures: result = x + 1" in lean
    assert "admit" in lean


def test_missing_function_raises():
    """Test that empty source raises error"""
    source = "# Just a comment"
    meta = {}

    with pytest.raises(ValueError, match="No functions found"):
        transpile(source, meta)


def test_missing_else_raises():
    """Test that missing else branch raises error"""
    source = '''
def bad(x: int) -> int:
    if x > 0:
        return x
    return 0
'''

    meta = {
        "bad": {
            "requires": "true",
            "ensures": "true"
        }
    }

    # This should work because there's a return after if
    # But if we modify to only have if without return after:
    source2 = '''
def bad(x: int) -> int:
    y = 0
    if x > 0:
        y = x
    return y
'''

    # This will fail because the if needs both branches
    with pytest.raises(NotImplementedError, match="if/else branches"):
        transpile(source2, meta)


def test_multiple_loops_raises():
    """Test that multiple loops raise error"""
    source = '''
def bad(n: int) -> int:
    s = 0
    i = 0
    while i < n:
        i = i + 1
    j = 0
    while j < n:
        j = j + 1
    return s
'''

    meta = {
        "bad": {
            "requires": "n >= 0",
            "ensures": "true"
        }
    }

    with pytest.raises(NotImplementedError, match="one while loop"):
        transpile(source, meta)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
