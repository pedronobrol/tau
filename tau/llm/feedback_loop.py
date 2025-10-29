"""
LLM-powered feedback loop for automatic invariant generation and refinement.

Requires: anthropic package (optional)
Install: pip install anthropic
"""

import ast
import json
from typing import Dict, List, Optional, Any

from ..core.transpiler import transpile
from ..core.models import ExternalFunctionContract
from ..utils.verification import verify_with_why3


# Check if anthropic is available
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    # Create stub type for type hints
    class Anthropic:
        pass


# Prompts
SYSTEM_PROMPT = """You are a formal verification assistant.
Given a Python function and its specification (requires/ensures),
you must propose loop invariants and a variant expression for Why3.

CRITICAL: In WhyML, loop variables are refs. You MUST use !var to dereference them.
Example: if Python has "i = 0; while i < n", invariants must use "!i" not "i".

Output STRICT JSON ONLY:
{"invariants": [...], "variant": "..."}

Rules:
- Use !var for ALL loop variables in invariants (e.g., "0 <= !i", "!c = !i")
- Use !var in variant too (e.g., "n - !i")
- Parameters like "n" don't need ! (only loop-local mutable variables)
- Invariants should capture properties preserved by the loop
- Variant must be a nonnegative integer expression that decreases each iteration
- Do not add explanations, only JSON

Example:
Python: i = 0; while i < n: i = i + 1
Correct invariants: ["0 <= !i", "!i <= n"]
Wrong invariants: ["0 <= i", "i <= n"]
"""

REFINE_PROMPT = """You are a formal verification assistant refining loop invariants and variant.
Given:
- The Python function
- Its requires/ensures spec
- Current invariants and variant
- The Why3 prover output (some VCs failed)
You must propose revised invariants and variant that make the proof succeed.

CRITICAL: Loop variables are refs in WhyML. You MUST use !var to dereference them.
If Why3 says "unbound variable x", you need to use "!x" instead.

Output STRICT JSON ONLY:
{"invariants": [...], "variant": "..."}

Rules:
- Use !var for ALL loop-local mutable variables (e.g., "!i", "!c", "!s")
- Parameters don't need ! (e.g., "n" is OK as-is)
- Check Why3 errors: "unbound variable i" means use "!i"
- Strengthen invariants if Why3 can't prove postcondition
"""

BUG_DETECTION_PROMPT = """You are a code correctness analyzer.

Analyze if the given Python code matches its specification.

Given:
- Python function code
- Specification (requires/ensures)
- Optional: Why3 verification feedback

Your task:
1. Trace through the code mentally
2. Determine what the code ACTUALLY computes
3. Check if this matches the specification
4. Decide: Is this a bug, or just needs stronger invariants?

Output STRICT JSON ONLY in one of two forms:

If you detect a clear mismatch (bug):
{
  "bug_detected": true,
  "bug_type": "off_by_one|wrong_accumulator|missing_increment|wrong_initial|specification_error|other",
  "explanation": "Brief explanation of the bug",
  "actual_behavior": "What the code actually computes",
  "expected_behavior": "What the spec requires"
}

If code seems correct but verification failed (needs better invariants):
{
  "bug_detected": false,
  "analysis": "Why verification might have failed",
  "suggested_invariants": ["inv1", "inv2", ...]
}

Examples:

Example 1 - Off-by-one:
Code: while i <= n: c = c + 1; i = i + 1
Spec: ensures result = n
Analysis: Loop runs n+1 times (i goes 0,1,2,...,n), so c = n+1 at exit.
Output: {"bug_detected": true, "bug_type": "off_by_one", ...}

Example 2 - Needs invariants:
Code: while i < n: c = c + 1; i = i + 1
Spec: ensures result = n
Analysis: Loop runs n times (i goes 0,1,...,n-1), so c = n at exit. Matches spec!
Output: {"bug_detected": false, "suggested_invariants": ["0 <= !i <= n", "!c = !i"]}
"""


def _get_client(api_key: Optional[str] = None) -> Optional[Anthropic]:
    """Get Anthropic client if available"""
    if not ANTHROPIC_AVAILABLE:
        return None

    try:
        if api_key:
            return Anthropic(api_key=api_key)

        # Check if env var is actually set before creating client
        # The Anthropic() constructor succeeds even without API key,
        # but will fail on first API call
        import os
        if 'ANTHROPIC_API_KEY' in os.environ and os.environ['ANTHROPIC_API_KEY']:
            return Anthropic()

        # No API key available
        return None
    except Exception:
        return None


def _call_llm(client: Anthropic,
              prompt: str,
              user_data: dict,
              model: str = "claude-3-5-haiku-20241022",
              validate_schema: str = "invariants") -> Optional[dict]:
    """
    Call LLM and parse JSON response.

    Args:
        client: Anthropic client
        prompt: System prompt
        user_data: User data dict
        model: Model name
        validate_schema: Schema to validate ("invariants" or "bug_detection" or "none")

    Returns:
        Dict with response keys, or None on error
    """
    try:
        text_payload = json.dumps(user_data, ensure_ascii=False)

        resp = client.messages.create(
            model=model,
            max_tokens=600,
            temperature=0.2,
            messages=[{"role": "user", "content": f"{prompt}\n\n{text_payload}"}],
        )

        text = resp.content[0].text.strip()

        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None

        result = json.loads(text[start:end + 1])

        # Validate structure based on schema
        if validate_schema == "invariants":
            if not isinstance(result, dict) or "invariants" not in result or "variant" not in result:
                return None
            if not isinstance(result["invariants"], list) or not isinstance(result["variant"], str):
                return None
        elif validate_schema == "bug_detection":
            if not isinstance(result, dict) or "bug_detected" not in result:
                return None
        elif validate_schema == "none":
            if not isinstance(result, dict):
                return None
        # else: no validation

        return result
    except Exception as e:
        print(f"LLM call failed: {e}")
        return None


def _default_heuristic(fn_name: str, fn_source: str) -> dict:
    """Fallback heuristic for simple loop patterns"""
    source_clean = fn_source.replace(" ", "").replace("\n", " ")
    
    # Pattern: while i < n with c = c + 1
    if "whilei<n" in source_clean and "c=c+1" in source_clean:
        return {"invariants": ["0 <= !i <= n", "!c = !i"], "variant": "n - !i"}
    
    # Pattern: while i < n
    if "whilei<n" in source_clean:
        return {"invariants": ["0 <= !i <= n"], "variant": "n - !i"}
    
    # Pattern: while i <= n
    if "whilei<=n" in source_clean:
        return {"invariants": ["0 <= !i <= n + 1"], "variant": "n - !i"}
    
    return {"invariants": ["true"], "variant": "0"}

def propose_loop_contract(fn_name: str,
                          fn_source: str,
                          requires: str,
                          ensures: str,
                          client: Optional[Anthropic] = None,
                          api_key: Optional[str] = None) -> dict:
    """
    Propose initial loop invariants and variant.

    Args:
        fn_name: Function name
        fn_source: Python function source
        requires: Precondition
        ensures: Postcondition
        client: Optional Anthropic client
        api_key: Optional API key (if client not provided)

    Returns:
        Dict with 'invariants' (list) and 'variant' (str)
    """
    if client is None:
        client = _get_client(api_key)

    if client is None:
        print("⚠️  LLM not available, using heuristic")
        return _default_heuristic(fn_name, fn_source)

    result = _call_llm(
        client,
        SYSTEM_PROMPT,
        {
            "function_name": fn_name,
            "python_function": fn_source,
            "requires": requires,
            "ensures": ensures
        }
    )

    if result is None:
        print("⚠️  LLM call failed, using heuristic")
        return _default_heuristic(fn_name, fn_source)

    return result


def detect_bug(fn_name: str,
               fn_source: str,
               requires: str,
               ensures: str,
               why3_output: Optional[str] = None,
               client: Optional[Anthropic] = None,
               api_key: Optional[str] = None) -> Optional[dict]:
    """
    Analyze if code has a bug or just needs better invariants.

    Args:
        fn_name: Function name
        fn_source: Python function source
        requires: Precondition
        ensures: Postcondition
        why3_output: Optional Why3 verification output
        client: Optional Anthropic client
        api_key: Optional API key

    Returns:
        Dict with bug analysis or None if LLM unavailable
    """
    if client is None:
        client = _get_client(api_key)

    if client is None:
        return None

    user_data = {
        "function_name": fn_name,
        "python_function": fn_source,
        "requires": requires,
        "ensures": ensures
    }

    if why3_output:
        user_data["why3_output"] = why3_output[-2000:]  # Last 2KB

    result = _call_llm(client, BUG_DETECTION_PROMPT, user_data, validate_schema="bug_detection")

    if result is None:
        return None

    # Convert true/false string to boolean if needed
    if isinstance(result["bug_detected"], str):
        result["bug_detected"] = result["bug_detected"].lower() == "true"

    return result


def refine_loop_contract(fn_name: str,
                         fn_source: str,
                         current_contract: dict,
                         why3_output: str,
                         requires: str,
                         ensures: str,
                         client: Optional[Anthropic] = None,
                         api_key: Optional[str] = None) -> dict:
    """
    Refine loop contract based on Why3 feedback.

    Args:
        fn_name: Function name
        fn_source: Python function source
        current_contract: Current invariants/variant dict
        why3_output: Why3 verification output
        requires: Precondition
        ensures: Postcondition
        client: Optional Anthropic client
        api_key: Optional API key

    Returns:
        Refined dict with 'invariants' (list) and 'variant' (str)
    """
    if client is None:
        client = _get_client(api_key)

    if client is None:
        print("⚠️  LLM not available, keeping current contract")
        return current_contract

    result = _call_llm(
        client,
        REFINE_PROMPT,
        {
            "function_name": fn_name,
            "python_function": fn_source,
            "requires": requires,
            "ensures": ensures,
            "current_contract": current_contract,
            "why3_output": (why3_output or "")[-4000:]  # Last 4KB
        }
    )

    if result is None:
        print("⚠️  LLM refinement failed, keeping current contract")
        return current_contract

    return result


def feedback_loop_transpile(python_source: str,
                            base_meta: Dict[str, Dict[str, Any]],
                            target_function: str,
                            max_rounds: int = 3,
                            external_contracts: Optional[Dict[str, ExternalFunctionContract]] = None,
                            api_key: Optional[str] = None,
                            verify: bool = True) -> Dict:
    """
    Transpile with LLM-powered feedback loop.

    Automatically generates and refines loop invariants/variants using LLM,
    then verifies with Why3 and iterates until proof succeeds or max rounds reached.

    Args:
        python_source: Python function source
        base_meta: Base specifications (requires/ensures). Invariants/variant optional.
        target_function: Name of function to process
        max_rounds: Maximum refinement iterations
        external_contracts: Optional external function contracts
        api_key: Optional Anthropic API key
        verify: Whether to run Why3 verification

    Returns:
        Dict with:
            - why_file: Path to final WhyML file
            - lean_file: Path to Lean file
            - whyml_source: Final WhyML source
            - lean_source: Lean source
            - functions: Function contracts
            - rounds: List of dicts with history for each round
            - final_round: Number of final round
            - verified: Whether proof succeeded

    Example:
        >>> source = '''
        ... def sum_to(n: int) -> int:
        ...     s = 0
        ...     i = 0
        ...     while i <= n:
        ...         s = s + i
        ...         i = i + 1
        ...     return s
        ... '''
        >>> meta = {
        ...     "sum_to": {
        ...         "requires": "n >= 0",
        ...         "ensures": "result = div (n * (n + 1)) 2"
        ...     }
        ... }
        >>> result = feedback_loop_transpile(source, meta, "sum_to")
        >>> print(result['verified'])
        True
    """
    # Get LLM client
    client = _get_client(api_key)

    if client is None and verify:
        print("⚠️  Warning: LLM not available. Will use heuristics only.")

    # Parse to get function
    module_ast = ast.parse(python_source)
    fns = [n for n in module_ast.body if isinstance(n, ast.FunctionDef)]
    fn_node = next((f for f in fns if f.name == target_function), None)

    if fn_node is None:
        raise ValueError(f"Function {target_function} not found")

    fn_source = ast.get_source_segment(python_source, fn_node) or python_source

    # Get base specs
    fn_meta = base_meta.get(target_function, {})
    requires = fn_meta.get("requires", "true")
    ensures = fn_meta.get("ensures", "true")

    # Initialize meta with base specs
    meta = json.loads(json.dumps(base_meta))

    # If no invariants/variant provided, propose them
    if not meta[target_function].get("invariants") or not meta[target_function].get("variant"):
        print(f"🤖 Proposing initial loop contract for {target_function}...")
        proposal = propose_loop_contract(target_function, fn_source, requires, ensures, client, api_key)
        meta[target_function]["invariants"] = proposal.get("invariants", [])
        meta[target_function]["variant"] = proposal.get("variant", "0")
        print(f"   Invariants: {proposal['invariants']}")
        print(f"   Variant: {proposal['variant']}")

    # Feedback loop
    rounds = []
    verified = False

    for round_num in range(1, max_rounds + 1):
        print(f"\n🔄 Round {round_num}/{max_rounds}")

        base_name = f"{target_function}_round{round_num:02d}"

        # Transpile
        result = transpile(
            python_source,
            meta,
            external_contracts=external_contracts,
            base_name=base_name,
            verify=False  # We'll verify manually
        )

        # Verify if requested
        verification_output = None
        if verify:
            print(f"   Verifying with Why3...")
            verification_output = verify_with_why3(result['why_file'], prover="Alt-Ergo,2.6.2", timeout=10)

            # Check if verified
            if "Valid" in verification_output and "Prover result is: Valid" in verification_output:
                verified = True
                print(f"   ✅ Proof succeeded!")
            else:
                print(f"   ❌ Proof failed or timed out")

                # On first failure, check if it's a bug in the code
                if round_num == 1 and client:
                    print(f"   🔍 Analyzing if code matches specification...")
                    bug_analysis = detect_bug(
                        target_function, fn_source, requires, ensures,
                        verification_output, client, api_key
                    )

                    if bug_analysis and bug_analysis.get("bug_detected"):
                        print(f"   🐛 Bug detected: {bug_analysis.get('bug_type', 'unknown')}")
                        print(f"   📝 {bug_analysis.get('explanation', '')}")
                        print(f"   ⚠️  Skipping refinement - code appears to have a bug")
                        # Store bug analysis and stop trying
                        rounds.append({
                            "round": round_num,
                            "meta": json.loads(json.dumps(meta)),
                            "why_file": result['why_file'],
                            "lean_file": result['lean_file'],
                            "verification": verification_output,
                            "verified": False,
                            "bug_analysis": bug_analysis
                        })
                        break  # Don't waste time refining buggy code

                # Try to refine if not last round
                if round_num < max_rounds and client:
                    print(f"   🤖 Refining contract...")
                    current = {
                        "invariants": meta[target_function].get("invariants", []),
                        "variant": meta[target_function].get("variant", "")
                    }
                    refined = refine_loop_contract(
                        target_function, fn_source, current,
                        verification_output, requires, ensures,
                        client, api_key
                    )
                    meta[target_function]["invariants"] = refined["invariants"]
                    meta[target_function]["variant"] = refined["variant"]
                    print(f"   New invariants: {refined['invariants']}")
                    print(f"   New variant: {refined['variant']}")

        rounds.append({
            "round": round_num,
            "meta": json.loads(json.dumps(meta)),
            "why_file": result['why_file'],
            "lean_file": result['lean_file'],
            "verification": verification_output,
            "verified": verified
        })

        if verified:
            break

    # Return final result
    final_result = rounds[-1]
    return {
        "why_file": final_result['why_file'],
        "lean_file": final_result['lean_file'],
        "whyml_source": result['whyml_source'],
        "lean_source": result['lean_source'],
        "functions": result['functions'],
        "rounds": rounds,
        "final_round": len(rounds),
        "verified": verified
    }
