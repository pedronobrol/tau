"""
Tests for expression translation
"""

import ast
import pytest
from tau.translators.expressions import ExpressionTranslator


def test_simple_variables():
    """Test variable name translation"""
    translator = ExpressionTranslator(set())
    expr = ast.parse("x").body[0].value
    assert translator.visit(expr) == "x"


def test_integer_constant():
    """Test integer constant translation"""
    translator = ExpressionTranslator(set())
    expr = ast.parse("42").body[0].value
    assert translator.visit(expr) == "42"


def test_boolean_constants():
    """Test boolean constant translation"""
    translator = ExpressionTranslator(set())

    true_expr = ast.parse("True").body[0].value
    assert translator.visit(true_expr) == "true"

    false_expr = ast.parse("False").body[0].value
    assert translator.visit(false_expr) == "false"


def test_arithmetic_operators():
    """Test arithmetic operator translation"""
    translator = ExpressionTranslator(set())

    cases = [
        ("a + b", "(a + b)"),
        ("a - b", "(a - b)"),
        ("a * b", "(a * b)"),
        ("a / b", "(a div b)"),
        ("a % b", "(a mod b)"),
    ]

    for python_expr, expected_why in cases:
        expr = ast.parse(python_expr).body[0].value
        result = translator.visit(expr)
        assert result == expected_why, f"Failed for {python_expr}: got {result}"


def test_comparison_operators():
    """Test comparison operator translation"""
    translator = ExpressionTranslator(set())

    cases = [
        ("a == b", "(a = b)"),
        ("a != b", "(a <> b)"),
        ("a < b", "(a < b)"),
        ("a <= b", "(a <= b)"),
        ("a > b", "(a > b)"),
        ("a >= b", "(a >= b)"),
    ]

    for python_expr, expected_why in cases:
        expr = ast.parse(python_expr).body[0].value
        result = translator.visit(expr)
        assert result == expected_why, f"Failed for {python_expr}: got {result}"


def test_boolean_operators():
    """Test boolean operator translation"""
    translator = ExpressionTranslator(set())

    and_expr = ast.parse("a and b").body[0].value
    assert translator.visit(and_expr) == "(a and b)"

    or_expr = ast.parse("a or b").body[0].value
    assert translator.visit(or_expr) == "(a or b)"


def test_unary_operators():
    """Test unary operator translation"""
    translator = ExpressionTranslator(set())

    neg_expr = ast.parse("-x").body[0].value
    assert translator.visit(neg_expr) == "(-x)"

    not_expr = ast.parse("not x").body[0].value
    assert translator.visit(not_expr) == "(not x)"


def test_conditional_expression():
    """Test conditional expression translation"""
    translator = ExpressionTranslator(set())

    expr = ast.parse("a if c else b").body[0].value
    result = translator.visit(expr)
    assert result == "(if c then a else b)"


def test_function_call():
    """Test function call translation"""
    translator = ExpressionTranslator({"foo"})

    expr = ast.parse("foo(x, y)").body[0].value
    result = translator.visit(expr)
    assert result == "foo(x, y)"


def test_nested_expressions():
    """Test nested expression translation"""
    translator = ExpressionTranslator(set())

    expr = ast.parse("(a + b) * (c - d)").body[0].value
    result = translator.visit(expr)
    assert result == "((a + b) * (c - d))"


def test_unknown_function_raises():
    """Test that unknown functions raise error"""
    translator = ExpressionTranslator(set())

    expr = ast.parse("unknown(x)").body[0].value
    with pytest.raises(NotImplementedError, match="Unknown function"):
        translator.visit(expr)


def test_chained_comparison_raises():
    """Test that chained comparisons raise error"""
    translator = ExpressionTranslator(set())

    expr = ast.parse("a < b < c").body[0].value
    with pytest.raises(NotImplementedError, match="Chained comparisons"):
        translator.visit(expr)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
