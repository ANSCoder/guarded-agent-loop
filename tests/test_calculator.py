import pytest

from agent_runtime.tools.calculator import calculate


@pytest.mark.parametrize(
    ("expression", "expected"),
    [("2+3", "5"), ("(1+2)*3", "9"), ("10/4", "2.5"), ("-3*-3", "9")],
)
def test_arithmetic(expression: str, expected: str) -> None:
    assert calculate({"expression": expression}) == expected


@pytest.mark.parametrize("expression", ["2**3", "__import__('os')", "abs(-1)"])
def test_rejects_anything_but_arithmetic(expression: str) -> None:
    with pytest.raises((ValueError, SyntaxError)):
        calculate({"expression": expression})
