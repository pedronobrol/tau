"""
Python AST expression translation to WhyML
"""

import ast
from typing import Dict, Set, Optional
from ..core.config import BIN_OP_TO_WHY, CMP_OP_TO_WHY
from ..core.models import ExternalFunctionContract


class ExpressionTranslator(ast.NodeVisitor):
    """Translates Python expressions to WhyML syntax"""

    def __init__(self,
                 known_functions: Set[str],
                 external_contracts: Optional[Dict[str, ExternalFunctionContract]] = None,
                 ref_vars: Optional[Set[str]] = None):
        self.known_functions = known_functions
        self.external_contracts = external_contracts or {}
        self.ref_vars = ref_vars if ref_vars is not None else set()

    def visit_Name(self, node: ast.Name) -> str:
        # Dereference if it's a ref variable
        if node.id in self.ref_vars:
            return f"!{node.id}"
        return node.id

    def visit_Constant(self, node: ast.Constant) -> str:
        if isinstance(node.value, bool):
            return "true" if node.value else "false"
        if isinstance(node.value, str):
            return f'"{node.value}"'
        return str(node.value)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return f"(-{operand})"
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.Not):
            return f"(not {operand})"
        raise NotImplementedError(f"Unsupported unary operator: {type(node.op).__name__}")

    def visit_BinOp(self, node: ast.BinOp) -> str:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = BIN_OP_TO_WHY.get(type(node.op))
        if not op:
            raise NotImplementedError(f"Unsupported binary operator: {type(node.op).__name__}")
        return f"({left} {op} {right})"

    def visit_BoolOp(self, node: ast.BoolOp) -> str:
        op = "and" if isinstance(node.op, ast.And) else "or"
        parts = [self.visit(v) for v in node.values]
        return "(" + f" {op} ".join(parts) + ")"

    def visit_Compare(self, node: ast.Compare) -> str:
        if not (len(node.ops) == 1 and len(node.comparators) == 1):
            raise NotImplementedError("Chained comparisons not supported")

        left = self.visit(node.left)
        right = self.visit(node.comparators[0])
        op = CMP_OP_TO_WHY.get(type(node.ops[0]))

        if not op:
            raise NotImplementedError(f"Unsupported comparison: {type(node.ops[0]).__name__}")

        return f"({left} {op} {right})"

    def visit_IfExp(self, node: ast.IfExp) -> str:
        test = self.visit(node.test)
        body = self.visit(node.body)
        orelse = self.visit(node.orelse)
        return f"(if {test} then {body} else {orelse})"

    def visit_Call(self, node: ast.Call) -> str:
        if not isinstance(node.func, ast.Name):
            raise NotImplementedError("Only simple function calls supported")

        callee = node.func.id
        if callee not in self.known_functions and callee not in self.external_contracts:
            raise NotImplementedError(f"Unknown function: {callee}")

        args = ", ".join(self.visit(arg) for arg in node.args)
        return f"{callee}({args})"

    def generic_visit(self, node: ast.AST) -> str:
        raise NotImplementedError(f"Unsupported expression: {type(node).__name__}")
