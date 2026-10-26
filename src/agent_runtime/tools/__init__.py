"""The built-in tools the runtime starts with."""

from pathlib import Path

from agent_runtime.tools.base import Tool
from agent_runtime.tools.calculator import calculate
from agent_runtime.tools.files import make_read_file, make_write_file

__all__ = ["Tool", "builtin_tools"]


def builtin_tools(root: Path) -> list[Tool]:
    """The built-in tools. The file tools are confined to root."""
    return [
        Tool(
            name="calculator",
            description="Evaluate an arithmetic expression with + - * / and parentheses.",
            input_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            run=calculate,
        ),
        make_read_file(root),
        make_write_file(root),
    ]
