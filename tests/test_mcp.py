import sys
from pathlib import Path

import pytest

from agent_runtime.mcp import ServerSpec, load_servers, mcp_tools

ECHO = str(Path(__file__).parent / "fixtures" / "echo_server.py")


def test_server_tools_are_exposed_with_prefix() -> None:
    tools = mcp_tools([ServerSpec("demo", sys.executable, (ECHO,))])
    assert [t.name for t in tools] == ["demo__echo", "demo__fail"]
    assert tools[0].input_schema["properties"]["text"]["type"] == "string"


def test_server_tool_can_be_called() -> None:
    tool = mcp_tools([ServerSpec("demo", sys.executable, (ECHO,))])[0]
    assert tool.run({"text": "hello"}) == "hello"


def test_a_failing_server_tool_raises_its_error() -> None:
    tool = mcp_tools([ServerSpec("demo", sys.executable, (ECHO,))])[1]
    with pytest.raises(RuntimeError, match="boom"):
        tool.run({})


def test_load_servers_reads_config(tmp_path: Path) -> None:
    path = tmp_path / "mcp.toml"
    path.write_text('[servers.demo]\ncommand = "python3"\nargs = ["server.py"]\n')
    assert load_servers(path) == [ServerSpec("demo", "python3", ("server.py",))]


def test_broken_server_is_skipped_with_a_warning(capsys: pytest.CaptureFixture[str]) -> None:
    assert mcp_tools([ServerSpec("broken", "no-such-command-xyz", ())]) == []
    assert "broken" in capsys.readouterr().err


def test_server_without_a_command_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "mcp.toml"
    path.write_text("[servers.nocmd]\nargs = []\n")
    assert load_servers(path) == []
    assert "nocmd" in capsys.readouterr().err
