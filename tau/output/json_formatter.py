"""
JSON output formatter for TAU verification results.
Generates comprehensive JSON with integrity hashing.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from tau.utils.hashing import ArtifactHasher


class VerificationJSONFormatter:
    """
    Formats verification results as structured JSON with integrity hashes.
    """

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, source_file: str, prover: str = "Alt-Ergo,2.6.2", timeout: int = 10):
        """
        Initialize formatter.

        Args:
            source_file: Path to the Python source file being verified
            prover: Why3 prover being used
            timeout: Prover timeout in seconds
        """
        self.source_file = source_file
        self.prover = prover
        self.timeout = timeout
        self.results: List[Dict[str, Any]] = []

    def add_result(self,
                   function_name: str,
                   line_number: int,
                   python_source: str,
                   verified: bool,
                   status: str,
                   reason: str,
                   duration: float,
                   specification: Dict[str, Any],
                   llm_info: Optional[Dict[str, Any]] = None,
                   bug_analysis: Optional[Dict[str, Any]] = None,
                   whyml_file: Optional[str] = None,
                   lean_file: Optional[str] = None) -> None:
        """
        Add a verification result for a function.

        Args:
            function_name: Name of the function
            line_number: Line number where function is defined
            python_source: Python source code of the function
            verified: Whether verification succeeded
            status: Status string ("passed", "failed", "error", etc.)
            reason: Human-readable reason for the result
            duration: Verification duration in seconds
            specification: Dict with requires, ensures, invariants, variant
            llm_info: Optional LLM usage information
            bug_analysis: Optional bug detection analysis
            whyml_file: Path to generated WhyML file
            lean_file: Path to generated Lean file
        """
        # Compute hashes
        python_hash = ArtifactHasher.hash_string(python_source)
        whyml_hash = ArtifactHasher.hash_file(whyml_file) if whyml_file else None
        lean_hash = ArtifactHasher.hash_file(lean_file) if lean_file else None

        # Compute combined hash
        combined_hash = None
        if python_hash and whyml_hash and lean_hash:
            combined_hash = ArtifactHasher.compute_combined_hash(
                python_hash, whyml_hash, lean_hash
            )

        result = {
            "function": {
                "name": function_name,
                "line": line_number,
                "source_hash": python_hash,
                "source_length": len(python_source)
            },
            "verification": {
                "verified": verified,
                "status": status,
                "reason": reason,
                "duration_seconds": round(duration, 2)
            },
            "specification": specification
        }

        # Add LLM info if available
        if llm_info:
            result["llm"] = llm_info

        # Add bug analysis if available
        if bug_analysis:
            result["bug_analysis"] = bug_analysis

        # Add artifacts section
        artifacts = {}
        if whyml_file:
            artifacts["whyml_file"] = whyml_file
            artifacts["whyml_hash"] = whyml_hash
        if lean_file:
            artifacts["lean_file"] = lean_file
            artifacts["lean_hash"] = lean_hash
            artifacts["lean_reconstruction"] = "template"  # Currently always template
        if combined_hash:
            artifacts["combined_hash"] = combined_hash

        if artifacts:
            result["artifacts"] = artifacts

        self.results.append(result)

    def generate(self) -> Dict[str, Any]:
        """
        Generate the complete JSON output structure.

        Returns:
            Dictionary representing the JSON structure
        """
        # Compute summary statistics
        total = len(self.results)
        passed = sum(1 for r in self.results if r["verification"]["verified"])
        failed = total - passed
        success_rate = passed / total if total > 0 else 0.0
        bugs_detected = sum(1 for r in self.results
                          if r.get("bug_analysis", {}).get("detected", False))

        return {
            "schema_version": self.SCHEMA_VERSION,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_file": self.source_file,
                "verifier_version": "tau-0.1.0",
                "prover": self.prover,
                "prover_timeout": self.timeout
            },
            "summary": {
                "total_functions": total,
                "passed": passed,
                "failed": failed,
                "success_rate": round(success_rate, 4),
                "bugs_detected": bugs_detected
            },
            "results": self.results
        }

    def to_json_string(self, indent: int = 2) -> str:
        """
        Generate JSON string.

        Args:
            indent: Number of spaces for indentation

        Returns:
            Formatted JSON string
        """
        return json.dumps(self.generate(), indent=indent)

    def save_to_file(self, output_path: str, indent: int = 2) -> None:
        """
        Save JSON to file.

        Args:
            output_path: Path to output JSON file
            indent: Number of spaces for indentation
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.generate(), f, indent=indent)
