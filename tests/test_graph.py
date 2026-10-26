import json
from pathlib import Path
from typing import Any

import pytest

from agent_runtime.graph import resume_task, run_task
from agent_runtime.loop import Runtime
from agent_runtime.tools import Tool
from agent_runtime.trace import Trace
from tests.conftest import Response, Script, call, make_runtime, text


class Killed(BaseException):
    """Stands in for the process being killed mid-tool. Not an Exception, so it is not caught."""


def _two_tools(root: Path, script: Script, first: Any, second: Any) -> Runtime:
    rt = make_runtime(root, script, rules={"first": "allow", "second": "allow"})
    rt.tools["first"] = Tool("first", "", {"type": "object"}, first)
    rt.tools["second"] = Tool("second", "", {"type": "object"}, second)
    return rt


def test_graph_gives_the_same_answer_as_the_loop(root: Path, tmp_path: Path) -> None:
    script = Script(
        Response([call("calculator", {"expression": "6*7"})], "tool_use"),
        Response([text("42")], "end_turn"),
    )
    rt = make_runtime(root, script)
    with Trace(tmp_path / "t.jsonl", "g1") as trace:
        result = run_task("answer", rt, trace)
    assert (result.text, result.stop_reason, result.steps) == ("42", "end_turn", 2)
    saved = json.loads((rt.checkpoint_dir / "g1.json").read_text())
    assert saved["node"] is None


def test_resume_continues_after_a_crash(root: Path, tmp_path: Path) -> None:
    crashing = Script(
        Response([call("calculator", {"expression": "1+1"})], "tool_use"),
        RuntimeError("process killed"),
    )
    rt = make_runtime(root, crashing)
    with Trace(tmp_path / "t.jsonl", "g2") as trace, pytest.raises(RuntimeError, match="killed"):
        run_task("count", rt, trace)

    saved = json.loads((rt.checkpoint_dir / "g2.json").read_text())
    assert saved["node"] == "model"
    assert saved["state"]["step"] == 1

    recovered = Script(Response([text("two")], "end_turn"))
    with Trace(tmp_path / "t.jsonl", "g2") as trace:
        result = resume_task(make_runtime(root, recovered), trace)
    assert (result.text, result.steps) == ("two", 2)
    assert recovered.calls[0][-1]["content"][0]["content"] == "2"


def test_resume_does_not_rerun_a_finished_tool(root: Path, tmp_path: Path) -> None:
    ran: list[str] = []
    second_works = [False]

    def first(args: dict[str, Any]) -> str:
        ran.append("first")
        return "one"

    def second(args: dict[str, Any]) -> str:
        ran.append("second")
        if not second_works[0]:
            raise Killed()
        return "two"

    script = Script(Response([call("first", {}, "a"), call("second", {}, "b")], "tool_use"))
    with Trace(tmp_path / "t.jsonl", "g3") as trace, pytest.raises(Killed):
        run_task("two tools", _two_tools(root, script, first, second), trace)
    assert ran == ["first", "second"]

    second_works[0] = True
    recovered = Script(Response([text("done")], "end_turn"))
    with Trace(tmp_path / "t.jsonl", "g3") as trace:
        result = resume_task(_two_tools(root, recovered, first, second), trace)
    assert result.text == "done"
    assert ran == ["first", "second", "second"]  # "first" is not rerun, only the one in flight
    assert [r["content"] for r in recovered.calls[0][-1]["content"]] == ["one", "two"]
