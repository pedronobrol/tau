"""
TAU Proof Certificate System

This module manages proof certificates for verified functions, enabling:
- Fast lookup of previously verified functions
- Sharing verification proofs across team members
- Complete auditability of formal verification results
"""

from tau.proofs.hasher import compute_function_hash, compute_body_hash
from tau.proofs.manager import ProofCertificateManager

__all__ = ['compute_function_hash', 'compute_body_hash', 'ProofCertificateManager']
