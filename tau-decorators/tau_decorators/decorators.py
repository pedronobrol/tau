"""
TAU Decorators - Lightweight stubs for formal verification

These are no-op decorators that serve as markers for the TAU verification system.
The actual verification happens on the TAU server when using the VS Code extension.

Usage:
    from tau_decorators import safe, requires, ensures

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
"""

from typing import Callable, TypeVar

F = TypeVar('F', bound=Callable)


def safe(func: F) -> F:
    """
    Mark a function for formal verification.

    The TAU system will analyze this function and verify that it meets
    its specified preconditions, postconditions, and loop invariants.

    Args:
        func: The function to mark for verification

    Returns:
        The original function (unchanged at runtime)
    """
    return func


def requires(spec: str) -> Callable[[F], F]:
    """
    Specify a precondition that must hold when the function is called.

    Uses WhyML syntax. Examples:
        @requires("n >= 0")
        @requires("n >= 0 /\\ x >= 0")

    Args:
        spec: WhyML specification string

    Returns:
        Decorator that returns the original function
    """
    def decorator(func: F) -> F:
        return func
    return decorator


def ensures(spec: str) -> Callable[[F], F]:
    """
    Specify a postcondition that will hold when the function returns.

    Uses WhyML syntax. Examples:
        @ensures("result = n")
        @ensures("result = n * x /\\ result >= 0")

    Args:
        spec: WhyML specification string

    Returns:
        Decorator that returns the original function
    """
    def decorator(func: F) -> F:
        return func
    return decorator


def invariant(spec: str) -> Callable[[F], F]:
    """
    Specify a loop invariant that holds before and after each loop iteration.

    Uses WhyML syntax with !var for loop variables. Examples:
        @invariant("0 <= !i <= n")
        @invariant("!acc = !i * x")

    Args:
        spec: WhyML specification string

    Returns:
        Decorator that returns the original function
    """
    def decorator(func: F) -> F:
        return func
    return decorator


def variant(spec: str) -> Callable[[F], F]:
    """
    Specify a variant expression that decreases with each loop iteration.

    Used to prove loop termination. Examples:
        @variant("n - !i")
        @variant("len(arr) - !idx")

    Args:
        spec: WhyML specification string

    Returns:
        Decorator that returns the original function
    """
    def decorator(func: F) -> F:
        return func
    return decorator


# Convenience exports
__all__ = ['safe', 'requires', 'ensures', 'invariant', 'variant']
