"""
Example file demonstrating @safe decorated functions.

This file contains both correct and buggy functions to test the verification system.
"""

from tau_decorators import safe, requires, ensures, invariant, variant


# Example 1: Simple function with manual invariants
@safe
@requires("n >= 0")
@ensures("result = n")
@invariant("0 <= !i <= n")
@invariant("!c = !i")
@variant("n - !i")
def count_to(n: int) -> int:
    """Count from 0 to n (returns n)"""
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c


# Example 2: Function without invariants (will use LLM)
@safe
@requires("n >= 0")
@ensures("result = n * x")
def multiply(x: int, n: int) -> int:
    """Multiply x by n using repeated addition"""
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result


# Example 3: Buggy function (off-by-one error)
@safe
@requires("n >= 0")
@ensures("result = n")
def buggy_count(n: int) -> int:
    """BUGGY: Returns n+1 instead of n"""
    c = 0
    i = 0
    while i <= n:  # BUG: should be i < n
        c = c + 1
        i = i + 1
    return c


# Example 4: Clamp function (no loops, should verify easily)
@safe
@requires("lo <= hi")
@ensures("(x < lo -> result = lo) /\\ (x > hi -> result = hi) /\\ (lo <= x /\\ x <= hi -> result = x)")
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


# Example 5: Function with multiple preconditions/postconditions
@safe
@requires("n >= 0")
@requires("x >= 0")
@ensures("result >= 0")
@ensures("result = n * x")
def multiply_positive(x: int, n: int) -> int:
    """Multiply two non-negative integers"""
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result


# Example 6: Sum function with mathematical formula
@safe
@requires("n >= 0")
@ensures("result = div (n * (n + 1)) 2")
def sum_to(n: int) -> int:
    """Sum of integers from 0 to n"""
    s = 0
    i = 0
    while i <= n:
        s = s + i
        i = i + 1
    return s


# Regular function without @safe (should be ignored)
def regular_function(x: int) -> int:
    """This function is NOT marked @safe, so it won't be verified"""
    return x * 2
