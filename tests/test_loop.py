import json
from pathlib import Path

from agent_runtime.graph import run_task
from agent_runtime.tools.base import Tool
from agent_runtime.trace import Trace
from tests.conftest import Response, Script, call, make_runtime, text


def test_final_answer_without_tools(root: Path, trace: Trace) -> None:
    script = Script(Response([text("hi")], "end_turn"))
    result = run_task("say hi", make_runtime(root, script), trace)
    assert (result.text, result.stop_reason, result.steps) == ("hi", "end_turn", 1)


def test_tool_result_goes_back_to_the_model(root: Path, trace: Trace) -> None:
    script = Script(
        Response([call("calculator", {"expression": "2+3"})], "tool_use"),
        Response([text("five")], "end_turn"),
    )
    result = run_task("add", make_runtime(root, script), trace)
    assert result.text == "five"
    tool_result = script.calls[1][-1]["content"][0]
    assert tool_result["content"] == "5"
    assert tool_result["is_error"] is False


def test_denied_tool_is_blocked_and_not_run(root: Path, trace: Trace) -> None:
    script = Script(
        Response([call("calculator", {"expression": "2+3"})], "tool_use"),
        Response([text("ok")], "end_turn"),
    )
    run_task("add", make_runtime(root, script, rules={"calculator": "deny"}), trace)
    tool_result = script.calls[1][-1]["content"][0]
    assert tool_result["is_error"] is True
    assert tool_result["content"] == "blocked by policy: calculator is deny"


def test_unknown_tool_is_denied_by_default(root: Path, trace: Trace) -> None:
    script = Script(
        Response([call("shell", {"cmd": "rm -rf /"})], "tool_use"),
        Response([text("ok")], "end_turn"),
    )
    run_task("x", make_runtime(root, script, rules={}), trace)
    assert script.calls[1][-1]["content"][0]["is_error"] is True


def test_ask_tool_runs_only_when_approved(root: Path, trace: Trace) -> None:
    asked: list[str] = []

    def approve(name: str, args: dict[str, object]) -> bool:
        asked.append(name)
        return False

    script = Script(
        Response([call("write_file", {"path": "out.txt", "content": "x"})], "tool_use"),
        Response([text("ok")], "end_turn"),
    )
    run_task("write", make_runtime(root, script, approve=approve), trace)
    assert asked == ["write_file"]
    assert not (root / "out.txt").exists()


def test_step_cap_stops_a_loop_that_never_ends(root: Path, trace: Trace) -> None:
    script = Script(
        *[Response([call("calculator", {"expression": "1+1"})], "tool_use") for _ in range(3)]
    )
    result = run_task("loop", make_runtime(root, script, max_steps=3), trace)
    assert (result.stop_reason, result.steps) == ("step_cap", 3)


def test_tool_error_goes_back_to_the_model(root: Path, trace: Trace) -> None:
    script = Script(
        Response([call("calculator", {"expression": "1/0"})], "tool_use"),
        Response([text("ok")], "end_turn"),
    )
    run_task("divide", make_runtime(root, script), trace)
    result = script.calls[1][-1]["content"][0]
    assert result["is_error"] is True
    assert result["content"] == "tool error: division by zero"


def test_slow_tool_times_out(root: Path, trace: Trace) -> None:
    import time

    def slow(args: dict[str, object]) -> str:
        time.sleep(2)
        return "late"

    script = Script(
        Response([call("slow", {})], "tool_use"),
        Response([text("ok")], "end_turn"),
    )
    runtime = make_runtime(root, script, rules={"slow": "allow"}, tool_timeout_s=0.1)
    runtime.tools["slow"] = Tool(name="slow", description="", input_schema={}, run=slow)
    run_task("wait", runtime, trace)
    result = script.calls[1][-1]["content"][0]
    assert result["is_error"] is True
    assert "timed out" in result["content"]


def test_long_tool_output_is_capped(root: Path, trace: Trace) -> None:
    script = Script(
        Response([call("read_file", {"path": "notes.txt"})], "tool_use"),
        Response([text("ok")], "end_turn"),
    )
    run_task("read", make_runtime(root, script, tool_output_cap=3), trace)
    content = script.calls[1][-1]["content"][0]["content"]
    assert content.startswith("hel")
    assert "[truncated 2 chars]" in content


def test_read_file_cannot_leave_the_workspace(root: Path, trace: Trace) -> None:
    script = Script(
        Response([call("read_file", {"path": "../../etc/hosts"})], "tool_use"),
        Response([text("ok")], "end_turn"),
    )
    run_task("escape", make_runtime(root, script), trace)
    result = script.calls[1][-1]["content"][0]
    assert result["is_error"] is True
    assert "outside the workspace" in result["content"]


def test_trace_records_every_step(root: Path, tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    script = Script(
        Response([call("calculator", {"expression": "2*2"})], "tool_use"),
        Response([text("four")], "end_turn"),
    )
    with Trace(trace_path, "abc") as trace:
        run_task("double", make_runtime(root, script), trace)
    records = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert [r["event"] for r in records] == ["model", "tool_call", "tool_result", "model", "stop"]
    assert records[0]["seconds"] >= 0  # how long the model call took, for finding what is slow


def test_max_tokens_stop_is_reported_not_hidden(root: Path, trace: Trace) -> None:
    script = Script(Response([text("half an ans")], "max_tokens"))
    result = run_task("long answer", make_runtime(root, script), trace)
    assert (result.text, result.stop_reason) == ("half an ans", "max_tokens")
