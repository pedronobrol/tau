#!/usr/bin/env python3
"""
Examples of buggy code that the LLM feedback loop catches

This demonstrates the full power of the LLM + formal verification system:
- We only provide requires/ensures (the spec)
- The LLM attempts to generate invariants
- Why3 verification fails, exposing the bug
- This shows the system detecting bugs automatically!
"""

import os
from tau.llm import feedback_loop_transpile

# Set API key from environment
# os.environ["ANTHROPIC_API_KEY"] = "your-api-key-here"


def example_off_by_one():
    """
    BUG: Off-by-one error in loop condition
    The loop should go from 0 to n-1, but goes to n
    """
    print("=" * 70)
    print("Example 1: Off-by-one Error")
    print("=" * 70)

    # BUGGY CODE - loop goes one iteration too far
    source = '''
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i <= n:  # BUG: should be i < n
        c = c + 1
        i = i + 1
    return c
'''

    # Only provide spec - let LLM try to generate invariants
    meta = {
        "count_to": {
            "requires": "n >= 0",
            "ensures": "result = n",  # Claims to return n (but code returns n+1)
        }
    }

    print("\nBuggy code:")
    print(source)
    print("\nSpecification: requires n >= 0, ensures result = n")
    print("Reality: Code returns n + 1 (off by one!)\n")
    print("🤖 Let's see if the LLM + Why3 catches this bug...\n")

    result = feedback_loop_transpile(
        source,
        meta,
        target_function="count_to",
        max_rounds=3,
        verify=True
    )

    print(f"\n{'='*70}")
    if result.get('verified'):
        print("❌ UNEXPECTED: Bug not caught! Verification passed.")
    else:
        print("✅ Bug detected by LLM + Why3!")
        print("\nThe system tried to verify but couldn't prove the postcondition")
        print("because the code actually returns n+1, not n!")

    return result


def example_wrong_accumulator():
    """
    BUG: Wrong accumulation formula
    Should add x once, but adds x twice
    """
    print("\n" + "=" * 70)
    print("Example 2: Wrong Accumulation")
    print("=" * 70)

    # BUGGY CODE - adds 2x instead of x
    source = '''
def multiply_n_times(x: int, n: int) -> int:
    acc = 0
    i = 0
    while i < n:
        acc = acc + x + x  # BUG: should be acc + x
        i = i + 1
    return acc
'''

    # Only provide spec
    meta = {
        "multiply_n_times": {
            "requires": "n >= 0",
            "ensures": "result = n * x",  # Claims n*x (but code does 2*n*x)
        }
    }

    print("\nBuggy code:")
    print(source)
    print("\nSpecification: result = n * x")
    print("Reality: Code computes 2 * n * x\n")
    print("🤖 Let's see if the LLM + Why3 catches this bug...\n")

    result = feedback_loop_transpile(
        source,
        meta,
        target_function="multiply_n_times",
        max_rounds=3,
        verify=True
    )

    print(f"\n{'='*70}")
    if result.get('verified'):
        print("❌ UNEXPECTED: Bug not caught!")
    else:
        print("✅ Bug detected by LLM + Why3!")
        print("\nThe invariant !acc = !i * x cannot be maintained")
        print("because the code does acc = acc + 2*x")

    return result


def example_missing_increment():
    """
    BUG: Forgot to increment loop counter (infinite loop)
    """
    print("\n" + "=" * 70)
    print("Example 3: Missing Increment (Infinite Loop)")
    print("=" * 70)

    # BUGGY CODE - forgot i = i + 1
    source = '''
def broken_count(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        # BUG: forgot i = i + 1
    return c
'''

    # Only provide spec
    meta = {
        "broken_count": {
            "requires": "n > 0",
            "ensures": "result = n",
        }
    }

    print("\nBuggy code:")
    print(source)
    print("\nBUG: Missing i = i + 1 causes infinite loop!")
    print("🤖 Let's see if the LLM + Why3 catches this bug...\n")

    result = feedback_loop_transpile(
        source,
        meta,
        target_function="broken_count",
        max_rounds=3,
        verify=True
    )

    print(f"\n{'='*70}")
    if result.get('verified'):
        print("❌ UNEXPECTED: Bug not caught!")
    else:
        print("✅ Bug detected by LLM + Why3!")
        print("\nThe variant doesn't decrease because !i never changes!")
        print("Why3 cannot prove termination.")

    return result


def example_wrong_initial_value():
    """
    BUG: Wrong initial value
    """
    print("\n" + "=" * 70)
    print("Example 4: Wrong Initial Value")
    print("=" * 70)

    # BUGGY CODE - starts at 1 instead of 0
    source = '''
def sum_to(n: int) -> int:
    s = 0
    i = 1  # BUG: should start at 0
    while i <= n:
        s = s + i
        i = i + 1
    return s
'''

    # Spec claims standard sum formula (which assumes starting from 0)
    meta = {
        "sum_to": {
            "requires": "n >= 0",
            "ensures": "result = div (n * (n + 1)) 2",
        }
    }

    print("\nBuggy code:")
    print(source)
    print("\nBUG: i starts at 1 instead of 0")
    print("Spec expects: sum from 0 to n = n*(n+1)/2")
    print("Code computes: sum from 1 to n = n*(n+1)/2 (correct for 1..n)")
    print("But missing the 0!\n")
    print("🤖 Let's see if the LLM + Why3 catches this bug...\n")

    result = feedback_loop_transpile(
        source,
        meta,
        target_function="sum_to",
        max_rounds=3,
        verify=True
    )

    print(f"\n{'='*70}")
    if result.get('verified'):
        print("❌ UNEXPECTED: Bug not caught!")
    else:
        print("✅ Bug detected by LLM + Why3!")
        print("\nThe LLM-generated invariants fail because i starts at 1, not 0")

    return result


def example_wrong_postcondition():
    """
    BUG: Code is correct but specification is wrong
    """
    print("\n" + "=" * 70)
    print("Example 5: Correct Code, Wrong Specification")
    print("=" * 70)

    # Correct code
    source = '''
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c
'''

    # BUGGY SPEC - claims result = n + 1
    meta = {
        "count_to": {
            "requires": "n >= 0",
            "ensures": "result = n + 1",  # BUG: should be result = n
        }
    }

    print("\nCode (correct):")
    print(source)
    print("\nBUGGY SPECIFICATION: claims result = n + 1")
    print("But code actually returns n\n")
    print("🤖 Let's see if the LLM + Why3 catches this spec error...\n")

    result = feedback_loop_transpile(
        source,
        meta,
        target_function="count_to",
        max_rounds=3,
        verify=True
    )

    print(f"\n{'='*70}")
    if result.get('verified'):
        print("❌ UNEXPECTED: Specification error not caught!")
    else:
        print("✅ Specification error detected by LLM + Why3!")
        print("\nThe postcondition result = n + 1 cannot be proven")
        print("because the code returns n")

    return result


def example_variable_confusion():
    """
    BUG: Using wrong variable (but happens to be correct)
    """
    print("\n" + "=" * 70)
    print("Example 6: Variable Confusion (Subtle)")
    print("=" * 70)

    # BUGGY CODE - returns i instead of c (but they're equal at end)
    source = '''
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return i  # BUG: returns i instead of c (but both equal n)
'''

    meta = {
        "count_to": {
            "requires": "n >= 0",
            "ensures": "result = n",
        }
    }

    print("\nBuggy code:")
    print(source)
    print("\nBUG: Returns i instead of c")
    print("In this case they're both n, so verification will PASS")
    print("This shows formal verification checks correctness, not intent!\n")
    print("🤖 Let's see what happens...\n")

    result = feedback_loop_transpile(
        source,
        meta,
        target_function="count_to",
        max_rounds=3,
        verify=True
    )

    print(f"\n{'='*70}")
    if result.get('verified'):
        print("✅ Verification passed (both i and c equal n)")
        print("\nThis demonstrates an important point:")
        print("Formal verification checks correctness, not developer intent!")
        print("If the code satisfies the spec (even accidentally), it passes.")
    else:
        print("❌ Verification failed")

    return result


def main():
    """Run all bug examples"""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "TAU - LLM-Powered Bug Detection Examples" + " " * 17 + "║")
    print("╚" + "=" * 68 + "╝\n")

    print("This demonstrates how the LLM + formal verification catches bugs!")
    print("We only provide requires/ensures - the system finds the bugs.\n")

    results = []

    try:
        results.append(("Off-by-one", example_off_by_one()))
        results.append(("Wrong accumulator", example_wrong_accumulator()))
        results.append(("Missing increment", example_missing_increment()))
        results.append(("Wrong initial value", example_wrong_initial_value()))
        results.append(("Wrong specification", example_wrong_postcondition()))
        results.append(("Variable confusion", example_variable_confusion()))

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        bugs_caught = 0
        for name, result in results:
            verified = result.get('verified', False)
            # For most examples, not verified = bug caught
            # Except variable confusion where we expect it to verify
            if name == "Variable confusion":
                if verified:
                    print(f"✅ {name:25} - Verified (as expected)")
                else:
                    print(f"⚠️  {name:25} - Failed unexpectedly")
            else:
                if not verified:
                    bugs_caught += 1
                    print(f"✅ {name:25} - Bug detected!")
                else:
                    print(f"❌ {name:25} - Bug not detected")

        print(f"\n{bugs_caught}/5 bugs successfully detected by LLM + formal verification!")
        print("(Variable confusion verified correctly as code matches spec)")

        print("\n" + "=" * 70)
        print("Key Insight:")
        print("=" * 70)
        print("The LLM + formal verification system automatically detects bugs!")
        print("\nYou only provide:")
        print("  • requires (precondition)")
        print("  • ensures (postcondition)")
        print("\nThe system:")
        print("  • Generates loop invariants (LLM)")
        print("  • Attempts verification (Why3)")
        print("  • Exposes bugs when proof fails")
        print("\nIf verification fails, either:")
        print("  1. Your code has a bug, or")
        print("  2. Your specification is wrong")
        print("\nEither way, you found a problem before it reached production!")

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
