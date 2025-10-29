"""
Python statement translation to WhyML imperative code
"""

import ast
import textwrap
from typing import List, Set, Optional
from ..core.models import LoopContract
from .expressions import ExpressionTranslator


def indent_block(text: str, spaces: int = 2) -> str:
    """Indent a block of text"""
    return textwrap.indent(text, " " * spaces)


def translate_statements(statements: List[ast.stmt],
                         expr_translator: ExpressionTranslator,
                         loop_contract: Optional[LoopContract],
                         ref_vars: Set[str]) -> str:
    """
    Translate Python statements to WhyML imperative code.

    Handles:
    - Assignments (with refs)
    - If/else conditionals
    - While loops with invariants/variants
    - Return statements
    """
    lines = []
    used_while = False

    for stmt in statements:
        if isinstance(stmt, ast.Assign):
            if not (len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)):
                raise NotImplementedError("Only simple variable assignments supported")

            var_name = stmt.targets[0].id
            value = expr_translator.visit(stmt.value)

            if var_name in ref_vars:
                # Update existing ref
                lines.append(f"{var_name} := {value};")
            else:
                # Create new ref
                lines.append(f"let {var_name} = ref {value} in")
                ref_vars.add(var_name)

        elif isinstance(stmt, ast.If):
            condition = expr_translator.visit(stmt.test)
            then_body = translate_statements(stmt.body, expr_translator, loop_contract, ref_vars)

            if not stmt.orelse:
                raise NotImplementedError("Both if/else branches required")

            else_body = translate_statements(stmt.orelse, expr_translator, loop_contract, ref_vars)

            lines.append(
                f"if {condition} then (\n"
                f"{indent_block(then_body)}\n"
                f") else (\n"
                f"{indent_block(else_body)}\n"
                f")"
            )

        elif isinstance(stmt, ast.While):
            if used_while:
                raise NotImplementedError("Only one while loop per function supported")
            used_while = True

            condition = expr_translator.visit(stmt.test)
            body = translate_statements(stmt.body, expr_translator, loop_contract, ref_vars)

            # Build while loop with correct WhyML syntax: while cond do invariant/variant body done
            loop_parts = [f"while {condition} do"]

            # Add invariants and variant AFTER do
            if loop_contract:
                for invariant in loop_contract.invariants:
                    loop_parts.append(f"  invariant {{ {invariant} }}")
                if loop_contract.variant:
                    loop_parts.append(f"  variant {{ {loop_contract.variant} }}")

            # Add body and done
            loop_parts.append(indent_block(body))
            loop_parts.append("done;")

            lines.append("\n".join(loop_parts))

        elif isinstance(stmt, ast.Return):
            lines.append(expr_translator.visit(stmt.value))

        else:
            raise NotImplementedError(f"Unsupported statement: {type(stmt).__name__}")

    return "\n".join(lines)
