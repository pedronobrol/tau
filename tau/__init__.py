"""
Tau: Python to WhyML Formal Verification Transpiler
"""

from .core.models import LoopContract, ExternalFunctionContract, FunctionContract
from .core.transpiler import transpile

__version__ = "0.1.0"
__all__ = [
    "transpile",
    "LoopContract",
    "ExternalFunctionContract",
    "FunctionContract"
]
