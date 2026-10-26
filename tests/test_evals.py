import json
from pathlib import Path

from agent_runtime.evals import load_tasks, run_evals
from tests.conftest import Response, Script, call, make_runtime, text


def _write_task(directory: Path, name: str, expect: str) -> None:
    (directory / f"{name}.json").write_text(json.dumps({"prompt": "q", "expect_contains": expect}))


def test_eval_passes_when_answer_has_the_expected_word(root: Path, tmp_path: Path) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    _write_task(tasks_dir, "001-math", "391")
    _write_task(tasks_dir, "002-wrong", "999")
    script = Script(
        Response([text("the answer is 391")], "end_turn"), Response([text("391")], "end_turn")
    )
    results = run_evals(
        load_tasks(tasks_dir), lambda _: make_runtime(root, script), tmp_path / "traces"
    )
    assert [(r["id"], r["passed"]) for r in results] == [("001-math", True), ("002-wrong", False)]


def test_blocked_expectation_reads_the_trace(root: Path, tmp_path: Path) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "004-blocked.json").write_text(
        json.dumps({"prompt": "q", "expect_blocked": "write_file"})
    )
    script = Script(
        Response([call("write_file", {"path": "n.txt", "content": "x"})], "tool_use"),
        Response([text("I could not save it")], "end_turn"),
    )
    results = run_evals(
        load_tasks(tasks_dir), lambda _: make_runtime(root, script), tmp_path / "traces"
    )
    assert results[0]["passed"] is True
