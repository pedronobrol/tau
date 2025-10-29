"""
Lean theorem skeleton generation
"""

from typing import List
from ..core.models import FunctionContract
from ..core.config import WHY_TYPE_TO_LEAN


def generate_lean_theorems(functions: List[FunctionContract], module_name: str) -> str:
    """
    Generate Lean theorem skeletons from function contracts.

    Args:
        functions: List of function contracts
        module_name: Module name for comment

    Returns:
        Lean source code
    """
    lines = [
        f"-- Lean theorems for {module_name}",
        "set_option autoImplicit true",
        "set_option sorryPermitted true",
        ""
    ]

    for fn in functions:
        # Convert arguments to Lean syntax
        args = " ".join(
            f"({name} : {WHY_TYPE_TO_LEAN.get(typ, typ)})"
            for name, typ in fn.args
        )

        lines.extend([
            f"-- requires: {fn.requires}",
            f"-- ensures: {fn.ensures}",
            f"theorem {fn.name}_correct {args} : Prop := by",
            "  admit",
            ""
        ])

    return "\n".join(lines)
