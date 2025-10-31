"""
Simple example with manual invariants (no LLM needed)
"""

from tau_decorators import safe_auto, safe, requires, ensures, invariant, variant


@safe_auto
def count_to(n: int) -> int:
    """Count from 0 to n"""
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c


@safe
@requires("lo <= x")
@ensures("(x < lo -> result = lo) /\\ (x > hi -> result = hi) /\\ (lo <= x /\\ x <= hi -> result = x)")
def clamp(x: int, lo: int, hi: int) -> int:
    """Clamp x to [lo, hi]"""
    t = x
    if t < lo:
        return lo
    else:
        if t > hi:
            return hi
        else:
            return t
