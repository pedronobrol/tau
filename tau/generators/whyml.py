"""
WhyML module generation
"""

import ast
from typing import Dict, List, Optional, Tuple
from ..core.models import FunctionContract, LoopContract, ExternalFunctionContract
from ..core.config import PY_TYPE_TO_WHY
from ..translators.expressions import ExpressionTranslator
from ..translators.statements import translate_statements, indent_block


def py_type_to_whyml(annotation: Optional[ast.expr]) -> str:
    """Convert Python type annotation to WhyML type"""
    if annotation is None:
        return "int"
    if isinstance(annotation, ast.Name):
        return PY_TYPE_TO_WHY.get(annotation.id, "int")
    return "int"


def generate_whyml_module(python_source: str,
                          function_meta: Dict[str, Dict],
                          external_contracts: Optional[Dict[str, ExternalFunctionContract]] = None,
                          module_name: Optional[str] = None) -> Tuple[str, List[FunctionContract], str]:
    """
    Generate WhyML module from Python source.

    Args:
        python_source: Python function source code
        function_meta: Specifications for each function
        external_contracts: External function contracts
        module_name: Optional module name

    Returns:
        (whyml_source, function_contracts, module_name)
    """
    # Parse Python source
    module_ast = ast.parse(python_source)
    function_defs = [node for node in module_ast.body if isinstance(node, ast.FunctionDef)]

    if not function_defs:
        raise ValueError("No functions found in source")

    # Collect function names
    known_functions = {fn.name for fn in function_defs}

    # Translate each function
    functions = []
    for fn_def in function_defs:
        # Parse arguments and return type
        args = [
            (arg.arg, py_type_to_whyml(arg.annotation))
            for arg in fn_def.args.args
        ]
        return_type = py_type_to_whyml(fn_def.returns)

        # Get specifications
        meta = function_meta.get(fn_def.name, {})
        requires = meta.get("requires", "true")
        ensures = meta.get("ensures", "true")
        invariants = meta.get("invariants", [])
        variant = meta.get("variant")

        # Create loop contract if needed
        loop = None
        if invariants or variant:
            loop = LoopContract(invariants=invariants, variant=variant)

        # Translate function body - create translator with ref_vars for this function
        ref_vars = set()
        expr_translator = ExpressionTranslator(known_functions, external_contracts, ref_vars)
        body = translate_statements(fn_def.body, expr_translator, loop, ref_vars)

        functions.append(FunctionContract(
            name=fn_def.name,
            args=args,
            return_type=return_type,
            requires=requires,
            ensures=ensures,
            loop=loop,
            body_expression=body
        ))

    # Generate module
    mod_name = module_name or f"M_{function_defs[0].name}"
    lines = [
        f"module {mod_name}",
        "use int.Int",
        "use bool.Bool",
        "use ref.Ref",
        "use int.ComputerDivision",
        ""
    ]

    # Add external function declarations
    if external_contracts:
        for ext_name, ext_spec in external_contracts.items():
            arg_sig = " ".join(f"({name}:{typ})" for name, typ in ext_spec.args)
            lines.extend([
                f"val {ext_name} {arg_sig} : {ext_spec.return_type}",
                f"  requires {{ {ext_spec.requires} }}",
                f"  ensures  {{ {ext_spec.ensures} }}",
                ""
            ])

    # Add function definitions
    for fn in functions:
        arg_sig = " ".join(f"({name}:{typ})" for name, typ in fn.args)
        lines.extend([
            f"let {fn.name} {arg_sig} : {fn.return_type} =",
            f"  requires {{ {fn.requires} }}",
            f"  ensures  {{ {fn.ensures} }}",
            indent_block(fn.body_expression),
            ""
        ])

    lines.append("end")

    return "\n".join(lines), functions, mod_name
