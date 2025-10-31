"""
Example demonstrating @safe_auto decorator.

The @safe_auto decorator automatically generates specifications
and verifies the function without manual intervention.
"""

from tau_decorators import safe_auto


# Example 1: Simple counting function
# The system will automatically infer:
# - @requires("n >= 0")
# - @ensures("result = n")
# - Loop invariants and variant
@safe_auto
def count_to(n: int) -> int:
    """Count from 0 to n (returns n)"""
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c


# Example 2: Multiplication by repeated addition
# The system will automatically infer all specifications
@safe_auto
def multiply(x: int, n: int) -> int:
    """Multiply x by n using repeated addition"""
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result


# Example 3: Clamp function (no loops)
@safe_auto
def clamp(x: int, lo: int, hi: int) -> int:
    """Clamp x to range [lo, hi]"""
    t = x
    if t < lo:
        return lo
    else:
        if t > hi:
            return hi
        else:
            return t
