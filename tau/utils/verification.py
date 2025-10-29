"""
Why3 verification utilities
"""

import subprocess
from typing import Optional


def verify_with_why3(why_file: str,
                     prover: str = "Alt-Ergo,2.6.2",
                     timeout: int = 10) -> str:
    """
    Run Why3 prover on a WhyML file.

    Args:
        why_file: Path to .why file
        prover: Prover name (default: Alt-Ergo,2.6.2)
        timeout: Timeout in seconds

    Returns:
        Verification output
    """
    try:
        result = subprocess.run(
            ["why3", "prove", why_file, "--prover", prover, "-t", str(timeout)],
            capture_output=True,
            text=True,
            timeout=timeout + 5
        )
        return result.stdout + result.stderr
    except FileNotFoundError:
        return "Why3 not found. Install with: opam install why3"
    except subprocess.TimeoutExpired:
        return f"Why3 verification timed out after {timeout}s"
    except Exception as e:
        return f"Why3 error: {e}"
