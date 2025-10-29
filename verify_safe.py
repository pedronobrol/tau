#!/usr/bin/env python3
"""
Verify @safe decorated functions in Python files.

Usage:
    python3 verify_safe.py myfile.py
    python3 verify_safe.py myfile.py --api-key sk-...
    python3 verify_safe.py myfile.py --verbose
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from tau.parser import SafeFunctionParser
from tau.llm import feedback_loop_transpile
from tau import transpile


class VerificationResult:
    """Result of verifying a single function"""

    def __init__(self, name: str, lineno: int):
        self.name = name
        self.lineno = lineno
        self.verified = False
        self.reason = ""
        self.used_llm = False
        self.bug_type = None

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

    try:
        # Prepare metadata
        meta = {
            func_info["name"]: {
                "requires": func_info["requires"],
                "ensures": func_info["ensures"]
            }
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

            result.verified = transpile_result.get("verified", False)

            if result.verified:
                result.reason = f"Proof succeeded (LLM generated invariants in {transpile_result.get('final_round', 0)} rounds)"
            else:
                # Check if bug was detected
                rounds = transpile_result.get("rounds", [])
                if rounds and rounds[0].get("bug_analysis"):
                    bug_analysis = rounds[0]["bug_analysis"]
                    result.reason = f"Bug detected: {bug_analysis.get('explanation', 'unknown')}"
                    result.bug_type = bug_analysis.get("bug_type", "unknown")
                else:
                    result.reason = "Proof failed (could not generate valid invariants)"

    except Exception as e:
        result.verified = False
        result.reason = f"Error: {str(e)}"

    return result


def verify_file(file_path: str, api_key: str = None, verbose: bool = False) -> VerificationSummary:
    """
    Verify all @safe decorated functions in a file.

    Args:
        file_path: Path to Python file
        api_key: Optional Anthropic API key
        verbose: Print verbose output

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

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Verify @safe decorated functions in Python files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Verify file with manual invariants
    python3 verify_safe.py examples/safe_functions.py

    # Verify file with LLM (requires API key)
    python3 verify_safe.py examples/safe_functions.py --api-key sk-...

    # Use API key from environment
    export ANTHROPIC_API_KEY=sk-...
    python3 verify_safe.py examples/safe_functions.py --verbose
        """
    )

    parser.add_argument("file", help="Python file to verify")
    parser.add_argument("--api-key", help="Anthropic API key (or use ANTHROPIC_API_KEY env var)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Check file exists
    if not Path(args.file).exists():
        print(f"❌ Error: File not found: {args.file}")
        sys.exit(1)

    # Get API key
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")

    # Verify file
    summary = verify_file(args.file, api_key, args.verbose)

    # Print summary
    summary.print_summary()

    # Exit with appropriate code
    sys.exit(0 if summary.failed == 0 else 1)


if __name__ == "__main__":
    main()
