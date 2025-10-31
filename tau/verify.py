"""
TAU verification library.
Main API for verifying @safe decorated functions.
"""

import time
from typing import List, Dict, Any, Optional

from tau.parser import SafeFunctionParser
from tau.llm import feedback_loop_transpile
from tau import transpile
from tau.output import VerificationJSONFormatter
from tau.proofs import compute_function_hash


class VerificationResult:
    """Result of verifying a single function"""

    def __init__(self, name: str, lineno: int):
        self.name = name
        self.lineno = lineno
        self.verified = False
        self.reason = ""
        self.used_llm = False
        self.bug_type = None
        # Additional fields for JSON output
        self.python_source = ""
        self.duration = 0.0
        self.specification = {}
        self.llm_info = None
        self.bug_analysis = None
        self.whyml_file = None
        self.lean_file = None
        self.hash = None  # Function semantic hash

    def __repr__(self):
        status = "✅ PASS" if self.verified else "❌ FAIL"
        return f"{status} {self.name}:{self.lineno} - {self.reason}"


class VerificationSummary:
    """Summary of verification results for a file"""

    def __init__(self, filename: str):
        self.filename = filename
        self.results: List[VerificationResult] = []

    def add_result(self, result: VerificationResult):
        self.results.append(result)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.verified)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.verified)

    def print_summary(self):
        """Print formatted summary"""
        print("\n" + "=" * 80)
        print(f"VERIFICATION SUMMARY: {self.filename}")
        print("=" * 80)

        if not self.results:
            print("⚠️  No @safe decorated functions found")
            return

        print(f"\nTotal functions analyzed: {self.total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success rate: {self.passed}/{self.total} ({100*self.passed//self.total if self.total > 0 else 0}%)")

        print("\n" + "-" * 80)
        print("DETAILED RESULTS")
        print("-" * 80)

        for result in self.results:
            print(f"\n{result}")
            if result.used_llm:
                print(f"   🤖 Used LLM to generate invariants")
            if result.bug_type:
                print(f"   🐛 Bug type: {result.bug_type}")

        print("\n" + "=" * 80)


def verify_function(func_info: Dict[str, Any], api_key: str = None, verbose: bool = False) -> VerificationResult:
    """
    Verify a single function.

    Args:
        func_info: Dict with function info from parser
        api_key: Optional Anthropic API key
        verbose: Print verbose output

    Returns:
        VerificationResult
    """
    result = VerificationResult(func_info["name"], func_info["lineno"])
    result.python_source = func_info["source"]

    start_time = time.time()

    try:
        # Check if auto_mode is enabled (@safe_auto decorator)
        auto_mode = func_info.get("auto_mode", False)

        # If auto_mode, generate requires/ensures specs first
        if auto_mode:
            if verbose:
                print(f"\n🤖 Auto-generating specifications for {func_info['name']}...")

            # Import spec generator and models
            from tau.llm.spec_generator import generate_specifications_sync
            from tau.server.models import FunctionInfo
            import ast

            # Parse function to extract details for FunctionInfo
            try:
                tree = ast.parse(func_info["source"])
                func_node = tree.body[0]

                # Extract parameters
                params = [(arg.arg, None) for arg in func_node.args.args]

                # Extract return type if annotated
                return_type = None
                if func_node.returns and isinstance(func_node.returns, ast.Name):
                    return_type = func_node.returns.id

                # Check if has loop
                has_loop = any(isinstance(n, ast.While) for n in ast.walk(func_node))

                # Build signature
                param_str = ", ".join(f"{name}" for name, _ in params)
                sig = f"def {func_info['name']}({param_str})"
                if return_type:
                    sig += f" -> {return_type}"

                # Create FunctionInfo object
                function_info_obj = FunctionInfo(
                    name=func_info["name"],
                    source=func_info["source"],
                    line_number=func_info.get("lineno", 1),
                    signature=sig,
                    has_loop=has_loop,
                    parameters=params,
                    return_type=return_type
                )

                # Generate specs from function info
                spec_result = generate_specifications_sync(
                    function_info=function_info_obj,
                    api_key=api_key
                )
            except Exception as e:
                if verbose:
                    print(f"   Error parsing function: {e}")
                result.verified = False
                result.reason = f"Auto-generation failed: Could not parse function - {e}"
                result.duration = time.time() - start_time
                return result

            if spec_result and spec_result.requires and spec_result.ensures:
                # Use generated specs (join list of clauses with /\)
                func_info["requires"] = " /\\ ".join(spec_result.requires)
                func_info["ensures"] = " /\\ ".join(spec_result.ensures)

                if verbose:
                    print(f"   Generated @requires: {func_info['requires']}")
                    print(f"   Generated @ensures: {func_info['ensures']}")
                    if spec_result.confidence:
                        print(f"   Confidence: {spec_result.confidence}")
                    if spec_result.reasoning:
                        print(f"   Reasoning: {spec_result.reasoning}")
            else:
                # Spec generation failed
                result.verified = False
                result.reason = "Auto-generation failed: Could not generate specifications"
                result.duration = time.time() - start_time
                return result

        # Prepare metadata
        meta = {
            func_info["name"]: {
                "requires": func_info["requires"],
                "ensures": func_info["ensures"]
            }
        }

        # Build specification dict for JSON
        result.specification = {
            "requires": func_info["requires"],
            "ensures": func_info["ensures"],
            "invariants": func_info["invariants"],
            "variant": func_info["variant"]
        }

        # If invariants/variant provided, use manual mode
        if func_info["invariants"] is not None or func_info["variant"] is not None:
            if verbose:
                print(f"\n📝 Verifying {func_info['name']} (manual mode)...")

            # Add invariants and variant
            if func_info["invariants"]:
                meta[func_info["name"]]["invariants"] = func_info["invariants"]
            if func_info["variant"]:
                meta[func_info["name"]]["variant"] = func_info["variant"]

            # Transpile and verify
            transpile_result = transpile(
                func_info["source"],
                meta,
                base_name=func_info["name"],
                verify=True
            )

            # Capture file paths
            result.whyml_file = transpile_result.get("why_file")
            result.lean_file = transpile_result.get("lean_file")

            verification_output = transpile_result.get("verification", "")

            if "Valid" in verification_output and "Prover result is: Valid" in verification_output:
                result.verified = True
                result.reason = "Proof succeeded with provided invariants"
            else:
                result.verified = False
                result.reason = "Proof failed with provided invariants"

        else:
            # Use LLM feedback loop
            if verbose:
                print(f"\n🤖 Verifying {func_info['name']} (LLM mode)...")

            result.used_llm = True

            transpile_result = feedback_loop_transpile(
                func_info["source"],
                meta,
                target_function=func_info["name"],
                max_rounds=3,
                api_key=api_key,
                verify=True
            )

            # Capture file paths
            result.whyml_file = transpile_result.get("why_file")
            result.lean_file = transpile_result.get("lean_file")

            result.verified = transpile_result.get("verified", False)

            # Capture LLM info
            rounds = transpile_result.get("rounds", [])
            if rounds:
                result.llm_info = {
                    "used": True,
                    "model": "claude-3-5-haiku-20241022",
                    "rounds": transpile_result.get("final_round", len(rounds)),
                    "total_attempts": len(rounds)
                }

            if result.verified:
                result.reason = f"Proof succeeded (LLM generated invariants in {transpile_result.get('final_round', 0)} rounds)"
                # Update specification with generated invariants
                if rounds and rounds[-1].get("invariants"):
                    result.specification["invariants"] = rounds[-1]["invariants"]
                if rounds and rounds[-1].get("variant"):
                    result.specification["variant"] = rounds[-1]["variant"]
            else:
                # Check if bug was detected
                if rounds and rounds[0].get("bug_analysis"):
                    bug_analysis = rounds[0]["bug_analysis"]
                    result.reason = f"Bug detected: {bug_analysis.get('explanation', 'unknown')}"
                    result.bug_type = bug_analysis.get("bug_type", "unknown")
                    result.bug_analysis = {
                        "detected": True,
                        "bug_type": bug_analysis.get("bug_type", "unknown"),
                        "explanation": bug_analysis.get("explanation", "unknown"),
                        "confidence": bug_analysis.get("confidence", 0.0)
                    }
                else:
                    result.reason = "Proof failed (could not generate valid invariants)"

    except Exception as e:
        result.verified = False
        result.reason = f"Error: {str(e)}"

    result.duration = time.time() - start_time

    # Compute semantic hash of function + specs
    try:
        hash_info = {
            "name": func_info["name"],
            "source": func_info["source"],
            "requires": result.specification.get("requires", ""),
            "ensures": result.specification.get("ensures", ""),
            "invariants": result.specification.get("invariants", []),
            "variant": result.specification.get("variant", "")
        }
        result.hash = compute_function_hash(hash_info)
    except Exception as e:
        if verbose:
            print(f"⚠️  Could not compute hash: {e}")
        result.hash = None

    return result


def verify_file(file_path: str, api_key: str = None, verbose: bool = False,
                json_output: Optional[str] = None, prover: str = "Alt-Ergo,2.6.2",
                timeout: int = 10) -> VerificationSummary:
    """
    Verify all @safe decorated functions in a file.

    Args:
        file_path: Path to Python file
        api_key: Optional Anthropic API key
        verbose: Print verbose output
        json_output: Optional path to save JSON output
        prover: Why3 prover to use
        timeout: Prover timeout in seconds

    Returns:
        VerificationSummary
    """
    summary = VerificationSummary(file_path)

    # Parse file
    parser = SafeFunctionParser()
    functions = parser.parse_file(file_path)

    if verbose:
        print(f"\n🔍 Found {len(functions)} @safe decorated functions")

    # Verify each function
    for func_info in functions:
        result = verify_function(func_info, api_key, verbose)
        summary.add_result(result)

    # Generate JSON output if requested
    if json_output:
        formatter = VerificationJSONFormatter(file_path, prover, timeout)

        for result in summary.results:
            formatter.add_result(
                function_name=result.name,
                line_number=result.lineno,
                python_source=result.python_source,
                verified=result.verified,
                status="passed" if result.verified else "failed",
                reason=result.reason,
                duration=result.duration,
                specification=result.specification,
                llm_info=result.llm_info,
                bug_analysis=result.bug_analysis,
                whyml_file=result.whyml_file,
                lean_file=result.lean_file
            )

        formatter.save_to_file(json_output)

        if verbose:
            print(f"\n💾 JSON output saved to: {json_output}")

    return summary
