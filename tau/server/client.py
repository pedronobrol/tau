"""
TAU API - Unified interface for specification generation and verification
"""
import os
import ast
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path

from tau.server.models import (
    GeneratedSpecs, VerificationProgress, ValidationResult,
    FunctionInfo, VerificationStage
)
from tau.verify import verify_file as _verify_file_impl, VerificationResult, VerificationSummary
from tau.llm.spec_generator import generate_specifications_sync
from tau.parser import SafeFunctionParser


class TauClient:
    """
    Unified API for TAU verification and spec generation.

    Example usage:
        client = TauClient(api_key="sk-ant-...")

        # Generate specs
        specs = api.generate_specs(function_source)

        # Verify function
        result = api.verify_function("myfile.py", "my_function")

        # Verify with streaming
        def on_progress(progress):
            print(f"{progress.stage}: {progress.message}")
        result = api.verify_function_stream("myfile.py", "my_function", on_progress)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-haiku-20241022"):
        """
        Initialize TAU API.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Claude model to use for spec generation
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

    def extract_function_info(self, file_path: str, function_name: str) -> Optional[FunctionInfo]:
        """
        Extract information about a specific function from a file.

        Args:
            file_path: Path to Python file
            function_name: Name of function to extract

        Returns:
            FunctionInfo object or None if function not found
        """
        try:
            with open(file_path, 'r') as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    # Extract function source
                    func_lines = source.split('\n')[node.lineno - 1:node.end_lineno]
                    func_source = '\n'.join(func_lines)

                    # Extract parameters
                    params = []
                    for arg in node.args.args:
                        arg_name = arg.arg
                        arg_type = None
                        if arg.annotation:
                            if isinstance(arg.annotation, ast.Name):
                                arg_type = arg.annotation.id
                        params.append((arg_name, arg_type))

                    # Extract return type
                    return_type = None
                    if node.returns:
                        if isinstance(node.returns, ast.Name):
                            return_type = node.returns.id

                    # Check for loops
                    has_loop = any(isinstance(n, ast.While) for n in ast.walk(node))

                    # Build signature
                    param_str = ", ".join(f"{name}: {typ}" if typ else name for name, typ in params)
                    sig = f"def {function_name}({param_str})"
                    if return_type:
                        sig += f" -> {return_type}"

                    return FunctionInfo(
                        name=function_name,
                        source=func_source,
                        line_number=node.lineno,
                        signature=sig,
                        has_loop=has_loop,
                        parameters=params,
                        return_type=return_type
                    )

            return None

        except Exception as e:
            print(f"❌ Error extracting function info: {e}")
            return None

    def generate_specs(
        self,
        function_source: str,
        context: str = "",
        include_invariants: bool = True
    ) -> Optional[GeneratedSpecs]:
        """
        Call Claude to generate @requires and @ensures specifications.

        Args:
            function_source: Python function source code
            context: Surrounding code for context
            include_invariants: Whether to generate loop invariants

        Returns:
            GeneratedSpecs with requires, ensures, reasoning
        """
        # Parse function to get info
        try:
            tree = ast.parse(function_source)
            func_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_node = node
                    break

            if not func_node:
                return None

            # Extract parameters
            params = []
            for arg in func_node.args.args:
                arg_name = arg.arg
                arg_type = None
                if arg.annotation and isinstance(arg.annotation, ast.Name):
                    arg_type = arg.annotation.id
                params.append((arg_name, arg_type))

            # Return type
            return_type = None
            if func_node.returns and isinstance(func_node.returns, ast.Name):
                return_type = func_node.returns.id

            # Has loop?
            has_loop = any(isinstance(n, ast.While) for n in ast.walk(func_node))

            function_info = FunctionInfo(
                name=func_node.name,
                source=function_source,
                line_number=func_node.lineno,
                signature=f"def {func_node.name}(...)",
                has_loop=has_loop,
                parameters=params,
                return_type=return_type
            )

            # Generate specs
            return generate_specifications_sync(
                function_info=function_info,
                context=context,
                api_key=self.api_key,
                model=self.model
            )

        except Exception as e:
            print(f"❌ Error generating specs: {e}")
            return None

    def verify_function(
        self,
        file_path: str,
        function_name: str,
        auto_generate_invariants: bool = True,
        verbose: bool = False
    ) -> Optional[VerificationResult]:
        """
        Verify a single function with optional auto-generation of invariants.

        Args:
            file_path: Path to Python file
            function_name: Name of function to verify
            auto_generate_invariants: Use LLM to generate invariants if needed
            verbose: Print detailed output

        Returns:
            VerificationResult with status, hash, diagnostics
        """
        # Verify entire file and extract result for specific function
        summary = _verify_file_impl(
            file_path=file_path,
            api_key=self.api_key if auto_generate_invariants else None,
            verbose=verbose
        )

        # Find result for requested function
        for result in summary.results:
            if result.name == function_name:
                return result

        return None

    def verify_function_stream(
        self,
        file_path: str,
        function_name: str,
        callback: Callable[[VerificationProgress], None],
        auto_generate_invariants: bool = True
    ) -> Optional[VerificationResult]:
        """
        Stream verification progress for real-time UI updates.

        Args:
            file_path: Path to Python file
            function_name: Name of function to verify
            callback: Called with VerificationProgress events
            auto_generate_invariants: Use LLM to generate invariants if needed

        Returns:
            VerificationResult when complete
        """
        import time
        start_time = time.time()

        # Stage 1: Parsing
        callback(VerificationProgress(
            stage=VerificationStage.PARSING,
            message=f"Parsing {Path(file_path).name}...",
            progress=0.1,
            function_name=function_name
        ))

        # Stage 2: Transpiling
        callback(VerificationProgress(
            stage=VerificationStage.TRANSPILING,
            message="Transpiling to WhyML...",
            progress=0.3,
            function_name=function_name
        ))

        # Stage 3: Proving (or LLM rounds)
        if auto_generate_invariants:
            # Simulate LLM rounds (in reality this would be integrated deeper)
            callback(VerificationProgress(
                stage=VerificationStage.LLM_ROUND,
                message="Generating invariants with Claude...",
                progress=0.5,
                function_name=function_name,
                llm_round=1,
                llm_max_rounds=3
            ))

        callback(VerificationProgress(
            stage=VerificationStage.PROVING,
            message="Running Why3 prover...",
            progress=0.7,
            function_name=function_name
        ))

        # Actually verify
        result = self.verify_function(
            file_path=file_path,
            function_name=function_name,
            auto_generate_invariants=auto_generate_invariants,
            verbose=False
        )

        # Stage 4: Completed
        duration = time.time() - start_time
        callback(VerificationProgress(
            stage=VerificationStage.COMPLETED if (result and result.verified) else VerificationStage.FAILED,
            message="Verification completed" if (result and result.verified) else "Verification failed",
            progress=1.0,
            function_name=function_name,
            duration_seconds=duration
        ))

        return result

    def verify_file(
        self,
        file_path: str,
        callback: Optional[Callable[[VerificationProgress], None]] = None,
        verbose: bool = False
    ) -> VerificationSummary:
        """
        Verify all @safe functions in a file with optional progress streaming.

        Args:
            file_path: Path to Python file
            callback: Optional callback for progress updates
            verbose: Print detailed output

        Returns:
            VerificationSummary with all results
        """
        if callback:
            callback(VerificationProgress(
                stage=VerificationStage.PARSING,
                message=f"Parsing {Path(file_path).name}...",
                progress=0.0
            ))

        summary = _verify_file_impl(
            file_path=file_path,
            api_key=self.api_key,
            verbose=verbose
        )

        if callback:
            callback(VerificationProgress(
                stage=VerificationStage.COMPLETED,
                message=f"Verified {summary.total} functions",
                progress=1.0
            ))

        return summary

    def validate_specs(
        self,
        requires: str,
        ensures: str,
        function_source: str
    ) -> ValidationResult:
        """
        Check if specifications are syntactically valid WhyML.

        Args:
            requires: Precondition string
            ensures: Postcondition string
            function_source: Python function source

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        # Basic syntax checks
        # Check for common mistakes
        if "!" not in requires and "!" not in ensures:
            # Check if function has loops - may need ! for loop vars
            try:
                tree = ast.parse(function_source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.While):
                        warnings.append("Function has a loop but no '!' references in specs - did you forget to dereference loop variables?")
                        break
            except:
                pass

        # Check for Python syntax instead of WhyML
        if " and " in requires or " and " in ensures:
            errors.append("Use '/\\' for logical AND, not 'and'")
        if " or " in requires or " or " in ensures:
            errors.append("Use '\\/' for logical OR, not 'or'")
        if "==" in requires or "==" in ensures:
            errors.append("Use '=' for equality, not '=='")
        if "!=" in requires or "!=" in ensures:
            errors.append("Use '<>' for inequality, not '!='")

        # Check balanced parentheses
        for spec_name, spec in [("requires", requires), ("ensures", ensures)]:
            if spec.count('(') != spec.count(')'):
                errors.append(f"Unbalanced parentheses in {spec_name}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
