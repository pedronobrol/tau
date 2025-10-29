"""
Test that tau-decorators work and linters are happy
"""
from tau_decorators import safe, requires, ensures, invariant, variant


@safe
@requires("n >= 0")
@ensures("result = n")
@invariant("0 <= !i <= n")
@invariant("!c = !i")
@variant("n - !i")
def count_to(n: int) -> int:
    """Count from 0 to n"""
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c


@safe
@requires("n >= 0 /\\ x >= 0")
@ensures("result = n * x")
def multiply(x: int, n: int) -> int:
    """Multiply x by n using addition"""
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result


if __name__ == "__main__":
    # These functions work normally at runtime
    print(f"count_to(5) = {count_to(5)}")  # Should print 5
    print(f"multiply(3, 4) = {multiply(3, 4)}")  # Should print 12
    print("✅ Decorators work at runtime!")
