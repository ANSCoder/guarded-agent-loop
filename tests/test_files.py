from pathlib import Path

import pytest

from agent_runtime.tools.files import make_read_file, make_write_file


def test_read_refuses_the_env_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=x", encoding="utf-8")
    with pytest.raises(ValueError, match="secret"):
        make_read_file(tmp_path).run({"path": ".env"})


def test_env_check_ignores_case(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="secret"):
        make_read_file(tmp_path).run({"path": ".ENV"})


def test_read_refuses_dot_folders(tmp_path: Path) -> None:
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "id_rsa").write_text("key", encoding="utf-8")
    with pytest.raises(ValueError, match="secret"):
        make_read_file(tmp_path).run({"path": ".ssh/id_rsa"})


def test_write_cannot_escape_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    with pytest.raises(ValueError, match="outside"):
        make_write_file(workspace).run({"path": "../outside.txt", "content": "x"})
    assert not (tmp_path / "outside.txt").exists()


def test_write_cannot_touch_the_env_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="secret"):
        make_write_file(tmp_path).run({"path": ".env", "content": "x"})
