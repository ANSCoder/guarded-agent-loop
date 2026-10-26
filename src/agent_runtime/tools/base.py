"""The Tool type. Built-in and MCP tools are both turned into this."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Tool:
    """A tool the model can call: name, description, JSON input schema, and the function to run."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(repr=False)
    run: Callable[[dict[str, Any]], str] = field(repr=False)
