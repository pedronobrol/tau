"""
Demo file to test proof certificate caching.
This file contains a function that has already been verified and cached.
"""

@safe
# @requires: n >= 0
# @ensures: result = n
# @invariant: 0 <= !i <= n
# @invariant: !c = !i
# @variant: n - !i
def count_to(n: int) -> int:
    """Count from 0 to n-1 and return the count."""
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c


@safe
# @requires: n >= 0
# @ensures: result >= 0
def factorial(n: int) -> int:
    """Compute factorial of n."""
    if n == 0:
        return 1
    result = 1
    i = 1
    while i <= n:
        result = result * i
        i = i + 1
    return result


# Test the functions
if __name__ == "__main__":
    print(f"count_to(5) = {count_to(5)}")
    print(f"factorial(5) = {factorial(5)}")
