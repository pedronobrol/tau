# Decorator-Based Verification API

## Overview

The easiest way to use TAU is with the `@safe` decorator system. Mark functions for verification, and run batch verification on entire files.

## Quick Start

### 1. Mark Functions with @safe

```python
# mycode.py
from tau.decorators import safe, requires, ensures, invariant, variant

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
```

### 2. Run Verification

```bash
python3 verify_safe.py mycode.py
```

### 3. See Results

```
================================================================================
VERIFICATION SUMMARY: mycode.py
================================================================================

Total functions analyzed: 1
✅ Passed: 1
❌ Failed: 0
Success rate: 1/1 (100%)

--------------------------------------------------------------------------------
DETAILED RESULTS
--------------------------------------------------------------------------------

✅ PASS count_to:7 - Proof succeeded with provided invariants

================================================================================
```

## Decorators

### @safe

Marks a function for formal verification. Must be the **outermost** decorator.

```python
@safe
def my_function(...):
    ...
```

### @requires(condition)

Specifies a precondition in WhyML syntax. Can use multiple times.

```python
@safe
@requires("n >= 0")
@requires("x > 0")
def foo(n: int, x: int) -> int:
    ...
```

Multiple `@requires` are combined with `/\` (logical AND).

### @ensures(condition)

Specifies a postcondition in WhyML syntax. Can use multiple times.

```python
@safe
@requires("n >= 0")
@ensures("result >= 0")
@ensures("result = n * 2")
def double(n: int) -> int:
    ...
```

Multiple `@ensures` are combined with `/\` (logical AND).

### @invariant(condition) [Optional]

Specifies a loop invariant. Can use multiple times for multiple invariants.

```python
@safe
@requires("n >= 0")
@ensures("result = n")
@invariant("0 <= !i <= n")  # Bounds
@invariant("!c = !i")        # Relationship
def count_to(n: int) -> int:
    ...
```

**If omitted, the LLM will automatically generate invariants!**

### @variant(expression) [Optional]

Specifies a termination variant (expression that decreases each iteration).

```python
@safe
@requires("n >= 0")
@ensures("result = n")
@invariant("0 <= !i <= n")
@variant("n - !i")  # Decreases from n to 0
def count_to(n: int) -> int:
    ...
```

**If omitted, the LLM will automatically generate the variant!**

## Automatic Invariant Generation

If you omit `@invariant` and `@variant`, TAU uses the LLM feedback loop to automatically generate them:

```python
@safe
@requires("n >= 0")
@ensures("result = n * x")
def multiply(x: int, n: int) -> int:
    """No invariants specified - LLM will generate them!"""
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result
```

**Verification:**
```bash
$ python3 verify_safe.py mycode.py

🤖 Proposing initial loop contract for multiply...
   Invariants: ['0 <= !i', '!i <= n', '!result = !i * x']
   Variant: n - !i

🔄 Round 1/3
   Verifying with Why3...
   ✅ Proof succeeded!

✅ PASS multiply:15 - Proof succeeded (LLM generated invariants in 1 rounds)
   🤖 Used LLM to generate invariants
```

## Bug Detection

TAU automatically detects bugs through failed verification:

```python
@safe
@requires("n >= 0")
@ensures("result = n")
def buggy_count(n: int) -> int:
    """BUG: Off-by-one error!"""
    c = 0
    i = 0
    while i <= n:  # Should be i < n
        c = c + 1
        i = i + 1
    return c
```

**Verification:**
```bash
$ python3 verify_safe.py mycode.py

🔍 Analyzing if code matches specification...
🐛 Bug detected: off_by_one
📝 The loop runs n+1 times instead of n times due to the condition i <= n

❌ FAIL buggy_count:25 - Bug detected: Loop runs n+1 times instead of n
   🤖 Used LLM to generate invariants
   🐛 Bug type: off_by_one
```

## Command Line Usage

### Basic Verification

```bash
python3 verify_safe.py myfile.py
```

### With API Key

```bash
# Pass directly
python3 verify_safe.py myfile.py --api-key sk-ant-...

# Or use environment variable
export ANTHROPIC_API_KEY=sk-ant-...
python3 verify_safe.py myfile.py
```

### Verbose Mode

```bash
python3 verify_safe.py myfile.py --verbose
```

Shows detailed progress for each function.

### Exit Codes

- `0` - All functions verified successfully
- `1` - One or more functions failed verification

## Complete Example

```python
# safe_math.py
from tau.decorators import safe, requires, ensures, invariant, variant

# Example 1: Manual invariants (most control)
@safe
@requires("n >= 0")
@ensures("result = n")
@invariant("0 <= !i <= n")
@invariant("!c = !i")
@variant("n - !i")
def count_to(n: int) -> int:
    c = 0
    i = 0
    while i < n:
        c = c + 1
        i = i + 1
    return c


# Example 2: Auto-generated invariants (easier)
@safe
@requires("n >= 0")
@ensures("result = n * x")
def multiply(x: int, n: int) -> int:
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result


# Example 3: No loops (trivial)
@safe
@requires("lo <= hi")
@ensures("(x < lo -> result = lo) /\\ (x > hi -> result = hi)")
def clamp(x: int, lo: int, hi: int) -> int:
    if x < lo:
        return lo
    elif x > hi:
        return hi
    else:
        return x


# Example 4: Multiple preconditions/postconditions
@safe
@requires("n >= 0")
@requires("x >= 0")
@ensures("result >= 0")
@ensures("result = n * x")
def multiply_positive(x: int, n: int) -> int:
    result = 0
    i = 0
    while i < n:
        result = result + x
        i = i + 1
    return result


# Regular function (NOT verified)
def helper(x: int) -> int:
    """This function won't be verified - no @safe decorator"""
    return x + 1
```

**Verify:**
```bash
$ python3 verify_safe.py safe_math.py

================================================================================
VERIFICATION SUMMARY: safe_math.py
================================================================================

Total functions analyzed: 4
✅ Passed: 4
❌ Failed: 0
Success rate: 4/4 (100%)

--------------------------------------------------------------------------------
DETAILED RESULTS
--------------------------------------------------------------------------------

✅ PASS count_to:7 - Proof succeeded with provided invariants

✅ PASS multiply:24 - Proof succeeded (LLM generated invariants in 1 rounds)
   🤖 Used LLM to generate invariants

✅ PASS clamp:38 - Proof succeeded (LLM generated invariants in 1 rounds)
   🤖 Used LLM to generate invariants

✅ PASS multiply_positive:54 - Proof succeeded (LLM generated invariants in 1 rounds)
   🤖 Used LLM to generate invariants

================================================================================
```

## WhyML Syntax Reference

### Basic Operators

- **Arithmetic**: `+`, `-`, `*`, `div`, `mod`
- **Comparison**: `=`, `<>`, `<`, `<=`, `>`, `>=`
- **Logic**: `/\` (and), `\/` (or), `->` (implies), `not`
- **Refs**: `!var` (dereference), `:=` (assignment)

### Common Patterns

**Bounds invariant:**
```python
@invariant("0 <= !i <= n")
```

**Equality invariant:**
```python
@invariant("!result = !i * x")
```

**Implication:**
```python
@ensures("x < lo -> result = lo")
```

**Conjunction:**
```python
@requires("n >= 0 /\\ x >= 0")
```

**Mathematical formula:**
```python
@ensures("result = div (n * (n + 1)) 2")
```

## Tips

1. **Start simple** - Use `@safe` with `@requires`/`@ensures` first, let LLM generate invariants
2. **Test manually** - If LLM struggles, add `@invariant`/`@variant` manually
3. **Use verbose mode** - Add `--verbose` to see what's happening
4. **Check bug reports** - Failed verification often reveals actual bugs!
5. **Iterate** - Refine specifications based on verification feedback

## Troubleshooting

### "No @safe decorated functions found"

Make sure you're importing decorators:
```python
from tau.decorators import safe, requires, ensures
```

### "LLM not available"

Set your API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or the system will fall back to heuristics.

### "Proof failed with provided invariants"

Your invariants may be incorrect. Try:
1. Remove `@invariant`/`@variant` to let LLM generate them
2. Check the generated WhyML in `why_out/`
3. Manually verify with: `why3 prove why_out/yourfile.why`

### "Bug detected"

This means your code doesn't match its specification! Check:
1. Is the bug type correct? (off_by_one, wrong_accumulator, etc.)
2. Does your code actually implement what `@ensures` claims?
3. Are your loop bounds correct?

## Comparison

| Mode | Control | Effort | LLM Required |
|------|---------|--------|--------------|
| Manual `@invariant` | Full | High | No |
| Auto `@safe` only | Medium | Low | Yes |
| Heuristic fallback | Low | Low | No |

## See Also

- [Main README](README.md) - Other ways to use TAU
- [Bug Detection Examples](examples/safe_functions.py) - More examples
- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Technical details
