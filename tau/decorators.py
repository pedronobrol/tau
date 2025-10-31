"""
Decorators for marking functions for formal verification.

Usage:
    @safe
    @requires("n >= 0")
    @ensures("result = n")
    def count_to(n: int) -> int:
        c = 0
        i = 0
        while i < n:
            c = c + 1
            i = i + 1
        return c

Optional invariants/variants:
    @safe
    @requires("n >= 0")
    @ensures("result = n")
    @invariant("0 <= !i <= n")
    @invariant("!c = !i")
    @variant("n - !i")
    def count_to(n: int) -> int:
        ...
"""

from functools import wraps
from typing import Callable, Any


def safe(func: Callable) -> Callable:
    """
    Mark function for formal verification.

    This decorator must be the outermost decorator.
    Requires explicit @requires and @ensures specifications.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    # Mark the function as needing verification
    wrapper.__safe__ = True
    wrapper.__safe_auto__ = False
    wrapper.__safe_specs__ = {
        "requires": [],
        "ensures": [],
        "invariants": [],
        "variant": None
    }

    return wrapper


def safe_auto(func: Callable) -> Callable:
    """
    Mark function for automatic formal verification with inferred specs.

    Automatically generates ALL specifications:
    - @requires (preconditions)
    - @ensures (postconditions)
    - @invariant (loop invariants)
    - @variant (termination proof)

    This decorator must be the outermost decorator.

    Example:
        @safe_auto
        def multiply(x: int, n: int) -> int:
            result = 0
            i = 0
            while i < n:
                result = result + x
                i = i + 1
            return result

        # System automatically infers:
        # @requires("n >= 0")
        # @ensures("result = n * x")
        # Plus loop invariants and variant
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    # Mark the function as needing verification with auto-generation
    wrapper.__safe__ = True
    wrapper.__safe_auto__ = True  # Enable automatic spec generation
    wrapper.__safe_specs__ = {
        "requires": [],
        "ensures": [],
        "invariants": [],
        "variant": None
    }

    return wrapper


def requires(condition: str) -> Callable:
    """
    Specify precondition for the function.

    Args:
        condition: WhyML condition (e.g., "n >= 0")
    """
    def decorator(func: Callable) -> Callable:
        if hasattr(func, '__safe_specs__'):
            func.__safe_specs__["requires"].append(condition)
        return func
    return decorator


def ensures(condition: str) -> Callable:
    """
    Specify postcondition for the function.

    Args:
        condition: WhyML condition (e.g., "result = n")
    """
    def decorator(func: Callable) -> Callable:
        if hasattr(func, '__safe_specs__'):
            func.__safe_specs__["ensures"].append(condition)
        return func
    return decorator


def invariant(condition: str) -> Callable:
    """
    Specify loop invariant (optional).

    Args:
        condition: WhyML invariant (e.g., "0 <= !i <= n")
    """
    def decorator(func: Callable) -> Callable:
        if hasattr(func, '__safe_specs__'):
            func.__safe_specs__["invariants"].append(condition)
        return func
    return decorator


def variant(expression: str) -> Callable:
    """
    Specify termination variant (optional).

    Args:
        expression: WhyML expression that decreases (e.g., "n - !i")
    """
    def decorator(func: Callable) -> Callable:
        if hasattr(func, '__safe_specs__'):
            func.__safe_specs__["variant"] = expression
        return func
    return decorator
