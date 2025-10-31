#!/usr/bin/env python3
"""
TAU Demo - Automated formal verification with decorators.
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from tau.verify import verify_file


def main():
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "TAU - Formal Verification Demo" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Check if API key is available
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

    if has_api_key:
        print("✅ Anthropic API key detected - LLM mode enabled")
    else:
        print("⚠️  No API key - using heuristics only")
        print("   Set ANTHROPIC_API_KEY in .env for LLM auto-generation")

    print()
    print("Verifying examples/safe_functions.py...")
    print()

    # Verify the example file
    try:
        results = verify_file(
            "examples/safe_functions.py",
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            verbose=True,
            json_output="verification_results.json"
        )

        # Print summary
        results.print_summary()

        # Exit with appropriate code
        sys.exit(0 if results.failed == 0 else 1)

    except FileNotFoundError:
        print("❌ Error: examples/safe_functions.py not found")
        print()
        print("Please run this script from the repository root:")
        print("  python3 demo.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
