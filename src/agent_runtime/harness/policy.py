"""Per-tool allow, ask or deny rules, read from config/policy.toml."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

ACTIONS = ("allow", "ask", "deny")


@dataclass(frozen=True)
class Policy:
    """The action for each tool name. A tool with no row is denied."""

    rules: dict[str, str]

    @classmethod
    def load(cls, path: Path) -> "Policy":
        """Read the [tools.<name>] tables. Any action other than allow, ask or deny is an error."""
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        rules: dict[str, str] = {}
        for name, row in data.get("tools", {}).items():
            action = row.get("action") if isinstance(row, dict) else None
            if action not in ACTIONS:
                raise ValueError(f"policy for {name!r} must set action to one of {ACTIONS}")
            rules[name] = action
        return cls(rules)

    def decide(self, tool: str) -> str:
        """Return allow, ask or deny for a tool. Unknown tools are denied."""
        # A new tool stays blocked until someone adds its policy row.
        return self.rules.get(tool, "deny")
