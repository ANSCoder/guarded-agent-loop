"""Command-line entry point: run a task, resume a run, or run the evals."""

import argparse
import json
import re
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
import httpx

from agent_runtime.config import Settings
from agent_runtime.evals import load_tasks, run_evals
from agent_runtime.graph import resume_task, run_task
from agent_runtime.harness.policy import Policy
from agent_runtime.loop import Runtime, deny_all, new_run_id
from agent_runtime.mcp import load_servers, mcp_tools
from agent_runtime.openai_compat import ModelReplyError, make_create
from agent_runtime.tools import builtin_tools
from agent_runtime.trace import Trace

RUN_ID = re.compile(r"[0-9a-f]{12}")


def ask_user(name: str, args: dict[str, Any]) -> bool:
    """Ask on the terminal. With no terminal, the answer is no: nothing is approved by accident."""
    try:
        answer = input(f"Allow {name} {json.dumps(args)}? [y/N] ")
    except EOFError:  # no terminal to ask on: a non-interactive run must not approve anything
        return False
    return answer.strip().lower() == "y"


def build_runtime(
    settings: Settings, root: Path, approve: Callable[[str, dict[str, Any]], bool] = ask_user
) -> Runtime:
    """Wire settings, built-in and MCP tools, policy and the model client into a Runtime."""
    tools = {t.name: t for t in builtin_tools(root)}
    if (root / settings.mcp_path).exists():
        for tool in mcp_tools(load_servers(root / settings.mcp_path)):
            tools[tool.name] = tool
    create: Callable[..., Any]
    if settings.provider == "openai":
        key = settings.api_key
        create = make_create(
            settings.base_url, key.get_secret_value() if key else None, settings.reasoning_effort
        )
    else:
        key = settings.anthropic_api_key
        client = anthropic.Anthropic(api_key=key.get_secret_value() if key else None)
        create = client.messages.create
    return Runtime(
        create=create,
        settings=settings,
        tools=tools,
        policy=Policy.load(root / settings.policy_path),
        checkpoint_dir=root / settings.checkpoint_dir,
        approve=approve,
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point. Exit codes: 0 ok, 1 eval failures, 2 setup or input error."""
    parser = argparse.ArgumentParser(prog="agent-runtime")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="run one task")
    run_p.add_argument("task")
    resume_p = sub.add_parser("resume", help="continue a run from its last checkpoint")
    resume_p.add_argument("run_id")
    trace_p = sub.add_parser("trace", help="print the events of a run with the time between them")
    trace_p.add_argument("run_id")
    eval_p = sub.add_parser("eval", help="run the fixed eval tasks")
    eval_p.add_argument("--dir", default="evals/tasks")
    args = parser.parse_args(argv)

    settings = Settings()
    # Reading a trace needs no model, so it needs no key either.
    if args.cmd != "trace":
        if settings.provider == "anthropic" and settings.anthropic_api_key is None:
            print(
                "error: set ANTHROPIC_API_KEY, or use AGENT_PROVIDER=openai with AGENT_BASE_URL",
                file=sys.stderr,
            )
            return 2
        if settings.provider == "openai" and not settings.base_url:
            print("error: AGENT_PROVIDER=openai needs AGENT_BASE_URL", file=sys.stderr)
            return 2
    try:
        return _dispatch(args, settings, Path.cwd())
    except (httpx.HTTPError, anthropic.APIError, ModelReplyError) as exc:  # a failed model call
        print(f"error: model call failed: {exc}", file=sys.stderr)
        return 2


def _show_trace(trace_dir: Path, run_id: str) -> int:
    path = trace_dir / f"{run_id}.jsonl"
    if not RUN_ID.fullmatch(run_id) or not path.exists():
        print(f"error: no trace named {run_id!r}", file=sys.stderr)
        return 2
    previous: datetime | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:  # the last line is cut off when a run is killed mid-write
            print("(unreadable line)")
            continue
        now = datetime.fromisoformat(event.pop("ts"))
        gap = (now - previous).total_seconds() if previous else 0.0
        previous = now
        event.pop("run_id", None)
        print(f"+{gap:6.1f}s  {event.pop('event'):<11} {json.dumps(event, ensure_ascii=False)}")
    return 0


def _dispatch(args: argparse.Namespace, settings: Settings, root: Path) -> int:
    if args.cmd == "trace":
        return _show_trace(root / settings.trace_dir, args.run_id)
    # The file tools are confined to this folder. Home or / would expose keys and personal files.
    if root in (Path.home(), Path(root.anchor)):
        print("error: run from the project folder, not your home folder or /", file=sys.stderr)
        return 2
    if args.cmd == "eval":
        return _eval(settings, root, Path(args.dir))
    if args.cmd == "resume":
        checkpoint = root / settings.checkpoint_dir / f"{args.run_id}.json"
        if not RUN_ID.fullmatch(args.run_id) or not checkpoint.exists():
            print(f"error: no saved run named {args.run_id!r}", file=sys.stderr)
            return 2
        rt = build_runtime(settings, root)
        trace_path = root / settings.trace_dir / f"{args.run_id}.jsonl"
        with Trace(trace_path, args.run_id) as trace:
            result = resume_task(rt, trace)
    else:
        rt = build_runtime(settings, root)
        run_id = new_run_id()
        trace_path = root / settings.trace_dir / f"{run_id}.jsonl"
        with Trace(trace_path, run_id) as trace:
            result = run_task(args.task, rt, trace)
    print(result.text)
    print(
        f"[{result.stop_reason} after {result.steps} steps, run {result.run_id}, "
        f"trace {trace_path}]",
        file=sys.stderr,
    )
    return 0


def _eval(settings: Settings, root: Path, directory: Path) -> int:
    def make_runtime(max_steps: int | None) -> Runtime:
        capped = settings.model_copy(update={"max_steps": max_steps}) if max_steps else settings
        return build_runtime(capped, root, approve=deny_all)

    results = run_evals(load_tasks(directory), make_runtime, root / settings.trace_dir)
    passed = sum(1 for r in results if r["passed"])
    for r in results:
        print(
            f"{'PASS' if r['passed'] else 'FAIL'} {r['id']} "
            f"({r['stop_reason']}, {r['steps']} steps)"
        )
    print(f"{passed}/{len(results)} passed on model {settings.model}")
    return 0 if passed == len(results) else 1
