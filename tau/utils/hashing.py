"""
Cryptographic hashing utilities for TAU verification artifacts.
Provides integrity checking for Python source, WhyML code, and Lean code.
"""

import hashlib
from typing import Optional


class ArtifactHasher:
    """
    Computes SHA-256 hashes for verification artifacts to ensure integrity.
    """

    @staticmethod
    def hash_string(content: str) -> str:
        """
        Compute SHA-256 hash of a string.

        Args:
            content: String to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def hash_file(file_path: str) -> Optional[str]:
        """
        Compute SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string, or None if file doesn't exist
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ArtifactHasher.hash_string(content)
        except (FileNotFoundError, IOError):
            return None

    @staticmethod
    def compute_combined_hash(python_hash: str, whyml_hash: str, lean_hash: str) -> str:
        """
        Compute combined hash from individual artifact hashes.
        This provides a quick integrity check for all three artifacts.

        Args:
            python_hash: SHA-256 hash of Python source
            whyml_hash: SHA-256 hash of WhyML code
            lean_hash: SHA-256 hash of Lean code

        Returns:
            Combined SHA-256 hash
        """
        combined = f"{python_hash}|{whyml_hash}|{lean_hash}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_integrity(json_result: dict,
                        python_source: str,
                        whyml_file: Optional[str] = None,
                        lean_file: Optional[str] = None) -> dict:
        """
        Verify the integrity of a JSON result against actual artifacts.

        Args:
            json_result: Function result dict from JSON output
            python_source: Python source code for the function
            whyml_file: Path to WhyML file (optional)
            lean_file: Path to Lean file (optional)

        Returns:
            Dictionary with verification results:
            {
                'valid': bool,
                'python_match': bool,
                'whyml_match': bool (or None if file not provided),
                'lean_match': bool (or None if file not provided),
                'combined_match': bool
            }
        """
        artifacts = json_result.get('artifacts', {})

        # Check Python source hash
        python_hash = ArtifactHasher.hash_string(python_source)
        python_match = python_hash == artifacts.get('source_hash')

        # Check WhyML hash
        whyml_match = None
        if whyml_file:
            whyml_hash = ArtifactHasher.hash_file(whyml_file)
            if whyml_hash:
                whyml_match = whyml_hash == artifacts.get('whyml_hash')

        # Check Lean hash
        lean_match = None
        if lean_file:
            lean_hash = ArtifactHasher.hash_file(lean_file)
            if lean_hash:
                lean_match = lean_hash == artifacts.get('lean_hash')

        # Check combined hash
        combined_hash = ArtifactHasher.compute_combined_hash(
            artifacts.get('source_hash', ''),
            artifacts.get('whyml_hash', ''),
            artifacts.get('lean_hash', '')
        )
        combined_match = combined_hash == artifacts.get('combined_hash')

        # Overall validity
        valid = python_match and combined_match
        if whyml_match is not None:
            valid = valid and whyml_match
        if lean_match is not None:
            valid = valid and lean_match

        return {
            'valid': valid,
            'python_match': python_match,
            'whyml_match': whyml_match,
            'lean_match': lean_match,
            'combined_match': combined_match
        }
