import copy
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from agent_runtime.config import Settings
from agent_runtime.harness.policy import Policy
from agent_runtime.loop import Runtime, deny_all
from agent_runtime.tools import builtin_tools
from agent_runtime.trace import Trace


@dataclass
class Block:
    type: str
    text: str | None = None
    id: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None


@dataclass
class Response:
    content: list[Block]
    stop_reason: str


def text(value: str) -> Block:
    return Block(type="text", text=value)


def call(name: str, args: dict[str, Any], call_id: str = "toolu_1") -> Block:
    return Block(type="tool_use", id=call_id, name=name, input=args)


class Script:
    """Stands in for messages.create: returns scripted responses in order and records each request.

    An Exception in the script is raised instead of returned.
    """

    def __init__(self, *responses: Response | Exception) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict[str, Any]]] = []

    def __call__(self, **kwargs: Any) -> Response:
        self.calls.append(copy.deepcopy(kwargs["messages"]))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_runtime(
    root: Path,
    script: Script,
    rules: dict[str, str] | None = None,
    approve: Any = deny_all,
    **settings: Any,
) -> Runtime:
    defaults: dict[str, Any] = {"max_steps": 5, "tool_timeout_s": 5.0, "tool_output_cap": 4000}
    return Runtime(
        create=script,
        settings=Settings(**{**defaults, **settings}),
        tools={t.name: t for t in builtin_tools(root)},
        policy=Policy(rules or {"calculator": "allow", "read_file": "allow", "write_file": "ask"}),
        checkpoint_dir=root / "checkpoints",
        approve=approve,
    )


@pytest.fixture
def trace(tmp_path: Path) -> Iterator[Trace]:
    t = Trace(tmp_path / "traces" / "run.jsonl", "run")
    yield t
    t.close()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    return tmp_path
