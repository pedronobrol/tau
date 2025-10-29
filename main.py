#!/usr/bin/env python3
"""
Tau CLI - Python to WhyML Transpiler
"""

from tau import transpile, ExternalFunctionContract


def example_clamp():
    """Example: Clamp function with nested conditionals"""
    print("\n" + "="*70)
    print("Example 1: Clamp Function")
    print("="*70)

    source = '''
def clamp(x: int, lo: int, hi: int) -> int:
    t = x
    if t < lo:
        return lo
    else:
        if t > hi:
            return hi
        else:
            return t
'''

    meta = {
        "clamp": {
            "requires": "lo <= hi",
            "ensures": "(x < lo -> result = lo) /\\ "
                      "(x > hi -> result = hi) /\\ "
                      "(lo <= x /\\ x <= hi -> result = x)"
        }
    }

    result = transpile(source, meta, base_name="clamp")

    print(f"\nGenerated files:")
    print(f"  WhyML: {result['why_file']}")
    print(f"  Lean:  {result['lean_file']}")
    print(f"\nWhyML source:\n{result['whyml_source']}")

    return result


def example_sum_to():
    """Example: Sum with loop invariants"""
    print("\n" + "="*70)
    print("Example 2: Sum To N (with loop)")
    print("="*70)

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
            "ensures": "result = div (n * (n + 1)) 2",
            "invariants": [
                "0 <= !i",
                "!i <= n + 1",
                "!s = div (!i * (!i - 1)) 2"
            ],
            "variant": "n - !i"
        }
    }

    result = transpile(source, meta, base_name="sum_to")

    print(f"\nGenerated files:")
    print(f"  WhyML: {result['why_file']}")
    print(f"  Lean:  {result['lean_file']}")
    print(f"\nWhyML source:\n{result['whyml_source']}")

    return result


def example_factorial():
    """Example: Factorial with loop"""
    print("\n" + "="*70)
    print("Example 3: Factorial")
    print("="*70)

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
            "ensures": "result >= 1",
            "invariants": [
                "1 <= !i",
                "!i <= n + 1",
                "!result >= 1"
            ],
            "variant": "n - !i + 1"
        }
    }

    result = transpile(source, meta, base_name="factorial")

    print(f"\nGenerated files:")
    print(f"  WhyML: {result['why_file']}")
    print(f"  Lean:  {result['lean_file']}")
    print(f"\nWhyML source:\n{result['whyml_source']}")

    return result


def example_external_contract():
    """Example: Function with external dependency"""
    print("\n" + "="*70)
    print("Example 4: External Function Contract")
    print("="*70)

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

    result = transpile(source, meta, external_contracts=external_contracts, base_name="norm1")

    print(f"\nGenerated files:")
    print(f"  WhyML: {result['why_file']}")
    print(f"  Lean:  {result['lean_file']}")
    print(f"\nWhyML source:\n{result['whyml_source']}")

    return result


def main():
    """Run all examples"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*20 + "TAU - Python to WhyML" + " "*27 + "║")
    print("╚" + "="*68 + "╝")

    results = []

    try:
        results.append(example_clamp())
        results.append(example_sum_to())
        results.append(example_factorial())
        results.append(example_external_contract())

        print("\n" + "="*70)
        print("✓ All examples completed successfully!")
        print(f"✓ Generated {len(results) * 2} files in ./why_out/")
        print("="*70)

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
