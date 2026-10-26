"""End to end: the real CLI and SDK over HTTP, against the local stub. Free, no key needed."""

import json
import shutil
from pathlib import Path

import pytest

from agent_runtime.cli import main
from tests.stub_api import asks_for, openai_asks_for, stub_api, stub_openai

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copytree(REPO / "config", tmp_path / "config")  # the real policy, in a clean folder
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    return tmp_path


def test_calculator_run_end_to_end(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with stub_api(asks_for("calculator", {"expression": "17*23"})) as url:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", url)
        assert main(["run", "What is 17 * 23?"]) == 0

    assert "result: 391" in capsys.readouterr().out
    (trace_file,) = (project / "traces").glob("*.jsonl")
    events = [json.loads(line)["event"] for line in trace_file.read_text().splitlines()]
    assert events == ["model", "tool_call", "tool_result", "model", "stop"]


def test_ask_tool_is_blocked_without_a_terminal(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_terminal(prompt: str = "") -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", no_terminal)
    with stub_api(asks_for("write_file", {"path": "notes.txt", "content": "hello"})) as url:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", url)
        assert main(["run", "Save hello to notes.txt"]) == 0

    assert "blocked by policy: write_file is ask" in capsys.readouterr().out
    assert not (project / "notes.txt").exists()


def test_openai_compatible_provider_end_to_end(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with stub_openai(openai_asks_for("calculator", {"expression": "17*23"})) as url:
        monkeypatch.setenv("AGENT_PROVIDER", "openai")
        monkeypatch.setenv("AGENT_BASE_URL", url)
        monkeypatch.setenv("AGENT_API_KEY", "hf_test_not_real")
        assert main(["run", "What is 17 * 23?"]) == 0

    assert "result: 391" in capsys.readouterr().out
