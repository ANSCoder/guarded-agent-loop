"""Arithmetic calculator. It parses the expression and never runs eval."""

import ast
import operator
from collections.abc import Callable
from typing import Any

Number = int | float

# Only these operators are allowed. Power is left out on purpose: 9**9**9 would hang the process.
_BINARY: dict[type[ast.operator], Callable[[Number, Number], Number]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _eval(node: ast.AST) -> Number:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        return _BINARY[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand)
    raise ValueError("only numbers and + - * / are allowed")


def calculate(args: dict[str, Any]) -> str:
    """Evaluate an expression such as 17 * 23. Only numbers, + - * / and unary minus are allowed."""
    return str(_eval(ast.parse(str(args["expression"]), mode="eval").body))
