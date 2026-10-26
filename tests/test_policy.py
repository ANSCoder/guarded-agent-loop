from pathlib import Path

import pytest

from agent_runtime.harness.policy import Policy


def test_load_reads_actions(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text('[tools.a]\naction = "allow"\n[tools.b]\naction = "ask"\n')
    policy = Policy.load(path)
    assert (policy.decide("a"), policy.decide("b")) == ("allow", "ask")


def test_unknown_tool_is_denied() -> None:
    assert Policy({}).decide("anything") == "deny"


def test_bad_action_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text('[tools.a]\naction = "maybe"\n')
    with pytest.raises(ValueError, match="must set action"):
        Policy.load(path)


def test_row_that_is_not_a_table_gets_the_same_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text('[tools]\na = "allow"\n')
    with pytest.raises(ValueError, match="must set action"):
        Policy.load(path)
