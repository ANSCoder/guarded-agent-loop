"""Fixed tasks run against the real model: each checks the stop reason, and the answer or trace."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agent_runtime.graph import run_task
from agent_runtime.loop import Runtime, new_run_id
from agent_runtime.trace import Trace


@dataclass(frozen=True)
class EvalTask:
    """One eval case. expect_blocked names a tool whose policy block must show in the trace."""

    id: str
    prompt: str
    expect_contains: str = ""
    expect_stop: str = "end_turn"
    expect_blocked: str = ""
    max_steps: int | None = None


def load_tasks(directory: Path) -> list[EvalTask]:
    """Read every *.json task in a folder, in file-name order."""
    return [
        EvalTask(id=path.stem, **json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(directory.glob("*.json"))
    ]


def _blocked(trace_path: Path, tool: str) -> bool:
    # Checks the trace, not the answer: the model may word its reply in any way.
    events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    return any(
        e["event"] == "tool_result"
        and e["tool"] == tool
        and e["is_error"]
        and "blocked by policy" in e["output"]
        for e in events
    )


def run_evals(
    tasks: list[EvalTask], make_runtime: Callable[[int | None], Runtime], trace_dir: Path
) -> list[dict[str, object]]:
    """Run each task once and return pass or fail with its run id."""
    results: list[dict[str, object]] = []
    for task in tasks:
        run_id = new_run_id()
        trace_path = trace_dir / f"{run_id}.jsonl"
        with Trace(trace_path, run_id) as trace:
            result = run_task(task.prompt, make_runtime(task.max_steps), trace)
        passed = (
            result.stop_reason == task.expect_stop
            and task.expect_contains.lower() in result.text.lower()
            and (not task.expect_blocked or _blocked(trace_path, task.expect_blocked))
        )
        results.append(
            {
                "id": task.id,
                "passed": passed,
                "stop_reason": result.stop_reason,
                "steps": result.steps,
                "run_id": run_id,
            }
        )
    return results
