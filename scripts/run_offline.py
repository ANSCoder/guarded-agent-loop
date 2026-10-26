"""Run the real CLI against the local stub model. Free: no key, no network, nothing billed.

The stub always asks for the calculator on 17 * 23, whatever the task says. Use it to check
that the CLI, trace and tool loop work. It does not test the real model.
"""

import os
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)  # so `tests` and `agent_runtime` import

from agent_runtime.cli import main  # noqa: E402
from tests.stub_api import asks_for, stub_api  # noqa: E402


def run_offline(argv: list[str]) -> int:
    task = " ".join(argv) or "What is 17 * 23?"
    with stub_api(asks_for("calculator", {"expression": "17*23"})) as url:
        # Forced, not defaulted: a real key in .env must never reach the real API from here.
        os.environ["ANTHROPIC_BASE_URL"] = url
        os.environ["ANTHROPIC_API_KEY"] = "offline-stub"
        # .env may say openai, which would send this demo to a real server instead of the stub.
        os.environ["AGENT_PROVIDER"] = "anthropic"
        return main(["run", task])


if __name__ == "__main__":
    raise SystemExit(run_offline(sys.argv[1:]))
