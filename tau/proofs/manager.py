"""
Proof Certificate Manager - handles storage and retrieval of verification results.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from .hasher import compute_function_hash, compute_body_hash, compute_source_hash


class ProofCertificateManager:
    """
    Manages proof certificates: storing, retrieving, and validating cached verification results.
    """

    def __init__(self, proofs_dir: str = "proofs"):
        """
        Initialize the proof certificate manager.

        Args:
            proofs_dir: Root directory for proof certificates (default: "proofs")
        """
        self.proofs_dir = Path(proofs_dir)
        self.config_path = self.proofs_dir / "config.json"
        self.index_path = self.proofs_dir / "index.json"
        self.artifacts_dir = self.proofs_dir / "artifacts"
        self.whyml_dir = self.proofs_dir / "whyml"
        self.lean_dir = self.proofs_dir / "lean"
        self.logs_dir = self.proofs_dir / "logs"

        self._ensure_directories()
        self.config = self._load_config()
        self.index = self._load_index()

    def _ensure_directories(self) -> None:
        """Create proof directories if they don't exist."""
        for directory in [
            self.proofs_dir,
            self.artifacts_dir,
            self.whyml_dir,
            self.lean_dir,
            self.logs_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}

    def _load_index(self) -> Dict[str, Any]:
        """Load proof index from index.json."""
        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                index = json.load(f)
                # Migrate schema if needed (backward compatibility)
                if "body_index" not in index:
                    index["body_index"] = {}
                    index["schema_version"] = "2.0.0"
                return index
        return {
            "schema_version": "2.0.0",  # Bumped for body_hash support
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "entries": {},
            "body_index": {},  # Maps body_hash -> list of full hashes
            "stats": {
                "total_entries": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_size_bytes": 0,
                "last_cleanup": datetime.utcnow().isoformat() + "Z"
            }
        }

    def _save_index(self) -> None:
        """Save proof index to index.json."""
        self.index["last_updated"] = datetime.utcnow().isoformat() + "Z"
        print(f"[ProofManager DEBUG] Saving index to {self.index_path}")
        print(f"[ProofManager DEBUG] Total entries: {len(self.index['entries'])}")
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f, indent=2)
        print(f"[ProofManager DEBUG] Index saved successfully")

    def lookup_proof(self, func_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Look up a cached proof certificate for a function.

        Args:
            func_info: Function information (name, source, specs)

        Returns:
            Proof certificate if found and valid, None otherwise
        """
        # Compute function hash
        func_hash = compute_function_hash(func_info)

        # Check if proof exists in index
        if func_hash not in self.index["entries"]:
            self.index["stats"]["cache_misses"] += 1
            self._save_index()
            return None

        entry = self.index["entries"][func_hash]

        # Validate proof certificate still exists
        artifacts_path = self.artifacts_dir / f"{func_hash}.json"
        if not artifacts_path.exists():
            # Entry exists but artifact is missing - clean up
            del self.index["entries"][func_hash]
            self.index["stats"]["total_entries"] -= 1
            self._save_index()
            return None

        # Load and return proof certificate
        with open(artifacts_path, 'r') as f:
            certificate = json.load(f)

        # Update access time and stats
        entry["last_accessed"] = datetime.utcnow().isoformat() + "Z"
        entry["access_count"] = entry.get("access_count", 0) + 1
        self.index["stats"]["cache_hits"] += 1
        self._save_index()

        return certificate

    def store_proof(
        self,
        func_info: Dict[str, Any],
        verified: bool,
        whyml_code: Optional[str] = None,
        lean_code: Optional[str] = None,
        why3_output: Optional[str] = None,
        reason: Optional[str] = None,
        duration: Optional[float] = None
    ) -> str:
        """
        Store a proof certificate after verification.

        Args:
            func_info: Function information (name, source, specs)
            verified: Whether verification passed
            whyml_code: Generated WhyML code
            lean_code: Generated Lean code
            why3_output: Raw Why3 verification output
            reason: Failure reason if verification failed
            duration: Verification duration in seconds

        Returns:
            Function hash (proof certificate ID)
        """
        print(f"[ProofManager DEBUG] store_proof called for {func_info.get('name', 'unknown')}")
        print(f"[ProofManager DEBUG] verified={verified}, has_whyml={whyml_code is not None}, has_lean={lean_code is not None}")

        # Compute all three hashes for proper auditing
        func_hash = compute_function_hash(func_info)       # AST-based semantic (cache lookup)
        source_hash = compute_source_hash(func_info)       # Exact source (auditing)
        body_hash = compute_body_hash(func_info)           # AST-based body-only (find similar)
        timestamp = datetime.utcnow().isoformat() + "Z"

        print(f"[ProofManager DEBUG] Computed hashes - func: {func_hash[:8]}, source: {source_hash[:8]}, body: {body_hash[:8]}")

        # Create proof certificate with full audit trail
        certificate = {
            # Primary hash for cache lookups (AST-based, semantic)
            "hash": func_hash,

            # Exact source hash for auditing (changes with any text modification)
            "source_hash": source_hash,

            # Body-only semantic hash for finding same function with different specs
            "body_hash": body_hash,

            "function_name": func_info["name"],
            "verified": verified,
            "timestamp": timestamp,
            "reason": reason,
            "duration": duration,

            # Store original source code for reproducibility and auditing
            "source_code": func_info["source"],

            "specs": {
                "requires": func_info.get("requires", ""),
                "ensures": func_info.get("ensures", ""),
                "invariants": func_info.get("invariants", []),
                "variant": func_info.get("variant", "")
            }
        }

        # Save WhyML code if provided
        if whyml_code:
            whyml_path = self.whyml_dir / f"{func_hash}.mlw"
            with open(whyml_path, 'w') as f:
                f.write(whyml_code)
            certificate["whyml_file"] = str(whyml_path.relative_to(self.proofs_dir))

        # Save Lean code if provided
        if lean_code:
            lean_path = self.lean_dir / f"{func_hash}.lean"
            with open(lean_path, 'w') as f:
                f.write(lean_code)
            certificate["lean_file"] = str(lean_path.relative_to(self.proofs_dir))

        # Save Why3 output log
        if why3_output:
            log_path = self.logs_dir / f"{func_hash}.log"
            with open(log_path, 'w') as f:
                f.write(why3_output)
            certificate["log_file"] = str(log_path.relative_to(self.proofs_dir))

        # Save certificate artifact
        artifacts_path = self.artifacts_dir / f"{func_hash}.json"
        with open(artifacts_path, 'w') as f:
            json.dump(certificate, f, indent=2)

        # Update index
        is_new_entry = func_hash not in self.index["entries"]

        self.index["entries"][func_hash] = {
            "function_name": func_info["name"],
            "verified": verified,
            "body_hash": body_hash,  # Store body_hash in index entry
            "created_at": timestamp,
            "last_accessed": timestamp,
            "access_count": 0,
            "artifact_file": str(artifacts_path.relative_to(self.proofs_dir))
        }

        # Update body_index: map body_hash -> list of full hashes
        if body_hash not in self.index["body_index"]:
            self.index["body_index"][body_hash] = []

        if func_hash not in self.index["body_index"][body_hash]:
            self.index["body_index"][body_hash].append(func_hash)

        if is_new_entry:
            self.index["stats"]["total_entries"] += 1

        self._save_index()
        self._update_cache_size()

        return func_hash

    def invalidate_proof(self, func_hash: str) -> bool:
        """
        Invalidate and delete a proof certificate.

        Args:
            func_hash: Function hash to invalidate

        Returns:
            True if proof was found and deleted, False otherwise
        """
        if func_hash not in self.index["entries"]:
            return False

        # Get body_hash before removing entry
        entry = self.index["entries"][func_hash]
        body_hash = entry.get("body_hash")

        # Delete artifact files
        artifacts_path = self.artifacts_dir / f"{func_hash}.json"
        whyml_path = self.whyml_dir / f"{func_hash}.mlw"
        lean_path = self.lean_dir / f"{func_hash}.lean"
        log_path = self.logs_dir / f"{func_hash}.log"

        for path in [artifacts_path, whyml_path, lean_path, log_path]:
            if path.exists():
                path.unlink()

        # Remove from body_index
        if body_hash and body_hash in self.index["body_index"]:
            if func_hash in self.index["body_index"][body_hash]:
                self.index["body_index"][body_hash].remove(func_hash)
            # Clean up empty body_hash entries
            if not self.index["body_index"][body_hash]:
                del self.index["body_index"][body_hash]

        # Remove from index
        del self.index["entries"][func_hash]
        self.index["stats"]["total_entries"] -= 1
        self._save_index()
        self._update_cache_size()

        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get proof cache statistics.

        Returns:
            Statistics dictionary with hits, misses, size, etc.
        """
        return self.index["stats"].copy()

    def clear_all(self) -> None:
        """Clear all proof certificates (dangerous!)."""
        # Delete all artifacts
        for directory in [self.artifacts_dir, self.whyml_dir, self.lean_dir, self.logs_dir]:
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)

        # Reset index
        self.index["entries"] = {}
        self.index["stats"] = {
            "total_entries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_size_bytes": 0,
            "last_cleanup": datetime.utcnow().isoformat() + "Z"
        }
        self._save_index()

    def _update_cache_size(self) -> None:
        """Update cache size statistics."""
        total_size = 0
        for directory in [self.artifacts_dir, self.whyml_dir, self.lean_dir, self.logs_dir]:
            if directory.exists():
                for path in directory.rglob('*'):
                    if path.is_file():
                        total_size += path.stat().st_size

        self.index["stats"]["cache_size_bytes"] = total_size
        self._save_index()

    def cleanup_old_proofs(self, max_age_days: Optional[int] = None) -> int:
        """
        Clean up old proof certificates based on age.

        Args:
            max_age_days: Maximum age in days (uses config if not specified)

        Returns:
            Number of proofs deleted
        """
        if max_age_days is None:
            max_age_days = self.config.get("max_age_days", 365)

        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        deleted = 0
        to_delete = []

        for func_hash, entry in self.index["entries"].items():
            created = datetime.fromisoformat(entry["created_at"].replace("Z", ""))
            if created < cutoff:
                to_delete.append(func_hash)

        for func_hash in to_delete:
            if self.invalidate_proof(func_hash):
                deleted += 1

        self.index["stats"]["last_cleanup"] = datetime.utcnow().isoformat() + "Z"
        self._save_index()

        return deleted

    def list_proofs(self, verified_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all proof certificates.

        Args:
            verified_only: Only return verified proofs

        Returns:
            List of proof certificate summaries
        """
        results = []
        for func_hash, entry in self.index["entries"].items():
            if verified_only and not entry["verified"]:
                continue

            results.append({
                "hash": func_hash,
                "function_name": entry["function_name"],
                "verified": entry["verified"],
                "created_at": entry["created_at"],
                "last_accessed": entry["last_accessed"],
                "access_count": entry["access_count"]
            })

        return sorted(results, key=lambda x: x["created_at"], reverse=True)

    def find_proofs_by_body(self, func_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all cached proofs for the same function body (ignoring specs).

        This is used to detect when a function's implementation matches a previously
        verified version, but with different specifications. Allows suggesting cached
        specs to the user.

        Args:
            func_info: Function information (name, source) - specs are ignored

        Returns:
            List of proof certificates with same body, sorted by timestamp (newest first)
        """
        body_hash = compute_body_hash(func_info)

        # Check if this body hash exists
        if body_hash not in self.index["body_index"]:
            return []

        # Get all full hashes for this body
        full_hashes = self.index["body_index"][body_hash]

        # Load certificates for each hash
        results = []
        for func_hash in full_hashes:
            # Load certificate
            artifacts_path = self.artifacts_dir / f"{func_hash}.json"
            if not artifacts_path.exists():
                continue

            with open(artifacts_path, 'r') as f:
                certificate = json.load(f)

            # Get index entry for metadata
            if func_hash in self.index["entries"]:
                entry = self.index["entries"][func_hash]
                results.append({
                    "hash": func_hash,
                    "body_hash": body_hash,
                    "function_name": certificate["function_name"],
                    "verified": certificate["verified"],
                    "specs": certificate["specs"],
                    "timestamp": certificate["timestamp"],
                    "reason": certificate.get("reason"),
                    "created_at": entry["created_at"],
                    "last_accessed": entry["last_accessed"]
                })

        # Sort by timestamp (newest first)
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)
