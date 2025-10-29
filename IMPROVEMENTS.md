# LLM Feedback Loop - Analysis and Improvements

## Current Performance: 4-5/6 bugs detected (80-83%)

## Issues Analysis

### Issue 1: LLM Cannot Distinguish "Bug in Code" vs "Need Stronger Invariants"

**Problem:** When Why3 fails, the LLM doesn't know if:
1. The code has a bug (and will NEVER verify)
2. The invariants are too weak (and need strengthening)

**Current Behavior:**
- LLM keeps refining invariants for 3 rounds
- Wastes time trying to prove buggy code
- Eventually fails, which correctly identifies the bug
- But doesn't give clear feedback about WHY it failed

**Example - Off-by-one Bug:**
```python
while i <= n:  # Should be i < n
    c = c + 1
    i = i + 1
# Spec: result = n
# Code returns: n + 1
```

LLM generates: `["0 <= !i", "!i <= n", "!c = !i"]`

These invariants are actually CORRECT for the code! But they prove `!c = n+1`, not `!c = n`.

Why3 fails on the postcondition: `result = n` cannot be proven because `result = !c = n+1`.

**The system works correctly** - it detects the bug - but it's not efficient.

### Issue 2: Complex Mathematical Invariants

**Problem:** Some bugs require sophisticated mathematical reasoning.

**Example - Wrong Initial Value:**
```python
s = 0
i = 1  # BUG: should be 0
while i <= n:
    s = s + i
    i = i + 1
# Spec: result = n*(n+1)/2  (sum from 0 to n)
# Code: computes sum from 1 to n = n*(n+1)/2
```

Wait, both equal `n*(n+1)/2`! But sum(0..n) = 0 + 1 + ... + n, while sum(1..n) = 1 + ... + n.

Actually sum(1..n) = n*(n+1)/2 - 0 = n*(n+1)/2, so they're NOT equal when n >= 0.

**The issue:** The LLM needs to generate:
```
!s = div ((!i - 1) * !i) 2
```

But this formula is only correct when starting from i=0! When i=1 initially, the invariant is false at loop entry.

**Why it's hard:**
- Requires precise mathematical reasoning
- LLM may generate approximately correct invariants
- But Why3 needs exact mathematical proofs
- Small errors in formulas cause verification to fail

### Issue 3: Limited Why3 Feedback Quality

**Problem:** Why3 output is often cryptic.

**Example Why3 Output:**
```
Prover result is: Timeout (5.00s)
```

This doesn't tell the LLM:
- Which specific verification condition (VC) failed
- Whether it's the invariant preservation, the postcondition, or the variant
- What values caused the failure

**Better feedback would be:**
```
VC "postcondition": Unknown
  Cannot prove: result = n
  Loop exit gives: !c = n + 1
```

But Why3 doesn't provide this level of detail in standard output.

## Proposed Improvements

### Improvement 1: Add Counterexample Generation

**Idea:** Use Why3's counterexample mode to get concrete values.

```bash
why3 prove file.why --prover "Alt-Ergo,2.6.2 (counterexamples)" -t 5
```

This can show:
```
Counterexample for postcondition:
  n = 3
  result = 4  (but spec requires result = 3)
```

**Implementation:**
```python
def verify_with_counterexamples(why_file: str, prover: str = "Alt-Ergo", timeout: int = 5):
    """Try to generate counterexamples on verification failure"""
    # First try normal verification
    result = verify_with_why3(why_file, prover, timeout)

    if "Valid" in result:
        return result, None

    # On failure, try counterexample mode
    ce_prover = f"{prover} (counterexamples)"
    ce_result = verify_with_why3(why_file, ce_prover, timeout)

    return result, ce_result
```

### Improvement 2: Teach LLM to Detect Impossible Proofs

**Idea:** Add a "code analysis" phase before refinement.

**New Prompt:**
```
Given the Python code and the spec, analyze:
1. What does the code ACTUALLY compute?
2. Does this match the specification?
3. If not, respond: {"bug": true, "analysis": "..."}
4. If yes, respond: {"bug": false, "invariants": [...], "variant": "..."}
```

**Example:**
```python
# Code
while i <= n:
    c = c + 1
    i = i + 1

# LLM Analysis:
# Loop runs from i=0 to i=n (inclusive), so n+1 iterations
# Therefore c = n + 1 at exit
# But spec says result = n
# CONCLUSION: Bug in code (off by one) OR bug in spec
```

### Improvement 3: Increase Max Rounds & Use Smarter Refinement

**Current:** 3 rounds max, each round tries random refinements

**Improvement:**
- Increase to 5 rounds
- Add structured refinement strategies:
  1. Round 1: Basic invariants
  2. Round 2: Add bounds invariants
  3. Round 3: Add relational invariants
  4. Round 4: Add mathematical invariants
  5. Round 5: Try weakest precondition analysis

### Improvement 4: Extract More Info from Why3

**Parse Why3 output to identify:**
```python
def parse_why3_output(output: str) -> dict:
    """Extract structured information from Why3 output"""
    result = {
        "valid": "Valid" in output,
        "timeout": "Timeout" in output,
        "unknown": "Unknown" in output,
        "failed_vcs": []
    }

    # Parse for specific VCs
    if "postcondition" in output.lower():
        result["failed_vcs"].append("postcondition")
    if "invariant" in output.lower():
        result["failed_vcs"].append("invariant")
    if "variant" in output.lower():
        result["failed_vcs"].append("variant")

    return result
```

### Improvement 5: Use Stronger LLM Model

**Current:** Claude 3.5 Haiku (fast, cheap, but less capable)

**Options:**
- Claude 3.5 Sonnet (better reasoning)
- Claude Opus (best reasoning, slower, expensive)
- GPT-4 (different reasoning style)

**Trade-offs:**
- Haiku: $0.0005/function, 2-5s
- Sonnet: $0.003/function, 5-10s
- Opus: $0.015/function, 10-20s

### Improvement 6: Hybrid Approach

**Idea:** Combine multiple strategies:

1. **First:** Try heuristics (instant, free)
2. **Second:** Try fast LLM (Haiku, 2s, cheap)
3. **Third:** If fails, try stronger LLM (Sonnet, 10s, moderate cost)
4. **Fourth:** If fails, try code analysis to detect obvious bugs
5. **Fifth:** Report failure with detailed analysis

## Implementation Priority

### High Priority (Would significantly improve detection rate)

1. ✅ **Counterexample generation** - Gives concrete feedback
2. ✅ **Bug detection mode** - LLM analyzes if code matches spec
3. ✅ **Better Why3 output parsing** - More structured feedback

### Medium Priority (Would improve user experience)

4. **Increase rounds to 5** - More attempts
5. **Use Sonnet for refinement** - Better reasoning
6. **Structured refinement strategies** - Systematic approach

### Low Priority (Diminishing returns)

7. **Hybrid model approach** - Complex but only marginal gains
8. **Custom SMT tactics** - Requires deep Why3 expertise

## Expected Impact

With improvements 1-3 implemented:
- **Current:** 4-5/6 bugs (80-83%)
- **Expected:** 5-6/6 bugs (90-100%)

The main remaining challenge would be bugs requiring very sophisticated mathematical reasoning that even stronger LLMs struggle with.

## Recommended Next Steps

1. Implement counterexample mode in verification
2. Add "bug detection" phase to LLM prompts
3. Parse Why3 output for structured feedback
4. Test on bug examples
5. Measure improvement in detection rate
