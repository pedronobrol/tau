"""
Type mappings and configuration constants
"""

import ast

# Operator mappings
BIN_OP_TO_WHY = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "div",
    ast.Mod: "mod"
}

CMP_OP_TO_WHY = {
    ast.Eq: "=",
    ast.NotEq: "<>",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">="
}

# Type mappings
PY_TYPE_TO_WHY = {
    "int": "int",
    "bool": "bool",
    "float": "real",
    "Nat": "int"
}

WHY_TYPE_TO_LEAN = {
    "int": "Int",
    "bool": "Bool",
    "real": "Real"
}
