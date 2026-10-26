from pathlib import Path

import pytest

from agent_runtime.cli import main


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)  # no .env here, so the real one is never read
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def test_run_without_a_key_exits_2(isolated: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "x"]) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_resume_rejects_a_path_as_run_id(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert main(["resume", "../x"]) == 2


def test_resume_unknown_run_exits_2(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert main(["resume", "0123456789ab"]) == 2


def test_run_from_the_home_folder_is_refused(
    isolated: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HOME", str(Path.cwd()))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert main(["run", "x"]) == 2
    assert "project folder" in capsys.readouterr().err


def test_trace_prints_events_with_gaps_and_needs_no_key(
    isolated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (isolated / "traces").mkdir()
    (isolated / "traces" / "0123456789ab.jsonl").write_text(
        '{"ts": "2026-01-01T00:00:00+00:00", "run_id": "r", "event": "model", "step": 1}\n'
        '{"ts": "2026-01-01T00:00:02.5+00:00", "run_id": "r", "event": "stop",'
        ' "reason": "end_turn"}\n'
        '{"ts": "cut off',
        encoding="utf-8",
    )
    assert main(["trace", "0123456789ab"]) == 0
    out = capsys.readouterr().out
    assert "+   2.5s  stop" in out
    assert "(unreadable line)" in out


def test_trace_rejects_a_path_as_run_id(isolated: Path) -> None:
    assert main(["trace", "../x"]) == 2
