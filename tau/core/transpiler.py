"""
Main transpilation pipeline
"""

from typing import Dict, Optional
from .models import ExternalFunctionContract
from ..generators.whyml import generate_whyml_module
from ..generators.lean import generate_lean_theorems
from ..utils.files import save_artifacts
from ..utils.verification import verify_with_why3


def transpile(python_source: str,
              function_meta: Dict[str, Dict],
              external_contracts: Optional[Dict[str, ExternalFunctionContract]] = None,
              module_name: Optional[str] = None,
              base_name: Optional[str] = None,
              verify: bool = False) -> Dict:
    """
    Transpile Python to WhyML and Lean.

    Args:
        python_source: Python function(s) source code
        function_meta: Specifications for each function:
            {
                "func_name": {
                    "requires": "precondition",
                    "ensures": "postcondition",
                    "invariants": ["inv1", ...],  # optional
                    "variant": "termination_expr"  # optional
                }
            }
        external_contracts: Optional external function contracts
        module_name: Optional WhyML module name
        base_name: Optional output file base name
        verify: Whether to run Why3 verification

    Returns:
        Dict with:
            - why_file: Path to WhyML file
            - lean_file: Path to Lean file
            - whyml_source: WhyML source code
            - lean_source: Lean source code
            - functions: List of FunctionContract objects
            - verification: Verification output (if verify=True)

    Raises:
        ValueError: If no functions found or invalid syntax
        NotImplementedError: If unsupported Python constructs used
    """
    # Generate WhyML
    whyml_source, functions, mod_name = generate_whyml_module(
        python_source,
        function_meta,
        external_contracts,
        module_name
    )

    # Generate Lean
    lean_source = generate_lean_theorems(functions, mod_name)

    # Save files
    why_path, lean_path = save_artifacts(whyml_source, lean_source, base_name)

    result = {
        "why_file": why_path,
        "lean_file": lean_path,
        "whyml_source": whyml_source,
        "lean_source": lean_source,
        "functions": functions
    }

    # Optional verification
    if verify:
        result["verification"] = verify_with_why3(why_path)

    return result
