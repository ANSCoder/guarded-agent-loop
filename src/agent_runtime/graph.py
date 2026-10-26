"""The agent loop as named nodes with edges, and a checkpoint saved before every node."""

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_runtime.loop import Runtime, call_model, run_tools, to_blocks
from agent_runtime.trace import Trace

State = dict[str, Any]
NodeFn = Callable[[State], str | None]


@dataclass(frozen=True)
class RunResult:
    """How a run ended: the answer, the stop reason, and how many model calls it used."""

    run_id: str
    text: str
    stop_reason: str
    steps: int


@dataclass(frozen=True)
class Graph:
    """Named nodes and the node a run starts from."""

    nodes: dict[str, NodeFn]
    start: str


def agent_graph(rt: Runtime, trace: Trace) -> Graph:
    """Build the model and tools nodes. A node returns the next node name, or None to stop."""

    def model(state: State) -> str | None:
        state["step"] += 1
        started = time.monotonic()
        response = call_model(rt, state["messages"])
        blocks = to_blocks(response.content)
        state["messages"].append({"role": "assistant", "content": blocks})
        trace.write(
            "model",
            step=state["step"],
            stop_reason=response.stop_reason,
            seconds=round(time.monotonic() - started, 2),
        )
        if response.stop_reason != "tool_use":
            # max_tokens means the answer was cut off, so it must not look like a normal finish.
            state["stop_reason"] = (
                "max_tokens" if response.stop_reason == "max_tokens" else "end_turn"
            )
            state["text"] = "".join(b["text"] for b in blocks if b["type"] == "text")
            trace.write("stop", step=state["step"], reason=state["stop_reason"])
            return None
        state["pending"] = [b for b in blocks if b["type"] == "tool_use"]
        state["results"] = []
        return "tools"

    def tools(state: State) -> str | None:
        # One tool per node, so each finished tool gets a checkpoint and resume skips it.
        if state["pending"]:
            block = state["pending"].pop(0)
            state["results"].extend(run_tools(rt, [block], trace, state["step"]))
            return "tools"
        state["messages"].append({"role": "user", "content": state["results"]})
        if state["step"] >= rt.settings.max_steps:
            state["stop_reason"] = "step_cap"
            trace.write("stop", step=state["step"], reason="step_cap")
            return None
        return "model"

    return Graph(nodes={"model": model, "tools": tools}, start="model")


def _checkpoint(rt: Runtime, trace: Trace) -> Path:
    return rt.checkpoint_dir / f"{trace.run_id}.json"


def _save(checkpoint: Path, node: str | None, state: State) -> None:
    # Write to a temp file and rename, so a crash mid-write never leaves a half-written checkpoint.
    tmp = checkpoint.with_suffix(".tmp")
    tmp.write_text(json.dumps({"node": node, "state": state}), encoding="utf-8")
    os.replace(tmp, checkpoint)


def run_graph(graph: Graph, state: State, checkpoint: Path, node: str | None) -> State:
    """Run nodes from `node` onward, saving a checkpoint before each one."""
    while node is not None:
        _save(checkpoint, node, state)
        node = graph.nodes[node](state)
    _save(checkpoint, None, state)
    return state


def _result(run_id: str, state: State) -> RunResult:
    return RunResult(run_id, state.get("text", ""), state["stop_reason"] or "", state["step"])


def run_task(task: str, rt: Runtime, trace: Trace) -> RunResult:
    """Start a new run for a task. Checkpoints go to the runtime's checkpoint folder."""
    state: State = {
        "messages": [{"role": "user", "content": task}],
        "step": 0,
        "text": "",
        "stop_reason": None,
        "pending": [],
        "results": [],
    }
    checkpoint = _checkpoint(rt, trace)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    graph = agent_graph(rt, trace)
    return _result(trace.run_id, run_graph(graph, state, checkpoint, graph.start))


def resume_task(rt: Runtime, trace: Trace) -> RunResult:
    """Continue a run from its last checkpoint. Uses the run id of the trace."""
    checkpoint = _checkpoint(rt, trace)
    data = json.loads(checkpoint.read_text(encoding="utf-8"))
    graph = agent_graph(rt, trace)
    return _result(trace.run_id, run_graph(graph, data["state"], checkpoint, data["node"]))
