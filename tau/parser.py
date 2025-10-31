"""
Parser to extract @safe decorated functions from Python files.
"""

import ast
import inspect
from typing import List, Dict, Any, Optional
from pathlib import Path


class SafeFunctionParser:
    """Parse Python files to find @safe decorated functions"""

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a Python file and extract all @safe decorated functions.

        Args:
            file_path: Path to Python file

        Returns:
            List of dicts with function info:
            {
                "name": str,
                "source": str,
                "requires": str,
                "ensures": str,
                "invariants": List[str] or None,
                "variant": str or None,
                "lineno": int
            }
        """
        with open(file_path, 'r') as f:
            source = f.read()

        tree = ast.parse(source, filename=file_path)
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = self._extract_safe_function(node, source)
                if func_info:
                    functions.append(func_info)

        return functions

    def _extract_safe_function(self, node: ast.FunctionDef, source: str) -> Optional[Dict[str, Any]]:
        """
        Extract function info if it has @safe or @safe_auto decorator.

        Returns:
            Dict with function info or None if not decorated
        """
        # Check if function has @safe or @safe_auto decorator
        has_safe = False
        auto_mode = False
        requires_list = []
        ensures_list = []
        invariants_list = []
        variant_value = None

        for decorator in node.decorator_list:
            # Handle simple decorators: @safe or @safe_auto
            if isinstance(decorator, ast.Name):
                if decorator.id == "safe":
                    has_safe = True
                    auto_mode = False
                elif decorator.id == "safe_auto":
                    has_safe = True
                    auto_mode = True

            # Handle decorator with arguments: @requires("...")
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorator_name = decorator.func.id

                    # Extract the string argument
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        arg_value = decorator.args[0].value

                        if decorator_name == "requires":
                            requires_list.append(arg_value)
                        elif decorator_name == "ensures":
                            ensures_list.append(arg_value)
                        elif decorator_name == "invariant":
                            invariants_list.append(arg_value)
                        elif decorator_name == "variant":
                            variant_value = arg_value

        if not has_safe:
            return None

        # Extract function source WITHOUT decorators
        # Get the full source including decorators first
        full_source = ast.get_source_segment(source, node)
        if full_source is None:
            return None

        # Parse just the function def line and body, skipping decorators
        # Find where the function actually starts (after decorators)
        lines = full_source.split('\n')
        func_start_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                func_start_idx = i
                break

        # Join from the def line onward
        func_source = '\n'.join(lines[func_start_idx:])

        # Keep the source AS-IS (with docstrings) for hash computation
        # The transpiler will need to handle docstrings or we handle them separately

        # Combine multiple requires/ensures with /\
        requires = " /\\ ".join(requires_list) if requires_list else "true"
        ensures = " /\\ ".join(ensures_list) if ensures_list else "true"

        return {
            "name": node.name,
            "source": func_source,
            "requires": requires,
            "ensures": ensures,
            "invariants": invariants_list if invariants_list else None,
            "variant": variant_value,
            "lineno": node.lineno,
            "auto_mode": auto_mode  # True if @safe_auto, False if @safe
        }

    def parse_module(self, module) -> List[Dict[str, Any]]:
        """
        Parse a loaded Python module to extract @safe decorated functions.

        Args:
            module: Loaded Python module

        Returns:
            List of function info dicts
        """
        functions = []

        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if hasattr(obj, '__safe__') and obj.__safe__:
                # Get source
                try:
                    source = inspect.getsource(obj)
                except OSError:
                    continue

                # Get specs
                specs = obj.__safe_specs__

                # Combine multiple requires/ensures
                requires = " /\\ ".join(specs["requires"]) if specs["requires"] else "true"
                ensures = " /\\ ".join(specs["ensures"]) if specs["ensures"] else "true"

                functions.append({
                    "name": name,
                    "source": source,
                    "requires": requires,
                    "ensures": ensures,
                    "invariants": specs["invariants"] if specs["invariants"] else None,
                    "variant": specs["variant"],
                    "lineno": obj.__code__.co_firstlineno
                })

        return functions
