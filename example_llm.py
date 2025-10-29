#!/usr/bin/env python3
"""
Example: LLM-powered automatic invariant generation

This demonstrates the feedback loop where an LLM (Claude) automatically
generates and refines loop invariants based on Why3 verification feedback.

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here
"""

import os
import sys

# Check if anthropic is available
try:
    import anthropic
    print("✓ Anthropic SDK found")
except ImportError:
    print("✗ Anthropic SDK not found")
    print("  Install with: pip install anthropic")
    sys.exit(1)

# Check for API key
if not os.getenv("ANTHROPIC_API_KEY"):
    print("✗ ANTHROPIC_API_KEY not set")
    print("  Set with: export ANTHROPIC_API_KEY=your_key_here")
    sys.exit(1)

print("✓ API key found\n")

from tau.llm import feedback_loop_transpile


def example_sum_to():
    """
    Example: Auto-generate invariants for sum_to function
    """
    print("=" * 70)
    print("Example: Sum To N (LLM-powered)")
    print("=" * 70)

    source = '''
def sum_to(n: int) -> int:
    s = 0
    i = 0
    while i <= n:
        s = s + i
        i = i + 1
    return s
'''

    # Only provide requires/ensures, let LLM propose invariants/variant
    meta = {
        "sum_to": {
            "requires": "n >= 0",
            "ensures": "result = div (n * (n + 1)) 2"
        }
    }

    print("\nInput function:")
    print(source)
    print("\nBase specification:")
    print(f"  requires: {meta['sum_to']['requires']}")
    print(f"  ensures:  {meta['sum_to']['ensures']}")
    print("\n" + "-" * 70)

    # Run feedback loop
    result = feedback_loop_transpile(
        source,
        meta,
        target_function="sum_to",
        max_rounds=3,
        verify=True
    )

    print("\n" + "=" * 70)
    print("Results:")
    print("=" * 70)
    print(f"Rounds: {result['final_round']}")
    print(f"Verified: {'✅ Yes' if result['verified'] else '❌ No'}")

    print("\nFinal contract:")
    final_meta = result['rounds'][-1]['meta']['sum_to']
    print(f"  Invariants:")
    for inv in final_meta['invariants']:
        print(f"    - {inv}")
    print(f"  Variant: {final_meta['variant']}")

    print(f"\nGenerated files:")
    print(f"  WhyML: {result['why_file']}")
    print(f"  Lean:  {result['lean_file']}")

    if result['verified']:
        print("\n🎉 Successfully verified with Why3!")
    else:
        print("\n⚠️  Could not verify within max rounds")

    return result


def example_factorial():
    """
    Example: Auto-generate invariants for factorial
    """
    print("\n\n" + "=" * 70)
    print("Example: Factorial (LLM-powered)")
    print("=" * 70)

    source = '''
def factorial(n: int) -> int:
    result = 1
    i = 1
    while i <= n:
        result = result * i
        i = i + 1
    return result
'''

    meta = {
        "factorial": {
            "requires": "n >= 0",
            "ensures": "result >= 1"  # Simple spec for demo
        }
    }

    print("\nInput function:")
    print(source)
    print("\nBase specification:")
    print(f"  requires: {meta['factorial']['requires']}")
    print(f"  ensures:  {meta['factorial']['ensures']}")
    print("\n" + "-" * 70)

    result = feedback_loop_transpile(
        source,
        meta,
        target_function="factorial",
        max_rounds=3,
        verify=True
    )

    print("\n" + "=" * 70)
    print("Results:")
    print("=" * 70)
    print(f"Rounds: {result['final_round']}")
    print(f"Verified: {'✅ Yes' if result['verified'] else '❌ No'}")

    print("\nFinal contract:")
    final_meta = result['rounds'][-1]['meta']['factorial']
    print(f"  Invariants:")
    for inv in final_meta['invariants']:
        print(f"    - {inv}")
    print(f"  Variant: {final_meta['variant']}")

    return result


def example_count_to():
    """
    Example: Simple counter (should verify quickly)
    """
    print("\n\n" + "=" * 70)
    print("Example: Count To (LLM-powered)")
    print("=" * 70)

    source = '''
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c
'''

    meta = {
        "count_to": {
            "requires": "n >= 0",
            "ensures": "result = n"
        }
    }

    print("\nInput function:")
    print(source)
    print("\n" + "-" * 70)

    result = feedback_loop_transpile(
        source,
        meta,
        target_function="count_to",
        max_rounds=2,
        verify=True
    )

    print("\n" + "=" * 70)
    print(f"Verified: {'✅ Yes' if result['verified'] else '❌ No'}")
    print("=" * 70)

    return result


def main():
    """Run all LLM examples"""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "TAU - LLM-Powered Verification" + " " * 22 + "║")
    print("╚" + "=" * 68 + "╝\n")

    try:
        # Run examples
        example_count_to()   # Simple, should verify quickly
        example_sum_to()     # More complex
        # example_factorial()  # Uncomment if you want to try this one

        print("\n" + "=" * 70)
        print("✓ All examples completed!")
        print("=" * 70)

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
