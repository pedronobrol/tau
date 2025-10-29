"""
Data models for function contracts and specifications
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class LoopContract:
    """Loop invariants and termination variant"""
    invariants: List[str]
    variant: Optional[str]


@dataclass
class ExternalFunctionContract:
    """Contract for external/library functions"""
    args: List[Tuple[str, str]]  # [(name, type)]
    return_type: str
    requires: str
    ensures: str


@dataclass
class FunctionContract:
    """Complete function specification with body"""
    name: str
    args: List[Tuple[str, str]]
    return_type: str
    requires: str
    ensures: str
    loop: Optional[LoopContract]
    body_expression: str
